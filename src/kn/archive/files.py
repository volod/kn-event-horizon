"""Bounded file I/O and filesystem publication primitives."""

import gzip
import os
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, flock
from hashlib import sha256
from pathlib import Path
from stat import S_ISREG
from tempfile import TemporaryDirectory
from typing import BinaryIO, Protocol

from kn.archive.model import CHUNK_SIZE, ArchiveError, ObjectInfo


class ByteReader(Protocol):
    def read(self, size: int, /) -> bytes: ...


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def mkdirs(path: Path) -> None:
    if path.is_symlink():
        raise ArchiveError("archive_directory")
    if path.is_dir():
        return
    mkdirs(path.parent)
    try:
        path.mkdir(exist_ok=True)
    except FileExistsError:
        raise ArchiveError("archive_directory") from None
    if path.is_symlink():
        raise ArchiveError("archive_directory")
    sync_directory(path.parent)


@contextmanager
def source_lock(root: Path, domain: str, source_id: str) -> Iterator[None]:
    directory = root / "locks" / domain
    check_directories(root, directory)
    with exclusive_lock(directory / source_id):
        yield


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    mkdirs(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags, 0o600), "wb") as lock:
        if not S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ArchiveError("archive_lock")
        flock(lock, LOCK_EX)
        yield


@contextmanager
def staging(root: Path) -> Iterator[Path]:
    directory = root / "staging"
    mkdirs(directory)
    with TemporaryDirectory(prefix="pending-", dir=directory) as pending:
        yield Path(pending)


def publish(staged: Path, destination: Path, root: Path) -> None:
    mkdirs(destination.parent)
    staged.rename(destination)
    sync_publication(destination, root)
    sync_directory(staged.parent)


def sync_publication(destination: Path, root: Path) -> None:
    # Include shared directories that a concurrent writer may have just created.
    for parent in destination.parents:
        sync_directory(parent)
        if parent == root.parent:
            break


def check_directories(root: Path, directory: Path) -> None:
    for part in directory.relative_to(root).parts:
        root /= part
        if root.is_symlink():
            raise ArchiveError("archive_symlink")


def synced_write(path: Path, contents: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(contents)
        sync_file(stream)


def sync_file(stream: BinaryIO) -> None:
    stream.flush()
    os.fsync(stream.fileno())


def checked_path(batch: Path, relative: str) -> Path:
    parent, _, name = relative.partition("/")
    directory = batch / parent
    path = directory / name
    if directory.is_symlink() or path.is_symlink():
        raise ArchiveError("archive_symlink")
    return path


def read_small(path: Path, limit: int) -> bytes:
    with open_regular(path) as stream:
        contents = stream.read(limit + 1)
    if len(contents) > limit:
        raise ArchiveError("document_size")
    return contents


@contextmanager
def open_regular(path: Path) -> Iterator[BinaryIO]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise ArchiveError("archive_file_missing") from None
    with os.fdopen(descriptor, "rb") as stream:
        if not S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ArchiveError("archive_file_type")
        yield stream


def copy_payload(source: BinaryIO, destination: BinaryIO | None, *, limit: int) -> ObjectInfo:
    digest = sha256()
    size = 0
    while chunk := source.read(CHUNK_SIZE):
        size += len(chunk)
        if size > limit:
            raise ArchiveError("payload_size")
        digest.update(chunk)
        if destination is not None:
            destination.write(chunk)
    return ObjectInfo(size=size, sha256=digest.hexdigest())


def file_info(path: Path, limit: int) -> ObjectInfo:
    with open_regular(path) as stream:
        return copy_payload(stream, None, limit=limit)


def decoded_size(stream: BinaryIO, encoding: str, limit: int) -> int:
    stream.seek(0)
    try:
        if encoding == "identity":
            size = stream.seek(0, os.SEEK_END)
        elif encoding in {"gzip", "x-gzip"}:
            with gzip.GzipFile(fileobj=stream, mode="rb") as decoded:
                size = _count_decoded(decoded, limit)
        else:
            size = _count_deflate(stream, limit)
    except (EOFError, OSError, zlib.error):
        raise ArchiveError("invalid_content_encoding") from None
    finally:
        stream.seek(0)
    if size > limit:
        raise ArchiveError("decoded_size")
    return size


def _count_decoded(stream: ByteReader, limit: int) -> int:
    size = 0
    while chunk := stream.read(min(CHUNK_SIZE, limit - size + 1)):
        size += len(chunk)
        if size > limit:
            raise ArchiveError("decoded_size")
    return size


def _count_deflate(stream: BinaryIO, limit: int) -> int:
    decoder = zlib.decompressobj()
    size = 0
    while chunk := stream.read(CHUNK_SIZE):
        while chunk:
            size += len(decoder.decompress(chunk, min(CHUNK_SIZE, limit - size + 1)))
            if size > limit:
                raise ArchiveError("decoded_size")
            if decoder.unused_data:
                raise ArchiveError("invalid_content_encoding")
            chunk = decoder.unconsumed_tail
    if not decoder.eof:
        raise ArchiveError("invalid_content_encoding")
    return size
