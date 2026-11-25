"""Reviewed lifecycle operations through the identity and review write-ahead journals."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.engine import Connection

from kn.identity import store
from kn.identity.events import Event, event
from kn.identity.journal import Journal, LockedJournal, new_id
from kn.identity.lifecycle_reviews import (
    REVIEW_REF,
    Change,
    Reclassification,
    ReviewDetails,
    check_binding,
    check_history,
    references,
    target,
)
from kn.identity.model import Merge, Mint, Reclassify, Restore, Retire, Split
from kn.identity.state import PENDING_MATCH, replay
from kn.review import store as review_store
from kn.review.journal import Journal as ReviewJournal
from kn.review.model import Decision, Request, Target
from kn.review.protocol import Reviewer, decide, project


@dataclass(frozen=True)
class OperationTarget:
    """The exact proposal against the identity snapshot held under the writer lock."""

    expected: Target

    def resolve(self, connection: Connection, target: Target) -> None:
        if not connection.in_transaction() or target != self.expected:
            raise ValueError("identity review requires the exact locked operation target")


def submit(
    connection: Connection,
    journal: Journal,
    change: Change,
    details: ReviewDetails,
    authenticate: Callable[[], Reviewer],
    clock: Callable[[], datetime],
    *,
    expected_head: str | None = None,
) -> Event:
    """Apply one accepted transition; the caller owns and commits the SQL transaction."""
    if isinstance(change, Merge) and change.authoritative is not None:
        raise ValueError("reviewed merges must use operator approval")
    if isinstance(change, Split):
        change = Split(
            kn_id=change.kn_id,
            successors=tuple(sorted(change.successors)),
            assignments=tuple(sorted(change.assignments, key=lambda item: item.item_id)),
        )
    reviewer = authenticate()
    reviewer.authorize(target(change, expected_head))
    review_journal = ReviewJournal(journal.data_dir)

    def write(locked: LockedJournal) -> Event:
        history = review_journal.read()
        check_history(references(locked.events), {item.decision_id: item for item in history})
        existing = next(
            (
                value
                for value in history
                if (value.reviewer, value.request_id) == (reviewer.principal, details.request_id)
            ),
            None,
        )
        return _write(
            connection,
            locked,
            change,
            details,
            reviewer,
            clock,
            review_journal,
            history,
            existing,
            expected_head,
        )

    return store.apply(connection, journal, write)


def _write(
    connection: Connection,
    locked: LockedJournal,
    change: Change,
    details: ReviewDetails,
    reviewer: Reviewer,
    clock: Callable[[], datetime],
    journal: ReviewJournal,
    history: tuple[Decision, ...],
    existing: Decision | None,
    expected_head: str | None,
) -> Event:
    prior = (
        next((item for item in locked.events if item.decision_ref == _ref(existing)), None)
        if existing
        else None
    )
    previous = locked.events[-1] if locked.events else None
    head = previous.event_id if previous else None
    if prior is None and expected_head is not None and expected_head != head:
        raise ValueError("identity history changed after review; inspect and confirm again")
    reviewed_target = target(change, prior.previous if prior else head)
    request = Request(**details.model_dump(), target=reviewed_target, outcome="accept")
    decision = decide(request, reviewer, existing.recorded_at if existing else clock())
    if existing is not None and decision != existing:
        raise ValueError("request ID reused with different content or a stale identity snapshot")
    value = prior or _make_event(change, previous, decision)
    check_binding(value, decision)
    if prior is not None:
        return prior
    if locked.state.pending_match() is not None:
        # Refuse before the decision is written; the matcher retry finishes its batch first.
        raise ValueError(PENDING_MATCH)

    replay((*locked.events, value))
    _require_acceptance(project((*history, decision), reviewed_target).heads, decision)
    saved = review_store.submit(
        connection,
        journal,
        OperationTarget(reviewed_target),
        request,
        lambda: reviewer,
        lambda: decision.recorded_at,
    )
    _require_acceptance(review_store.projection(connection, reviewed_target).heads, saved)
    locked.append(value)
    return value


def _require_acceptance(heads: tuple[str, ...], decision: Decision) -> None:
    if heads != (decision.decision_id,):
        raise ValueError("identity operation requires a single accepted review decision")


def _ref(decision: Decision) -> str:
    return REVIEW_REF + decision.decision_id


def _make_event(change: Change, previous: Event | None, decision: Decision) -> Event:
    payload: Merge | Split | Retire | Restore | Reclassify
    if isinstance(change, Reclassification):
        payload = Reclassify(
            kn_id=change.kn_id,
            successor=Mint(
                kn_id=new_id(decision.performed_at),
                entity_class=change.entity_class,
                anchor=change.anchor,
            ),
        )
    else:
        payload = change
    return event(
        payload,
        previous=previous,
        occurred_at=decision.performed_at,
        actor=decision.reviewer,
        reason=decision.reason,
        evidence=decision.evidence,
        decision_ref=_ref(decision),
    )
