"""Read matching evidence from the current identity registry."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta

from kn.identity.matching.observe import Key
from kn.identity.matching.scoring import Value
from kn.identity.model import Attribute, Identifier, SourceKey
from kn.identity.profiles import Profile
from kn.identity.state import Holding, RecordKey, State, record_key

type View = dict[str, str]
type ReadingKey = tuple[str, RecordKey | None, str]
# A reading after the instant ranks behind every reading at or before it, then by distance.
type Distance = tuple[bool, timedelta]
type Readings = dict[ReadingKey, tuple[Distance, set[str]]]


def source_links(state: State, record: SourceKey) -> list[Holding]:
    return state.links(record)


def anchor(state: State, record: SourceKey) -> str | None:
    return state.anchors.get(record_key(record))


def identifiers(
    state: State, key: Key, *, before: int | None = None
) -> list[tuple[str, Identifier]]:
    """Current owner and interval of each recorded validity interval of one identifier."""
    return [
        (item.kn_id, payload)
        for item in state.identifiers(key.namespace, key.value)
        if isinstance(payload := item.event.payload, Identifier)
        and item.ended_event is None
        and (before is None or item.event.sequence < before)
    ]


def holder(state: State, key: Key, at: datetime) -> tuple[tuple[str, Identifier] | None, bool]:
    """The owner and interval that hold an identifier at an instant, and whether it is reserved.

    An interval starts at its first observation, so an observation earlier than every recorded
    interval belongs to the earliest holder. An instant between two holders has no holder, and a
    later interval reserves the identifier: an open-ended new observation would overlap it.
    """
    recorded = identifiers(state, key)
    intervals = [
        (owner, identifier)
        for owner, identifier in recorded
        if identifier.valid_to is None or at < identifier.valid_to
    ]
    current = next((item for item in intervals if item[1].valid_from <= at), None)
    if current is None and all(at < identifier.valid_from for _, identifier in recorded):
        current = min(intervals, key=lambda item: item[1].valid_from, default=None)
    return current, current is None and bool(intervals)


def authoritative_targets(
    state: State,
    keys: tuple[Key, ...],
    entity_class: str,
    at: datetime,
) -> tuple[dict[str, tuple[Key, ...]], bool]:
    matches: dict[str, tuple[Key, ...]] = {}
    conflict = False
    for key in sorted(keys, key=lambda item: item.parts):
        current, reserved = holder(state, key, at)
        conflict |= reserved
        if current is None:
            continue
        owner, identifier = current
        if (
            is_active(state, entity_class, owner)
            and identifier.issuer == key.issuer
            and identifier.authority == "authoritative"
        ):
            matches[owner] = (*matches.get(owner, ()), key)
        else:
            conflict = True
    return matches, conflict


def is_active(state: State, entity_class: str, key: str | None) -> bool:
    item = state.objects.get(key) if key is not None else None
    return item is not None and item.state == "active" and item.entity_class == entity_class


def blocked_owners(state: State, profile: Profile, left: Mapping[str, Value]) -> set[str]:
    """Use the smallest historical bucket in each complete block to find possible owners.

    The scorer still checks the entire block against each as-of record view. This preserves
    matches when a different profile normalized the stored reading or its owner changed.
    """
    normalizers = {item.field_id: item.normalizer for item in profile.attributes}
    candidates: set[str] = set()
    for block in profile.blocking_keys:
        if all(key in left for key in block):
            bucket = min(
                (
                    state.attributes.lookup(key, normalizers[key], left[key].normalized)
                    for key in block
                ),
                key=len,
            )
            candidates.update(state.holdings[key].kn_id for key in bucket)
    return {key for key in candidates if is_active(state, profile.entity_class, key)}


def current_attributes(
    state: State, candidates: Iterable[str], at: datetime
) -> dict[str, tuple[View, ...]]:
    """Latest readings of each candidate, one view per contributing source record.

    Merged and linked records keep their own evidence, so one record's newer reading never hides
    another record's. Readings recorded without a source record form one view of their own.
    """
    readings = _latest_readings(state, candidates, at)
    views: dict[str, dict[RecordKey | None, View]] = defaultdict(dict)
    for (kn_id, origin, field_id), (_, values) in readings.items():
        view = views[kn_id].setdefault(origin, {})
        if len(values) == 1:
            (view[field_id],) = values
    return {
        kn_id: tuple(view for _, view in sorted(by_origin.items(), key=_origin_order))
        for kn_id, by_origin in views.items()
    }


def _latest_readings(state: State, candidates: Iterable[str], at: datetime) -> Readings:
    """Each record's reading of each field closest to the observation instant.

    The latest reading at or before the instant wins. A record whose readings all come later
    contributes its earliest one, so an older observation that arrives late still finds it.
    """
    readings: Readings = {}
    for item in (holding for key in candidates for holding in state.owned(key).values()):
        payload, when = item.event.payload, item.event.occurred_at
        if not isinstance(payload, Attribute):
            continue
        origin = record_key(payload.record) if payload.record is not None else None
        key = (item.kn_id, origin, payload.field_id)
        distance = (when > at, abs(when - at))
        closest = readings.get(key)
        if closest is None or distance < closest[0]:
            readings[key] = (distance, {payload.original})
        elif distance == closest[0]:
            closest[1].add(payload.original)
    return readings


def _origin_order(item: tuple[RecordKey | None, View]) -> tuple[bool, RecordKey]:
    origin = item[0]
    return origin is not None, origin or ("", "")
