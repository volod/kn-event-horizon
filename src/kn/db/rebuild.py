"""Atomic, explicitly disposable rebuild of all KN schemas through the Alembic baseline."""

import os

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.db.governance import upgrade, verify
from kn.db.platform import SCHEMAS, apply_platform
from kn.db.seeds import load_reviewed_seeds
from kn.db.verification import verify_compiled_catalog


class RebuildRefused(ValueError):
    """The environment is not explicitly marked as a disposable development environment."""


def require_development() -> None:
    """Check before opening a database connection and again at the destructive boundary."""
    if os.environ.get("KN_ENVIRONMENT") != "development":
        raise RebuildRefused(
            "rebuild requires KN_ENVIRONMENT=development; released data cannot be rebuilt"
        )


def rebuild(connection: Connection) -> None:
    """The caller commits; a failure restores the previous schemas even when caught.

    After the drop, the database is empty, and the normal upgrade recreates it: the same
    SQLAlchemy metadata and Alembic revisions as every deployment, never SQL text.
    """
    require_development()
    if not connection.in_transaction():
        raise ValueError("rebuild requires a caller-owned transaction")
    # All schemas form one group: references and the Alembic marker cannot become partial.
    with connection.begin_nested():
        apply_platform(connection)
        _drop_schemas(connection)
        upgrade(connection)
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
        # Without CASCADE, PostgreSQL drops only an empty schema (RESTRICT).
        connection.execute(sa.schema.DropSchema(schema))
