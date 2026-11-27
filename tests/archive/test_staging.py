from pathlib import Path

from kn.archive import Archive
from tests.archive.fixtures import AT, LIMITS, batch, capture


def _leftover(root: Path, *scope: str) -> Path:
    path = root.joinpath("staging", *scope, "pending-interrupted")
    path.mkdir(parents=True)
    (path / "body.pending").write_bytes(b"partial")
    return path


def test_writers_reclaim_only_what_their_own_lock_left(tmp_path: Path) -> None:
    from kn.archive.ledger import FetchLedger  # Keep pyarrow threads out of forked tests.

    archive = Archive(tmp_path / "archive")
    entry = archive.commit(batch(), [capture()], limits=LIMITS).captures[0]
    own = _leftover(archive.root, "_sources", "space", "space:example")
    other = _leftover(archive.root, "_sources", "space", "space:other")
    package = _leftover(archive.root, "space", "space:example", "run-1")
    archive.commit(batch("next"), [capture()], limits=LIMITS)
    assert not own.exists()
    assert other.exists() and package.exists()

    _leftover(archive.root, "_sources", "space", "space:example")
    archive.withdraw(entry.record_id, "expired", AT)
    assert not own.exists()

    ledger = FetchLedger(archive.root, tmp_path / "index")
    stale = _leftover(ledger.root)
    ledger.reindex()
    assert not stale.exists()
    assert not list((ledger.root / "staging").iterdir())
