from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

from kn.archive import Archive
from kn.archive.model import ArchiveError
from tests.archive.committed import restore_committed
from tests.archive.independent import manifests, read_segment


def test_records_committed_by_an_earlier_release_still_read(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    expected = restore_committed("committed-v1", root)
    archive = Archive(root)
    assert archive.verify() == expected["verify"]
    assert [item.fetch_id for item in archive.iter_metadata()] == expected["replay_order"]
    for fetch_id, frozen in expected["captures"].items():
        output = BytesIO()
        metadata = archive.replay(fetch_id, output)
        assert metadata.model_dump(mode="json") == frozen["metadata"]
        assert sha256(output.getvalue()).hexdigest() == frozen["replay_sha256"]
    for record in expected["tombstoned"]:
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            archive.replay(f"urn:uuid:{record}", BytesIO())
    from kn.archive.ledger import FetchLedger  # Keep pyarrow threads out of forked tests.

    ledger = FetchLedger(root, tmp_path / "index")
    assert ledger.reindex().model_dump() == expected["coverage"]
    assert [row.fetch_id for row in ledger.query()] == expected["replay_order"]


def test_an_independent_reader_accepts_the_committed_records(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    restore_committed("committed-v1", root)
    read = 0
    for directory, manifest in manifests(root):
        for entry in manifest["captures"]:  # type: ignore[attr-defined]
            segment = directory / entry["payload_path"]
            if entry["backend"] == "warc" and segment.exists():
                records = read_segment(segment)
                assert {row["version"] for row in records} == {"WARC/1.1"}
                assert all(row["block_ok"] for row in records)
                read += 1
    assert read == 3
