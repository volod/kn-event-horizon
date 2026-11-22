"""Transactional Alembic entrypoint, also used by deployment and tests."""

from collections.abc import Callable, Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

from kn.contracts import Contract
from kn.contracts.model import canonical
from kn.contracts.registry import marker_table, registered_contracts, validate_registry
from kn.db.catalog import PG_EXTENSION, PG_NAMESPACE, PG_ROLES, UNSAFE_ROLE_ATTRIBUTES
from kn.db.platform import (
    EXTENSION,
    MIGRATION_SCHEMA,
    ROLE_KINDS,
    SCHEMAS,
    apply_platform,
    role_name,
)
from kn.db.statements import ResetRole, SetRole
from kn.db.verification import verify_privileges, verify_registered_tables, verify_structure

MIGRATIONS = Path(__file__).parent / "migrations"
# The baseline reads the deployment set from here; tests supply a fixture registry.
CONTRACTS_ATTRIBUTE = "contracts"
__all__ = [
    "CONTRACTS_ATTRIBUTE",
    "MIGRATION_SCHEMA",
    "deployment",
    "governed_migrations",
    "record_installed",
    "upgrade",
    "verify",
    "verify_contracts",
]


def deployment(contracts: Sequence[Contract] | None = None) -> tuple[Contract, ...]:
    """The registered contracts, or a supplied set that passes the same validation."""
    if contracts is None:
        return registered_contracts()
    validate_registry(contracts)
    return tuple(contracts)


def migration_config(connection: Connection, contracts: Sequence[Contract] | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    config.attributes[CONTRACTS_ATTRIBUTE] = deployment(contracts)
    return config


def upgrade(connection: Connection, contracts: Sequence[Contract] | None = None) -> None:
    """`alembic upgrade head` in the caller's transaction; no migration commits independently."""
    command.upgrade(migration_config(connection, contracts), "head")


def governed_migrations(connection: Connection, migrate: Callable[[], None]) -> None:
    """The Alembic environment converges the platform policy around every revision run."""
    apply_platform(connection)
    connection.execute(SetRole(role_name(MIGRATION_SCHEMA, "owner")))
    migrate()
    connection.execute(ResetRole())
    apply_platform(connection)


def verify(connection: Connection, contracts: Sequence[Contract] | None = None) -> str:
    """Verify catalog policy and the migration revision without persistent probe objects."""
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    config = migration_config(connection, contracts)
    head = ScriptDirectory.from_config(config).get_current_head()
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
    verify_contracts(connection, config.attributes[CONTRACTS_ATTRIBUTE])
    verify_privileges(connection)
    postgis = connection.scalar(
        sa.select(PG_EXTENSION.c.extversion).where(PG_EXTENSION.c.extname == EXTENSION)
    )
    return f"kn roles verified: {len(SCHEMAS)} schemas, {len(SCHEMAS) * len(ROLE_KINDS)} roles, postgis {postgis}"


def verify_contracts(connection: Connection, contracts: Sequence[Contract] | None = None) -> None:
    """Every registered contract is installed at its digest, with its tables and no others.

    These read-only checks also run before a loader imports a package.
    """
    deployed = deployment(contracts)
    marker = marker_table()
    if not sa.inspect(connection).has_table(marker.name, schema=marker.schema):
        raise ValueError(
            "contract baseline changed; use an explicit development rebuild and backfill"
        )
    installed = {
        row.contract_id: (row.version, row.digest)
        for row in connection.execute(
            sa.select(marker.c.contract_id, marker.c.version, marker.c.digest)
        )
    }
    if installed != {
        contract.contract_id: (contract.version, contract.digest) for contract in deployed
    }:
        raise ValueError(
            "contract digest drift; rebuild development data or apply a release migration"
        )
    verify_structure(connection, deployed)
    verify_registered_tables(connection, deployed)


def record_installed(
    connection: Connection, contracts: Sequence[Contract], *, marker_schema: str | None = None
) -> None:
    """Write one marker row per contract after the baseline creates its tables."""
    marker = marker_table(marker_schema)
    connection.execute(
        marker.insert(),
        [
            {
                "contract_id": contract.contract_id,
                "version": contract.version,
                "digest": contract.digest,
                "storage_schema": contract.schema,
                "managed_tables_json": canonical([table.name for table in contract.tables]),
            }
            for contract in contracts
        ],
    )
