"""One Python policy for PostGIS, schema roles, and default privileges, as SQLAlchemy constructs."""

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.schemas import platform_policy
from kn.db.catalog import PG_ROLES
from kn.db.statements import (
    PUBLIC,
    AlterRole,
    AlterSchemaOwner,
    CreateExtension,
    CreateRole,
    ObjectKind,
    Privileges,
    UpdateExtension,
)

POLICY = platform_policy()
SCHEMAS: tuple[str, ...] = tuple(POLICY["schemas"])
ROLE_KINDS: tuple[str, ...] = tuple(POLICY["roleKinds"])
LOCK_NAMESPACE = 0x4B4E4253
# The Alembic version table lives here.
MIGRATION_SCHEMA = "system"
VERSION_TABLE = "alembic_version"
EXTENSION = "postgis"
EXTENSION_SCHEMA = "public"
ROLE_ATTRIBUTES = (
    "NOLOGIN",
    "NOSUPERUSER",
    "NOCREATEDB",
    "NOCREATEROLE",
    "NOREPLICATION",
    "NOBYPASSRLS",
    "INHERIT",
)
LOADER_TABLE = ("SELECT", "INSERT", "UPDATE", "DELETE")
LOADER_SEQUENCE = ("USAGE", "SELECT")
READER_TABLE = ("SELECT",)


def role_name(schema: str, kind: str) -> str:
    return f"kn_{schema}_{kind}"


def apply_platform(connection: Connection) -> None:
    """Converge roles and grants atomically under the same lock as schema deployment."""
    connection.execute(sa.select(sa.func.pg_advisory_xact_lock(LOCK_NAMESPACE, 0)))
    connection.execute(CreateExtension(EXTENSION, EXTENSION_SCHEMA))
    connection.execute(UpdateExtension(EXTENSION))
    database = str(connection.scalar(sa.select(sa.func.current_database())))
    connection.execute(Privileges("REVOKE", ("ALL",), "DATABASE", database, (PUBLIC,)))
    connection.execute(Privileges("REVOKE", ("CREATE",), "SCHEMA", EXTENSION_SCHEMA, (PUBLIC,)))
    for schema in SCHEMAS:
        _roles(connection, schema, database)
        _grants(connection, schema)


def _roles(connection: Connection, schema: str, database: str) -> None:
    for kind in ROLE_KINDS:
        role = role_name(schema, kind)
        exists = connection.scalar(
            sa.select(sa.literal(1)).select_from(PG_ROLES).where(PG_ROLES.c.rolname == role)
        )
        if not exists:
            connection.execute(CreateRole(role))
        connection.execute(AlterRole(role, ROLE_ATTRIBUTES))
        connection.execute(Privileges("GRANT", ("CONNECT",), "DATABASE", database, (role,)))
    connection.execute(sa.schema.CreateSchema(schema, if_not_exists=True))
    connection.execute(AlterSchemaOwner(schema, role_name(schema, "owner")))


def _grants(connection: Connection, schema: str) -> None:
    owner, loader, reader = (role_name(schema, kind) for kind in ROLE_KINDS)
    revoked = (PUBLIC, loader, reader)
    connection.execute(Privileges("REVOKE", ("ALL",), "SCHEMA", schema, revoked))
    connection.execute(Privileges("GRANT", ("USAGE",), "SCHEMA", schema, (loader, reader)))
    grants: tuple[tuple[tuple[str, ...], ObjectKind, ObjectKind, str], ...] = (
        (LOADER_TABLE, "ALL TABLES IN SCHEMA", "TABLES", loader),
        (LOADER_SEQUENCE, "ALL SEQUENCES IN SCHEMA", "SEQUENCES", loader),
        (READER_TABLE, "ALL TABLES IN SCHEMA", "TABLES", reader),
    )
    # Existing objects first, then the owner's defaults for objects created later.
    for privileges, existing, _, grantee in grants:
        connection.execute(Privileges("GRANT", privileges, existing, schema, (grantee,)))
    for privileges, _, future, grantee in grants:
        connection.execute(
            Privileges("GRANT", privileges, future, None, (grantee,), defaults=(owner, schema))
        )
