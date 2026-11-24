"""Operator lookups against the durable identity history."""

from collections.abc import Iterator
from typing import Literal

from kn.identity.events import Event
from kn.identity.journal import Journal
from kn.identity.model import Match, Merge, Reclassify, Split, uuid7
from kn.identity.state import Object, State

type Query = Literal["show", "resolve", "history"]


def inspect(journal: Journal, action: Query, kn_id: str) -> dict[str, object]:
    state = journal.state()
    terminal = state.resolve(uuid7(kn_id))
    if action == "resolve":
        return {"action": action, "kn_id": kn_id, "successors": list(terminal)}
    item = state.objects[kn_id]
    if action == "history":
        lineage = _lineage(state, item)
        return {
            "action": action,
            "kn_id": kn_id,
            "events": [
                event.model_dump(mode="json")
                for event in state.events
                if lineage.intersection(_participants(event))
            ],
        }
    return {
        "action": action,
        "kn_id": kn_id,
        "entity_class": item.entity_class,
        "state": item.state,
        "anchor": item.anchor.model_dump(mode="json"),
        "mint_event": item.mint_event,
        "successors": list(state.redirects.get(kn_id, ())),
        "holdings": [
            holding.event.model_dump(mode="json") for holding in state.owned(kn_id).values()
        ],
    }


def _participants(event: Event) -> Iterator[str]:
    payload = event.payload
    if hasattr(payload, "kn_id"):
        yield payload.kn_id
    if isinstance(payload, Merge):
        yield payload.survivor
    elif isinstance(payload, Split):
        yield from payload.successors
    elif isinstance(payload, Reclassify):
        yield payload.successor.kn_id
    elif isinstance(payload, Match):
        yield from (candidate.kn_id for candidate in payload.candidates)
        if payload.trace is not None and payload.trace.minted_id is not None:
            yield payload.trace.minted_id


def _lineage(state: State, item: Object) -> set[str]:
    """Include direct participants and the subsequent history of their redirect path."""
    pending = [item.kn_id]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in visited:
            visited.add(current)
            pending.extend(state.objects[current].successors)
    return visited
