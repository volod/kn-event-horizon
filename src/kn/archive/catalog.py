"""Discover authoritative committed batches and withdrawals without an index."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISREG

from kn.archive.files import read_small
from kn.archive.model import (
    MAX_DESCRIPTOR,
    MAX_MANIFEST,
    MAX_WARC_BODY,
    ArchiveError,
    BatchKey,
    Entry,
    Manifest,
    Tombstone,
    decode,
    object_paths,
    record_directory,
    stable_id,
)

MANIFEST_NAME = "manifest.json"
_MAX_CAPTURE_DIRECTORY = MAX_WARC_BODY + 3 * MAX_DESCRIPTOR


@dataclass(frozen=True, slots=True)
class Located:
    batch: BatchKey
    directory: Path
    entry: Entry

    def objects(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.entry.payload_path, self.entry.metadata_path)))


def check_reference(located: Located, target: Located | None) -> Located | None:
    if located.entry.revisit_of is None:
        return None
    if (
        target is None
        or target.entry.record_id != located.entry.revisit_of
        or target.entry.revisit_of is not None
        or target.entry.backend != "warc"
        or target.batch.parts()[:2] != located.batch.parts()[:2]
        or target.entry.fetched_at > located.entry.fetched_at
        or target.entry.payload_sha256 != located.entry.payload_sha256
    ):
        raise ArchiveError("revisit_target")
    return target


def batch_directory(root: Path, key: BatchKey) -> Path:
    return root.joinpath("captures", *key.parts())


def tombstone_path(root: Path, record_id: str) -> Path:
    return root / "tombstones" / (record_directory(record_id) + ".json")


def _directories(parent: Path, name: str | None = None) -> Iterator[Path]:
    if parent.is_symlink():
        raise ArchiveError("archive_symlink")
    if not parent.exists():
        return
    children = sorted(parent.iterdir()) if name is None else [parent / name]
    for child in children:
        if name is not None and not child.exists() and not child.is_symlink():
            continue
        if child.is_symlink() or not child.is_dir():
            raise ArchiveError("archive_directory")
        yield child


def manifests(
    root: Path, domain: str | None = None, source_id: str | None = None
) -> Iterator[tuple[Path, Manifest]]:
    for directory in _directories(root / "captures", domain):
        for source in _directories(directory, source_id):
            for run in _directories(source):
                for batch in _directories(run):
                    yield batch, read_manifest(batch, root)


def read_manifest(path: Path, root: Path) -> Manifest:
    filename = path / MANIFEST_NAME
    if filename.is_symlink():
        raise ArchiveError("archive_symlink")
    manifest = decode(Manifest, read_small(filename, MAX_MANIFEST), "manifest_schema")
    if path != batch_directory(root, manifest.batch):
        raise ArchiveError("manifest_scope")
    dates = [capture.fetched_at for capture in manifest.captures]
    if manifest.first_capture_at != min(dates) or manifest.last_capture_at != max(dates):
        raise ArchiveError("manifest_time_range")
    if len({entry.key for entry in manifest.captures}) != len(manifest.captures):
        raise ArchiveError("duplicate_capture")
    for entry in manifest.captures:
        _check_entry(manifest.batch, entry)
    return manifest


def _check_entry(batch: BatchKey, entry: Entry) -> None:
    if entry.record_id != stable_id(batch, entry.key, "record") or entry.fetch_id != stable_id(
        batch, entry.key, "fetch"
    ):
        raise ArchiveError("capture_id")
    paths = object_paths(entry.record_id, entry.backend, entry.payload_sha256)
    if paths != (entry.payload_path, entry.metadata_path):
        raise ArchiveError("object_path")
    if entry.backend == "warc":
        _check_members(entry)
    elif (
        any((entry.payload_member, entry.metadata_member, entry.request_member, entry.revisit_of))
        or entry.metadata.size > MAX_DESCRIPTOR
        or entry.payload.sha256 != entry.payload_sha256
    ):
        raise ArchiveError("blob_locator")


def _check_members(entry: Entry) -> None:
    if entry.payload != entry.metadata or entry.payload.size > _MAX_CAPTURE_DIRECTORY:
        raise ArchiveError("warc_locator")
    if entry.payload_member is None or entry.metadata_member is None:
        raise ArchiveError("warc_locator")
    members = [entry.payload_member]
    if entry.request_member is not None:
        members.append(entry.request_member)
    members.append(entry.metadata_member)
    offset = 0
    for member in members:
        if member.offset != offset:
            raise ArchiveError("warc_locator")
        offset += member.length
    if offset != entry.payload.size:
        raise ArchiveError("warc_locator")


def _tombstone_files(root: Path) -> list[Path]:
    directory = root / "tombstones"
    if directory.is_symlink():
        raise ArchiveError("archive_symlink")
    return sorted(directory.iterdir()) if directory.exists() else []


def _read_tombstones(
    root: Path,
    files: list[Path],
    records: dict[str, Located],
    domain: str | None,
    source_id: str | None,
) -> dict[str, Tombstone]:
    result = {}
    for filename in files:
        if filename.is_symlink() or not filename.is_file():
            raise ArchiveError("tombstone_path")
        stone = decode(Tombstone, read_small(filename, MAX_DESCRIPTOR), "tombstone_schema")
        if (domain and stone.batch.domain != domain) or (
            source_id and stone.batch.source_id != source_id
        ):
            continue
        located = records.get(stone.record_id)
        if located is None or filename != tombstone_path(root, stone.record_id):
            raise ArchiveError("tombstone_capture")
        if (stone.batch, stone.payload_sha256, stone.objects) != (
            located.batch,
            located.entry.payload_sha256,
            located.objects(),
        ):
            raise ArchiveError("tombstone_capture")
        result[stone.record_id] = stone
    return result


def is_withdrawn(root: Path, record_id: str, revisit_of: str | None) -> bool:
    """Check current withdrawal markers without scanning committed batches."""
    if (root / "tombstones").is_symlink():
        raise ArchiveError("archive_symlink")
    for identifier in (record_id, revisit_of):
        if identifier is None:
            continue
        try:
            mode = tombstone_path(root, identifier).stat(follow_symlinks=False).st_mode
        except FileNotFoundError:
            continue
        if not S_ISREG(mode):
            raise ArchiveError("tombstone_path")
        return True
    return False


@dataclass(frozen=True, slots=True)
class Catalog:
    records: dict[str, Located]
    fetches: dict[str, Located]
    tombstones: dict[str, Tombstone]
    batches: int

    @classmethod
    def load(
        cls, root: Path, *, domain: str | None = None, source_id: str | None = None
    ) -> "Catalog":
        tombstones = _tombstone_files(root)
        records: dict[str, Located] = {}
        fetches: dict[str, Located] = {}
        batches = 0
        for directory, manifest in manifests(root, domain, source_id):
            batches += 1
            for entry in manifest.captures:
                located = Located(manifest.batch, directory, entry)
                if entry.record_id in records or entry.fetch_id in fetches:
                    raise ArchiveError("duplicate_capture")
                records[entry.record_id] = fetches[entry.fetch_id] = located
        return cls(
            records,
            fetches,
            _read_tombstones(root, tombstones, records, domain, source_id),
            batches,
        )

    def lookup(self, identifier: str) -> Located:
        located = self.records.get(identifier) or self.fetches.get(identifier)
        if located is None:
            raise ArchiveError("capture_not_found")
        return located

    def withdrawn(self, entry: Entry) -> bool:
        return entry.record_id in self.tombstones or entry.revisit_of in self.tombstones
