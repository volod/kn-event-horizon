"""Rebuild an archive committed by an earlier release from its frozen, uncompressed records.

`committed-v1` holds the records, descriptors and tombstones that the release audited in record
0057 wrote, and what that release read back from them. Records are `<role>.warc.txt` and blob
bodies `blob.txt`, so the fixture check scans them as text. Never regenerate a frozen fixture: add
a new directory for a new format version, so every older one keeps proving that it still reads.
"""

import gzip
import json
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parents[1] / "fixtures/archive"
_ROLES = (("payload", "payload_member"), ("request", "request_member"))


def restore_committed(name: str, root: Path) -> dict[str, Any]:
    """Write the fixture's committed batches under root and return its expected reads."""
    fixture = FIXTURES / name
    layout = json.loads((fixture / "layout.json").read_bytes())
    for batch in layout["batches"]:
        directory = root / batch["path"]
        directory.mkdir(parents=True)
        manifest = batch["manifest"]
        for entry in manifest["captures"]:
            folder = entry["record_id"].removeprefix("urn:uuid:")
            source = fixture / folder
            if not source.is_dir():
                continue  # Purged by its tombstone; the manifest keeps the original locators.
            (directory / folder).mkdir()
            if entry["backend"] == "blob":
                shutil.copyfile(source / "blob.txt", directory / entry["payload_path"])
                shutil.copyfile(
                    fixture / entry["metadata_path"], directory / entry["metadata_path"]
                )
            else:
                _write_segment(source, directory / entry["payload_path"], entry)
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="ascii")
    shutil.copytree(fixture / "tombstones", root / "tombstones")
    expected: dict[str, Any] = json.loads((fixture / "expected.json").read_bytes())
    return expected


def _write_segment(source: Path, path: Path, entry: dict[str, Any]) -> None:
    """Compress each frozen record into its own gzip member and relocate the members."""
    segment = b""
    for role, field in (*_ROLES, ("metadata", "metadata_member")):
        if entry[field] is None:
            continue
        member = gzip.compress((source / f"{role}.warc.txt").read_bytes(), mtime=0)
        entry[field] = {"offset": len(segment), "length": len(member)}
        segment += member
    path.write_bytes(segment)
    entry["payload"] = entry["metadata"] = {
        "size": len(segment),
        "sha256": sha256(segment).hexdigest(),
    }
