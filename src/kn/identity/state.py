"""Pure replay validation. Invalid events never reach the durable append boundary."""

from dataclasses import dataclass, field
from datetime import datetime

from kn.identity.events import Event
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

    def active(self, kn_id: str) -> Object:
        item = self.objects.get(kn_id)
        if item is None or item.state != "active":
            raise ValueError("identity transition requires an active object")
        return item

    def record(self, key: SourceKey) -> None:
        self.records[key.record_id] = key

    def mint(self, payload: Mint, event: Event) -> None:
        if payload.kn_id in self.objects:
            raise ValueError("KN ID must never be reused")
        if record_key(payload.anchor) in self.anchors:
            raise ValueError("anchoring source record already minted an identity")
        self.record(payload.anchor)
        self.anchors[record_key(payload.anchor)] = payload.kn_id
        self.objects[payload.kn_id] = Object(
            payload.kn_id, payload.entity_class, payload.anchor, event.event_id
        )

    def resolve(self, kn_id: str) -> tuple[str, ...]:
        if kn_id not in self.objects:
            raise ValueError("unknown KN ID")
        return self.redirects.get(kn_id, (kn_id,))

    def redirect(self, item: Object, successors: tuple[str, ...]) -> None:
        item.successors = successors
        for ancestor, targets in self.redirects.items():
            if item.kn_id in targets:
                self.redirects[ancestor] = tuple(
                    sorted((set(targets) - {item.kn_id}).union(successors))
                )
        self.redirects[item.kn_id] = tuple(sorted(successors))

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
        return {
            key: value
            for key, value in self.holdings.items()
            if value.kn_id == kn_id and value.ended_event is None
        }

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
            self.holdings[event.event_id] = Holding(event, payload.kn_id)
        else:
            self._other(event)
        self.events.append(event)

    def _other(self, event: Event) -> None:
        payload = event.payload
        if isinstance(payload, Version):
            self._version(payload, event)
        elif isinstance(payload, Match):
            self._match(payload, event)
        elif isinstance(payload, ChangeSet):
            self._changes(payload, event)
        elif isinstance(payload, Seen):
            self._seen(payload, event)
        else:
            from kn.identity.transitions import transition

            transition(self, event)

    def _changes(self, payload: ChangeSet, event: Event) -> None:
        version = self.versions.get(payload.version_id)
        if version is None:
            raise ValueError("change set requires a known source version")
        if payload.version_id in self.version_changes:
            raise ValueError("source version already has a change set")
        if len({item.field_id for item in payload.changes}) != len(payload.changes):
            raise ValueError("duplicate field changes")
        hashes = {item.field_id: item.digest for item in version.field_hashes}
        if any(
            item.current_hash is not None and hashes.get(item.field_id) != item.current_hash
            for item in payload.changes
        ):
            raise ValueError("change set hashes must equal its version's field hashes")
        self.changes[event.event_id] = payload
        self.version_changes[payload.version_id] = event.event_id
        self.positions[event.event_id] = event.sequence

    def _seen(self, payload: Seen, event: Event) -> None:
        version = self.versions.get(payload.version_id)
        if version is None:
            raise ValueError("a sighting requires a known source version")
        sighting = (payload.version_id, payload.fetch_id)
        if payload.fetch_id == version.fetch_id or sighting in self.sightings:
            raise ValueError("source version was already seen in this fetch")
        self.sightings[sighting] = event.sequence
        self._saw(version.record, payload.observed_at)

    def _saw(self, record: SourceKey, observed_at: datetime) -> None:
        """Older observations remain history without reducing `last_seen`."""
        key = record.record_id
        self.last_seen[key] = max(observed_at, self.last_seen.get(key, observed_at))

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
        self.holdings[event.event_id] = Holding(event, payload.kn_id)
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
        self.holdings[event.event_id] = Holding(event, payload.kn_id)
        self.identifier_keys.setdefault(key, []).append(event.event_id)

    def _version(self, payload: Version, event: Event) -> None:
        version_key = (*record_key(payload.record), payload.version)
        if version_key in self.version_keys:
            raise ValueError("source record version already exists")
        self.record(payload.record)
        self.versions[event.event_id] = payload
        self.version_keys[version_key] = event.event_id
        self.record_versions.setdefault(payload.record.record_id, []).append(event.event_id)
        self.positions[event.event_id] = event.sequence
        self._saw(payload.record, payload.observed_at)

    def _match(self, payload: Match, event: Event) -> None:
        check_match(payload, self.active)
        self.record(payload.record)
        self.matches[event.event_id] = payload
        if payload.trace is not None:
            self.requests.setdefault(payload.trace.request_digest, event)
            self.last_traced = event


def replay(events: tuple[Event, ...]) -> State:
    state = State()
    for event in events:
        state.apply(event)
    return state
