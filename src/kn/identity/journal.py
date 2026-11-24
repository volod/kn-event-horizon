"""Locked, fsynced, append-only local identity log. SQL is a disposable projection."""

import fcntl
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from kn.contracts.model import canonical
from kn.identity.events import Event, event
from kn.identity.model import Mint, SourceKey
from kn.identity.state import State, replay
from kn.review.journal import _sync_directory
from kn.review.model import Instant

JOURNAL_NAME = "events-v1.jsonl"
UUID_RANDOM_BITS = 74


class LockedJournal:
    def __init__(self, stream: BinaryIO, data_dir: Path) -> None:
        self.stream = stream
        self.data_dir = data_dir
        content = stream.read()
        if content and not content.endswith(b"\n"):
            raise ValueError("incomplete identity journal; restore before appending")
        self.events = tuple(Event.model_validate_json(line) for line in content.splitlines())
        self.state = replay(self.events)

    def append(self, value: Event) -> bool:
        # Pydantic model_copy/model_construct can bypass even frozen-model validation.
        value = Event.model_validate_json(canonical(value.model_dump(mode="json")))
        if value.sequence <= len(self.events):
            if self.events[value.sequence - 1] == value:
                return False
            raise ValueError("identity event sequence already contains different content")
        # Validate on a fresh state so a refused append cannot change the locked view.
        state = replay((*self.events, value))
        encoded = (canonical(value.model_dump(mode="json")) + "\n").encode("ascii")
        self.stream.seek(0, os.SEEK_END)
        self.stream.write(encoded)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.events = (*self.events, value)
        self.state = state
        return True

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
        existing = next(
            (item for item in self.state.objects.values() if item.anchor == anchor), None
        )
        if existing is not None:
            if existing.entity_class != entity_class:
                raise ValueError("anchor already minted a different entity class")
            return existing.kn_id
        kn_id = new_id(occurred_at)
        self.append(
            event(
                Mint(kn_id=kn_id, entity_class=entity_class, anchor=anchor),
                previous=self.events[-1] if self.events else None,
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

    @contextmanager
    def locked(self) -> Iterator[LockedJournal]:
        self._check_path()
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "r+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            _sync_directory(directory)
            _sync_directory(directory.parent)
            yield LockedJournal(stream, self.data_dir)

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
            return LockedJournal(stream, self.data_dir).state
