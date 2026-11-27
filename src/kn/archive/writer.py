"""Stage captures and commit immutable manifests and objects together."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from kn.archive.catalog import MANIFEST_NAME, Catalog, batch_directory, read_manifest
from kn.archive.files import (
    check_directories,
    copy_payload,
    decoded_size,
    file_info,
    publish,
    reclaim_staging,
    source_lock,
    source_staging,
    staging,
    sync_directory,
    sync_file,
    sync_publication,
    synced_write,
)
from kn.archive.inputs import prepare
from kn.archive.model import (
    MAX_CAPTURES,
    MAX_DESCRIPTOR,
    MAX_WARC_BODY,
    MAX_WARC_MEMBER,
    ArchiveError,
    BatchKey,
    Capture,
    Entry,
    HttpMetadata,
    Limits,
    Manifest,
    Member,
    Metadata,
    Redaction,
    encode,
    object_paths,
    record_directory,
    stable_id,
)
from kn.archive.reader import check_revisit, read_metadata, replay_payload
from kn.archive.warc import write_warc


@dataclass(frozen=True, slots=True)
class _Commit:
    batch: BatchKey
    limits: Limits
    redaction: Redaction
    catalog: Catalog | None


def commit(
    root: Path, batch: BatchKey, captures: Iterable[Capture], limits: Limits, redaction: Redaction
) -> Manifest:
    domain, source, *_ = batch.parts()
    destination = batch_directory(root, batch)
    with source_lock(root, domain, source):
        check_directories(root, destination)
        # Batch keys are caller-provided idempotency keys. Retry does not consume input streams.
        if destination.exists():
            sync_publication(destination, root)
            return read_manifest(destination, root)
        if limits.max_payload_bytes < 0 or limits.max_decoded_bytes < 0:
            raise ArchiveError("archive_limits")
        scope = source_staging(domain, source)
        reclaim_staging(root, *scope)
        with staging(root, *scope) as staged:
            manifest = _stage(root, staged, batch, captures, limits, redaction)
            publish(staged, destination, root)
            return manifest


def _stage(
    root: Path,
    staged: Path,
    batch: BatchKey,
    captures: Iterable[Capture],
    limits: Limits,
    redaction: Redaction,
) -> Manifest:
    entries: dict[str, Entry] = {}
    catalog = None
    for capture in captures:
        if capture.key in entries or len(entries) == MAX_CAPTURES:
            raise ArchiveError("batch_capture_count_or_key")
        if capture.revisit_of is not None and catalog is None:
            # A revisit target belongs to the same source, so other sources are never read.
            catalog = Catalog.load(root, domain=batch.domain, source_id=batch.source_id)
        options = _Commit(batch, limits, redaction, catalog)
        entries[capture.key] = _stage_capture(staged, capture, options)
    if not entries:
        raise ArchiveError("empty_batch")
    dates = [entry.fetched_at for entry in entries.values()]
    manifest = Manifest(
        version=1,
        batch=batch,
        first_capture_at=min(dates),
        last_capture_at=max(dates),
        captures=tuple(entries.values()),
    )
    synced_write(staged / MANIFEST_NAME, encode(manifest))
    sync_directory(staged)
    return manifest


def _stage_capture(staged: Path, capture: Capture, options: _Commit) -> Entry:
    prepared = prepare(capture, options.redaction)
    record_id = stable_id(options.batch, capture.key, "record")
    folder = staged / record_directory(record_id)
    folder.mkdir()
    pending = folder / "body.pending"
    limit = options.limits.max_payload_bytes
    if capture.backend == "warc":
        limit = min(limit, MAX_WARC_BODY)
    with pending.open("x+b") as body:
        payload = copy_payload(capture.body, body, limit=limit)
        expanded_size = (
            decoded_size(body, prepared.encoding, options.limits.max_decoded_bytes)
            if payload.size
            else 0
        )
        http = capture.http
        metadata = Metadata(
            key=capture.key,
            batch=options.batch,
            record_id=record_id,
            fetch_id=stable_id(options.batch, capture.key, "fetch"),
            origin_uri=prepared.origin_uri,
            fetched_at=prepared.fetched_at,
            kind=prepared.kind,
            status=http.status if http else None,
            mime_type=prepared.mime_type,
            payload_sha256=payload.sha256,
            payload_size=payload.size,
            config_sha256=capture.config_sha256,
            code_sha256=capture.code_sha256,
            retention=capture.retention,
            http=HttpMetadata(
                method=http.method,
                protocol=http.protocol,
                request_headers=prepared.request_headers,
                response_headers=prepared.response_headers,
            )
            if http
            else None,
            request_sha256=prepared.request_sha256,
            revisit_of=capture.revisit_of,
            decoded_size=expanded_size,
        )
        paths = object_paths(record_id, capture.backend, payload.sha256)
        payload_path, metadata_path = (staged / path for path in paths)
        descriptor = encode(metadata)
        if len(descriptor) > MAX_DESCRIPTOR:
            raise ArchiveError("descriptor_size")
        members: tuple[Member | None, Member | None, Member | None] = (None, None, None)
        if capture.backend == "blob":
            sync_file(body)
        else:
            target = _revisit_target(options.catalog, metadata)
            with payload_path.open("xb") as stream:
                members = write_warc(stream, metadata, descriptor, body, target)
                sync_file(stream)
    if capture.backend == "blob":
        pending.rename(payload_path)
        synced_write(metadata_path, descriptor)
    else:
        pending.unlink()
        payload = file_info(payload_path, MAX_WARC_MEMBER)
    meta_info = payload if capture.backend == "warc" else file_info(metadata_path, MAX_DESCRIPTOR)
    sync_directory(folder)
    return Entry(
        key=metadata.key,
        record_id=metadata.record_id,
        fetch_id=metadata.fetch_id,
        backend=capture.backend,
        payload_path=paths[0],
        metadata_path=paths[1],
        payload=payload,
        metadata=meta_info,
        payload_member=members[0],
        metadata_member=members[1],
        request_member=members[2],
        revisit_of=metadata.revisit_of,
        payload_sha256=metadata.payload_sha256,
        fetched_at=metadata.fetched_at,
    )


def _revisit_target(catalog: Catalog | None, metadata: Metadata) -> Metadata | None:
    if metadata.revisit_of is None:
        return None
    assert catalog is not None
    located = catalog.records.get(metadata.revisit_of)
    if located is None or catalog.withdrawn(located.entry):
        raise ArchiveError("revisit_target")
    target = read_metadata(located)
    check_revisit(metadata, target)
    replay_payload(located, target, None)
    return target
