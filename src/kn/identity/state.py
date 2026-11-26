"""Pure replay validation. Invalid events never reach the durable append boundary."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from kn.identity.attribute_index import AttributeIndex
from kn.identity.events import REVIEW_REF, Event
from kn.identity.match_records import check_match, check_match_link
from kn.identity.model import (
    Attribute,
    ChangeSet,
    Identifier,
    Link,
    Match,
    Mint,
    Seen,
    SourceKey,
    Version,
)
from kn.identity.tracking.replay import record_change_set, record_sighting, record_version

PENDING_MATCH = "retry the pending identity match before recording another"
type RecordKey = tuple[str, str]


def record_key(record: SourceKey) -> RecordKey:
    return record.source, record.key


@dataclass
class Object:
    kn_id: str
    entity_class: str
    anchor: SourceKey
    mint_event: str
    state: str = "active"
    successors: tuple[str, ...] = ()


@dataclass
class Holding:
    event: Event
    kn_id: str
    ended_event: str | None = None
    ended_sequence: int | None = None

    def was_active(self, before: int) -> bool:
        return self.event.sequence < before and (
            self.ended_sequence is None or self.ended_sequence >= before
        )


@dataclass
class ChangedRows:
    """Mutable rows touched by a suffix, including redirect ancestors."""

    objects: set[str] = field(default_factory=set)
    records: set[str] = field(default_factory=set)
    holdings: set[str] = field(default_factory=set)
    redirects: set[str] = field(default_factory=set)


@dataclass
class State:
    events: list[Event] = field(default_factory=list)
    objects: dict[str, Object] = field(default_factory=dict)
    records: dict[str, SourceKey] = field(default_factory=dict)
    last_seen: dict[str, datetime] = field(default_factory=dict)
    holdings: dict[str, Holding] = field(default_factory=dict)
    versions: dict[str, Version] = field(default_factory=dict)
    matches: dict[str, Match] = field(default_factory=dict)
    changes: dict[str, ChangeSet] = field(default_factory=dict)
    redirects: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Lookup indexes keep validation and resolution linear in the length of the history.
    anchors: dict[RecordKey, str] = field(default_factory=dict)
    record_links: dict[RecordKey, list[str]] = field(default_factory=dict)
    identifier_keys: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    version_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    record_versions: dict[str, list[str]] = field(default_factory=dict)
    version_changes: dict[str, str] = field(default_factory=dict)
    # Journal sequence of each sighting, version and change set, for as-of comparisons.
    sightings: dict[tuple[str, str], int] = field(default_factory=dict)
    positions: dict[str, int] = field(default_factory=dict)
    requests: dict[str, Event] = field(default_factory=dict)
    last_traced: Event | None = None
    reviewed: list[Event] = field(default_factory=list)
    owner_keys: dict[str, dict[str, None]] = field(default_factory=dict)
    redirect_sources: dict[str, set[str]] = field(default_factory=dict)
    attributes: AttributeIndex = field(default_factory=AttributeIndex)
    dirty: ChangedRows | None = None

    def active(self, kn_id: str) -> Object:
        item = self.objects.get(kn_id)
        if item is None or item.state != "active":
            raise ValueError("identity transition requires an active object")
        return item

    def record(self, key: SourceKey) -> None:
        record_id = key.record_id
        if record_id not in self.records:
            self.records[record_id] = key
            if self.dirty is not None:
                self.dirty.records.add(record_id)

    def mint(self, payload: Mint, event: Event) -> None:
        if payload.kn_id in self.objects:
            raise ValueError("KN ID must never be reused")
        if record_key(payload.anchor) in self.anchors:
            raise ValueError("anchoring source record already minted an identity")
        self.record(payload.anchor)
        self.anchors[record_key(payload.anchor)] = payload.kn_id
        item = Object(payload.kn_id, payload.entity_class, payload.anchor, event.event_id)
        self.objects[item.kn_id] = item
        self.set_status(item, "active")

    def resolve(self, kn_id: str) -> tuple[str, ...]:
        if kn_id not in self.objects:
            raise ValueError("unknown KN ID")
        return self.redirects.get(kn_id, (kn_id,))

    def set_status(self, item: Object, value: str) -> None:
        item.state = value
        if self.dirty is not None:
            self.dirty.objects.add(item.kn_id)

    def redirect(self, item: Object, successors: tuple[str, ...]) -> None:
        item.successors = successors
        for ancestor in tuple(self.redirect_sources.get(item.kn_id, ())):
            targets = (set(self.redirects[ancestor]) - {item.kn_id}).union(successors)
            self._set_redirect(ancestor, targets)
        self._set_redirect(item.kn_id, set(successors))

    def _set_redirect(self, key: str, targets: set[str]) -> None:
        for previous in self.redirects.get(key, ()):
            self.redirect_sources[previous].remove(key)
        for target in targets:
            self.redirect_sources.setdefault(target, set()).add(key)
        self.redirects[key] = tuple(sorted(targets))
        if self.dirty is not None:
            self.dirty.objects.add(key)
            self.dirty.redirects.add(key)

    def links(self, record: SourceKey) -> list[Holding]:
        """Current and closed links of one source record, in journal order."""
        return [self.holdings[key] for key in self.record_links.get(record_key(record), ())]

    def identifiers(self, namespace: str, value: str) -> list[Holding]:
        """Every recorded validity interval of one identifier, in journal order."""
        return [self.holdings[key] for key in self.identifier_keys.get((namespace, value), ())]

    def pending_match(self) -> Event | None:
        """The latest traced match while any of its recorded follow-up events is missing."""
        entry = self.last_traced
        if entry is None or not isinstance(match := entry.payload, Match) or match.trace is None:
            return None
        complete = len(self.events) >= entry.sequence + match.trace.followup_count
        return None if complete else entry

    def owned(self, kn_id: str) -> dict[str, Holding]:
        return {key: self.holdings[key] for key in self.owner_keys.get(kn_id, ())}

    def _hold(self, event: Event, kn_id: str) -> None:
        key = event.event_id
        self.holdings[key] = Holding(event, kn_id)
        self.owner_keys.setdefault(kn_id, {})[key] = None
        if self.dirty is not None:
            self.dirty.holdings.add(key)

    def end(self, holding: Holding, event: Event) -> None:
        key = holding.event.event_id
        del self.owner_keys[holding.kn_id][key]
        holding.ended_event = event.event_id
        holding.ended_sequence = event.sequence
        if self.dirty is not None:
            self.dirty.holdings.add(key)

    def transfer(self, holding: Holding, target: str) -> None:
        key = holding.event.event_id
        del self.owner_keys[holding.kn_id][key]
        self.owner_keys.setdefault(target, {})[key] = None
        holding.kn_id = target
        if self.dirty is not None:
            self.dirty.holdings.add(key)

    def apply(self, event: Event) -> None:
        previous = self.events[-1] if self.events else None
        if event.sequence != len(self.events) + 1 or event.previous != (
            previous.event_id if previous else None
        ):
            raise ValueError("identity journal sequence or predecessor mismatch")
        payload = event.payload
        if isinstance(payload, Mint):
            self.mint(payload, event)
        elif isinstance(payload, Link):
            self._link(payload, event)
        elif isinstance(payload, Identifier):
            self._identifier(payload, event)
        elif isinstance(payload, Attribute):
            self.active(payload.kn_id)
            if payload.record is not None and payload.record.record_id not in self.records:
                raise ValueError("attribute must cite a known source record")
            self._hold(event, payload.kn_id)
            self.attributes.add(event.event_id, payload)
        else:
            self._other(event)
        self.events.append(event)
        if event.decision_ref is not None and event.decision_ref.startswith(REVIEW_REF):
            self.reviewed.append(event)

    def _other(self, event: Event) -> None:
        payload = event.payload
        if isinstance(payload, Version):
            record_version(self, payload, event)
        elif isinstance(payload, Match):
            self._match(payload, event)
        elif isinstance(payload, ChangeSet):
            record_change_set(self, payload, event)
        elif isinstance(payload, Seen):
            record_sighting(self, payload, event)
        else:
            from kn.identity.transitions import transition

            transition(self, event)

    def saw(self, record: SourceKey, observed_at: datetime) -> None:
        """Older observations remain history without reducing `last_seen`."""
        key = record.record_id
        previous = self.last_seen.get(key)
        if previous is None or observed_at > previous:
            self.last_seen[key] = observed_at
            if self.dirty is not None:
                self.dirty.records.add(key)

    def _link(self, payload: Link, event: Event) -> None:
        self.active(payload.kn_id)
        if any(item.ended_event is None for item in self.links(payload.record)):
            raise ValueError("source record already has an active link")
        if payload.match_id is not None:
            match = self.matches.get(payload.match_id)
            if match is None or match.record != payload.record:
                raise ValueError("link requires a matching stored decision")
            check_match_link(payload, match, self.objects[payload.kn_id].anchor)
        self.record(payload.record)
        self._hold(event, payload.kn_id)
        self.record_links.setdefault(record_key(payload.record), []).append(event.event_id)

    def _identifier(self, payload: Identifier, event: Event) -> None:
        self.active(payload.kn_id)
        key = (payload.namespace, payload.value)
        for holding in self.identifiers(*key):
            other = holding.event.payload
            assert isinstance(other, Identifier)
            if (other.valid_to is None or payload.valid_from < other.valid_to) and (
                payload.valid_to is None or other.valid_from < payload.valid_to
            ):
                raise ValueError("identifier validity overlaps in its namespace")
        self._hold(event, payload.kn_id)
        self.identifier_keys.setdefault(key, []).append(event.event_id)

    def _match(self, payload: Match, event: Event) -> None:
        check_match(payload, self.active)
        self.record(payload.record)
        self.matches[event.event_id] = payload
        if payload.trace is not None:
            self.requests.setdefault(payload.trace.request_digest, event)
            self.last_traced = event


def replay(events: Iterable[Event], *, track_after: int | None = None) -> State:
    state = State()
    for event in events:
        if track_after is not None and event.sequence == track_after + 1:
            state.dirty = ChangedRows()
        state.apply(event)
    return state
