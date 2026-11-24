"""Refuse stale and unauthenticated workflow requests and verify durable review references."""

from pathlib import Path

import pytest
from sqlalchemy.engine import Connection

from kn.db.rebuild import rebuild
from kn.identity import lifecycle, store
from kn.identity.journal import Journal, LockedJournal
from kn.identity.model import Merge, Retire
from kn.review.journal import Journal as ReviewJournal
from kn.review.protocol import Reviewer
from tests.identity.fixtures import NOW, A, B, C
from tests.integration.test_identity_lifecycle import (
    REVIEWER,
    _decision_ids,
    _details,
    _journal,
    _submit,
)


def test_stale_review_and_agent_principal_cannot_apply(
    rebuild_connection: Connection, tmp_path: Path
) -> None:
    journal = _journal(tmp_path)
    rebuild(rebuild_connection, data_dir=tmp_path)
    prior = journal.read()[-1].event_id
    _submit(rebuild_connection, journal, Retire(kn_id=C), "other")
    change = Merge(kn_id=A, survivor=B)
    with pytest.raises(ValueError, match="changed after review"):
        lifecycle.submit(
            rebuild_connection,
            journal,
            change,
            _details("stale"),
            lambda: REVIEWER,
            lambda: NOW,
            expected_head=prior,
        )
    agent = Reviewer("automation:fixture", "agent", True, frozenset({"workflow"}))
    with pytest.raises(ValueError, match="authorized human"):
        lifecycle.submit(
            rebuild_connection, journal, change, _details("agent"), lambda: agent, lambda: NOW
        )
    assert journal.state().resolve(A) == (A,)
    assert len(ReviewJournal(tmp_path).read()) == 1


def test_pending_approval_does_not_apply_against_changed_snapshot(
    rebuild_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = _journal(tmp_path)
    rebuild(rebuild_connection, data_dir=tmp_path)
    change = Merge(kn_id=A, survivor=B)

    def interrupt(log, value):
        raise OSError("fixture interrupted between the two durable appends")

    with monkeypatch.context() as interrupted:
        interrupted.setattr(LockedJournal, "append", interrupt)
        with pytest.raises(OSError, match="interrupted"):
            _submit(rebuild_connection, journal, change, "pending")
    _submit(rebuild_connection, journal, Retire(kn_id=C), "other")
    with pytest.raises(ValueError, match="stale identity snapshot"):
        _submit(rebuild_connection, journal, change, "pending")
    assert journal.state().resolve(A) == (A,)
    assert len(ReviewJournal(tmp_path).read()) == 2
    assert len(_decision_ids(rebuild_connection)) == 1


def test_replay_refuses_missing_review_and_preserves_sql_state(
    rebuild_connection: Connection, tmp_path: Path
) -> None:
    journal = _journal(tmp_path)
    rebuild(rebuild_connection, data_dir=tmp_path)
    _submit(rebuild_connection, journal, Merge(kn_id=A, survivor=B), "reviewed")
    before = _decision_ids(rebuild_connection)
    decision_file = ReviewJournal(tmp_path).path
    saved = decision_file.read_bytes()
    decision_file.write_bytes(b"")
    try:
        with pytest.raises(ValueError, match="requires a unique durable review decision"):
            store.replay(rebuild_connection, Journal(tmp_path))
        assert _decision_ids(rebuild_connection) == before
    finally:
        decision_file.write_bytes(saved)
    assert store.replay(rebuild_connection, journal).resolve(A) == (B,)
