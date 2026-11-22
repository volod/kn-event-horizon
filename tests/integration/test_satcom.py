"""Real source mixtures preserve every typed value and raw cell on PostgreSQL."""

import secrets
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from kn.contracts import Field, load_contract
from kn.contracts.evolution import evolve
from kn.contracts.sqlalchemy import metadata
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import read_package
from tests.integration.harness import IntegrationDatabase, ScratchSchemas


def test_real_mixture_round_trips_and_additive_evolution_preserves_data(
    integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas, source_package: Path
) -> None:
    schema = scratch_schemas.schema("satcom")
    contract = replace(load_contract(), schema=schema)
    package = read_package(source_package, contract)
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    model = metadata(contract)
    try:
        with engine.begin() as connection:
            model.create_all(connection)
            connection.execute(
                model.tables[f"{schema}.satcom_contract"].insert(),
                {
                    "contract_id": contract.contract_id,
                    "version": contract.version,
                    "digest": contract.digest,
                    "managed_tables_json": "[]",
                },
            )
            assert import_package(connection, package, contract)
        with engine.begin() as connection:
            assert not import_package(connection, package, contract)
            for name, expected in package.rows.items():
                table = model.tables[f"{schema}.{name}"]
                actual = connection.execute(sa.select(table)).mappings().all()
                keys = contract.table(name).primary_key
                actual_by_key = {tuple(row[field] for field in keys): dict(row) for row in actual}
                expected_by_key = {tuple(row[field] for field in keys): row for row in expected}
                assert actual_by_key == expected_by_key, name
            countries = contract.table("countries")
            updated = replace(
                countries,
                fields=(
                    *countries.fields,
                    Field("new_note", "space.countries.new_note", "string", False, False),
                ),
            )
            next_contract = replace(
                contract,
                version="1.1.0",
                tables=tuple(
                    updated if table.name == "countries" else table for table in contract.tables
                ),
            )
            evolve(Operations(MigrationContext.configure(connection)), contract, next_contract)
            assert connection.scalar(
                sa.select(sa.func.count()).select_from(
                    metadata(next_contract).tables[f"{schema}.countries"]
                )
            ) == len(package.rows["countries"])
        # A deferred FK must fail at commit, and the import manifest must roll back with it.
        broken_id = "f" * 64
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                model.tables[f"{schema}.satcom_imports"].insert(),
                {
                    "import_id": broken_id,
                    "contract_version": contract.version,
                    "contract_digest": contract.digest,
                    "adapter_version": contract.source_profile,
                },
            )
            claim = dict(package.rows["evidence_claims"][0])
            claim.update(import_id=broken_id, source_id="missing")
            connection.execute(model.tables[f"{schema}.evidence_claims"].insert(), claim)
        with engine.connect() as connection:
            table = model.tables[f"{schema}.satcom_imports"]
            assert (
                connection.scalar(
                    sa.select(sa.func.count())
                    .select_from(table)
                    .where(table.c.import_id == broken_id)
                )
                == 0
            )
    finally:
        engine.dispose()


def test_development_rebuild_is_transactional_and_keeps_unmanaged_tables(
    integration_database: IntegrationDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kn.db.governance import verify_contract
    from kn.db.rebuild import rebuild

    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    model = metadata(load_contract())
    imports = model.tables["space.satcom_imports"]
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    try:
        with engine.connect() as connection:
            original = connection.scalar(sa.select(sa.func.count()).select_from(imports))
            connection.rollback()
            transaction = connection.begin()
            try:
                unrelated = sa.Table(
                    f"kn_unmanaged_rebuild_{secrets.token_hex(4)}",
                    sa.MetaData(schema="space"),
                    sa.Column("id", sa.Integer(), primary_key=True),
                )
                unrelated.create(connection)
                connection.execute(unrelated.insert(), {"id": 7})
                rebuild(connection)
                assert connection.scalar(sa.select(unrelated.c.id)) == 7
                assert connection.scalar(sa.select(sa.func.count()).select_from(imports)) == 0
                verify_contract(connection)
            finally:
                transaction.rollback()
            assert connection.scalar(sa.select(sa.func.count()).select_from(imports)) == original
    finally:
        engine.dispose()
