"""Rebuild loads reviewed vocabulary as DML and preserves stable content across reruns."""

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.rebuild import rebuild
from kn.db.seeds import load_reviewed_seeds
from kn.semantic.seeds import reviewed_snapshot
from kn.semantic.structure import semantic_contract


def stored_snapshot(connection: Connection) -> dict[str, list[dict]]:
    model = metadata(semantic_contract())
    return {
        name: [
            dict(row)
            for row in connection.execute(
                sa.select(model.tables["semantic." + name]).order_by(
                    *model.tables["semantic." + name].primary_key.columns
                )
            ).mappings()
        ]
        for name in reviewed_snapshot()
    }


def test_reviewed_seeds_rebuild_twice_idempotency_and_conflict(
    rebuild_connection: Connection,
) -> None:
    connection = rebuild_connection
    rebuild(connection)
    first = stored_snapshot(connection)
    expected = reviewed_snapshot()
    assert len(first["terms"]) == 825
    assert len(first["concept_mappings"]) == 69
    assert sum(row["verification_state"] == "verified" for row in first["concept_schemes"]) == 4
    for name, rows in expected.items():
        assert len(first[name]) == len(rows)
        assert {
            tuple(sorted((key, value) for key, value in row.items() if value is not None))
            for row in rows
        } == {
            tuple(sorted((key, value) for key, value in row.items() if value is not None))
            for row in first[name]
        }
    load_reviewed_seeds(connection)
    assert stored_snapshot(connection) == first
    assert connection.scalar(sa.text("SELECT current_user = session_user"))
    rebuild(connection)
    assert stored_snapshot(connection) == first
    assert connection.scalar(sa.text("SELECT count(*) FROM semantic.entity_tags")) == 0
    with pytest.raises(ValueError, match="conflicts"), connection.begin_nested():
        connection.exec_driver_sql(
            "UPDATE semantic.terms SET definition='changed' WHERE code='S01'"
        )
        load_reviewed_seeds(connection)
    assert stored_snapshot(connection) == first
