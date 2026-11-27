import shutil
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pytest

from kn.archive import Archive
from kn.archive.model import ArchiveError, HttpExchange
from tests.archive.fixtures import AT, LIMITS, SAMPLE, batch, capture

_RUNTIME = shutil.ignore_patterns("locks", "staging")


def test_an_older_backup_with_current_tombstones_reads_and_stays_suppressed(
    tmp_path: Path,
) -> None:
    live = Archive(tmp_path / "live")
    kept = live.commit(batch(), [capture()], limits=LIMITS).captures[0]
    older = tmp_path / "older-backup"
    shutil.copytree(live.root, older, ignore=_RUNTIME)
    late = live.commit(batch("late"), [capture(key="late")], limits=LIMITS).captures[0]
    newer = tmp_path / "newer-backup"
    shutil.copytree(live.root, newer, ignore=_RUNTIME)
    live.withdraw(late.record_id, "expired", AT)

    # Restore the older backup, then apply the current tombstones before reading.
    restored = Archive(tmp_path / "restored")
    shutil.copytree(older, restored.root)
    shutil.copytree(live.root / "tombstones", restored.root / "tombstones")
    expected = {"batches": 1, "captures": 1, "tombstones": 1, "status": "verified"}
    assert restored.verify() == expected
    output = BytesIO()
    restored.replay(kept.fetch_id, output)
    assert output.getvalue() == SAMPLE
    with pytest.raises(ArchiveError, match="capture_tombstoned"):
        restored.replay(late.record_id, BytesIO())

    # A batch later recovered from a newer backup stays withdrawn.
    late_batch = Path("captures", *batch("late").parts())
    shutil.copytree(newer / late_batch, restored.root / late_batch)
    assert restored.verify() == expected | {"batches": 2}
    for identifier in (late.record_id, late.fetch_id):
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            restored.replay(identifier, BytesIO())


def test_a_tombstone_naming_a_capture_its_batch_lacks_is_refused(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive")
    archive.commit(batch(), [capture()], limits=LIMITS)
    # Another archive's tombstone for a different capture key in a batch with the same key.
    other = Archive(tmp_path / "other")
    stranger = other.commit(batch(), [capture(key="stranger")], limits=LIMITS).captures[0]
    other.withdraw(stranger.record_id, "expired", AT)
    shutil.copytree(other.root / "tombstones", archive.root / "tombstones")
    with pytest.raises(ArchiveError, match="tombstone_capture"):
        archive.verify()


def test_reindex_over_a_restore_tells_withdrawn_from_lost_captures(tmp_path: Path) -> None:
    from kn.archive.ledger import FetchLedger  # Keep pyarrow threads out of forked tests.

    live = Archive(tmp_path / "live")
    live.commit(batch(), [capture()], limits=LIMITS)
    older = tmp_path / "older-backup"
    shutil.copytree(live.root, older, ignore=_RUNTIME)
    withdrawn = live.commit(batch("withdrawn"), [capture()], limits=LIMITS).captures[0]
    live.commit(batch("unsaved"), [capture()], limits=LIMITS)
    FetchLedger(live.root, tmp_path / "index").reindex()
    live.withdraw(withdrawn.record_id, "expired", AT, purge=True)

    restored = tmp_path / "restored"
    shutil.copytree(older, restored)
    shutil.copytree(live.root / "tombstones", restored / "tombstones")
    ledger = FetchLedger(restored, tmp_path / "index")
    with pytest.raises(ArchiveError, match=r"^capture_lost$"):
        ledger.reindex()
    unsaved = Path("captures", *batch("unsaved").parts())
    shutil.copytree(live.root / unsaved, restored / unsaved)
    coverage = ledger.reindex()
    assert (coverage.covered_captures, coverage.published_retained) == (2, 2)
    assert withdrawn.record_id not in {row.record_id for row in ledger.query()}


def test_a_revisit_of_a_withdrawal_missing_from_the_restore_stays_suppressed(
    tmp_path: Path,
) -> None:
    from kn.archive.ledger import FetchLedger  # Keep pyarrow threads out of forked tests.

    live = Archive(tmp_path / "live")
    http = HttpExchange("GET", 200)
    original = live.commit(batch(), [capture(http=http)], limits=LIMITS).captures[0]
    later = capture(http=http, revisit_of=original.record_id, fetched_at=AT + timedelta(days=1))
    revisit = live.commit(batch("revisit"), [later], limits=LIMITS).captures[0]
    live.withdraw(original.record_id, "expired", AT, purge=True)
    restored = Archive(tmp_path / "restored")
    shutil.copytree(live.root, restored.root, ignore=_RUNTIME)
    shutil.rmtree(restored.root.joinpath("captures", *batch().parts()))  # Not recovered.
    assert restored.verify() == {"batches": 1, "captures": 0, "tombstones": 2, "status": "verified"}
    for identifier in (original.record_id, revisit.fetch_id):
        with pytest.raises(ArchiveError, match="capture_tombstoned"):
            restored.replay(identifier, BytesIO())
    coverage = FetchLedger(restored.root, tmp_path / "index").reindex()
    assert (coverage.covered_captures, coverage.published_retained) == (1, 0)
