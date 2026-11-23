"""Pure replay validation. Invalid events never reach the durable append boundary."""

from dataclasses import dataclass, field
from datetime import datetime

from kn.identity.events import Event
from kn.identity.model import (
    Attribute,
    ChangeSet,
    Identifier,
    Link,
    Match,
    Mint,
    SourceKey,
    Version,
)


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
        if any(item.anchor == payload.anchor for item in self.objects.values()):
            raise ValueError("anchoring source record already minted an identity")
        self.record(payload.anchor)
        self.objects[payload.kn_id] = Object(
            payload.kn_id, payload.entity_class, payload.anchor, event.event_id
        )

    def resolve(self, kn_id: str) -> tuple[str, ...]:
        pending = [kn_id]
        visited: set[str] = set()
        targets: set[str] = set()
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            item = self.objects.get(key)
            if item is None:
                raise ValueError("unknown KN ID")
            if item.successors:
                pending.extend(item.successors)
            else:
                targets.add(key)
        return tuple(sorted(targets))

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
        else:
            from kn.identity.transitions import transition

            transition(self, event)

    def _changes(self, payload: ChangeSet, event: Event) -> None:
        if payload.version_id not in self.versions:
            raise ValueError("change set requires a known source version")
        if any(value.version_id == payload.version_id for value in self.changes.values()):
            raise ValueError("source version already has a change set")
        if len({item.field_id for item in payload.changes}) != len(payload.changes):
            raise ValueError("duplicate field changes")
        self.changes[event.event_id] = payload

    def _link(self, payload: Link, event: Event) -> None:
        self.active(payload.kn_id)
        if any(
            isinstance(item.event.payload, Link)
            and item.event.payload.record == payload.record
            and item.ended_event is None
            for item in self.holdings.values()
        ):
            raise ValueError("source record already has an active link")
        if payload.match_id is not None:
            match = self.matches.get(payload.match_id)
            if match is None or match.record != payload.record or match.selected != payload.kn_id:
                raise ValueError("link requires a matching stored decision")
            candidate = next(
                (item for item in match.candidates if item.kn_id == payload.kn_id), None
            )
            if candidate is None or (
                payload.score,
                payload.probability,
                payload.profile_digest,
                payload.profile_version,
            ) != (
                candidate.score,
                candidate.probability,
                match.profile_digest,
                match.profile_version,
            ):
                raise ValueError("link score and profile must match the stored decision")
        self.record(payload.record)
        self.holdings[event.event_id] = Holding(event, payload.kn_id)

    def _identifier(self, payload: Identifier, event: Event) -> None:
        self.active(payload.kn_id)
        for holding in self.holdings.values():
            other = holding.event.payload
            if not isinstance(other, Identifier):
                continue
            if (other.namespace, other.value) == (payload.namespace, payload.value) and (
                (other.valid_to is None or payload.valid_from < other.valid_to)
                and (payload.valid_to is None or other.valid_from < payload.valid_to)
            ):
                raise ValueError("identifier validity overlaps in its namespace")
        self.holdings[event.event_id] = Holding(event, payload.kn_id)

    def _version(self, payload: Version, event: Event) -> None:
        if any(
            (item.record, item.version) == (payload.record, payload.version)
            for item in self.versions.values()
        ):
            raise ValueError("source record version already exists")
        self.record(payload.record)
        self.versions[event.event_id] = payload
        key = payload.record.record_id
        self.last_seen[key] = max(payload.observed_at, self.last_seen.get(key, payload.observed_at))

    def _match(self, payload: Match, event: Event) -> None:
        keys = [item.kn_id for item in payload.candidates]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate match candidates")
        for key in keys:
            self.active(key)
        if (payload.decision == "link") != (payload.selected is not None):
            raise ValueError("only link decisions select a candidate")
        if payload.selected is not None and payload.selected not in keys:
            raise ValueError("selected match must be a candidate")
        self.record(payload.record)
        self.matches[event.event_id] = payload


def replay(events: tuple[Event, ...]) -> State:
    state = State()
    for event in events:
        state.apply(event)
    return state
