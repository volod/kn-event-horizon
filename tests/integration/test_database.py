"""Smoke tests of the integration database: the pinned server, logins, and scratch schemas."""

import secrets
from pathlib import Path

import psycopg
import pytest
import yaml
from psycopg import sql

from tests.integration.harness import (
    SCRATCH_PREFIX,
    TOKEN_DIGITS,
    TOKEN_LIMIT,
    Connection,
    IntegrationDatabase,
    ScratchSchemas,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = yaml.safe_load((ROOT / "deploy" / "versions.yaml").read_text(encoding="utf-8"))
COMPONENTS = MANIFEST["images"]["postgres"]["components"]
# The bootstrap installs PostGIS only. The image's own init script would add more.
BOOTSTRAP_EXTENSIONS = ["plpgsql", "postgis"]
# "Kyiv" in Ukrainian, written as escapes to keep the source ASCII.
KYIV = "\u041a\u0438\u0457\u0432"


def _schema_exists(connection: Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT count(*) FROM pg_catalog.pg_namespace WHERE nspname = %s", [name]
    ).fetchone()
    return row == (1,)


def test_the_database_runs_the_pinned_server_with_the_bootstrap_extensions(
    db_connection: Connection,
) -> None:
    row = db_connection.execute(
        "SELECT current_setting('server_version'), public.postgis_lib_version(), "
        "(SELECT array_agg(extname::text ORDER BY extname) FROM pg_catalog.pg_extension)"
    ).fetchone()

    assert row is not None
    version, postgis, extensions = row
    assert version.split()[0] == COMPONENTS["postgresql"]
    assert postgis == COMPONENTS["postgis"]
    assert extensions == BOOTSTRAP_EXTENSIONS


def test_a_tcp_login_without_a_password_is_refused(
    integration_database: IntegrationDatabase, tmp_path: Path
) -> None:
    with pytest.raises(psycopg.OperationalError, match="password"):
        integration_database.connect(password="", passfile=str(tmp_path / "no-passfile")).close()


def test_a_scratch_schema_round_trips_a_geometry_and_ukrainian_text(
    scratch_schemas: ScratchSchemas, db_connection: Connection
) -> None:
    table = sql.Identifier(scratch_schemas.schema("smoke"), "place")
    db_connection.execute(
        sql.SQL(
            "CREATE TABLE {} (id integer PRIMARY KEY, label text NOT NULL, "
            "geom public.geometry(Point, 4326) NOT NULL)"
        ).format(table)
    )
    db_connection.execute(
        sql.SQL(
            "INSERT INTO {} VALUES (1, %s, public.ST_SetSRID(public.ST_MakePoint(%s, %s), 4326))"
        ).format(table),
        [KYIV, 30.52, 50.45],
    )

    row = db_connection.execute(
        sql.SQL("SELECT label, public.ST_AsText(geom) FROM {}").format(table)
    ).fetchone()

    assert row == (KYIV, "POINT(30.52 50.45)")


def test_scratch_schemas_are_private_to_their_session_and_dropped_when_it_closes(
    integration_database: IntegrationDatabase,
    scratch_schemas: ScratchSchemas,
    db_connection: Connection,
) -> None:
    own = scratch_schemas.schema("kept")
    other = ScratchSchemas.create(integration_database)
    try:
        private = other.schema("private")
        assert other.prefix != scratch_schemas.prefix
        assert _schema_exists(db_connection, private)
    finally:
        other.close()

    assert not _schema_exists(db_connection, private)
    assert _schema_exists(db_connection, own)


def test_a_new_session_drops_the_schemas_of_a_session_that_holds_no_lock(
    integration_database: IntegrationDatabase,
    scratch_schemas: ScratchSchemas,
    db_connection: Connection,
) -> None:
    own = scratch_schemas.schema("live")
    left_behind = f"{SCRATCH_PREFIX}{secrets.randbelow(TOKEN_LIMIT):0{TOKEN_DIGITS}x}_left"
    with integration_database.connect(autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(left_behind)))

    ScratchSchemas.create(integration_database).close()

    assert not _schema_exists(db_connection, left_behind)
    assert _schema_exists(db_connection, own)


@pytest.mark.parametrize("name", ["", "Upper", "1st", "with-dash", "x" * 47])
def test_a_scratch_schema_name_must_be_a_short_lowercase_identifier(
    scratch_schemas: ScratchSchemas, name: str
) -> None:
    with pytest.raises(ValueError, match="scratch schema name"):
        scratch_schemas.schema(name)
