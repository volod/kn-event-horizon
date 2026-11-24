"""Read matching evidence from the current identity registry."""

from collections import defaultdict
from datetime import datetime

from kn.identity.matching.observe import Key
from kn.identity.model import Attribute, Identifier, Link, SourceKey
from kn.identity.state import Holding, State


def source_links(state: State, record: SourceKey) -> list[Holding]:
    return [
        item
        for item in state.holdings.values()
        if isinstance(item.event.payload, Link) and item.event.payload.record == record
    ]


def anchor(state: State, record: SourceKey) -> str | None:
    return next((obj.kn_id for obj in state.objects.values() if obj.anchor == record), None)


def known_identifiers(state: State) -> dict[tuple[str, str], list[tuple[str, Identifier]]]:
    result: dict[tuple[str, str], list[tuple[str, Identifier]]] = defaultdict(list)
    for item in state.holdings.values():
        if isinstance(payload := item.event.payload, Identifier) and item.ended_event is None:
            result[payload.namespace, payload.value].append((item.kn_id, payload))
    return result


def authoritative_targets(
    state: State,
    keys: tuple[Key, ...],
    active: set[str],
    at: datetime,
) -> tuple[dict[str, tuple[Key, ...]], bool]:
    known = known_identifiers(state)
    matches: dict[str, tuple[Key, ...]] = {}
    conflict = False
    for key in sorted(keys, key=lambda item: item.parts):
        intervals = [
            (owner, identifier)
            for owner, identifier in known.get((key.namespace, key.value), ())
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
) -> dict[str, dict[str, str]]:
    readings: dict[tuple[str, str], tuple[datetime, set[str]]] = {}
    for item in state.holdings.values():
        payload, when = item.event.payload, item.event.occurred_at
        if (
            item.kn_id not in candidates
            or item.ended_event is not None
            or not isinstance(payload, Attribute)
            or when > at
        ):
            continue
        key = (item.kn_id, payload.field_id)
        latest, values = readings.get(key, (when, set()))
        if when > latest:
            readings[key] = (when, {payload.original})
        elif when == latest:
            values.add(payload.original)
            readings[key] = (latest, values)
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for (kn_id, field_id), (_, values) in readings.items():
        if len(values) == 1:
            (value,) = values
            result[kn_id][field_id] = value
    return result
