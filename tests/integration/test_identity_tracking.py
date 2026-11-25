"""Partial-update tracking through PostgreSQL: change sets, claims, confirmations and recovery."""

from datetime import timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.rebuild import rebuild
from kn.db.statements import SetConstraints
from kn.evidence.asof import claims_as_of
from kn.evidence.store import evidence_contract, evidence_tables
from kn.identity import store
from kn.identity.journal import Journal
from kn.identity.tracking.delivery import Delivery
from kn.identity.tracking.writer import Receipt, track
from tests.identity.tracking_fixtures import (
    PACKAGE,
    PRICE,
    RECORD,
    T0,
    VOLTAGE,
    delivery,
    link,
    package,
    price,
    voltage,
)
from tests.integration.test_model_baseline import _snapshot


def _track(connection: Connection, journal: Journal, item: Delivery) -> Receipt:
    return track(
        connection,
        journal,
        item,
        actor="engine:fixture",
        clock=lambda: item.fetched_at + timedelta(minutes=1),
    )


def _count(connection: Connection, table: sa.Table) -> int:
    return connection.scalar(sa.select(sa.func.count()).select_from(table)) or 0


def test_partial_updates_claim_confirm_and_survive_rollback_and_rebuild(
    rebuild_connection: Connection, tmp_path: Path
) -> None:
    connection = rebuild_connection
    journal = Journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    link(journal, RECORD)
    other = RECORD.model_copy(update={"key": "OFFER-00043"})
    link(journal, other)
    evidence = evidence_tables()
    claims, confirmations = evidence["claims"], evidence["claim_confirmations"]

    first = delivery(price("1.20"), package("SOT-23"), voltage("5.5"), fetch=1)
    with pytest.raises(RuntimeError, match="interrupted"), connection.begin_nested():
        _track(connection, journal, first)
        raise RuntimeError("interrupted")
    assert _count(connection, claims) == 0
    # The journaled version is pending; the same delivery completes its claims.
    assert _track(connection, journal, first).written == 6
    assert _track(connection, journal, first).written == 0

    price_only = _track(connection, journal, delivery(price("1.25"), fetch=2))
    assert price_only.written == 2
    emptied = _track(connection, journal, delivery(package(None), fetch=3))
    assert emptied.tracked.changes[0].change == "emptied"
    again = _track(connection, journal, delivery(package(None), fetch=4))
    assert again.tracked.outcome == "seen" and again.written == 2
    late = delivery(price("0.90"), fetch=0, fetched_at=T0 + timedelta(minutes=30))
    assert _track(connection, journal, late).tracked.outcome == "history"
    _track(connection, journal, delivery(price("7.00"), fetch=5, record=other))

    current = {
        row.field_id: row
        for row in connection.execute(
            claims_as_of(claims).where(claims.c.record_id == RECORD.record_id)
        )
    }
    assert current[PRICE].value_number == 1.25 and current[PRICE].supersedes is not None
    assert current[PACKAGE].missing_reason == "source_empty"
    assert current[VOLTAGE].change_kind == "added"
    assert _count(connection, claims) == 6 and _count(connection, confirmations) == 1

    identity = metadata(store.contract()).tables
    records = identity["identity.source_records"]
    seen = dict(connection.execute(sa.select(records.c.record_id, records.c.last_seen)).all())
    assert seen[RECORD.record_id] == T0 + timedelta(hours=4)
    assert seen[other.record_id] == T0 + timedelta(hours=5)
    assert _count(connection, identity["identity.source_versions"]) == 5
    assert _count(connection, identity["identity.change_sets"]) == 4

    # Check the deferred claim and evidence references before rebuilding in this transaction.
    names = tuple(
        sorted(
            str(key.name) for table in evidence.values() for key in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints("evidence", names, deferred=False))
    before = _snapshot(connection, [store.contract(), evidence_contract()])
    connection.exec_driver_sql("DROP SCHEMA identity CASCADE")
    rebuild(connection, data_dir=tmp_path)
    after = _snapshot(connection, [store.contract()])
    assert after == {key: value for key, value in before.items() if key in after}
