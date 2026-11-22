"""KN group roles: each role is allowed what it is granted and refused outside its grants.

Every probe runs inside one transaction per test that is always rolled back, so the KN schemas are
unchanged afterwards. Probe tables carry a random name, so parallel runs never collide.
"""

import secrets
from collections.abc import Iterator

import pytest
from psycopg import errors, sql

from kn.db.platform import SCHEMAS as PLATFORM_SCHEMAS
from tests.integration.harness import Connection

SCHEMAS = list(PLATFORM_SCHEMAS)


def _role(schema: str, kind: str) -> sql.Identifier:
    return sql.Identifier(f"kn_{schema}_{kind}")


def _as_role(connection: Connection, role: sql.Identifier, statement: sql.Composable) -> None:
    """Run one statement as a role inside a savepoint, so a refusal keeps the transaction."""
    with connection.transaction():
        connection.execute(sql.SQL("SET LOCAL ROLE {}").format(role))
        connection.execute(statement)
        connection.execute("RESET ROLE")


def _refused(connection: Connection, role: sql.Identifier, statement: sql.Composable) -> None:
    with pytest.raises(errors.InsufficientPrivilege):
        _as_role(connection, role, statement)


def _create_probe(connection: Connection, schema: str, name: str) -> sql.Identifier:
    table = sql.Identifier(schema, name)
    _as_role(
        connection,
        _role(schema, "owner"),
        sql.SQL("CREATE TABLE {} (id integer GENERATED ALWAYS AS IDENTITY, label text)").format(
            table
        ),
    )
    return table


@pytest.fixture
def probe_name() -> str:
    return f"kn_test_roles_{secrets.token_hex(4)}"


@pytest.fixture
def probe(db_connection: Connection, probe_name: str) -> Iterator[Connection]:
    """The test's connection inside a transaction that is rolled back, checked afterwards."""
    with db_connection.transaction(force_rollback=True):
        yield db_connection
    kept = db_connection.execute(
        "SELECT (SELECT count(*) FROM pg_catalog.pg_class WHERE relname LIKE %(name)s)"
        " + (SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname LIKE %(name)s)",
        {"name": f"{probe_name}%"},
    ).fetchone()
    db_connection.rollback()
    assert kept == (0,), f"probe objects {probe_name}* were committed"


@pytest.mark.parametrize("schema", SCHEMAS)
def test_each_role_acts_inside_its_own_schema_and_is_refused_beyond_its_grants(
    probe: Connection, probe_name: str, schema: str
) -> None:
    owner, loader, reader = (_role(schema, kind) for kind in ("owner", "loader", "reader"))
    # Created by the owner after the bootstrap, so loader and reader reach it through the
    # default privileges, as they will reach the tables of later tasks.
    table = _create_probe(probe, schema, probe_name)
    insert = sql.SQL("INSERT INTO {} (label) VALUES ('probe')").format(table)
    select = sql.SQL("SELECT count(*) FROM {}").format(table)
    other_table = sql.Identifier(schema, f"{probe_name}_refused")
    create_other = sql.SQL("CREATE TABLE {} (id integer)").format(other_table)

    _as_role(probe, loader, insert)
    _as_role(probe, loader, sql.SQL("DELETE FROM {}").format(table))
    _as_role(probe, reader, select)

    _refused(probe, loader, create_other)
    _refused(probe, loader, sql.SQL("TRUNCATE {}").format(table))
    _refused(probe, reader, insert)
    _refused(probe, reader, create_other)
    name = sql.Identifier(probe_name)
    for role in (owner, loader, reader):
        _refused(probe, role, sql.SQL("CREATE TABLE public.{} (id integer)").format(name))
        _refused(probe, role, sql.SQL("CREATE TEMPORARY TABLE {} (id integer)").format(name))


@pytest.mark.parametrize("schema", SCHEMAS)
def test_no_role_reaches_another_schema(probe: Connection, probe_name: str, schema: str) -> None:
    other = SCHEMAS[(SCHEMAS.index(schema) + 1) % len(SCHEMAS)]
    table = _create_probe(probe, other, probe_name)

    _refused(
        probe,
        _role(schema, "owner"),
        sql.SQL("CREATE TABLE {} (id integer)").format(
            sql.Identifier(other, f"{probe_name}_refused")
        ),
    )
    _refused(
        probe,
        _role(schema, "loader"),
        sql.SQL("INSERT INTO {} (label) VALUES ('x')").format(table),
    )
    _refused(probe, _role(schema, "reader"), sql.SQL("SELECT * FROM {}").format(table))


def test_no_kn_role_can_log_in(probe: Connection) -> None:
    rows = probe.execute(
        "SELECT rolname FROM pg_catalog.pg_roles WHERE rolname ~ '^kn_' AND rolcanlogin"
    ).fetchall()

    assert rows == []


def test_a_login_in_a_reader_group_becomes_no_other_role(
    probe: Connection, probe_name: str
) -> None:
    # SET ROLE is checked against the session user, so the probe acts as a login of the group.
    login = sql.Identifier(probe_name)
    probe.execute(sql.SQL("CREATE ROLE {} LOGIN IN ROLE kn_system_reader").format(login))

    def set_role(role: str) -> None:
        with probe.transaction():
            probe.execute(sql.SQL("SET LOCAL SESSION AUTHORIZATION {}").format(login))
            probe.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
            probe.execute("RESET ROLE")
            probe.execute("RESET SESSION AUTHORIZATION")

    set_role("kn_system_reader")
    for role in ("postgres", "kn_system_owner", "kn_system_loader", "kn_space_reader"):
        with pytest.raises(errors.InsufficientPrivilege):
            set_role(role)
