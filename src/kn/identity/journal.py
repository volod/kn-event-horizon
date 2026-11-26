"""Locked, fsynced, append-only local identity log. SQL is a disposable projection."""

import fcntl
import os
import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from kn.contracts.model import canonical
from kn.identity.events import Event, event
from kn.identity.model import Mint, SourceKey
from kn.identity.state import PENDING_MATCH, ChangedRows, State, record_key, replay
from kn.review.journal import _sync_directory
from kn.review.model import Instant

JOURNAL_NAME = "events-v1.jsonl"
UUID_RANDOM_BITS = 74
INTERRUPTED = "reopen the identity journal after an interrupted append"
type Stamp = tuple[int, int, int, int, int]


def _stamp(stream: BinaryIO) -> Stamp:
    info = os.fstat(stream.fileno())
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _load(stream: BinaryIO) -> State:
    def entries() -> Iterator[Event]:
        for line in stream:
            if not line.endswith(b"\n"):
                raise ValueError("incomplete identity journal; restore before appending")
            yield Event.model_validate_json(line)

    return replay(entries())


class LockedJournal:
    def __init__(
        self, stream: BinaryIO, data_dir: Path, cached: tuple[Stamp, State] | None = None
    ) -> None:
        self.stream = stream
        self.data_dir = data_dir
        self.stamp: Stamp | None = _stamp(stream)
        self._state = cached[1] if cached is not None and cached[0] == self.stamp else _load(stream)
        self.initial_sequence = len(self.state.events)
        self.state.dirty = ChangedRows()

    @property
    def state(self) -> State:
        if self.stamp is None:
            raise ValueError(INTERRUPTED)
        return self._state

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self.state.events)

    @property
    def head(self) -> Event | None:
        return self.state.events[-1] if self.state.events else None

    def append(self, value: Event, *, before_write: Callable[[], None] | None = None) -> bool:
        # Pydantic model_copy/model_construct can bypass even frozen-model validation.
        value = Event.model_validate_json(canonical(value.model_dump(mode="json")))
        if value.sequence <= len(self.state.events):
            if self.state.events[value.sequence - 1] == value:
                return False
            raise ValueError("identity event sequence already contains different content")
        if self.state.pending_match() is not None:
            # Only the match retry may finish its recorded follow-up events.
            raise ValueError(PENDING_MATCH)
        self._extend((value,), before_write=before_write)
        return True

    def append_batch(self, values: tuple[Event, ...]) -> None:
        """Append a validated batch: a match decision with its follow-ups, or a tracked version.

        Callers check for a pending match first and own the order of their events.
        """
        if values:
            self._extend(
                tuple(Event.model_validate_json(item.model_dump_json()) for item in values)
            )

    def _extend(
        self, values: tuple[Event, ...], *, before_write: Callable[[], None] | None = None
    ) -> None:
        if self.stream.closed:
            raise ValueError(INTERRUPTED)
        length = len(self.state.events)
        encoded = "".join(canonical(value.model_dump(mode="json")) + "\n" for value in values)
        try:
            for value in values:
                self.state.apply(value)
            if before_write is not None:
                before_write()
        except BaseException:
            # A refused batch may have applied part of its suffix to the in-memory state.
            self._state = replay(self.state.events[:length], track_after=self.initial_sequence)
            if self.state.dirty is None:
                self.state.dirty = ChangedRows()
            raise
        self.stamp = None
        self._write(encoded.encode("ascii"))
        self.stamp = _stamp(self.stream)

    def _write(self, encoded: bytes) -> None:
        self.stream.seek(0, os.SEEK_END)
        self.stream.write(encoded)
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def mint(
        self,
        anchor: SourceKey,
        entity_class: str,
        *,
        occurred_at: Instant,
        actor: str,
        reason: str,
        evidence: str,
    ) -> str:
        known = self.state.anchors.get(record_key(anchor))
        existing = self.state.objects[known] if known is not None else None
        if existing is not None:
            if existing.entity_class != entity_class:
                raise ValueError("anchor already minted a different entity class")
            return existing.kn_id
        kn_id = new_id(occurred_at)
        self.append(
            event(
                Mint(kn_id=kn_id, entity_class=entity_class, anchor=anchor),
                previous=self.head,
                occurred_at=occurred_at,
                actor=actor,
                reason=reason,
                evidence=evidence,
            )
        )
        return kn_id


def new_id(occurred_at: Instant) -> str:
    milliseconds = int(occurred_at.timestamp() * 1000)
    if not 0 <= milliseconds < 2**48:
        raise ValueError("UUIDv7 timestamp outside 48-bit range")
    random = secrets.randbits(UUID_RANDOM_BITS)
    bits = (milliseconds << 80) | (7 << 76) | ((random >> 62) << 64)
    bits |= (2 << 62) | (random & ((1 << 62) - 1))
    return f"kn:{UUID(int=bits)}"


class Journal:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.path = data_dir / "identity" / JOURNAL_NAME
        self._cached: tuple[Stamp, State] | None = None

    @contextmanager
    def locked(self, *, reuse: bool = True) -> Iterator[LockedJournal]:
        self._check_path()
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "r+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            _sync_directory(directory)
            _sync_directory(directory.parent)
            cached, self._cached = self._cached, None
            locked = LockedJournal(stream, self.data_dir, cached if reuse else None)
            try:
                yield locked
            finally:
                if locked.stamp is not None:
                    locked.state.dirty = None
                    if reuse:
                        self._cached = locked.stamp, locked.state

    def _check_path(self) -> None:
        if any(part.is_symlink() for part in (self.path, *self.path.parents)):
            raise ValueError("identity journal path must not contain symlinks")

    def read(self) -> tuple[Event, ...]:
        with self.locked() as journal:
            return journal.events

    def append(self, value: Event) -> bool:
        with self.locked() as journal:
            return journal.append(value)

    def state(self) -> State:
        self._check_path()
        try:
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return State()
        with os.fdopen(descriptor, "rb") as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            return _load(stream)
