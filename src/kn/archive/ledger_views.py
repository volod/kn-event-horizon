"""Publish and pin complete generations of the derived Parquet view."""

import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, flock
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from pydantic import Field, model_validator

from kn.archive.files import mkdirs, open_regular, publish, staging, sync_directory, synced_write
from kn.archive.ledger_model import LedgerCoverage, PartitionKey
from kn.archive.model import ArchiveError, ByteCount, Document, VersionOne, decode, encode

_POINTER = "CURRENT"
_READERS = "readers.lock"
_VIEWS = "views"
_GENERATION = r"^[0-9a-f]{32}$"
_MANAGED_VIEW = re.compile(_GENERATION)


class Partition(PartitionKey):
    covered_captures: Annotated[int, Field(gt=0)]
    published_retained: ByteCount

    @model_validator(mode="after")
    def check_counts(self) -> "Partition":
        if self.published_retained > self.covered_captures:
            raise ArchiveError("index_coverage")
        return self


class Snapshot(Document):
    version: VersionOne = 1
    generation: Annotated[str, Field(pattern=_GENERATION)]
    partitions: tuple[Partition, ...]

    @model_validator(mode="after")
    def check_partitions(self) -> "Snapshot":
        keys = [partition.order() for partition in self.partitions]
        if keys != sorted(set(keys)):
            raise ArchiveError("index_partitions")
        return self

    def location(self, root: Path) -> Path:
        return root / _VIEWS / self.generation

    def coverage(self) -> LedgerCoverage:
        return LedgerCoverage(
            partitions=len(self.partitions),
            covered_captures=sum(part.covered_captures for part in self.partitions),
            published_retained=sum(part.published_retained for part in self.partitions),
        )


def load_snapshot(root: Path) -> Snapshot | None:
    pointer = root / _POINTER
    if not pointer.exists() and not pointer.is_symlink():
        return None
    with open_regular(pointer) as stream:
        snapshot = decode(Snapshot, stream.read(), "index_snapshot")
    location = snapshot.location(root)
    if location.parent.is_symlink() or location.is_symlink() or not location.is_dir():
        raise ArchiveError("index_snapshot")
    return snapshot


@contextmanager
def pin_snapshot(root: Path) -> Iterator[Snapshot | None]:
    pointer = root / _POINTER
    if not pointer.exists() and not pointer.is_symlink():
        yield None
        return
    with open_regular(root / _READERS) as readers:
        flock(readers, LOCK_SH)
        yield load_snapshot(root)


def publish_snapshot(root: Path, view: Path, partitions: list[Partition]) -> Snapshot:
    snapshot = Snapshot(generation=uuid4().hex, partitions=tuple(partitions))
    readers = root / _READERS
    if not readers.exists() and not readers.is_symlink():
        synced_write(readers, b"")
    with open_regular(readers):
        pass
    mkdirs(root / _VIEWS)
    with staging(root) as pending:
        pointer = pending / _POINTER
        synced_write(pointer, encode(snapshot))
        sync_directory(view)
        publish(view, snapshot.location(root), root)
        replace_pointer(pointer, root / _POINTER)
        try:
            sync_directory(root)
        except OSError:
            raise ArchiveError("index_publication_uncertain") from None
    _prune(root, snapshot, readers)
    return snapshot


def replace_pointer(pending: Path, current: Path) -> None:
    pending.replace(current)


def _prune(root: Path, snapshot: Snapshot, lock: Path) -> None:
    try:
        with open_regular(lock) as readers:
            flock(readers, LOCK_EX | LOCK_NB)
            for path in (root / _VIEWS).iterdir():
                if path.name != snapshot.generation and _MANAGED_VIEW.fullmatch(path.name):
                    shutil.rmtree(path, ignore_errors=True)
    except (OSError, ArchiveError):
        # A pinned reader or a cleanup error can defer reclamation to the next publication.
        return
