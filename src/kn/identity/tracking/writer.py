"""Durable entry point: journal the version and change set, then write claims in one transaction."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence import store as evidence_store
from kn.evidence.records import Record
from kn.identity import store
from kn.identity.journal import Journal, LockedJournal
from kn.identity.tracking.changes import Tracked, prepare
from kn.identity.tracking.claims import evidence_rows
from kn.identity.tracking.delivery import Delivery
from kn.review.model import utc


@dataclass(frozen=True)
class Receipt:
    tracked: Tracked
    rows: tuple[Record, ...]
    # Evidence rows this call stored; a retried delivery stores none.
    written: int


class SqlClaims:
    """Claim lookup by the record version that made it, through `claims_version_idx`."""

    def __init__(self, connection: Connection, table: sa.Table) -> None:
        self.connection = connection
        self.table = table

    def claim(self, record_id: str, field_id: str, version_id: str) -> str | None:
        table = self.table
        query = (
            sa.select(table.c.claim_key)
            .where(
                table.c.source_version_id == version_id,
                table.c.record_id == record_id,
                table.c.field_id == field_id,
            )
            .order_by(table.c.claim_key)
            .limit(1)
        )
        return self.connection.scalar(query)


def track(
    connection: Connection,
    journal: Journal,
    delivery: Delivery,
    *,
    actor: str,
    clock: Callable[[], datetime],
    tables: Mapping[str, sa.Table] | None = None,
) -> Receipt:
    """Track one mapped record delivery in a caller-owned READ COMMITTED transaction.

    The record or its parent must already be linked. Claims are validated before the journal
    append, so a refused delivery leaves no history. A rolled-back transaction can leave the
    journaled version pending; the same delivery retried completes its claims.
    """
    recorded_at = utc(clock())
    if recorded_at < delivery.fetched_at:
        raise ValueError("claims cannot be recorded before their fetch")
    tables = tables or evidence_store.evidence_tables()
    claims = SqlClaims(connection, tables["claims"])

    def write(locked: LockedJournal) -> tuple[Tracked, tuple[Record, ...]]:
        tracked, events = prepare(locked, delivery, actor=actor)
        rows = evidence_rows(tracked, delivery, claims, recorded_at)
        locked.append_batch(events)
        return tracked, rows

    tracked, rows = store.apply(connection, journal, write)
    written = evidence_store.record(connection, rows, tables)
    return Receipt(tracked, rows, written)
