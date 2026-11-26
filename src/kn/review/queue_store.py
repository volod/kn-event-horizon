"""Append-before-apply queue decisions and deterministic explicit reattachment."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.reviews import ReviewDecision
from kn.evidence.store import evidence_tables, record
from kn.evidence.vocabulary import FACT_REVIEW_KINDS, ReviewOutcome
from kn.identity import store as identity_store
from kn.identity.journal import Journal as IdentityJournal
from kn.identity.journal import LockedJournal
from kn.review import store
from kn.review.identity import effects
from kn.review.journal import JOURNAL_NAME, Journal
from kn.review.model import Decision, Request, Target
from kn.review.protocol import Reviewer, decide, project
from kn.review.queue import Item, items, validate_item
from kn.review.targets import ContractResolver


def journals(data_dir: Path) -> tuple[Journal, ...]:
    root = data_dir / "decisions"
    logs = [Journal(data_dir)] if (root / JOURNAL_NAME).exists() else []
    return (
        *logs,
        *(Journal(data_dir, path.parent.name) for path in sorted(root.glob(f"*/{JOURNAL_NAME}"))),
    )


def history(data_dir: Path) -> tuple[Decision, ...]:
    events = tuple(event for log in journals(data_dir) for event in log.read())
    from kn.review.protocol import validate_history

    validate_history(events)
    return events


@dataclass(frozen=True)
class ItemResolver:
    resolver: ContractResolver
    item: Item

    def resolve(self, connection: Connection, target: Target) -> None:
        if target != self.item.target:
            raise ValueError("review item version changed")
        validate_item(connection, self.resolver, self.item)


def submit(
    connection: Connection,
    data_dir: Path,
    domain: str,
    resolver: ContractResolver,
    request: Request,
    authenticate: Callable[[], Reviewer],
    clock: Callable[[], datetime],
    tables: Mapping[str, sa.Table] | None = None,
) -> Decision:
    reviewer = authenticate()
    reviewer.authorize(request.target)
    identity = IdentityJournal(data_dir)
    log = Journal(data_dir, domain)
    identity_store.lock(connection)
    store.lock(connection)
    _check_domain(data_dir, log, request, reviewer)
    if request.queue is None:
        return store.submit(connection, log, resolver, request, lambda: reviewer, clock)

    def apply(locked: LockedJournal) -> Decision:
        item = _queue_item(connection, resolver, identity, locked, request, tables)
        proposed = _proposal(data_dir, item, request, reviewer, clock)
        planned = effects(locked, proposed)
        saved = store.submit(
            connection,
            log,
            ItemResolver(resolver, item),
            request,
            lambda: reviewer,
            lambda: proposed.recorded_at,
        )
        locked.append_batch(planned)
        apply_fact_event(connection, saved, tables)
        return saved

    return identity_store.apply(connection, identity, apply)


def _queue_item(
    connection: Connection,
    resolver: ContractResolver,
    identity: IdentityJournal,
    locked: LockedJournal,
    request: Request,
    tables: Mapping[str, sa.Table] | None,
) -> Item:
    choice = request.queue
    assert choice is not None
    item = items(connection, resolver, identity, tables, locked.state).get(choice.item_id)
    if item is None or choice != item.choice(choice.selected):
        raise ValueError("unknown review item or changed candidates")
    if item.kind in FACT_REVIEW_KINDS and choice.selected is None:
        raise ValueError("fact decisions require an explicit claim candidate")
    return item


def _proposal(
    data_dir: Path, item: Item, request: Request, reviewer: Reviewer, clock: Callable[[], datetime]
) -> Decision:
    events = history(data_dir)
    existing = next(
        (
            e
            for e in events
            if (e.reviewer, e.request_id) == (reviewer.principal, request.request_id)
        ),
        None,
    )
    if item.kind.startswith("identity_") and existing is None:
        current = project([e for e in events if e.target == item.target], item.target)
        if current.heads != request.predecessors:
            raise ValueError("identity review must explicitly supersede its current heads")
    return existing or decide(request, reviewer, clock())


def apply_fact_event(
    connection: Connection, event: Decision, tables: Mapping[str, sa.Table] | None = None
) -> None:
    choice = event.queue
    if choice is None or choice.kind not in FACT_REVIEW_KINDS:
        return
    outcome: ReviewOutcome = (
        "select"
        if event.outcome in {"accept", "supersede"}
        else "reject"
        if event.outcome == "reject"
        else "dismiss"
    )
    row = ReviewDecision(
        item_id=choice.item_id,
        outcome=outcome,
        selected_claim_key=choice.selected if outcome == "select" else None,
        reviewer=event.reviewer,
        reason=event.reason,
        performed_at=event.performed_at,
        recorded_at=event.recorded_at,
        human_verification_decision_id=event.decision_id,
    )
    record(connection, (row,), tables or evidence_tables())


def _check_domain(data_dir: Path, log: Journal, request: Request, reviewer: Reviewer) -> None:
    existing = next(
        (
            e
            for e in history(data_dir)
            if (e.reviewer, e.request_id) == (reviewer.principal, request.request_id)
        ),
        None,
    )
    if existing and existing not in log.read():
        raise ValueError("request ID already belongs to another domain")
