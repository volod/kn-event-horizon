"""Capture, metadata lookup, replay, verification and withdrawal."""

from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import BinaryIO

from kn.archive.catalog import (
    MANIFEST_NAME,
    Catalog,
    Located,
    batch_directory,
    check_reference,
    is_withdrawn,
    read_manifest,
)
from kn.archive.config import archive_root, check_roots, index_root, resolve_archive_path
from kn.archive.files import check_directories
from kn.archive.model import (
    ArchiveError,
    BatchKey,
    Capture,
    Limits,
    Manifest,
    Metadata,
    Redaction,
    Tombstone,
)
from kn.archive.reader import (
    check_revisit,
    read_metadata,
    replay_payload,
    verify_directory,
    verify_remaining_objects,
)
from kn.archive.retention import withdraw
from kn.archive.writer import commit

_DEFAULT_REDACTION = Redaction()


class Archive:
    def __init__(self, root: Path, *, index_root: Path | None = None) -> None:
        self.root = resolve_archive_path(root)
        self.index_root = None if index_root is None else resolve_archive_path(index_root)
        if self.index_root is not None:
            check_roots(self.root, self.index_root)

    @classmethod
    def configured(cls, project_root: Path | None = None, *, use_index: bool = True) -> "Archive":
        root = archive_root(project_root)
        return cls(root, index_root=index_root(project_root, required=False) if use_index else None)

    def commit(
        self,
        batch: BatchKey,
        captures: Iterable[Capture],
        *,
        limits: Limits,
        redaction: Redaction = _DEFAULT_REDACTION,
    ) -> Manifest:
        return commit(self.root, batch, captures, limits, redaction)

    def metadata(self, identifier: str) -> Metadata:
        return read_metadata(self._resolve(identifier, self._catalog))

    def iter_metadata(self) -> Iterator[Metadata]:
        catalog = self._catalog()
        ordered = sorted(
            catalog.records.values(), key=lambda row: (row.entry.fetched_at, row.entry.fetch_id)
        )
        for located in ordered:
            if not catalog.withdrawn(located.entry):
                yield read_metadata(located)

    def replay(self, identifier: str, output: BinaryIO) -> Metadata:
        catalog = cache(self._catalog)
        located = self._resolve(identifier, catalog)
        metadata = read_metadata(located)
        target = self._target(located, catalog)
        _replay(located, metadata, output, target)
        return metadata

    def verify(self) -> dict[str, object]:
        catalog = self._catalog()
        directories: dict[Path, set[str]] = {}
        retained = 0
        for located in catalog.records.values():
            verify_directory(located)
            directories.setdefault(located.directory, {MANIFEST_NAME}).add(
                located.entry.payload_path.partition("/")[0]
            )
            target = catalog.target(located)
            if catalog.withdrawn(located.entry):
                verify_remaining_objects(
                    located, removal_recorded=located.entry.record_id in catalog.tombstones
                )
            else:
                _replay(located, read_metadata(located), None, target)
                retained += 1
        for directory, expected in directories.items():
            if {path.name for path in directory.iterdir()} - expected:
                raise ArchiveError("unexpected_object")
        return {
            "batches": catalog.batches,
            "captures": retained,
            "tombstones": len(catalog.tombstones),
            "status": "verified",
        }

    def withdraw(
        self, identifier: str, reason: str, withdrawn_at: datetime, *, purge: bool = False
    ) -> tuple[Tombstone, ...]:
        hint = self._index_hint(identifier)
        batch = None if hint is None else hint.batch
        return withdraw(self.root, identifier, reason, withdrawn_at, purge=purge, batch=batch)

    def _catalog(self) -> Catalog:
        if not self.root.is_dir():
            raise ArchiveError("archive_root_unavailable")
        return Catalog.load(self.root)

    def _resolve(self, identifier: str, load_catalog: Callable[[], Catalog]) -> Located:
        located = self._index_hint(identifier)
        if located is None:
            catalog = load_catalog()
            located = catalog.lookup(identifier)
            withdrawn = catalog.withdrawn(located.entry)
        else:
            withdrawn = is_withdrawn(self.root, located.entry.record_id, located.entry.revisit_of)
        if withdrawn:
            raise ArchiveError("capture_tombstoned")
        return located

    def _index_hint(self, identifier: str) -> Located | None:
        if self.index_root is None:
            return None
        from kn.archive.ledger import FetchLedger

        try:
            batch = FetchLedger(self.root, self.index_root).locate_batch(identifier)
            if batch is None:
                return None
            directory = batch_directory(self.root, batch)
            check_directories(self.root, directory)
            manifest = read_manifest(directory, self.root)
        except (ArchiveError, OSError):
            return None
        for entry in manifest.captures:
            if identifier in (entry.record_id, entry.fetch_id):
                return Located(batch, directory, entry)
        return None

    def _target(self, located: Located, load_catalog: Callable[[], Catalog]) -> Located | None:
        if located.entry.revisit_of is None:
            return None
        try:
            target = self._resolve(located.entry.revisit_of, load_catalog)
        except ArchiveError as error:
            if error.code == "capture_not_found":
                raise ArchiveError("revisit_target") from None
            raise
        return check_reference(located, target)


def _replay(
    located: Located, metadata: Metadata, output: BinaryIO | None, target: Located | None
) -> None:
    if target is None:
        replay_payload(located, metadata, output)
        return
    previous = read_metadata(target)
    check_revisit(metadata, previous)
    replay_payload(located, metadata, None, previous)
    replay_payload(target, previous, output)
