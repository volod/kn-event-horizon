"""Transactional projection and write-ahead application on a trusted local journal."""

from collections.abc import Callable
from functools import cache

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts import Contract, load_contract
from kn.contracts.model import canonical
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.db.statements import SetConstraints
from kn.identity.journal import Journal, LockedJournal
from kn.identity.projection import rows
from kn.identity.state import State

# Distinct from platform/review locks. Rebuild takes this before dropping identity tables.
IDENTITY_LOCK = 0x4B4E4944


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
    with journal.locked() as locked, connection.begin_nested():
        _project(connection, locked)
        return locked.state


def apply[T](connection: Connection, journal: Journal, write: Callable[[LockedJournal], T]) -> T:
    """Append/fsync first. A rolled-back SQL transaction leaves recoverable pending history."""
    lock(connection)
    with journal.locked() as locked, connection.begin_nested():
        _check_prefix(connection, locked)
        result = write(locked)
        _project(connection, locked)
        return result


def _check_prefix(connection: Connection, locked: LockedJournal) -> None:
    table = metadata(contract()).tables["identity.lifecycle_events"]
    stored: list[str] = list(
        connection.scalars(sa.select(table.c.event_json).order_by(table.c.sequence)).all()
    )
    expected = [canonical(event.model_dump(mode="json")) for event in locked.events]
    if stored != expected[: len(stored)]:
        raise ValueError("SQL identity history is not a prefix of the durable journal")


def _project(connection: Connection, locked: LockedJournal) -> None:
    _check_prefix(connection, locked)
    model = metadata(contract())
    projected = rows(locked.state)
    events = model.tables["identity.lifecycle_events"]
    count = connection.scalar(sa.select(sa.func.count()).select_from(events)) or 0
    # All foreign keys are deferred: replace disposable state in the caller's savepoint.
    for table in reversed(model.sorted_tables):
        if table is not events:
            connection.execute(table.delete())
    for table in model.sorted_tables:
        content = projected[table.name]
        if table is events:
            content = content[count:]
        if content:
            connection.execute(table.insert(), content)
    _check_references(connection, model)


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
