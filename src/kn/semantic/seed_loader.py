"""Load the validated reviewed snapshot into the semantic schema inside the rebuild."""

from typing import Any

from sqlalchemy import MetaData, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
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
            _load_table(connection, model.tables["semantic." + name], rows)
        _check_references(connection, model)


def _load_table(connection: Connection, table: Table, rows: list[dict[str, Any]]) -> None:
    # Explicit nulls give all parameter sets one shape; the semantic contract has no SQL defaults.
    native = [{column.name: row.get(column.name) for column in table.columns} for row in rows]
    if not native:
        return
    connection.execute(insert(table).on_conflict_do_nothing(), native)
    keys = [column.name for column in table.primary_key.columns]
    stored = {
        tuple(row[key] for key in keys): dict(row)
        for row in connection.execute(select(table)).mappings()
    }
    for row in native:
        if stored.get(tuple(row[key] for key in keys)) != row:
            raise ValueError("reviewed seed conflicts with stored content; rebuild required")


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
