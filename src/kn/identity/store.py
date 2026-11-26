"""Transactional projection and write-ahead application on a trusted local journal."""

from collections.abc import Callable
from functools import cache

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from kn.contracts import Contract, load_contract
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.db.statements import SetConstraints
from kn.identity.checkpoint import advance, prefix
from kn.identity.journal import Journal, LockedJournal
from kn.identity.lifecycle_reviews import restore
from kn.identity.projection import Value, rows
from kn.identity.state import State
from kn.identity.state import replay as replay_state

# Distinct from platform/review locks. Rebuild takes this before dropping identity tables.
IDENTITY_LOCK = 0x4B4E4944
MUTABLE_COLUMNS = {
    "objects": ("state", "current_redirect"),
    "source_records": ("last_seen",),
    "identifiers": ("kn_id",),
    "attributes": ("kn_id",),
    "links": ("kn_id", "ended_event"),
}


@cache
def contract() -> Contract:
    root = RESOURCES / "identity"
    return load_contract(root / "1.0.0.json", references=root / "references.json")


def lock(connection: Connection) -> None:
    if not connection.in_transaction():
        raise ValueError("identity projection requires a caller-owned transaction")
    if connection.get_isolation_level() != "READ COMMITTED":
        raise ValueError("identity projection requires READ COMMITTED isolation")
    connection.execute(sa.select(sa.func.pg_advisory_xact_lock(IDENTITY_LOCK)))


def replay(connection: Connection, journal: Journal) -> State:
    """Replay before any raw imports; a caught error rolls back all projection changes."""
    lock(connection)
    with journal.locked(reuse=False) as locked, connection.begin_nested():
        model = metadata(contract())
        events = model.tables["identity.lifecycle_events"]
        count = prefix(connection, events, locked.state.events, full=True)
        restore(connection, locked)
        projected = rows(locked.state)
        # Explicit replay restores disposable rows even when the SQL event prefix is complete.
        for table in reversed(model.sorted_tables):
            if table is not events:
                connection.execute(table.delete())
        for table in model.sorted_tables:
            content = projected[table.name]
            if table is events:
                content = content[count:]
            if content:
                connection.execute(table.insert(), content)
        _finish(connection, model, locked)
        return locked.state


def apply[T](connection: Connection, journal: Journal, write: Callable[[LockedJournal], T]) -> T:
    """Append/fsync first. A rolled-back SQL transaction leaves recoverable pending history."""
    lock(connection)
    with journal.locked() as locked, connection.begin_nested():
        events = metadata(contract()).tables["identity.lifecycle_events"]
        count = prefix(connection, events, locked.state.events)
        result = write(locked)
        _project(connection, locked, count)
        return result


def _project(connection: Connection, locked: LockedJournal, count: int) -> None:
    # Review writers take the review lock before resolving any target rows.
    restore(connection, locked)
    if count == len(locked.state.events):
        return
    state = locked.state
    if count != locked.initial_sequence:
        # A reset or rollback can leave a durable suffix we haven't tracked in this lock.
        state = replay_state(state.events, track_after=count)
    assert state.dirty is not None
    projected = rows(state, count)
    model = metadata(contract())
    redirects = model.tables["identity.redirects"]
    if state.dirty.redirects:
        connection.execute(redirects.delete().where(redirects.c.kn_id.in_(state.dirty.redirects)))
    for table in model.sorted_tables:
        content = projected[table.name]
        if table.name == "links":
            # The partial unique index is immediate. Close prior links before new ones.
            content.sort(key=lambda row: row["ended_event"] is None)
        if content:
            _write_rows(connection, table, content)
    _finish(connection, model, locked)


def _write_rows(connection: Connection, table: sa.Table, content: list[dict[str, Value]]) -> None:
    columns = MUTABLE_COLUMNS.get(table.name)
    if columns is None:
        connection.execute(table.insert(), content)
        return
    statement = insert(table)
    connection.execute(
        statement.on_conflict_do_update(
            index_elements=list(table.primary_key),
            set_={name: statement.excluded[name] for name in columns},
        ),
        content,
    )


def _finish(connection: Connection, model: sa.MetaData, locked: LockedJournal) -> None:
    _check_references(connection, model)
    if locked.head is not None:
        advance(connection, locked.head)


def _check_references(connection: Connection, model: sa.MetaData) -> None:
    names = tuple(
        sorted(
            str(item.name)
            for table in model.tables.values()
            for item in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints("identity", names, deferred=False))
    connection.execute(SetConstraints("identity", names, deferred=True))
