"""Run reviewed lifecycle commands against PostgreSQL and exercise durable recovery."""

import json
import logging
import secrets
from pathlib import Path

import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

from kn import cli
from kn.db.rebuild import rebuild
from kn.identity import lifecycle, operator, store
from kn.identity.journal import Journal, LockedJournal
from kn.identity.lifecycle_reviews import REVIEW_REF, ReviewDetails
from kn.identity.model import Link, Merge, Retire
from kn.identity.projection import rows
from kn.review.journal import Journal as ReviewJournal
from kn.review.protocol import Reviewer
from tests.identity.fixtures import KEY, NOW, OTHER, A, B, C, D, E, history
from tests.integration.harness import IntegrationDatabase
from tests.integration.test_model_baseline import _snapshot

REVIEWER = Reviewer("local:fixture-reviewer", "human", True, frozenset({"workflow"}))


def _journal(data_dir: Path) -> Journal:
    journal = Journal(data_dir)
    for item in history()[:14]:
        journal.append(item)
    return journal


def _details(request_id: str) -> ReviewDetails:
    return ReviewDetails(
        request_id=request_id,
        performed_at=NOW,
        reason="Reviewed records",
        evidence="archive:review",
    )


def _submit(connection: Connection, journal: Journal, change, request_id: str):
    return lifecycle.submit(
        connection, journal, change, _details(request_id), lambda: REVIEWER, lambda: NOW
    )


def _run_cli(caplog: pytest.LogCaptureFixture, locale: str, action: str, *args: str) -> dict:
    caplog.set_level(logging.INFO, logger="kn.operator")
    review = [
        "--request-id",
        f"fixture-{action}-{args[0]}",
        "--reason",
        "Reviewed ownership",
        "--evidence",
        "archive:review",
        "--performed-at",
        NOW.isoformat(),
    ]
    assert cli.main(["--locale", locale, "--json", "identity", action, *args, *review]) == 0
    return json.loads(caplog.records[-1].message)


def _decision_ids(connection: Connection) -> set[str]:
    return set(
        connection.scalars(sa.text("SELECT decision_id FROM evidence.human_verification_decisions"))
    )


def test_cli_merge_split_rebuild_and_reclassify(
    integration_database: IntegrationDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    journal = _journal(tmp_path)
    name = f"kn_lifecycle_{secrets.token_hex(8)}"
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(operator, "local_reviewer", lambda *args: REVIEWER)
    engine = sa.create_engine(
        "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
    )
    monkeypatch.setattr(operator, "engine_from_env", lambda: engine)
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with engine.begin() as connection:
                rebuild(connection, data_dir=tmp_path)
            receipts = (*_merge_and_split(journal, caplog), *_retire_and_restore(journal, caplog))
            ids = {receipt["decision_id"] for receipt in receipts}
            assert all(
                receipt["event"]["decision_ref"] == REVIEW_REF + receipt["decision_id"]
                for receipt in receipts
            )
            with engine.begin() as connection:
                before = _snapshot(connection, [store.contract()])
                assert _decision_ids(connection) == ids
            for _ in range(2):
                with engine.begin() as connection:
                    rebuild(connection, data_dir=tmp_path)
                    assert _snapshot(connection, [store.contract()]) == before
                    assert _decision_ids(connection) == ids
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def _merge_and_split(journal: Journal, caplog: pytest.LogCaptureFixture) -> tuple[dict, ...]:
    first = _run_cli(caplog, "en", "merge", A, B)
    assert _run_cli(caplog, "uk", "merge", A, B) == first
    second = _run_cli(caplog, "uk", "merge", B, C)
    assert journal.state().resolve(A) == (C,)
    assignments = []
    for key, holding in journal.state().owned(C).items():
        payload = holding.event.payload
        successor = E if isinstance(payload, Link) and payload.record == OTHER else D
        assignments.extend(("--assign", f"{key}={successor}"))
    split = _run_cli(caplog, "en", "split", C, D, E, *assignments)
    assert _run_cli(caplog, "uk", "split", C, E, D, *assignments) == split
    assert journal.state().resolve(A) == (D, E)
    assert journal.state().resolve(C) == (D, E)
    active = {
        row["record_id"]: row["kn_id"]
        for row in rows(journal.state())["links"]
        if not row["ended_event"]
    }
    assert active == {KEY.record_id: D, OTHER.record_id: E}

    return first, second, split


def _retire_and_restore(journal: Journal, caplog: pytest.LogCaptureFixture) -> tuple[dict, ...]:
    reclassified = _run_cli(
        caplog,
        "uk",
        "reclassify",
        E,
        "core.manufacturer",
        "--anchor-source",
        "fixture:reclassification",
        "--anchor-key",
        "001",
    )
    successor = reclassified["event"]["payload"]["successor"]["kn_id"]
    assert journal.state().resolve(E) == (successor,)
    retire = _run_cli(caplog, "en", "retire", successor)
    restore = _run_cli(caplog, "uk", "restore", successor)
    assert journal.state().owned(successor) == {}
    assert journal.state().objects[successor].state == "active"

    _refuse_cross_class(journal, caplog, successor)
    return reclassified, retire, restore


def _refuse_cross_class(journal: Journal, caplog: pytest.LogCaptureFixture, successor: str) -> None:
    count = len(journal.read())
    assert (
        cli.main(
            [
                "--json",
                "identity",
                "merge",
                D,
                successor,
                "--request-id",
                "different-classes",
                "--performed-at",
                NOW.isoformat(),
                "--reason",
                "Attempt cross-class merge",
                "--evidence",
                "archive:review",
            ]
        )
        == 1
    )
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_INPUT"}}
    assert len(journal.read()) == count


def test_decision_only_interruption_and_retry(
    rebuild_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = _journal(tmp_path)
    rebuild(rebuild_connection, data_dir=tmp_path)
    real_write = LockedJournal._write

    def interrupt(log, encoded):
        raise OSError("fixture interrupted between the two durable appends")

    with monkeypatch.context() as interrupted:
        interrupted.setattr(LockedJournal, "_write", interrupt)
        with pytest.raises(OSError, match="interrupted"):
            _submit(rebuild_connection, journal, Merge(kn_id=A, survivor=B), "retry")
    (decision,) = ReviewJournal(tmp_path).read()
    assert journal.state().resolve(A) == (A,)
    assert _decision_ids(rebuild_connection) == set()
    value = _submit(rebuild_connection, journal, Merge(kn_id=A, survivor=B), "retry")
    assert value.decision_ref == REVIEW_REF + decision.decision_id
    assert _decision_ids(rebuild_connection) == {decision.decision_id}
    assert LockedJournal._write is real_write
    with pytest.raises(ValueError, match="reused"):
        _submit(rebuild_connection, journal, Retire(kn_id=B), "retry")


def test_sql_failure_after_both_appends_replays_without_duplicate_decision(
    rebuild_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = _journal(tmp_path)
    rebuild(rebuild_connection, data_dir=tmp_path)
    real_project = store._project

    def interrupt(connection, locked, count):
        real_project(connection, locked, count)
        connection.exec_driver_sql("SELECT 1 / 0")

    with monkeypatch.context() as interrupted:
        interrupted.setattr(store, "_project", interrupt)
        with pytest.raises(DBAPIError, match="division by zero"):
            _submit(rebuild_connection, journal, Merge(kn_id=A, survivor=B), "sql-retry")
    (decision,) = ReviewJournal(tmp_path).read()
    pending = journal.read()[-1]
    assert _decision_ids(rebuild_connection) == set()
    assert store.replay(rebuild_connection, journal).resolve(A) == (B,)
    assert _decision_ids(rebuild_connection) == {decision.decision_id}
    assert _submit(rebuild_connection, journal, Merge(kn_id=A, survivor=B), "sql-retry") == pending
