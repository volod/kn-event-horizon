"""Transactional Alembic entrypoint, also used by deployment and tests."""

from collections.abc import Callable
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

from kn.contracts import Contract, load_contract
from kn.contracts.model import canonical
from kn.contracts.sqlalchemy import metadata
from kn.db.catalog import PG_EXTENSION, PG_NAMESPACE, PG_ROLES, UNSAFE_ROLE_ATTRIBUTES
from kn.db.platform import EXTENSION, apply_platform, role_name
from kn.db.statements import ResetRole, SetRole
from kn.db.verification import verify_privileges, verify_structure

MIGRATIONS = Path(__file__).parent / "migrations"
# The Alembic version table lives here and is owned by this schema's owner role.
MIGRATION_SCHEMA = "system"


def migration_config(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    return config


def upgrade(connection: Connection) -> None:
    """`alembic upgrade head` in the caller's transaction; no migration commits independently."""
    command.upgrade(migration_config(connection), "head")


def governed_migrations(connection: Connection, migrate: Callable[[], None]) -> None:
    """The Alembic environment converges the platform policy around every revision run."""
    apply_platform(connection)
    connection.execute(SetRole(role_name(MIGRATION_SCHEMA, "owner")))
    migrate()
    connection.execute(ResetRole())
    apply_platform(connection)


def verify(connection: Connection) -> str:
    """Verify catalog policy and the migration revision without persistent probe objects."""
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from kn.db.platform import ROLE_KINDS, SCHEMAS

    head = ScriptDirectory.from_config(migration_config(connection)).get_current_head()
    current = MigrationContext.configure(
        connection, opts={"version_table_schema": MIGRATION_SCHEMA}
    )
    if current.get_current_revision() != head:
        raise ValueError("database schema revision differs from the governed head")
    for schema in SCHEMAS:
        owner = connection.scalar(
            sa.select(sa.func.pg_get_userbyid(PG_NAMESPACE.c.nspowner)).where(
                PG_NAMESPACE.c.nspname == schema
            )
        )
        if owner != role_name(schema, "owner"):
            raise ValueError(f"schema owner mismatch: {schema}")
        for kind in ROLE_KINDS:
            role = role_name(schema, kind)
            attributes = connection.execute(
                sa.select(*UNSAFE_ROLE_ATTRIBUTES).where(PG_ROLES.c.rolname == role)
            ).one_or_none()
            if attributes != (False,) * len(UNSAFE_ROLE_ATTRIBUTES):
                raise ValueError(f"unsafe or missing role: {role}")
    verify_contract(connection)
    verify_privileges(connection)
    postgis = connection.scalar(
        sa.select(PG_EXTENSION.c.extversion).where(PG_EXTENSION.c.extname == EXTENSION)
    )
    return f"kn roles verified: {len(SCHEMAS)} schemas, {len(SCHEMAS) * len(ROLE_KINDS)} roles, postgis {postgis}"


def verify_contract(connection: Connection) -> None:
    """Read-only checks also run before a loader imports a package."""
    contract = load_contract()
    model = metadata(contract)
    if not sa.inspect(connection).has_table("satcom_contract", schema=contract.schema):
        raise ValueError(
            "contract baseline changed; use an explicit development rebuild and backfill"
        )
    marker = model.tables[f"{contract.schema}.satcom_contract"]
    installed = connection.execute(
        sa.select(marker.c.version, marker.c.digest).where(
            marker.c.contract_id == contract.contract_id
        )
    ).one_or_none()
    if installed != (contract.version, contract.digest):
        raise ValueError(
            "contract digest drift; rebuild development data or apply a release migration"
        )
    verify_structure(connection)


def install_contract(connection: Connection, contract: Contract) -> None:
    """Initialize the shared installed-contract marker after baseline or generated DDL."""
    marker = metadata(contract).tables[f"{contract.schema}.satcom_contract"]
    connection.execute(
        marker.insert(),
        {
            "contract_id": contract.contract_id,
            "version": contract.version,
            "digest": contract.digest,
            "managed_tables_json": canonical([table.name for table in contract.tables]),
        },
    )
