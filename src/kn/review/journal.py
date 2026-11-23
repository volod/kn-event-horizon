"""Private, fsynced write-ahead JSON Lines journal under DATA_DIR/decisions/.

A committed file event may precede its SQL projection. A failed SQL transaction leaves it
available for retry; SQL must never be the only durable copy. File tampering is outside this
trusted local boundary. External assessments must not be copied here without a trust policy.
"""

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from kn.contracts.model import canonical
from kn.review.model import Decision
from kn.review.protocol import validate_history

JOURNAL_NAME = "human-verification-v1.jsonl"


class LockedJournal:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        content = stream.read()
        if content and not content.endswith(b"\n"):
            raise ValueError("incomplete decision journal; restore before appending")
        try:
            self.events = tuple(Decision.model_validate_json(line) for line in content.splitlines())
            validate_history(self.events)
        except ValueError:
            raise ValueError("invalid decision journal; restore before appending") from None

    def append(self, event: Decision) -> bool:
        if event in self.events:
            return False
        validate_history((*self.events, event))
        encoded = (canonical(event.model_dump(mode="json")) + "\n").encode("ascii")
        self.stream.seek(0, os.SEEK_END)
        self.stream.write(encoded)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.events = (*self.events, event)
        return True


class Journal:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "decisions" / JOURNAL_NAME

    @contextmanager
    def locked(self) -> Iterator[LockedJournal]:
        """One lock covers validation, request deduplication and a durable append."""
        directory = self.path.parent
        if any(part.is_symlink() for part in (self.path, *self.path.parents)):
            raise ValueError("decision journal path must not contain symlinks")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            # Sync the directory entry too: fsync(file) alone cannot make creation durable.
            _sync_directory(directory)
            # A newly created decisions/ directory must itself survive a crash as well.
            _sync_directory(directory.parent)
            yield LockedJournal(stream)

    def read(self) -> tuple[Decision, ...]:
        with self.locked() as journal:
            return journal.events

    def append(self, event: Decision) -> bool:
        with self.locked() as journal:
            return journal.append(event)


def _sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
