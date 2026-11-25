"""Idempotent evidence writes: a repeated key is a no-op, a changed row under it is refused."""

from collections.abc import Iterable, Iterator, Mapping
from functools import cache

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from kn.contracts.loader import load_contract
from kn.contracts.model import Contract
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.evidence.model import Claim, Confirmation
from kn.evidence.records import Record

CONTRACT = RESOURCES / "evidence" / "claims" / "1.0.0.json"


@cache
def evidence_contract() -> Contract:
    return load_contract(CONTRACT)


@cache
def evidence_tables(schema: str | None = None) -> dict[str, sa.Table]:
    """Contract tables by name, compiled once per schema; tests may use a scratch schema."""
    return {table.name: table for table in metadata(evidence_contract(), schema).tables.values()}


def record(
    connection: Connection,
    records: Iterable[Record],
    tables: Mapping[str, sa.Table] | None = None,
) -> int:
    """Write rows and the evidence they embed in one savepoint; return how many were new.

    The caller owns the transaction. Foreign keys are deferred, so rows may arrive in any
    order within it. A key already stored with other content fails the whole batch.
    """
    if not connection.in_transaction():
        raise ValueError("evidence writes require a caller-owned transaction")
    tables = tables or evidence_tables()
    added = 0
    with connection.begin_nested():
        for item in _expanded(records):
            added += _write(connection, tables[item.TABLE], item)
    return added


def _expanded(records: Iterable[Record]) -> Iterator[Record]:
    for item in records:
        if isinstance(item, Claim | Confirmation):
            yield item.evidence
        yield item


def _write(connection: Connection, table: sa.Table, item: Record) -> int:
    row = item.row()
    keys = list(table.primary_key.columns)
    inserted = connection.execute(
        insert(table).values(**row).on_conflict_do_nothing(index_elements=keys).returning(*keys)
    ).first()
    stored = (
        connection.execute(sa.select(table).where(*(key == row[key.name] for key in keys)))
        .mappings()
        .one()
    )
    ignored = item.FIRST_SEEN | item.MUTABLE
    if any(stored[name] != value for name, value in row.items() if name not in ignored):
        raise ValueError(f"{item.TABLE} already stores different content under this key")
    return int(inserted is not None)
