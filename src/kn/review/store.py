"""Transactional PostgreSQL projection of trusted write-ahead human decisions."""

from collections.abc import Callable
from datetime import datetime
from functools import cache

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, ScalarResult

from kn.contracts.loader import load_contract
from kn.contracts.model import canonical
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.review.journal import Journal
from kn.review.model import Decision, Projection, Request, Target, digest
from kn.review.protocol import Reviewer, decide, project
from kn.review.targets import TargetResolver

# Serialize appends through the SQL boundary before taking the journal lock. Global locking
# also makes request IDs unique across targets; caller transactions must stay short.
DECISION_LOCK = 0x4B4E48564C4F47


@cache
def decision_table() -> sa.Table:
    contract = load_contract(RESOURCES / "evidence" / "1.0.0.json")
    return metadata(contract).tables["evidence.human_verification_decisions"]


def _lock(connection: Connection) -> None:
    if not connection.in_transaction():
        raise ValueError("decision application requires a caller-owned transaction")
    if connection.get_isolation_level() != "READ COMMITTED":
        raise ValueError("decision application requires READ COMMITTED isolation")
    connection.execute(sa.select(sa.func.pg_advisory_xact_lock(DECISION_LOCK)))


def submit(
    connection: Connection,
    journal: Journal,
    resolver: TargetResolver,
    request: Request,
    authenticate: Callable[[], Reviewer],
    clock: Callable[[], datetime],
) -> Decision:
    """Authenticate independently of input, persist once, apply atomically; caller commits.

    Journal files must be operator-owned, not populated from imports. There is no public API
    accepting an external Decision as authenticated. Replay trusts only this local journal.
    """
    reviewer = authenticate()
    reviewer.authorize(request.target)
    _lock(connection)
    with connection.begin_nested():
        resolver.resolve(connection, request.target)
        with journal.locked() as log:
            existing = next(
                (
                    event
                    for event in log.events
                    if (event.reviewer, event.request_id)
                    == (reviewer.principal, request.request_id)
                ),
                None,
            )
            decision = existing or decide(request, reviewer, clock())
            saved_request = Request.model_validate(
                {
                    key: value
                    for key, value in decision.model_dump().items()
                    if key in Request.model_fields
                }
            )
            if saved_request != request:
                raise ValueError("request ID reused with different decision content")
            log.append(decision)
            _apply(connection, log.events, request.target)
    return decision


def replay_target(
    connection: Connection, journal: Journal, resolver: TargetResolver, target: Target
) -> Projection:
    """Replay one restored exact target. Coverage-wide pending/stale reports come later."""
    _lock(connection)
    with connection.begin_nested():
        resolver.resolve(connection, target)
        with journal.locked() as log:
            _apply(connection, log.events, target)
        return projection(connection, target)


def _apply(connection: Connection, events: tuple[Decision, ...], target: Target) -> None:
    table = decision_table()
    for event in events:
        if event.target != target:
            continue
        document = canonical(event.model_dump(mode="json"))
        connection.execute(
            insert(table)
            .values(
                decision_id=event.decision_id,
                target_id=target.target_id,
                request_key=digest([event.reviewer, event.request_id]),
                reviewer=event.reviewer,
                performed_at=event.performed_at,
                recorded_at=event.recorded_at,
                outcome=event.outcome,
                event_json=document,
            )
            .on_conflict_do_nothing()
        )
        if (
            connection.scalar(
                sa.select(table.c.event_json).where(table.c.decision_id == event.decision_id)
            )
            != document
        ):
            raise ValueError("stored decision differs from durable journal")


def projection(connection: Connection, target: Target) -> Projection:
    """Historical projection for an exact version; callers resolve current versions first."""
    table = decision_table()
    documents: ScalarResult[str] = connection.scalars(
        sa.select(table.c.event_json).where(table.c.target_id == target.target_id)
    )
    return project((Decision.model_validate_json(document) for document in documents), target)
