"""Plan one delivery against a record's validated identity history, without writing.

A field's baseline is the hash of the record's latest claim for it, so a partial version
compares each stated field with that field's previous statement, not with the whole previous
version. A field the source first states as empty has nothing to clear and is not stated.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from kn.identity.events import Event, event
from kn.identity.journal import LockedJournal
from kn.identity.model import Change, ChangeSet, FieldChange, Payload, Seen, SourceKey, Version
from kn.identity.state import PENDING_MATCH, State
from kn.identity.tracking.delivery import Delivery, Ordering, Statement

type Outcome = Literal["current", "history", "seen"]
CLAIMED = frozenset({"added", "changed", "emptied"})
REASON = "Partial-update tracking"
_NUMERIC = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class Baseline:
    digest: str
    # The version whose change set created the record's current claim for the field.
    version_id: str


@dataclass(frozen=True)
class Tracked:
    kn_id: str
    version_id: str
    change_set_id: str | None
    outcome: Outcome
    # Fields that create claims or confirmations; empty for a version kept as history.
    changes: tuple[FieldChange, ...] = ()
    baseline: dict[str, Baseline] = field(default_factory=dict)


def owner(state: State, delivery: Delivery) -> str:
    """The record's own active link wins; a weak-key fragment follows its parent's link."""
    for key in (delivery.record, delivery.parent):
        if key is not None:
            for holding in state.links(key):
                if holding.ended_event is None:
                    return holding.kn_id
    raise ValueError("link the record or its parent record before tracking its changes")


def order(version: Version, ordering: Ordering) -> tuple[int | datetime, datetime, str]:
    primary: int | datetime | None = version.observed_at
    if ordering == "version":
        primary = int(version.version) if _NUMERIC.fullmatch(version.version) else None
    elif ordering == "updated":
        primary = version.source_updated_at
    if primary is None:
        raise ValueError(f"record versions cannot be ordered by {ordering}")
    return primary, version.observed_at, version.version


def current(
    state: State, record: SourceKey, ordering: Ordering, at: int | None = None
) -> str | None:
    """The record's latest version, as of a journal sequence when one is given."""
    versions = [
        key
        for key in state.record_versions.get(record.record_id, ())
        if at is None or state.positions[key] < at
    ]
    return max(versions, key=lambda key: order(state.versions[key], ordering), default=None)


def baseline(state: State, record: SourceKey, at: int | None = None) -> dict[str, Baseline]:
    """Each field's latest claim hash from change sets recorded before a journal sequence."""
    result: dict[str, Baseline] = {}
    for version_id in state.record_versions.get(record.record_id, ()):
        change_set = state.version_changes.get(version_id)
        if change_set is not None and (at is None or state.positions[change_set] < at):
            for item in state.changes[change_set].changes:
                if item.change in CLAIMED and item.current_hash is not None:
                    result[item.field_id] = Baseline(item.current_hash, version_id)
    return result


def classify(known: dict[str, Baseline], statements: tuple[Statement, ...]) -> list[FieldChange]:
    stated = {item.field_id: item for item in statements}
    return [_change(name, known.get(name), stated.get(name)) for name in sorted({*known, *stated})]


def _change(name: str, known: Baseline | None, item: Statement | None) -> FieldChange:
    previous = known.digest if known is not None else None
    if item is None or (item.value is None and known is None):
        return FieldChange(field_id=name, change="not_stated", previous_hash=previous)
    current = item.digest
    change: Change
    if previous is None:
        change = "added"
    elif previous == current:
        change = "unchanged"
    else:
        change = "emptied" if item.value is None else "changed"
    return FieldChange(field_id=name, change=change, previous_hash=previous, current_hash=current)


def prepare(
    locked: LockedJournal, delivery: Delivery, *, actor: str
) -> tuple[Tracked, tuple[Event, ...]]:
    """The outcome and the events still to append; a retried delivery appends nothing new."""
    state = locked.state
    if state.pending_match() is not None:
        raise ValueError(PENDING_MATCH)
    kn_id = owner(state, delivery)
    record = delivery.record
    key = (record.source, record.key, delivery.version_text)
    known = state.version_keys.get(key)
    if known is None and delivery.version is None:
        known = _sighted(state, delivery)
    head = current(state, record, delivery.ordering)
    planner = _Planner(locked, delivery, kn_id, actor)
    if known is not None:
        return planner.repeat(known, head)
    incoming = delivery.version_payload()
    if head is not None and order(incoming, delivery.ordering) < order(
        state.versions[head], delivery.ordering
    ):
        return planner.history(incoming)
    if (
        head is not None
        and delivery.version is None
        and state.versions[head].content_digest == delivery.content_digest
    ):
        return planner.seen(head)
    return planner.new(incoming)


def _sighted(state: State, delivery: Delivery) -> str | None:
    """A fetch that was recorded as a sighting of an identical version."""
    for version_id in state.record_versions.get(delivery.record.record_id, ()):
        if (version_id, delivery.fetch_id) in state.sightings:
            return version_id
    return None


class _Planner:
    def __init__(self, locked: LockedJournal, delivery: Delivery, kn_id: str, actor: str) -> None:
        self.state = locked.state
        self.last = locked.events[-1] if locked.events else None
        self.delivery = delivery
        self.kn_id = kn_id
        self.actor = actor

    def _events(self, *payloads: Payload) -> tuple[Event, ...]:
        """Chain new events after the journal head without appending them."""
        result: list[Event] = []
        for payload in payloads:
            result.append(
                event(
                    payload,
                    previous=result[-1] if result else self.last,
                    occurred_at=self.delivery.fetched_at,
                    actor=self.actor,
                    reason=REASON,
                    evidence=self.delivery.archive_record_id,
                )
            )
        return tuple(result)

    def history(self, incoming: Version) -> tuple[Tracked, tuple[Event, ...]]:
        events = self._events(incoming)
        return Tracked(self.kn_id, events[0].event_id, None, "history"), events

    def new(self, incoming: Version) -> tuple[Tracked, tuple[Event, ...]]:
        known = baseline(self.state, self.delivery.record)
        changes = tuple(classify(known, self.delivery.statements))
        version = self._events(incoming)[0]
        events = self._events(incoming, ChangeSet(version_id=version.event_id, changes=changes))
        tracked = Tracked(
            self.kn_id, version.event_id, events[1].event_id, "current", changes, known
        )
        return tracked, events

    def finish(self, version_id: str) -> tuple[Tracked, tuple[Event, ...]]:
        """An interrupted write recorded the current version but not yet its change set."""
        known = baseline(self.state, self.delivery.record)
        changes = tuple(classify(known, self.delivery.statements))
        events = self._events(ChangeSet(version_id=version_id, changes=changes))
        tracked = Tracked(self.kn_id, version_id, events[0].event_id, "current", changes, known)
        return tracked, events

    def seen(self, version_id: str) -> tuple[Tracked, tuple[Event, ...]]:
        """A sighting confirms the then-current version's claims; an older one only adds time.

        A retried sighting is judged as of its journal position, so it confirms the same claims.
        """
        delivery = self.delivery
        events: tuple[Event, ...] = ()
        at = self.state.sightings.get((version_id, delivery.fetch_id))
        if at is None:
            payload = Seen(
                version_id=version_id,
                fetch_id=delivery.fetch_id,
                archive_record_id=delivery.archive_record_id,
                observed_at=delivery.fetched_at,
            )
            events = self._events(payload)
        head = current(self.state, delivery.record, delivery.ordering, at)
        change_set = self.state.version_changes.get(version_id)
        if (
            version_id != head
            or change_set is None
            or (at is not None and self.state.positions[change_set] > at)
        ):
            return Tracked(self.kn_id, version_id, None, "seen"), events
        known = baseline(self.state, delivery.record, at)
        changes = tuple(classify(known, delivery.statements))
        return Tracked(self.kn_id, version_id, None, "seen", changes, known), events

    def repeat(self, version_id: str, head: str | None) -> tuple[Tracked, tuple[Event, ...]]:
        stored = self.state.versions[version_id]
        if stored.field_hashes != self.delivery.field_hashes:
            raise ValueError("a source version was delivered again with different content")
        if stored.fetch_id != self.delivery.fetch_id:
            return self.seen(version_id)
        change_set = self.state.version_changes.get(version_id)
        if change_set is not None:
            changes = self.state.changes[change_set].changes
            known = baseline(self.state, self.delivery.record, self.state.positions[change_set])
            return Tracked(self.kn_id, version_id, change_set, "current", changes, known), ()
        if version_id == head:
            return self.finish(version_id)
        return Tracked(self.kn_id, version_id, None, "history"), ()
