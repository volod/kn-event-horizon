"""Explicit development rebuild of contract-managed projection tables only."""

import json
import os

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

from kn.contracts import load_contract
from kn.db.governance import MIGRATIONS, upgrade
from kn.db.platform import apply_platform, ddl


def rebuild(connection: Connection) -> None:
    """Drop disposable SATCOM projections only when development is explicitly selected."""
    if os.environ.get("KN_ENVIRONMENT") != "development":
        raise ValueError(
            "rebuild requires KN_ENVIRONMENT=development; released data cannot be rebuilt"
        )
    contract = load_contract()
    apply_platform(connection)
    inspector = sa.inspect(connection)
    existing = set(inspector.get_table_names(schema=contract.schema))
    managed = {table.name for table in contract.tables}
    if "satcom_contract" in existing:
        marker = sa.Table(
            "satcom_contract", sa.MetaData(), schema=contract.schema, autoload_with=connection
        )
        previous = connection.scalar(
            sa.select(marker.c.managed_tables_json).where(
                marker.c.contract_id == contract.contract_id
            )
        )
        if previous:
            managed.update(json.loads(previous))
    old = sa.MetaData(schema=contract.schema)
    old.reflect(connection, only=sorted(existing & managed), resolve_fks=False)
    ddl(connection, f"SET LOCAL ROLE kn_{contract.schema}_owner")
    old.drop_all(connection)
    ddl(connection, "SET LOCAL ROLE kn_system_owner")
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.stamp(config, "base")
    ddl(connection, "RESET ROLE")
    upgrade(connection)
