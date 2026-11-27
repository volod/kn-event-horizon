"""Transactional PostgreSQL projection of trusted write-ahead human decisions."""

from collections.abc import Callable, Collection
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
from kn.review.reports import ReplayEntry, ReplayReport, ReplayState
from kn.review.targets import TargetResolver, TargetUnavailable

# Serialize appends through the SQL boundary before taking the journal lock. Global locking
# also makes request IDs unique across targets; caller transactions must stay short.
DECISION_LOCK = 0x4B4E48564C4F47
DECISION_CONTRACT = "kn.core.human_verification"
DECISION_DATASET = "human_verification_decisions"


@cache
def decision_table() -> sa.Table:
    contract = load_contract(RESOURCES / "evidence" / "1.0.0.json")
    return metadata(contract).tables[f"{contract.schema}.{DECISION_DATASET}"]


def lock(connection: Connection) -> None:
    """Serialize review writers before locking reviewed rows or replacing their schemas."""
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
    lock(connection)
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
    """Replay one restored exact target or refuse the write."""
    lock(connection)
    with connection.begin_nested():
        resolver.resolve(connection, target)
        with journal.locked() as log:
            _apply(connection, log.events, target)
        return projection(connection, target)


def replay(
    connection: Connection,
    journal: Journal,
    resolver: TargetResolver,
    *,
    complete: bool = False,
    contract_id: str | None = None,
    restored_ids: frozenset[str] = frozenset(),
) -> ReplayReport:
    """Reapply the trusted journal atomically; leave unresolved events in durable history."""
    lock(connection)
    with connection.begin_nested():
        groups: dict[Target, dict[str, Decision]] = {}
        for event in journal.read():
            if contract_id is None or event.target.contract_id in {contract_id, DECISION_CONTRACT}:
                groups.setdefault(event.target, {})[event.decision_id] = event
        report = {}
        audit_targets = {}
        for target, events in groups.items():
            if (target.contract_id, target.dataset) == (DECISION_CONTRACT, DECISION_DATASET):
                audit_targets[target] = events
            else:
                report[target.target_id] = _restore_target(
                    connection, resolver, target, events, complete, restored_ids
                )
        report.update(_restore_audit_targets(connection, resolver, audit_targets, complete))
        return tuple(report[key] for key in sorted(report))


def _restore_audit_targets(
    connection: Connection,
    resolver: TargetResolver,
    groups: dict[Target, dict[str, Decision]],
    complete: bool,
) -> dict[str, ReplayEntry]:
    # Audit reviews can depend on other decisions restored in this pass or a prior delivery.
    report = {}
    while groups:
        unresolved = {}
        for target, events in groups.items():
            entry = _restore_target(connection, resolver, target, events, complete, frozenset())
            report[entry.target_id] = entry
            if entry.state in {"pending", "orphan"}:
                unresolved[target] = events
        if len(unresolved) == len(groups):
            break
        groups = unresolved
    return report


def _restore_target(
    connection: Connection,
    resolver: TargetResolver,
    target: Target,
    events: dict[str, Decision],
    complete: bool,
    restored_ids: frozenset[str],
) -> ReplayEntry:
    state: ReplayState = "applied"
    if not events.keys() <= restored_ids:
        try:
            resolver.resolve(connection, target)
        except TargetUnavailable as unavailable:
            state = (
                ("orphan" if complete else "pending")
                if unavailable.state == "missing"
                else unavailable.state
            )
        else:
            for event in events.values():
                _insert(connection, event)
    return ReplayEntry(target.target_id, target.contract_id, target.dataset, state)


def _apply(connection: Connection, events: tuple[Decision, ...], target: Target) -> None:
    for event in events:
        if event.target == target:
            _insert(connection, event)


def replay_selected(
    connection: Connection,
    journal: Journal,
    select: Callable[[dict[str, Decision]], tuple[str, ...]],
) -> None:
    """Reproject decisions referenced by another durable log after validating its references."""
    lock(connection)
    with journal.locked() as log, connection.begin_nested():
        by_id = {event.decision_id: event for event in log.events}
        for key in select(by_id):
            _insert(connection, by_id[key])


def _insert(connection: Connection, event: Decision) -> None:
    table = decision_table()
    document = canonical(event.model_dump(mode="json"))
    connection.execute(
        insert(table)
        .values(
            decision_id=event.decision_id,
            target_id=event.target.target_id,
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


def history(connection: Connection, target_ids: Collection[str]) -> dict[str, list[Decision]]:
    """Trusted exact-target history, read in one query for a row's review scopes."""
    if not target_ids:
        return {}
    table = decision_table()
    documents: ScalarResult[str] = connection.scalars(
        sa.select(table.c.event_json).where(table.c.target_id.in_(target_ids))
    )
    groups: dict[str, list[Decision]] = {}
    for document in documents:
        event = Decision.model_validate_json(document)
        groups.setdefault(event.target.target_id, []).append(event)
    return groups


def projection(connection: Connection, target: Target) -> Projection:
    """Trusted historical lookup for an exact version, without audience filtering."""
    key = target.target_id
    return project(history(connection, (key,)).get(key, ()), target)
