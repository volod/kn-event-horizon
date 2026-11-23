"""Install reviewed rows idempotently while preserving conflicting stored content."""

from collections.abc import Mapping, Sequence

from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection


def load_seed_rows(
    connection: Connection, table: Table, rows: Sequence[Mapping[str, object]]
) -> None:
    # Explicit nulls give every parameter set the same shape for these reviewed tables.
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
            raise ValueError(f"reviewed seed conflicts with stored content in {table.fullname}")
