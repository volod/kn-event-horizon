"""Lifecycle validation and ownership changes for durable replay."""

from datetime import datetime

from kn.identity.events import Event
from kn.identity.model import Identifier, Link, Merge, Reclassify, Restore, Retire, Split, Unlink
from kn.identity.state import State


def transition(state: State, event: Event) -> None:
    payload = event.payload
    if isinstance(payload, Unlink):
        _unlink(state, payload, event)
    elif isinstance(payload, Restore):
        _restore(state, payload)
    elif isinstance(payload, Retire):
        _retire(state, payload, event)
    elif isinstance(payload, Merge):
        _merge(state, payload, event)
    elif isinstance(payload, Split):
        _split(state, payload)
    elif isinstance(payload, Reclassify):
        _reclassify(state, payload, event)
    else:
        raise ValueError("unsupported identity transition")


def _unlink(state: State, payload: Unlink, event: Event) -> None:
    state.active(payload.kn_id)
    links = [
        item
        for item in state.owned(payload.kn_id).values()
        if isinstance(item.event.payload, Link) and item.event.payload.record == payload.record
    ]
    if not links:
        raise ValueError("cannot unlink a record without its active link")
    links[0].ended_event = event.event_id


def _restore(state: State, payload: Restore) -> None:
    item = state.objects.get(payload.kn_id)
    if item is None or item.state != "retired" or item.successors:
        raise ValueError("only a retired object without a successor can be restored")
    item.state = "active"


def _retire(state: State, payload: Retire, event: Event) -> None:
    item = state.active(payload.kn_id)
    item.state = "retired"
    for holding in state.owned(payload.kn_id).values():
        if isinstance(holding.event.payload, Link):
            holding.ended_event = event.event_id


def _reclassify(state: State, payload: Reclassify, event: Event) -> None:
    item = state.active(payload.kn_id)
    if item.entity_class == payload.successor.entity_class:
        raise ValueError("reclassification requires a different class")
    state.mint(payload.successor, event)
    item.state = "retired"
    state.redirect(item, (payload.successor.kn_id,))
    for holding in state.owned(payload.kn_id).values():
        holding.kn_id = payload.successor.kn_id


def _merge(state: State, payload: Merge, event: Event) -> None:
    item, target = state.active(payload.kn_id), state.active(payload.survivor)
    if item.kn_id == target.kn_id or item.entity_class != target.entity_class:
        raise ValueError("merge requires distinct active objects of the same class")
    if payload.authoritative is not None:
        _require_authority(state, payload, payload.authoritative, event.occurred_at)
    item.state = "merged"
    state.redirect(item, (target.kn_id,))
    for holding in state.owned(item.kn_id).values():
        holding.kn_id = target.kn_id


def _require_authority(state: State, merge: Merge, proof: Identifier, at: datetime) -> None:
    participants = {merge.kn_id, merge.survivor}
    if proof.kn_id not in participants or not _authoritative_at(proof, at):
        raise ValueError("merge requires a current authoritative observation on a participant")
    (other,) = participants - {proof.kn_id}
    if not any(
        isinstance(known := holding.event.payload, Identifier)
        and (known.namespace, known.value, known.issuer)
        == (proof.namespace, proof.value, proof.issuer)
        and _authoritative_at(known, at)
        for holding in state.owned(other).values()
    ):
        raise ValueError("merge requires a shared current authoritative identifier")


def _authoritative_at(identifier: Identifier, at: datetime) -> bool:
    return (
        identifier.authority == "authoritative"
        and identifier.valid_from <= at
        and (identifier.valid_to is None or at < identifier.valid_to)
    )


def _split(state: State, payload: Split) -> None:
    item = state.active(payload.kn_id)
    if len(set(payload.successors)) != len(payload.successors) or item.kn_id in payload.successors:
        raise ValueError("split requires distinct successors")
    for key in payload.successors:
        if state.active(key).entity_class != item.entity_class:
            raise ValueError("split successors must have the same class")
    owned = state.owned(payload.kn_id)
    assignments = {part.item_id: part.successor for part in payload.assignments}
    if len(assignments) != len(payload.assignments) or assignments.keys() != owned.keys():
        raise ValueError("split assigns each active link, identifier and attribute exactly once")
    if not set(assignments.values()) <= set(payload.successors):
        raise ValueError("split assignment targets an undeclared successor")
    item.state = "split"
    state.redirect(item, payload.successors)
    for key, holding in owned.items():
        holding.kn_id = assignments[key]
