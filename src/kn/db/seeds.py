"""Explicit reviewed seed registry; proposals and source packages are never discovered here."""

from collections.abc import Callable

from sqlalchemy.engine import Connection

from kn.db.platform import SCHEMAS, ddl

# Append a schema and deterministic loader only after its reviewed seed task is accepted.
REVIEWED_SEED_LOADERS: tuple[tuple[str, Callable[[Connection], None]], ...] = ()


def load_reviewed_seeds(connection: Connection) -> None:
    """Load reviewed content in the rebuild transaction with DML privileges only."""
    for schema, loader in REVIEWED_SEED_LOADERS:
        if schema not in SCHEMAS:
            raise ValueError("reviewed seeds must target a KN schema")
        ddl(connection, f"SET LOCAL ROLE kn_{schema}_loader")
        loader(connection)
        ddl(connection, "RESET ROLE")
