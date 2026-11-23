"""Combined fixture rebuild for the registered subset of the development model.

This prepares the checkpoint; missing model owners remain open plan prerequisites.
"""

import json
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.compiler import compile_registry
from kn.contracts.model import Contract, canonical
from kn.contracts.registry import registered_contracts
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import verify
from kn.db.platform import role_name
from kn.db.rebuild import rebuild
from kn.db.statements import ResetRole, SetConstraints, SetRole
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import Package, read_package
from kn.semantic import Snapshot, validate_model
from kn.semantic.seeds import reviewed_snapshot
from tests.integration.identity_fixtures import seed_identity_fixture
from tests.integration.review_fixtures import replay_review_fixture
from tests.integration.semantic_fixtures import native_rows, text_fixture
from tests.semantic.conftest import REFERENCES

# Every new owner must supply fixture replay before this suite can cover its registration.
FIXTURE_OWNERS = {
    "kn.system.governance",
    "kn.space.satcom",
    "kn.core.semantic",
    "kn.core.human_verification",
    "kn.core.identity",
}


def _snapshot(connection: Connection, contracts: Sequence[Contract]) -> dict[str, list[dict]]:
    result = {}
    for contract in contracts:
        for table in metadata(contract).tables.values():
            result[table.fullname] = [
                dict(row)
                for row in connection.execute(
                    sa.select(table).order_by(*table.primary_key.columns)
                ).mappings()
            ]
    return result


def _encoded(value: object) -> dict[str, str]:
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"type": "timestamp", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    raise TypeError(f"unsupported baseline value: {type(value).__name__}")


def _assert_satcom(snapshot: dict[str, list[dict]], package: Package, contract: Contract) -> None:
    for name, rows in package.rows.items():
        keys = contract.table(name).primary_key
        expected = sorted(rows, key=lambda row: tuple(row[key] for key in keys))
        assert snapshot[f"space.{name}"] == expected, name
    raw = {
        (row["table_name"], row["row_number"]): row["cells_json"]
        for row in snapshot["space.satcom_rows"]
    }
    assert raw == {
        (name, number): canonical(row)
        for name, rows in package.raw_rows.items()
        for number, row in enumerate(rows, start=2)
    }


def _assert_semantic(
    snapshot: dict[str, list[dict]], contract: Contract, fixture: Snapshot
) -> None:
    expected_rows = native_rows(contract, reviewed_snapshot())
    for name, rows in fixture.items():
        expected_rows.setdefault(name, []).extend(rows)
    for name, rows in expected_rows.items():
        table = contract.table(name)
        expected = list(rows)
        expected.sort(key=lambda row: tuple(row[key] for key in table.primary_key))
        assert snapshot[f"semantic.{name}"] == expected, name


def _drain_references(connection: Connection, contract: Contract) -> None:
    names = tuple(
        sorted(
            str(reference.name)
            for table in metadata(contract).tables.values()
            for reference in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints(contract.schema, names, deferred=False))
    connection.execute(SetConstraints(contract.schema, names, deferred=True))


def test_registered_model_fixture_rebuild_is_lossless_and_repeatable(
    rebuild_connection: Connection, source_package: Path, tmp_path: Path
) -> None:
    contracts = registered_contracts()
    assert {contract.contract_id for contract in contracts} == FIXTURE_OWNERS, (
        "extend combined-baseline fixtures for every newly registered model owner"
    )
    compile_registry(contracts, tmp_path / "compiled")
    compile_registry(contracts, tmp_path / "compiled", check=True)
    satcom = next(contract for contract in contracts if contract.contract_id == "kn.space.satcom")
    semantic = next(
        contract for contract in contracts if contract.contract_id == "kn.core.semantic"
    )
    package = read_package(source_package, satcom)
    semantic_fixture = text_fixture()
    validate_model(semantic_fixture, REFERENCES)
    semantic_fixture = native_rows(semantic, semantic_fixture)
    connection = rebuild_connection
    seed_identity_fixture(tmp_path)
    snapshots = []
    for iteration in range(2):
        rebuild(connection, contracts, data_dir=tmp_path)
        connection.execute(SetRole(role_name(satcom.schema, "loader")))
        assert import_package(connection, package, satcom)
        assert not import_package(connection, package, satcom)
        connection.execute(ResetRole())
        _drain_references(connection, satcom)
        connection.execute(SetRole(role_name(semantic.schema, "loader")))
        for table in metadata(semantic).tables.values():
            connection.execute(table.insert(), semantic_fixture[table.name])
        connection.execute(ResetRole())
        _drain_references(connection, semantic)
        replay_review_fixture(connection, contracts, tmp_path)
        verify(connection, contracts)
        snapshot = _snapshot(connection, contracts)
        _assert_satcom(snapshot, package, satcom)
        _assert_semantic(snapshot, semantic, semantic_fixture)
        assert all(snapshot.values()), "provide at least one representative row per table"
        (tmp_path / f"rebuild-{iteration + 1}.json").write_text(
            json.dumps(snapshot, default=_encoded, ensure_ascii=True, sort_keys=True, indent=2)
            + "\n",
            encoding="ascii",
        )
        snapshots.append(snapshot)
    assert snapshots[0] == snapshots[1]
