"""Explicit reviewed seed registry; proposals and source packages are never discovered here."""

from collections.abc import Callable

from sqlalchemy.engine import Connection

from kn.db.platform import SCHEMAS, role_name
from kn.db.statements import ResetRole, SetRole
from kn.semantic.seeds import load_reviewed_seeds as load_semantic_seeds

# Explicit registry: no proposal discovery at rebuild time.
REVIEWED_SEED_LOADERS: tuple[tuple[str, Callable[[Connection], None]], ...] = (
    ("semantic", load_semantic_seeds),
)


def load_reviewed_seeds(connection: Connection) -> None:
    """Load reviewed content in the rebuild transaction with DML privileges only."""
    for schema, loader in REVIEWED_SEED_LOADERS:
        if schema not in SCHEMAS:
            raise ValueError("reviewed seeds must target a KN schema")
        connection.execute(SetRole(role_name(schema, "loader")))
        loader(connection)
        connection.execute(ResetRole())
