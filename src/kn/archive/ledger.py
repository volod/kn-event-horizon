"""Derived, recoverable fetch coverage and Parquet metadata queries."""

from collections import defaultdict
from collections.abc import Generator, Iterator
from contextlib import closing
from datetime import UTC
from heapq import merge
from itertools import groupby
from pathlib import Path

from kn.archive.catalog import Catalog, Located, is_withdrawn
from kn.archive.config import archive_root, check_roots, index_root, resolve_archive_path
from kn.archive.files import (
    check_directories,
    exclusive_lock,
    mkdirs,
    reclaim_staging,
    staging,
    sync_directory,
)
from kn.archive.ledger_model import (
    CaptureScope,
    CoverageRow,
    LedgerCoverage,
    LedgerRow,
    PartitionKey,
    ledger_row,
)
from kn.archive.ledger_parquet import find_batch, read_record_ids, read_rows, write_rows
from kn.archive.ledger_views import (
    Partition,
    Snapshot,
    load_snapshot,
    pin_snapshot,
    publish_snapshot,
)
from kn.archive.model import ArchiveError, BatchKey
from kn.archive.reader import check_payload_locator, read_metadata

_ALL = CaptureScope()


class FetchLedger:
    def __init__(self, archive: Path, index: Path) -> None:
        self.archive = resolve_archive_path(archive)
        self.root = resolve_archive_path(index)
        check_roots(self.archive, self.root)

    @classmethod
    def configured(cls, project_root: Path | None = None) -> "FetchLedger":
        index = index_root(project_root)
        assert index is not None
        return cls(archive_root(project_root), index)

    def reindex(self, scope: CaptureScope = _ALL) -> LedgerCoverage:
        self._require_archive()
        try:
            with exclusive_lock(self.root / "reindex.lock"):
                reclaim_staging(self.root)
                return self._reindex(scope)
        except OSError:
            raise ArchiveError("index_io") from None

    def _reindex(self, scope: CaptureScope) -> LedgerCoverage:
        with staging(self.root) as view:
            previous = None if scope.is_full() else load_snapshot(self.root)
            catalog = Catalog.load(
                self.archive, domain=scope.effective_domain, source_id=scope.source_id
            )
            self._check_retained(previous, catalog, scope)
            groups = _group(catalog, scope)
            partitions = self._build(view, previous, groups, catalog, scope)
            return publish_snapshot(self.root, view, partitions).coverage()

    def coverage(self) -> LedgerCoverage | None:
        """Counts at publication time. A missing view has no coverage."""
        with pin_snapshot(self.root) as snapshot:
            return None if snapshot is None else snapshot.coverage()

    def covered(self, scope: CaptureScope = _ALL) -> Generator[CoverageRow]:
        """Committed input receipts, including captures suppressed at publication."""
        with closing(self._rows(scope)) as rows:
            for row in rows:
                yield CoverageRow.model_validate(row.model_dump(exclude={"capture"}))

    def query(self, scope: CaptureScope = _ALL) -> Generator[LedgerRow]:
        """Retained rows in the published coverage, in archive replay order."""
        self._require_archive()
        with closing(self._rows(scope)) as rows:
            for row in rows:
                if row.capture is not None and not is_withdrawn(
                    self.archive, row.record_id, row.revisit_of
                ):
                    yield row

    def locate_batch(self, identifier: str) -> BatchKey | None:
        """Find the published batch hint for an ID, subject to archive validation."""
        with pin_snapshot(self.root) as snapshot:
            if snapshot is not None:
                view = snapshot.location(self.root)
                for part in reversed(snapshot.partitions):
                    if batch := find_batch(_partition_path(part, view), identifier):
                        return batch
        return None

    def _rows(self, scope: CaptureScope) -> Generator[LedgerRow]:
        with pin_snapshot(self.root) as snapshot:
            if snapshot is None:
                return
            view = snapshot.location(self.root)
            # Keep only a day's partitions open at once and globally merge their replay order.
            for parts in _by_day(snapshot, scope):
                streams = (read_rows(_partition_path(part, view), part, scope) for part in parts)
                yield from merge(*streams, key=LedgerRow.order)

    def _build(
        self,
        view: Path,
        previous: Snapshot | None,
        groups: dict[PartitionKey, list[Located]],
        catalog: Catalog,
        scope: CaptureScope,
    ) -> list[Partition]:
        existing = (
            {}
            if previous is None
            else {
                PartitionKey(domain=part.domain, source_id=part.source_id, day=part.day): part
                for part in previous.partitions
            }
        )
        partitions = []
        for key in sorted(groups.keys() | existing.keys(), key=PartitionKey.order):
            path = key.path(view)
            prior = existing.get(key)
            if prior is not None and previous is not None:
                previous_path = _partition_path(key, previous.location(self.root))
                if not key.overlaps(scope):
                    _link(previous_path, path)
                    partitions.append(prior)
                    continue
                carryover = read_rows(previous_path, key, scope, outside=True)
            else:
                carryover = iter(())
            replacements = (self._project(located, catalog) for located in groups.get(key, ()))
            total, retained = write_rows(path, merge(carryover, replacements, key=LedgerRow.order))
            if total:
                partitions.append(
                    Partition(
                        **key.model_dump(), covered_captures=total, published_retained=retained
                    )
                )
        return partitions

    def _check_retained(
        self, previous: Snapshot | None, catalog: Catalog, scope: CaptureScope
    ) -> None:
        """Refuse to drop a covered capture that the archive lost without a tombstone."""
        try:
            snapshot = previous if previous is not None else load_snapshot(self.root)
            covered = set() if snapshot is None else set(self._covered_ids(snapshot, scope))
        except ArchiveError:
            if previous is not None:
                raise
            return  # A full rebuild replaces a damaged view, which cannot vouch for coverage.
        if covered - catalog.records.keys() - catalog.tombstones.keys():
            raise ArchiveError("capture_lost")

    def _covered_ids(self, snapshot: Snapshot, scope: CaptureScope) -> Iterator[str]:
        view = snapshot.location(self.root)
        for part in snapshot.partitions:
            if part.overlaps(scope):
                yield from read_record_ids(_partition_path(part, view), scope)

    def _project(self, located: Located, catalog: Catalog) -> LedgerRow:
        entry = located.entry
        target = catalog.target(located)
        withdrawn_by = entry.record_id if entry.record_id in catalog.tombstones else None
        if withdrawn_by is None:
            check_payload_locator(located)
            if entry.revisit_of in catalog.tombstones:
                withdrawn_by = entry.revisit_of
            elif target is not None:
                check_payload_locator(target)
        metadata = read_metadata(located) if withdrawn_by is None else None
        return ledger_row(self.archive, located, metadata, withdrawn_by)

    def _require_archive(self) -> None:
        if not self.archive.is_dir():
            raise ArchiveError("archive_root_unavailable")


def _group(catalog: Catalog, scope: CaptureScope) -> dict[PartitionKey, list[Located]]:
    groups: defaultdict[PartitionKey, list[Located]] = defaultdict(list)
    for located in catalog.records.values():
        fetched_at = located.entry.fetched_at
        if scope.contains(fetched_at):
            key = PartitionKey(
                domain=located.batch.domain,
                source_id=located.batch.source_id,
                day=fetched_at.astimezone(UTC).date(),
            )
            groups[key].append(located)
    for group in groups.values():
        group.sort(key=lambda item: (item.entry.fetched_at, item.entry.fetch_id))
    return dict(groups)


def _by_day(snapshot: Snapshot, scope: CaptureScope) -> Iterator[list[Partition]]:
    for _, grouped in groupby(snapshot.partitions, key=lambda part: part.day):
        parts = [part for part in grouped if part.overlaps(scope)]
        if parts:
            yield parts


def _partition_path(key: PartitionKey, view: Path) -> Path:
    path = key.path(view)
    check_directories(view, path.parent)
    if path.is_symlink() or not path.is_file():
        raise ArchiveError("index_partition")
    return path


def _link(previous: Path, path: Path) -> None:
    mkdirs(path.parent)
    path.hardlink_to(previous)
    sync_directory(path.parent)
