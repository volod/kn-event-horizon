"""Durable logical withdrawals with optional deletion of isolated objects."""

from datetime import UTC, datetime
from pathlib import Path

from kn.archive.catalog import Catalog, Located, tombstone_path
from kn.archive.files import (
    checked_path,
    publish,
    reclaim_staging,
    source_lock,
    source_staging,
    staging,
    sync_directory,
    synced_write,
)
from kn.archive.inputs import valid_key
from kn.archive.model import ArchiveError, BatchKey, Tombstone, encode


def withdraw(
    root: Path,
    identifier: str,
    reason: str,
    withdrawn_at: datetime,
    *,
    purge: bool,
    batch: BatchKey | None = None,
) -> tuple[Tombstone, ...]:
    """Withdraw a capture and its revisits; `batch` is an index hint that avoids a full scan."""
    if not valid_key(reason) or withdrawn_at.utcoffset() is None:
        raise ArchiveError("withdrawal_input")
    if batch is None:
        batch = Catalog.load(root).lookup(identifier).batch
    domain, source, *_ = batch.parts()
    with source_lock(root, domain, source):
        # Revisits of a capture belong to its source, so other sources are never read.
        catalog = Catalog.load(root, domain=domain, source_id=source)
        reclaim_staging(root, *source_staging(domain, source))
        affected = _affected(catalog, identifier)
        stones = tuple(
            _persist(root, catalog, located, reason, withdrawn_at.astimezone(UTC))
            for located in affected
        )
        if purge:
            for located in affected:
                _purge(located)
        return stones


def _affected(catalog: Catalog, identifier: str) -> tuple[Located, ...]:
    target = catalog.lookup(identifier)
    target_id = target.entry.record_id
    dependents = tuple(
        candidate
        for candidate in catalog.records.values()
        if candidate.entry.revisit_of == target_id
    )
    return (target, *dependents)


def _persist(
    root: Path, catalog: Catalog, located: Located, reason: str, withdrawn_at: datetime
) -> Tombstone:
    identifier = located.entry.record_id
    destination = tombstone_path(root, identifier)
    if existing := catalog.tombstones.get(identifier):
        sync_directory(destination.parent)
        return existing
    stone = Tombstone(
        version=1,
        record_id=identifier,
        payload_sha256=located.entry.payload_sha256,
        batch=located.batch,
        objects=located.objects(),
        reason=reason,
        withdrawn_at=withdrawn_at,
    )
    with staging(root, *source_staging(*located.batch.parts()[:2])) as staged:
        pending = staged / destination.name
        synced_write(pending, encode(stone))
        publish(pending, destination, root)
    return stone


def _purge(located: Located) -> None:
    for relative in located.objects():
        path = checked_path(located.directory, relative)
        if path.parent.is_dir():
            path.unlink(missing_ok=True)
            sync_directory(path.parent)
