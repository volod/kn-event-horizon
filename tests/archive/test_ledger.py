import shutil
from datetime import timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from kn.archive import Archive, reader, retention
from kn.archive.ledger_model import CaptureScope, LedgerRow
from kn.archive.model import ArchiveError, HttpExchange
from tests.archive.fixtures import (
    AT,
    LIMITS,
    SAMPLE,
    batch,
    capture,
    committed_path,
    rewrite_descriptor,
)

if TYPE_CHECKING:
    from kn.archive.ledger import FetchLedger


@pytest.fixture
def archives(tmp_path: Path) -> tuple[Archive, "FetchLedger"]:
    from kn.archive.ledger import FetchLedger

    archive = Archive(tmp_path / "archive")
    ledger = FetchLedger(archive.root, tmp_path / "index")
    return archive, ledger


def test_full_reindex_recovery_and_archive_only_replay(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    warc = archive.commit(batch("warc"), [capture(http=HttpExchange("GET", 200))], limits=LIMITS)
    blob = archive.commit(batch("legacy"), [capture(backend="blob")], limits=LIMITS)
    rewrite_descriptor(archive.root, "legacy", {"schema_version": 1})
    other = batch("other", domain="gdelt", source="events")
    archive.commit(other, [capture(fetched_at=AT + timedelta(days=1))], limits=LIMITS)
    archive.commit(batch(source="catalog"), [capture(backend="blob")], limits=LIMITS)
    with patch.object(reader, "read_member", wraps=reader.read_member) as read_member:
        coverage = ledger.reindex()
    assert read_member.call_count == 2
    assert all(call.args[1].offset > 0 for call in read_member.call_args_list)
    rows = list(ledger.query())
    replay_order = [item.fetch_id for item in archive.iter_metadata()]
    assert [row.fetch_id for row in rows] == replay_order
    assert coverage.covered_captures == 4
    assert coverage.partitions == 3
    _assert_mixed_metadata(rows, blob.captures[0].record_id, warc.captures[0].record_id)
    for row in rows:
        output = BytesIO()
        assert archive.replay(row.fetch_id, output).record_id == row.record_id
        assert output.getvalue() == SAMPLE
    shutil.rmtree(ledger.root)
    assert [item.fetch_id for item in archive.iter_metadata()] == replay_order
    assert ledger.reindex() == coverage
    assert list(ledger.query()) == rows


def _assert_mixed_metadata(rows: list[LedgerRow], blob_id: str, warc_id: str) -> None:
    by_id = {row.record_id: row for row in rows}
    legacy = by_id[blob_id].capture
    assert legacy is not None
    assert legacy.decoded_size is None and legacy.offset is None
    response = by_id[warc_id].capture
    assert response is not None
    assert response.offset == 0 and response.length is not None
    assert response.relative_path.startswith("captures/space/space:example/")
    assert response.status == 200


def test_scoped_reindex_keeps_outside_coverage_and_resolves_gaps(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    inside, end = AT + timedelta(hours=1), AT + timedelta(hours=2)
    first = archive.commit(batch(), [capture()], limits=LIMITS).captures[0]
    other = archive.commit(batch(source="other"), [capture()], limits=LIMITS).captures[0]
    ledger.reindex()
    other_partition = "space:other/2026-01-02.parquet"
    inode = next(ledger.root.glob(f"views/*/space/{other_partition}")).stat().st_ino
    later = archive.commit(
        batch("late"),
        [capture(fetched_at=inside), capture(key="boundary", fetched_at=end)],
        limits=LIMITS,
    ).captures
    indexed = Archive(archive.root, index_root=ledger.root)
    with patch("kn.archive.Catalog.load", side_effect=AssertionError("archive scan")):
        assert indexed.metadata(first.fetch_id).record_id == first.record_id
        output = BytesIO()
        assert indexed.replay(first.record_id, output).fetch_id == first.fetch_id
        assert output.getvalue() == SAMPLE
    assert indexed.metadata(later[0].record_id).fetch_id == later[0].fetch_id

    offset = timezone(timedelta(hours=2))
    scope = CaptureScope(
        source_id="space:example", since=inside.astimezone(offset), before=end.astimezone(offset)
    )
    coverage = ledger.reindex(scope)
    assert coverage.covered_captures == 3
    assert coverage.partitions == 2
    assert next(ledger.root.glob(f"views/*/space/{other_partition}")).stat().st_ino == inode
    assert {row.record_id for row in ledger.query()} == {
        first.record_id,
        other.record_id,
        later[0].record_id,
    }
    assert [row.record_id for row in ledger.query(scope)] == [later[0].record_id]
    assert indexed.metadata(later[1].fetch_id).record_id == later[1].record_id


def test_failed_publication_keeps_the_prior_coverage(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    archive.commit(batch(), [capture()], limits=LIMITS)
    coverage = ledger.reindex()
    rows = list(ledger.query())
    archive.commit(batch("late"), [capture()], limits=LIMITS)
    with (
        patch("kn.archive.ledger_views.replace_pointer", side_effect=OSError),
        pytest.raises(ArchiveError, match="index_io"),
    ):
        ledger.reindex()
    assert ledger.coverage() == coverage
    assert list(ledger.query()) == rows
    assert ledger.reindex().covered_captures == 2


def test_tombstones_hide_stale_rows_and_purged_revisits(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    http = HttpExchange("GET", 200)
    original = archive.commit(batch(), [capture(http=http)], limits=LIMITS).captures[0]
    revisit = archive.commit(
        batch("revisit"),
        [capture(http=http, revisit_of=original.record_id, fetched_at=AT + timedelta(days=1))],
        limits=LIMITS,
    ).captures[0]
    ledger.reindex()
    archive.withdraw(original.record_id, "expired", AT, purge=True)
    indexed = Archive(archive.root, index_root=ledger.root)
    assert ledger.coverage().published_retained == 2
    assert list(ledger.query()) == []
    for entry in (original, revisit):
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            indexed.metadata(entry.fetch_id)
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            indexed.replay(entry.record_id, BytesIO())
    result = ledger.reindex()
    assert result.covered_captures == 2 and result.published_retained == 0
    assert list(ledger.query()) == []
    assert {row.record_id for row in ledger.covered()} == {original.record_id, revisit.record_id}


def test_missing_live_blob_blocks_reindex_but_recorded_purge_is_covered(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    key = batch()
    entry = archive.commit(key, [capture(backend="blob")], limits=LIMITS).captures[0]
    before = ledger.reindex()
    committed_path(archive.root, key, entry.payload_path).unlink()
    with pytest.raises(ArchiveError, match="archive_file_missing"):
        ledger.reindex()
    assert ledger.coverage() == before
    archive.withdraw(entry.fetch_id, "expired", AT, purge=True)
    assert ledger.reindex().published_retained == 0
    assert {row.withdrawn_by for row in ledger.covered()} == {entry.record_id}


def test_target_tombstone_suppresses_revisit_before_its_own_tombstone(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    http = HttpExchange("GET", 200)
    original = archive.commit(batch(), [capture(http=http)], limits=LIMITS).captures[0]
    revisit_time = AT + timedelta(days=1)
    revisit = archive.commit(
        batch("revisit"),
        [capture(http=http, revisit_of=original.record_id, fetched_at=revisit_time)],
        limits=LIMITS,
    ).captures[0]
    ledger.reindex()
    affected = retention._affected
    with patch.object(retention, "_affected", side_effect=lambda *args: affected(*args)[:1]):
        archive.withdraw(original.record_id, "expired", AT)
    assert list(ledger.query()) == []
    indexed = Archive(archive.root, index_root=ledger.root)
    with pytest.raises(ArchiveError, match="capture_tombstoned"):
        indexed.metadata(revisit.fetch_id)
    scope = CaptureScope(since=revisit_time)
    ledger.reindex(scope)
    (receipt,) = ledger.covered(scope)
    assert receipt.record_id == revisit.record_id
    assert receipt.withdrawn_by == original.record_id


def test_pinned_reader_keeps_its_complete_view_during_publication(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    archive.commit(batch(), [capture()], limits=LIMITS)
    archive.commit(batch("tomorrow"), [capture(fetched_at=AT + timedelta(days=1))], limits=LIMITS)
    ledger.reindex()
    original = list(ledger.query())
    rows = ledger.query()
    assert next(rows) == original[0]
    archive.commit(batch("new"), [capture()], limits=LIMITS)
    assert ledger.reindex().covered_captures == 3
    assert list(rows) == original[1:]
    assert len(list(ledger.root.glob("views/*"))) == 2
    ledger.reindex()
    assert len(list(ledger.root.glob("views/*"))) == 1


def test_damaged_index_falls_back_to_archive_and_full_reindex_repairs_it(
    archives: tuple[Archive, "FetchLedger"],
) -> None:
    archive, ledger = archives
    entry = archive.commit(batch(), [capture()], limits=LIMITS).captures[0]
    expected = ledger.reindex()
    (ledger.root / "CURRENT").write_bytes(b"{}")
    indexed = Archive(archive.root, index_root=ledger.root)
    assert indexed.metadata(entry.fetch_id).record_id == entry.record_id
    with pytest.raises(ArchiveError, match="index_snapshot"):
        ledger.reindex(CaptureScope(domain="space"))
    assert ledger.reindex() == expected


def test_partition_writes_multiple_sorted_row_groups(
    archives: tuple[Archive, "FetchLedger"], monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyarrow.parquet import ParquetFile

    archive, ledger = archives
    monkeypatch.setattr("kn.archive.ledger_parquet._ROW_GROUP_SIZE", 2)
    captures = [capture(key=f"capture-{index}", backend="blob") for index in range(5)]
    archive.commit(batch(), captures, limits=LIMITS)
    assert ledger.reindex().covered_captures == 5
    (filename,) = ledger.root.rglob("*.parquet")
    with ParquetFile(filename) as parquet:
        assert parquet.num_row_groups == 3
    assert [row.fetch_id for row in ledger.query()] == [
        row.fetch_id for row in archive.iter_metadata()
    ]
