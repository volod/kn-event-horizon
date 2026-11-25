"""Read matching evidence from the current identity registry."""

from collections import defaultdict
from datetime import datetime

from kn.identity.matching.observe import Key
from kn.identity.model import Attribute, Identifier, SourceKey
from kn.identity.state import Holding, RecordKey, State, record_key

type View = dict[str, str]


def source_links(state: State, record: SourceKey) -> list[Holding]:
    return state.links(record)


def anchor(state: State, record: SourceKey) -> str | None:
    return state.anchors.get(record_key(record))


def identifiers(state: State, key: Key) -> list[tuple[str, Identifier]]:
    """Current owner and interval of each recorded validity interval of one identifier."""
    return [
        (item.kn_id, payload)
        for item in state.identifiers(key.namespace, key.value)
        if isinstance(payload := item.event.payload, Identifier) and item.ended_event is None
    ]


def authoritative_targets(
    state: State,
    keys: tuple[Key, ...],
    active: set[str],
    at: datetime,
) -> tuple[dict[str, tuple[Key, ...]], bool]:
    matches: dict[str, tuple[Key, ...]] = {}
    conflict = False
    for key in sorted(keys, key=lambda item: item.parts):
        intervals = [
            (owner, identifier)
            for owner, identifier in identifiers(state, key)
            if identifier.valid_to is None or at < identifier.valid_to
        ]
        current = next((item for item in intervals if item[1].valid_from <= at), None)
        if current is None:
            # An open-ended new observation would overlap a reserved interval.
            conflict |= bool(intervals)
            continue
        owner, identifier = current
        if (
            owner in active
            and identifier.issuer == key.issuer
            and identifier.authority == "authoritative"
        ):
            matches[owner] = (*matches.get(owner, ()), key)
        else:
            conflict = True
    return matches, conflict


def current_attributes(
    state: State, candidates: set[str], at: datetime
) -> dict[str, tuple[View, ...]]:
    """Latest readings of each candidate, one view per contributing source record.

    Merged and linked records keep their own evidence, so one record's newer reading never hides
    another record's. Readings recorded without a source record form one view of their own.
    """
    readings: dict[tuple[str, RecordKey | None, str], tuple[datetime, set[str]]] = {}
    for item in state.holdings.values():
        payload, when = item.event.payload, item.event.occurred_at
        if (
            item.kn_id not in candidates
            or item.ended_event is not None
            or not isinstance(payload, Attribute)
            or when > at
        ):
            continue
        origin = record_key(payload.record) if payload.record is not None else None
        key = (item.kn_id, origin, payload.field_id)
        latest, values = readings.get(key, (when, set()))
        if when > latest:
            readings[key] = (when, {payload.original})
        elif when == latest:
            values.add(payload.original)
            readings[key] = (latest, values)
    views: dict[str, dict[RecordKey | None, View]] = defaultdict(dict)
    for (kn_id, origin, field_id), (_, values) in readings.items():
        view = views[kn_id].setdefault(origin, {})
        if len(values) == 1:
            (view[field_id],) = values
    return {
        kn_id: tuple(view for _, view in sorted(by_origin.items(), key=_origin_order))
        for kn_id, by_origin in views.items()
    }


def _origin_order(item: tuple[RecordKey | None, View]) -> tuple[bool, RecordKey]:
    origin = item[0]
    return origin is not None, origin or ("", "")
