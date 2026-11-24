"""Atomic, explicitly disposable rebuild of all KN schemas through the Alembic baseline."""

import os
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts import Contract
from kn.db.governance import deployment, upgrade, verify
from kn.db.platform import SCHEMAS, apply_platform
from kn.db.seeds import load_reviewed_seeds
from kn.db.verification import verify_compiled_catalog
from kn.identity.journal import Journal
from kn.identity.store import lock as identity_lock
from kn.identity.store import replay as replay_identity
from kn.quality.project_root import discover_project_root
from kn.review.store import lock as review_lock


class RebuildRefused(ValueError):
    """The environment is not explicitly marked as a disposable development environment."""


def require_development() -> None:
    """Check before opening a database connection and again at the destructive boundary."""
    if os.environ.get("KN_ENVIRONMENT") != "development":
        raise RebuildRefused(
            "rebuild requires KN_ENVIRONMENT=development; released data cannot be rebuilt"
        )


def rebuild(
    connection: Connection,
    contracts: Sequence[Contract] | None = None,
    *,
    data_dir: Path | None = None,
) -> None:
    """The caller commits; a failure restores the previous schemas even when caught.

    After the drop, the database is empty, and the normal upgrade recreates every registered
    contract: the same SQLAlchemy metadata and Alembic revisions as every deployment, never SQL
    text. Tests supply a fixture deployment set.
    """
    require_development()
    if not connection.in_transaction():
        raise ValueError("rebuild requires a caller-owned transaction")
    deployed = deployment(contracts)
    # All schemas form one group: references and the Alembic marker cannot become partial.
    with connection.begin_nested():
        apply_platform(connection)
        identity_lock(connection)
        review_lock(connection)
        _drop_schemas(connection)
        upgrade(connection, deployed)
        if any(contract.contract_id == "kn.core.identity" for contract in deployed):
            directory = data_dir or Path(os.environ.get("DATA_DIR", ".data"))
            if not directory.is_absolute():
                directory = discover_project_root() / directory
            replay_identity(connection, Journal(directory))
        load_reviewed_seeds(connection)
        verify(connection, deployed)
        verify_compiled_catalog(connection, deployed)


def _drop_schemas(connection: Connection) -> None:
    """RESTRICT protects objects outside KN; unsupported non-table objects refuse safely."""
    old = sa.MetaData()
    for schema in SCHEMAS:
        old.reflect(connection, schema=schema, resolve_fks=False)
    old.drop_all(connection)
    for schema in reversed(SCHEMAS):
        # Without CASCADE, PostgreSQL drops only an empty schema (RESTRICT).
        connection.execute(sa.schema.DropSchema(schema))
