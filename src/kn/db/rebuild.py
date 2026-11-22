"""Atomic, explicitly disposable rebuild of all KN schemas from compiled contracts."""

import os

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

from kn.contracts import load_contract
from kn.contracts.ddl import postgresql_ddl
from kn.db.governance import MIGRATIONS, install_contract, verify
from kn.db.platform import SCHEMAS, apply_platform, ddl
from kn.db.seeds import load_reviewed_seeds
from kn.db.verification import verify_compiled_catalog


def require_development() -> None:
    """Check before opening a database connection and again at the destructive boundary."""
    if os.environ.get("KN_ENVIRONMENT") != "development":
        raise ValueError(
            "rebuild requires KN_ENVIRONMENT=development; released data cannot be rebuilt"
        )


def rebuild(connection: Connection) -> None:
    """The caller commits; a failure restores the previous schemas even when caught."""
    require_development()
    if not connection.in_transaction():
        raise ValueError("rebuild requires a caller-owned transaction")
    contract = load_contract()
    generated = postgresql_ddl(contract)
    # All schemas form one group: references and the Alembic marker cannot become partial.
    with connection.begin_nested():
        apply_platform(connection)
        _drop_schemas(connection)
        apply_platform(connection)
        ddl(connection, f"SET LOCAL ROLE kn_{contract.schema}_owner")
        connection.exec_driver_sql(generated)
        install_contract(connection, contract)
        ddl(connection, "SET LOCAL ROLE kn_system_owner")
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.stamp(config, "head")
        ddl(connection, "RESET ROLE")
        apply_platform(connection)
        load_reviewed_seeds(connection)
        verify(connection)
        verify_compiled_catalog(connection)


def _drop_schemas(connection: Connection) -> None:
    """RESTRICT protects objects outside KN; unsupported non-table objects refuse safely."""
    old = sa.MetaData()
    for schema in SCHEMAS:
        old.reflect(connection, schema=schema, resolve_fks=False)
    old.drop_all(connection)
    for schema in reversed(SCHEMAS):
        ddl(connection, f"DROP SCHEMA {schema} RESTRICT")
