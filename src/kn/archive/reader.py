"""Integrity-checked reads from committed WARC members and blob descriptors."""

from datetime import timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from kn.archive.catalog import Located
from kn.archive.files import checked_path, copy_payload, file_info, open_regular, read_small
from kn.archive.inputs import prepare
from kn.archive.model import (
    MAX_DESCRIPTOR,
    ArchiveError,
    Capture,
    Entry,
    HttpExchange,
    Metadata,
    Redaction,
    decode_metadata,
)
from kn.archive.warc import read_member, verify_member


def read_metadata(located: Located) -> Metadata:
    entry = located.entry
    path = checked_path(located.directory, entry.metadata_path)
    if entry.metadata_member is None:
        raw = read_small(path, MAX_DESCRIPTOR)
        if len(raw) != entry.metadata.size or sha256(raw).hexdigest() != entry.metadata.sha256:
            raise ArchiveError("descriptor_digest")
        metadata = decode_metadata(raw)
    else:
        with open_regular(path) as stream:
            headers, raw = read_member(stream, entry.metadata_member, limit=2 * MAX_DESCRIPTOR)
        if len(raw) > MAX_DESCRIPTOR:
            raise ArchiveError("descriptor_size")
        metadata = decode_metadata(raw)
        verify_member(headers, raw, metadata, "metadata")
    _check_metadata(located, metadata)
    return metadata


def _check_metadata(located: Located, metadata: Metadata) -> None:
    entry = located.entry
    if (
        metadata.batch != located.batch
        or metadata.key != entry.key
        or metadata.record_id != entry.record_id
        or metadata.fetch_id != entry.fetch_id
        or metadata.payload_sha256 != entry.payload_sha256
        or metadata.revisit_of != entry.revisit_of
        or metadata.fetched_at != entry.fetched_at
        or metadata.fetched_at.utcoffset() != timedelta(0)
    ):
        raise ArchiveError("capture_manifest")
    _check_kind(entry, metadata)
    _check_http(metadata)


def _check_kind(entry: Entry, metadata: Metadata) -> None:
    if (metadata.http is None) != (metadata.status is None):
        raise ArchiveError("capture_http")
    expected = "blob"
    if entry.backend == "warc":
        if (entry.request_member is None) != (metadata.http is None):
            raise ArchiveError("warc_request_locator")
        expected = "resource" if metadata.http is None else "response"
        if metadata.revisit_of is not None:
            expected = "revisit"
    elif metadata.payload_size != entry.payload.size:
        raise ArchiveError("payload_size")
    if metadata.kind != expected:
        raise ArchiveError("capture_kind")


def _check_http(metadata: Metadata) -> None:
    # Reapply the default redaction and validation to persisted fields.
    http = metadata.http
    assert http is None or metadata.status is not None
    exchange = (
        None
        if http is None
        else HttpExchange(
            http.method,
            metadata.status or 0,
            http.request_headers,
            http.response_headers,
            http.protocol,
        )
    )
    candidate = Capture(
        key=metadata.key,
        origin_uri=metadata.origin_uri,
        fetched_at=metadata.fetched_at,
        body=BytesIO(),
        config_sha256=metadata.config_sha256,
        code_sha256=metadata.code_sha256,
        retention=metadata.retention,
        backend="blob" if metadata.kind == "blob" else "warc",
        mime_type=metadata.mime_type,
        http=exchange,
        revisit_of=metadata.revisit_of,
    )
    prepared = prepare(candidate, Redaction())
    if (prepared.origin_uri, prepared.mime_type) != (metadata.origin_uri, metadata.mime_type):
        raise ArchiveError("capture_redaction")
    if http is not None and (prepared.request_headers, prepared.response_headers) != (
        http.request_headers,
        http.response_headers,
    ):
        raise ArchiveError("capture_redaction")
    if metadata.request_sha256 is not None and metadata.request_sha256 != prepared.request_sha256:
        raise ArchiveError("capture_request_digest")


def check_revisit(metadata: Metadata, target: Metadata) -> None:
    if (
        target.kind != "response"
        or target.record_id != metadata.revisit_of
        or target.batch.parts()[:2] != metadata.batch.parts()[:2]
        or target.fetched_at > metadata.fetched_at
        or target.origin_uri != metadata.origin_uri
        or target.retention != metadata.retention
        or target.request_sha256 != metadata.request_sha256
        or metadata.request_sha256 is None
        or target.payload_sha256 != metadata.payload_sha256
        or target.payload_size != metadata.payload_size
    ):
        raise ArchiveError("revisit_target")


def replay_payload(
    located: Located, metadata: Metadata, output: BinaryIO | None, target: Metadata | None = None
) -> None:
    entry = located.entry
    path = checked_path(located.directory, entry.payload_path)
    if entry.payload_member is None:
        with open_regular(path) as stream:
            if copy_payload(stream, None, limit=entry.payload.size) != entry.payload:
                raise ArchiveError("payload_digest")
            if output is not None:
                stream.seek(0)
                copy_payload(stream, output, limit=entry.payload.size)
        return
    with open_regular(path) as stream:
        if copy_payload(stream, None, limit=entry.payload.size) != entry.payload:
            raise ArchiveError("warc_object_digest")
        fields, block = read_member(stream, entry.payload_member)
        payload = verify_member(fields, block, metadata, metadata.kind, target)
        if entry.request_member is not None:
            fields, block = read_member(stream, entry.request_member, limit=MAX_DESCRIPTOR)
            verify_member(fields, block, metadata, "request")
    if output is not None:
        output.write(payload)


def verify_remaining_objects(located: Located, *, removal_recorded: bool) -> None:
    """Validate surviving bytes of a withdrawn capture after an interrupted purge."""
    entry = located.entry
    for path, info in {
        entry.payload_path: entry.payload,
        entry.metadata_path: entry.metadata,
    }.items():
        candidate = checked_path(located.directory, path)
        if (candidate.exists() or not removal_recorded) and file_info(candidate, info.size) != info:
            raise ArchiveError("withdrawn_object_digest")
    if checked_path(located.directory, entry.metadata_path).exists():
        read_metadata(located)


def verify_directory(located: Located) -> None:
    folder = checked_path(located.directory, located.entry.payload_path).parent
    expected = {Path(path).name for path in located.objects()}
    if folder.exists() and {file.name for file in folder.iterdir()} - expected:
        raise ArchiveError("unexpected_object")
