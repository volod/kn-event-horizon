import shutil
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from warcio.archiveiterator import ArchiveIterator

from kn.archive import Archive, retention
from kn.archive.model import ArchiveError, HttpExchange, Retention
from kn.archive.warc import REVISIT_PROFILE
from tests.archive.fixtures import AT, LIMITS, SAMPLE, batch, capture, committed_path


def test_revisit_replay_and_withdrawal_survive_relocation(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive")
    http = HttpExchange("GET", 200)
    original = archive.commit(batch(), [capture(http=http)], limits=LIMITS).captures[0]
    later = capture(http=http, revisit_of=original.record_id, fetched_at=AT + timedelta(seconds=1))
    revisit = archive.commit(batch("revisit"), [later], limits=LIMITS).captures[0]
    output = BytesIO()
    assert archive.replay(revisit.record_id, output).kind == "revisit"
    assert output.getvalue() == SAMPLE
    assert archive.verify()["captures"] == 2
    path = committed_path(archive.root, batch("revisit"), revisit.payload_path)
    with path.open("rb") as stream:
        record = next(iter(ArchiveIterator(stream, check_digests="raise")))
        assert record.rec_type == "revisit"
        assert record.rec_headers.get_header("WARC-Profile") == REVISIT_PROFILE
        assert record.rec_headers.get_header("WARC-Refers-To") == f"<{original.record_id}>"
        assert record.rec_headers.get_header("WARC-Truncated") == "length"
        assert record.raw_stream.read() == b""

    # Stop after the target tombstone publishes and before its dependent gets a tombstone.
    persist = retention._persist

    def stop_before_dependent(*args, **kwargs):
        if args[2].entry.record_id == revisit.record_id:
            raise RuntimeError("interrupted")
        return persist(*args, **kwargs)

    with (
        patch.object(retention, "_persist", side_effect=stop_before_dependent),
        pytest.raises(RuntimeError, match="interrupted"),
    ):
        archive.withdraw(original.record_id, "expired", AT, purge=True)
    with pytest.raises(ArchiveError, match="capture_tombstoned"):
        archive.replay(revisit.fetch_id, BytesIO())
    assert path.exists()
    assert archive.verify()["captures"] == 0
    original_bytes = path.read_bytes()
    path.unlink()
    with pytest.raises(ArchiveError, match="archive_file_missing"):
        archive.verify()
    path.write_bytes(original_bytes)

    stones = archive.withdraw(original.fetch_id, "expired", AT, purge=True)
    assert {stone.record_id for stone in stones} == {original.record_id, revisit.record_id}
    assert not path.exists()
    assert archive.withdraw(original.record_id, "expired", AT, purge=True) == stones
    restored = Archive(tmp_path / "restored")
    shutil.copytree(archive.root, restored.root)
    assert list(restored.iter_metadata()) == []
    assert restored.verify() == {"batches": 2, "captures": 0, "tombstones": 2, "status": "verified"}
    for identifier in (original.record_id, revisit.fetch_id):
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            restored.replay(identifier, BytesIO())


def test_revisits_require_identical_request_payload_and_retention(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    http = HttpExchange("GET", 200)
    original = archive.commit(batch(), [capture(http=http)], limits=LIMITS).captures[0]
    base = {"http": http, "revisit_of": original.record_id}
    variants = [
        capture(b"other", **base),
        capture(**(base | {"origin_uri": "https://example.test/other"})),
        capture(**(base | {"retention": Retention(access="private", deletion_scope="fixture")})),
        capture(**(base | {"http": HttpExchange("POST", 200)})),
        capture(**(base | {"http": HttpExchange("GET", 200, (("Authorization", "synthetic"),))})),
    ]
    for candidate in variants:
        with pytest.raises(ArchiveError, match=r"revisit_(target|request)"):
            archive.commit(batch("invalid"), [candidate], limits=LIMITS)
    archive.withdraw(original.record_id, "expired", AT)
    with pytest.raises(ArchiveError, match="revisit_target"):
        archive.commit(batch("invalid"), [capture(**base)], limits=LIMITS)


def test_blob_deletion_does_not_affect_identical_independent_capture(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    entries = archive.commit(
        batch(),
        [
            capture(backend="blob"),
            capture(
                backend="blob",
                key="independent",
                retention=Retention(access="internal", deletion_scope="independent"),
            ),
        ],
        limits=LIMITS,
    ).captures
    archive.withdraw(entries[0].record_id, "expired", AT, purge=True)
    output = BytesIO()
    archive.replay(entries[1].record_id, output)
    assert output.getvalue() == SAMPLE
    assert archive.verify()["captures"] == 1
