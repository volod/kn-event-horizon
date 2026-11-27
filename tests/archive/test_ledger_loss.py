import shutil
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from kn.archive import Archive
from kn.archive.ledger_model import CaptureScope
from kn.archive.model import ArchiveError
from tests.archive.fixtures import AT, LIMITS, batch, capture

if TYPE_CHECKING:
    from kn.archive.ledger import FetchLedger


def _ledger(archive: Archive, index: Path) -> "FetchLedger":
    from kn.archive.ledger import FetchLedger  # Keep pyarrow threads out of forked tests.

    return FetchLedger(archive.root, index)


def test_reindex_refuses_to_forget_a_lost_batch(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive")
    ledger = _ledger(archive, tmp_path / "index")
    archive.commit(batch(), [capture()], limits=LIMITS)
    archive.commit(batch("lost"), [capture(fetched_at=AT + timedelta(hours=1))], limits=LIMITS)
    archive.commit(batch(source="other"), [capture()], limits=LIMITS)
    coverage = ledger.reindex()
    rows = list(ledger.covered())
    shutil.rmtree(archive.root.joinpath("captures", *batch("lost").parts()))
    for scope in (
        CaptureScope(),
        CaptureScope(source_id="space:example"),
        CaptureScope(since=AT + timedelta(minutes=30)),
    ):
        with pytest.raises(ArchiveError, match=r"^capture_lost$"):
            ledger.reindex(scope)
        assert ledger.coverage() == coverage
        assert list(ledger.covered()) == rows
    assert ledger.reindex(CaptureScope(source_id="space:other")).covered_captures == 3
    shutil.rmtree(ledger.root)  # Accept the loss explicitly: rebuild from the archive alone.
    assert ledger.reindex().covered_captures == 2


def test_a_damaged_view_cannot_block_the_full_rebuild_that_replaces_it(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive")
    ledger = _ledger(archive, tmp_path / "index")
    archive.commit(batch(), [capture()], limits=LIMITS)
    expected = ledger.reindex()
    (partition,) = ledger.root.rglob("*.parquet")
    partition.write_bytes(b"PAR1")
    with pytest.raises(ArchiveError, match="index_parquet"):
        ledger.reindex(CaptureScope(domain="space"))
    assert ledger.reindex() == expected
