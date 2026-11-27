"""Archive-only capture, metadata lookup, replay, verification and withdrawal."""

from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from kn.archive.catalog import MANIFEST_NAME, Catalog, Located
from kn.archive.config import archive_root, resolve_archive_path
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
    def __init__(self, root: Path) -> None:
        self.root = resolve_archive_path(root)

    @classmethod
    def configured(cls, project_root: Path | None = None) -> "Archive":
        return cls(archive_root(project_root))

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
        catalog = self._catalog()
        return read_metadata(_retained(catalog, identifier))

    def iter_metadata(self) -> Iterator[Metadata]:
        catalog = self._catalog()
        ordered = sorted(
            catalog.records.values(), key=lambda row: (row.entry.fetched_at, row.entry.fetch_id)
        )
        for located in ordered:
            if not catalog.withdrawn(located.entry):
                yield read_metadata(located)

    def replay(self, identifier: str, output: BinaryIO) -> Metadata:
        catalog = self._catalog()
        located = _retained(catalog, identifier)
        metadata = read_metadata(located)
        _replay(catalog, located, metadata, output)
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
            if catalog.withdrawn(located.entry):
                verify_remaining_objects(
                    located, removal_recorded=located.entry.record_id in catalog.tombstones
                )
                _check_reference(catalog, located)
            else:
                _replay(catalog, located, read_metadata(located), None)
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
        return withdraw(self.root, identifier, reason, withdrawn_at, purge=purge)

    def _catalog(self) -> Catalog:
        if not self.root.is_dir():
            raise ArchiveError("archive_root_unavailable")
        return Catalog.load(self.root)


def _retained(catalog: Catalog, identifier: str) -> Located:
    located = catalog.lookup(identifier)
    if catalog.withdrawn(located.entry):
        raise ArchiveError("capture_tombstoned")
    return located


def _check_reference(catalog: Catalog, located: Located) -> Located | None:
    reference = located.entry.revisit_of
    if reference is None:
        return None
    target = catalog.records.get(reference)
    if (
        target is None
        or target.entry.revisit_of is not None
        or target.entry.backend != "warc"
        or target.batch.parts()[:2] != located.batch.parts()[:2]
        or target.entry.fetched_at > located.entry.fetched_at
        or target.entry.payload_sha256 != located.entry.payload_sha256
    ):
        raise ArchiveError("revisit_target")
    return target


def _replay(
    catalog: Catalog, located: Located, metadata: Metadata, output: BinaryIO | None
) -> None:
    target = _check_reference(catalog, located)
    if target is None:
        replay_payload(located, metadata, output)
        return
    previous = read_metadata(_retained(catalog, target.entry.record_id))
    check_revisit(metadata, previous)
    replay_payload(located, metadata, None, previous)
    replay_payload(target, previous, output)
