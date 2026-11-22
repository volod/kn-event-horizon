"""Transactional Alembic entrypoint, also used by deployment and tests."""

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

from kn.contracts import Contract, load_contract
from kn.contracts.loader import canonical
from kn.contracts.sqlalchemy import metadata
from kn.db.platform import apply_platform, ddl
from kn.db.verification import verify_privileges, verify_structure

MIGRATIONS = Path(__file__).parent / "migrations"


def upgrade(connection: Connection) -> None:
    """The caller owns the transaction; no migration commits independently."""
    apply_platform(connection)
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    ddl(connection, "SET LOCAL ROLE kn_system_owner")
    command.upgrade(config, "head")
    ddl(connection, "RESET ROLE")
    apply_platform(connection)


def verify(connection: Connection) -> str:
    """Verify catalog policy and the migration revision without persistent probe objects."""
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from kn.db.platform import ROLE_KINDS, SCHEMAS

    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    head = ScriptDirectory.from_config(config).get_current_head()
    current = MigrationContext.configure(connection, opts={"version_table_schema": "system"})
    if current.get_current_revision() != head:
        raise ValueError("database schema revision differs from the governed head")
    for schema in SCHEMAS:
        owner = connection.scalar(
            sa.text("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = :schema"),
            {"schema": schema},
        )
        if owner != f"kn_{schema}_owner":
            raise ValueError(f"schema owner mismatch: {schema}")
        for kind in ROLE_KINDS:
            role = f"kn_{schema}_{kind}"
            attributes = connection.execute(
                sa.text(
                    "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
                    "rolbypassrls FROM pg_roles WHERE rolname = :role"
                ),
                {"role": role},
            ).one_or_none()
            if attributes != (False,) * 6:
                raise ValueError(f"unsafe or missing role: {role}")
    verify_contract(connection)
    verify_privileges(connection)
    postgis = connection.scalar(
        sa.text("SELECT extversion FROM pg_extension WHERE extname='postgis'")
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
