"""Load the validated reviewed snapshot into the semantic schema inside the rebuild."""

from sqlalchemy import MetaData
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.seed_rows import load_seed_rows
from kn.db.statements import SetConstraints
from kn.semantic.seeds import reviewed_snapshot
from kn.semantic.structure import semantic_contract


def load_reviewed_seeds(connection: Connection) -> None:
    """Idempotent inserts; a changed row requires a rebuild, never a silent overwrite."""
    if not connection.in_transaction():
        raise ValueError("reviewed seed loading requires a caller-owned transaction")
    snapshot = reviewed_snapshot()
    model = metadata(semantic_contract())
    with connection.begin_nested():
        for name, rows in snapshot.items():
            load_seed_rows(connection, model.tables["semantic." + name], rows)
        _check_references(connection, model)


def _check_references(connection: Connection, model: MetaData) -> None:
    """Drain deferred seed triggers so another rebuild can drop these tables in this transaction."""
    names = tuple(
        sorted(
            str(reference.name)
            for table in model.tables.values()
            for reference in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints("semantic", names, deferred=False))
    connection.execute(SetConstraints("semantic", names, deferred=True))
