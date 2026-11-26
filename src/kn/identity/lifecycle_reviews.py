"""Bind operator decisions to exact identity operations and recover their SQL rows."""

from collections.abc import Iterable

from sqlalchemy.engine import Connection

from kn.identity.events import REVIEW_REF, Event
from kn.identity.journal import LockedJournal
from kn.identity.model import KnId, Merge, Reclassify, Restore, Retire, SourceKey, Split
from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Decision, Frozen, Instant, KeyPart, Purpose, Target, Text, digest

PURPOSE: Purpose = "workflow"


class Reclassification(Frozen):
    """The requested change; the new ID is first made public by the durable event."""

    kn_id: KnId
    entity_class: Text
    anchor: SourceKey


type Change = Merge | Split | Retire | Restore | Reclassification


class ReviewDetails(Frozen):
    request_id: Text
    performed_at: Instant
    reason: Text
    evidence: Text


def change_from_event(value: Event) -> Change:
    payload = value.payload
    if isinstance(payload, Reclassify):
        return Reclassification(
            kn_id=payload.kn_id,
            entity_class=payload.successor.entity_class,
            anchor=payload.successor.anchor,
        )
    if isinstance(payload, (Merge, Split, Retire, Restore)):
        return payload
    raise ValueError("identity review references an unsupported transition")


def target(change: Change, previous: str | None) -> Target:
    intent = change.model_dump(mode="json")
    if isinstance(change, Reclassification):
        intent["kind"] = "reclassified"
    return Target(
        contract_id="kn.core.identity",
        dataset="objects",
        key=(KeyPart(field_id="identity.objects.kn_id", kind="string", value=change.kn_id),),
        scope="record",
        version=digest({"previous": previous, "change": intent}),
        purpose=PURPOSE,
    )


def check_binding(value: Event, decision: Decision) -> None:
    if (
        decision.outcome != "accept"
        or decision.target != target(change_from_event(value), value.previous)
        or value.actor != decision.reviewer
        or value.reason != decision.reason
        or value.evidence != decision.evidence
        or value.occurred_at != decision.performed_at
    ):
        raise ValueError("identity event does not match its accepted review decision")


def references(events: Iterable[Event]) -> list[tuple[Event, str]]:
    return [
        (value, value.decision_ref.removeprefix(REVIEW_REF))
        for value in events
        if value.decision_ref and value.decision_ref.startswith(REVIEW_REF)
    ]


def check_history(
    reviewed: list[tuple[Event, str]], decisions: dict[str, Decision]
) -> tuple[str, ...]:
    seen: set[str] = set()
    for value, key in reviewed:
        decision = decisions.get(key)
        if decision is None or key in seen:
            raise ValueError("identity history requires a unique durable review decision")
        check_binding(value, decision)
        seen.add(key)
    return tuple(key for _, key in reviewed)


def restore(connection: Connection, locked: LockedJournal) -> None:
    reviewed = references(locked.state.reviewed)
    if not reviewed:
        return
    store.replay_selected(
        connection, Journal(locked.data_dir), lambda decisions: check_history(reviewed, decisions)
    )
