"""One Python policy for PostGIS, schema roles, and default privileges."""

import json

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.schemas import RESOURCES

POLICY = json.loads((RESOURCES / "platform.json").read_text())
SCHEMAS: tuple[str, ...] = tuple(POLICY["schemas"])
ROLE_KINDS: tuple[str, ...] = tuple(POLICY["roleKinds"])
LOCK_NAMESPACE = 0x4B4E4253
LOADER_TABLE = "SELECT, INSERT, UPDATE, DELETE"


def ddl(connection: Connection, statement: str) -> None:
    """Platform DDL is generated only from validated internal identifiers, never input data."""
    connection.execute(sa.DDL(statement))


def apply_platform(connection: Connection) -> None:
    """Converge roles and grants atomically under the same lock as schema deployment."""
    connection.execute(sa.select(sa.func.pg_advisory_xact_lock(LOCK_NAMESPACE, 0)))
    ddl(connection, "CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")
    ddl(connection, "ALTER EXTENSION postgis UPDATE")
    database = connection.scalar(sa.select(sa.func.current_database()))
    quoted_db = connection.dialect.identifier_preparer.quote_identifier(str(database))
    ddl(connection, f"REVOKE ALL ON DATABASE {quoted_db} FROM PUBLIC")
    ddl(connection, "REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    for schema in SCHEMAS:
        _roles(connection, schema, quoted_db)
        _grants(connection, schema)


def _roles(connection: Connection, schema: str, database: str) -> None:
    for kind in ROLE_KINDS:
        role = f"kn_{schema}_{kind}"
        exists = connection.scalar(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
        )
        if not exists:
            ddl(connection, f"CREATE ROLE {role}")
        ddl(
            connection,
            f"ALTER ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOREPLICATION NOBYPASSRLS INHERIT",
        )
        ddl(connection, f"GRANT CONNECT ON DATABASE {database} TO {role}")
    ddl(connection, f"CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION kn_{schema}_owner")
    ddl(connection, f"ALTER SCHEMA {schema} OWNER TO kn_{schema}_owner")


def _grants(connection: Connection, schema: str) -> None:
    owner, loader, reader = (f"kn_{schema}_{kind}" for kind in ROLE_KINDS)
    ddl(connection, f"REVOKE ALL ON SCHEMA {schema} FROM PUBLIC, {loader}, {reader}")
    ddl(connection, f"GRANT USAGE ON SCHEMA {schema} TO {loader}, {reader}")
    for prefix in ("", f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {schema} "):
        tables = "TABLES" if prefix else f"ALL TABLES IN SCHEMA {schema}"
        sequences = "SEQUENCES" if prefix else f"ALL SEQUENCES IN SCHEMA {schema}"
        ddl(connection, f"{prefix}GRANT {LOADER_TABLE} ON {tables} TO {loader}")
        ddl(connection, f"{prefix}GRANT USAGE, SELECT ON {sequences} TO {loader}")
        ddl(connection, f"{prefix}GRANT SELECT ON {tables} TO {reader}")
