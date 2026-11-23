"""Every registered contract deploys, rebuilds, and verifies through one Alembic baseline."""

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.registry import marker_table
from kn.db.governance import verify
from kn.db.rebuild import rebuild
from tests.contracts.test_registry import fixture_contracts
from tests.integration.test_rebuild import catalog


def test_rebuild_creates_and_records_every_registered_contract(
    rebuild_connection: Connection,
) -> None:
    contracts = fixture_contracts()
    rebuild(rebuild_connection, contracts)
    marker = marker_table()
    rows = rebuild_connection.execute(
        sa.select(marker.c.contract_id, marker.c.version, marker.c.digest, marker.c.storage_schema)
    ).all()
    assert sorted(rows) == sorted(
        (item.contract_id, item.version, item.digest, item.schema) for item in contracts
    )
    inspector = sa.inspect(rebuild_connection)
    for contract in contracts:
        assert {table.name for table in contract.tables} <= set(
            inspector.get_table_names(schema=contract.schema)
        )
    assert "fixture_observations_time_idx" in {
        index["name"] for index in inspector.get_indexes("fixture_observations", schema="space")
    }
    verify(rebuild_connection, contracts)
    first = catalog(rebuild_connection)
    rebuild(rebuild_connection, contracts)
    assert catalog(rebuild_connection) == first


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("DROP TABLE semantic.fixture_terms", "structure"),
        (
            "UPDATE system.installed_contracts SET digest = 'old' "
            "WHERE contract_id = 'kn.space.fixture_observations'",
            "digest drift",
        ),
        (
            "DELETE FROM system.installed_contracts WHERE storage_schema = 'semantic'",
            "digest drift",
        ),
        (
            "UPDATE system.installed_contracts SET storage_schema = 'identity' "
            "WHERE contract_id = 'kn.space.fixture_observations'",
            "digest drift",
        ),
        (
            "UPDATE system.installed_contracts SET managed_tables_json = '[]' "
            "WHERE contract_id = 'kn.space.fixture_observations'",
            "digest drift",
        ),
        ("CREATE TABLE space.unregistered (id integer)", "schema space"),
        ("CREATE TABLE identity.unregistered (id integer)", "schema identity"),
    ],
)
def test_verification_refuses_missing_drifted_and_unregistered_tables(
    rebuild_connection: Connection, damage: str, message: str
) -> None:
    contracts = fixture_contracts()
    rebuild(rebuild_connection, contracts)
    rebuild_connection.exec_driver_sql(damage)
    with pytest.raises(ValueError, match=message):
        verify(rebuild_connection, contracts)


def test_the_default_deployment_refuses_a_fixture_contract_left_behind(
    rebuild_connection: Connection,
) -> None:
    rebuild(rebuild_connection, fixture_contracts())
    with pytest.raises(ValueError, match="digest drift"):
        verify(rebuild_connection)
    rebuild(rebuild_connection)
    verify(rebuild_connection)
