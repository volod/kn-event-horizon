"""Generated names, release evolution, and structural checks on PostGIS scratch schemas."""

from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import Connection

from kn.contracts import Contract, Field, load_contract
from kn.contracts.ddl import postgresql_ddl
from kn.contracts.evolution import evolve
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import install_contract
from kn.db.verification import verify_compiled_catalog, verify_structure
from tests.contracts.test_compiler import compiler_document, reference_catalog, write_document
from tests.contracts.test_physical import LONG_FIELD, LONG_TABLE, contract_with, field, reference
from tests.integration.harness import IntegrationDatabase, ScratchSchemas


@pytest.fixture
def scratch_connection(integration_database: IntegrationDatabase) -> Iterator[Connection]:
    """A rolled-back transaction, so each test leaves no object in its scratch schema."""
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            yield connection
            transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def in_schema(scratch_schemas: ScratchSchemas) -> Callable[[Contract, str], Contract]:
    return lambda contract, name: replace(contract, schema=scratch_schemas.schema(name))


def test_long_and_composite_generated_names_apply_and_verify(
    tmp_path: Path, scratch_connection: Connection, in_schema: Callable[[Contract, str], Contract]
) -> None:
    parent = [field(name, key=True) for name in ("a", "b", "c")]
    child = [
        field("k", key=True),
        field("a2"),
        field("b2"),
        field("c2", foreignKey=reference("a2", "b2", "c2")),
        field("d2", foreignKey=reference("a2", "b2", "d2")),
    ]
    long_table = [
        field("id", key=True),
        field(LONG_FIELD, "string", enum=["x", "y"]),
        field("g" * 47, "string", partialDate=True),
    ]
    data = contract_with(("parent", parent), ("child", child), (LONG_TABLE, long_table))
    contract = load_contract(write_document(tmp_path, data))
    contract = in_schema(contract, "names")
    scratch_connection.exec_driver_sql(postgresql_ddl(contract))
    verify_compiled_catalog(scratch_connection, contract)
    verify_structure(scratch_connection, contract)


def test_additive_evolution_applies_the_comments_that_verification_compares(
    scratch_connection: Connection, in_schema: Callable[[Contract, str], Contract]
) -> None:
    old = in_schema(load_contract(), "evolution")
    countries = old.table("countries")
    fields = list(countries.fields)
    fields[2] = replace(fields[2], description="Changed column description")
    added = Field("new_note", "space.countries.new_note", "string", False, False, "New note")
    table = replace(countries, description="Changed table description", fields=(*fields, added))
    new = replace(
        old,
        version="1.1.0",
        tables=tuple(table if item.name == table.name else item for item in old.tables),
    )
    metadata(old).create_all(scratch_connection)
    install_contract(scratch_connection, old)
    evolve(Operations(MigrationContext.configure(scratch_connection)), old, new)
    verify_structure(scratch_connection, new)


@pytest.mark.filterwarnings("ignore:Did not recognize type 'geometry'")
def test_structural_verification_compares_geometry_types(
    tmp_path: Path, scratch_connection: Connection, in_schema: Callable[[Contract, str], Contract]
) -> None:
    document = write_document(tmp_path, compiler_document())
    contract = load_contract(document, references=reference_catalog(tmp_path))
    contract = in_schema(contract, "geometry")
    scratch_connection.exec_driver_sql(postgresql_ddl(contract))
    verify_structure(scratch_connection, contract)
    scratch_connection.exec_driver_sql(
        f'ALTER TABLE {contract.schema}."select" ALTER COLUMN coverage '
        "TYPE geometry(MultiPolygon,4326) USING ST_Multi(coverage)"
    )
    with pytest.raises(ValueError, match="structure"):
        verify_structure(scratch_connection, contract)
