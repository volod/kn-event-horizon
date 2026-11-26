"""Validate the SQL event prefix using a disposable, transactionally invalidated checkpoint."""

from collections.abc import Sequence
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import ExecutableDDLElement
from sqlalchemy.sql.compiler import DDLCompiler

from kn.contracts.model import canonical
from kn.db.statements import LockTableForWrite
from kn.identity.events import Event

CHECKPOINT = sa.Table(
    "projection_checkpoint",
    sa.MetaData(),
    sa.Column("singleton", sa.Boolean, primary_key=True),
    sa.Column("sequence", sa.BigInteger, nullable=False),
    sa.Column("event_id", sa.String(64), nullable=False),
    sa.CheckConstraint("singleton", name="projection_checkpoint_singleton"),
    schema="identity",
)
INVALIDATE = "invalidate_projection_checkpoint"
MISMATCH = "SQL identity history is not a prefix of the durable journal"


def prefix(
    connection: Connection, table: sa.Table, history: Sequence[Event], *, full: bool = False
) -> int:
    # The advisory lock serializes KN writers. This also excludes direct SQL writes between
    # prefix validation and checkpoint advancement. It is compatible with normal readers.
    connection.execute(LockTableForWrite(table))
    count, complete = (0, False) if full else _checkpoint(connection, table, history)
    if complete:
        return count
    query = sa.select(table.c.sequence, table.c.event_json).order_by(table.c.sequence)
    if count:
        query = query.where(table.c.sequence > count)
    verified = count
    for sequence, document in connection.execute(query):
        count += 1
        if count != sequence or count > len(history):
            raise ValueError(MISMATCH)
        if canonical(history[count - 1].model_dump(mode="json")) != document:
            raise ValueError(MISMATCH)
    if count > verified and not full:
        advance(connection, history[count - 1])
    return count


def _checkpoint(
    connection: Connection, table: sa.Table, history: Sequence[Event]
) -> tuple[int, bool]:
    # The unique sequence index supports both bounds without reading the validated prefix.
    limits = sa.select(
        sa.func.min(table.c.sequence).label("first"), sa.func.max(table.c.sequence).label("last")
    ).subquery()
    marker = connection.execute(
        sa.select(
            CHECKPOINT.c.sequence, CHECKPOINT.c.event_id, limits.c.first, limits.c.last
        ).select_from(CHECKPOINT.join(limits, sa.true()))
    ).first()
    if marker is None:
        return 0, False
    count = cast(int, marker.sequence)
    if (
        marker.first != 1
        or not 0 < count <= len(history)
        or history[count - 1].event_id != marker.event_id
    ):
        raise ValueError(MISMATCH)
    return count, marker.last == count


def advance(connection: Connection, head: Event) -> None:
    connection.execute(
        insert(CHECKPOINT)
        .values(singleton=True, sequence=head.sequence, event_id=head.event_id)
        .on_conflict_do_update(
            index_elements=[CHECKPOINT.c.singleton],
            set_={"sequence": head.sequence, "event_id": head.event_id},
        )
    )


class CreateCheckpointInvalidator(ExecutableDDLElement):
    inherit_cache = False


class CreateCheckpointTrigger(ExecutableDDLElement):
    inherit_cache = False

    def __init__(self, events: sa.Table) -> None:
        self.events = events


class DropCheckpointInvalidator(ExecutableDDLElement):
    inherit_cache = False


def _function(compiler: DDLCompiler) -> str:
    quote = compiler.preparer.quote
    return f"{quote(str(CHECKPOINT.schema))}.{quote(INVALIDATE)}()"


@compiles(CreateCheckpointInvalidator)
def _create_invalidator(
    element: CreateCheckpointInvalidator, compiler: DDLCompiler, **kw: Any
) -> str:
    return f"""
        CREATE FUNCTION {_function(compiler)} RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            DELETE FROM {compiler.preparer.format_table(CHECKPOINT)};
            RETURN NULL;
        END;
        $$
    """


@compiles(CreateCheckpointTrigger)
def _create_trigger(element: CreateCheckpointTrigger, compiler: DDLCompiler, **kw: Any) -> str:
    name = compiler.preparer.quote(INVALIDATE)
    table = compiler.preparer.format_table(element.events)
    return (
        f"CREATE TRIGGER {name} AFTER UPDATE OR DELETE OR TRUNCATE ON {table} "
        f"FOR EACH STATEMENT EXECUTE FUNCTION {_function(compiler)}"
    )


@compiles(DropCheckpointInvalidator)
def _drop_invalidator(element: DropCheckpointInvalidator, compiler: DDLCompiler, **kw: Any) -> str:
    return f"DROP FUNCTION IF EXISTS {_function(compiler)}"
