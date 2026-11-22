"""Generated SQL executes directly on scratch PostGIS schemas and enforces intent."""

from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from kn.contracts import load_contract
from kn.contracts.ddl import postgresql_ddl
from tests.contracts.test_compiler import compiler_document, reference_catalog, write_document
from tests.integration.harness import IntegrationDatabase, ScratchSchemas


def test_generated_ddl_applies_complete_satcom_model(
    integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> None:
    schema = scratch_schemas.schema("compiled_satcom")
    contract = replace(load_contract(), schema=schema)
    with integration_database.connect() as connection:
        connection.execute(postgresql_ddl(contract))
        rows = connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s", [schema]
        ).fetchall()
        assert {row[0] for row in rows} == {table.name for table in contract.tables}
        # Unicode literals in generated ASCII SQL preserve original comments and enum checks.
        expected = next(
            field
            for table in contract.tables
            for field in table.fields
            if not field.description.isascii()
        )
        description = connection.execute(
            "SELECT col_description(c.oid, a.attnum) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN pg_attribute a ON a.attrelid = c.oid "
            "WHERE n.nspname = %s AND a.attname = %s AND col_description(c.oid, a.attnum) = %s",
            [schema, expected.name, expected.description],
        ).fetchone()
        assert description == (expected.description,)


def test_generated_geometry_checks_comments_and_indexes(
    tmp_path: Path, integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> None:
    schema = scratch_schemas.schema("compiled_geometry")
    data = compiler_document()
    contract = replace(
        load_contract(write_document(tmp_path, data), references=reference_catalog(tmp_path)),
        schema=schema,
    )
    ddl = postgresql_ddl(contract)
    with integration_database.connect() as connection:
        connection.execute(ddl)
        insert = sql.SQL(
            'INSERT INTO {}."select" (id, coverage) VALUES (%s, ST_GeomFromText(%s, %s))'
        ).format(sql.Identifier(schema))
        connection.execute(insert, [1, "POLYGON((0 0,0 1,1 1,0 0))", 4326])
        for wkt, srid in [
            ("POLYGON EMPTY", 4326),
            ("POLYGON((0 0,1 1,0 1,1 0,0 0))", 4326),
            ("POINT(0 0)", 4326),
            ("POLYGON((0 0,0 1,1 1,0 0))", 3857),
        ]:
            with pytest.raises(psycopg.Error), connection.transaction():
                connection.execute(insert, [2, wkt, srid])
        indexes = connection.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname = %s AND indexname = 'coverage_idx'",
            [schema],
        ).fetchone()
        assert indexes is not None and "USING gist" in indexes[0]
        comment = connection.execute(
            "SELECT obj_description(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s AND c.relname = 'select'",
            [schema],
        ).fetchone()
        assert comment == (data["schema"][0]["description"],)


def test_generated_partition_parent_accepts_reviewed_partition(
    tmp_path: Path, integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> None:
    data = compiler_document()
    table = data["schema"][0]
    table["customProperties"] = [
        {"property": "kn.partition", "value": {"strategy": "range", "fields": ["id"]}}
    ]
    table["properties"] = table["properties"][:1]
    schema = scratch_schemas.schema("compiled_partition")
    contract = replace(load_contract(write_document(tmp_path, data)), schema=schema)
    with integration_database.connect() as connection:
        connection.execute(postgresql_ddl(contract))
        connection.execute(
            sql.SQL(
                'CREATE TABLE {}.part PARTITION OF {}."select" FOR VALUES FROM (0) TO (10)'
            ).format(sql.Identifier(schema), sql.Identifier(schema))
        )
        connection.execute(
            sql.SQL('INSERT INTO {}."select" (id) VALUES (1)').format(sql.Identifier(schema))
        )
        assert connection.execute(
            sql.SQL("SELECT id FROM {}.part").format(sql.Identifier(schema))
        ).fetchone() == (1,)
