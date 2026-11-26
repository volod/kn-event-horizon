"""Read-only lineage of an object or field: identity history, records, claims and the fact.

A lookup by a merged, split or reclassified ID shows the lineage of its terminal successors. The
view covers those successors and every object that redirects to them, so a merged ID shows its
survivor's lineage with the merge event. A claim about a split object belongs to the successor
that now holds its source record. Identity rows carry no rights statement, so an audience that
does not permit every rights statement sees no identity attribute or match feature values.
"""

from collections import Counter
from collections.abc import Callable, Collection, Iterator
from typing import Any

from kn.evidence.lineage import EvidenceRows, Row, View, evidence_view, gap
from kn.evidence.ranking import Audience
from kn.identity.events import Event
from kn.identity.lineage_records import held_by_successor, records
from kn.identity.model import Attribute, Identifier, Link, Match, uuid7
from kn.identity.queries import participants
from kn.identity.state import Holding, State

KN_PREFIX = "kn:"
QUALIFIER = ":"
# Events shown in their own sections rather than in the identity history.
HELD_KINDS = frozenset({"linked", "identifier_recorded", "attribute_recorded", "match_recorded"})


def target(state: State, reference: str) -> str:
    """A KN ID, or the one object that holds a qualified identifier `namespace:value`."""
    if reference.startswith(KN_PREFIX):
        state.resolve(uuid7(reference))
        return reference
    owners = {
        holding.kn_id
        for index, character in enumerate(reference)
        if character == QUALIFIER
        for holding in state.identifiers(reference[:index], reference[index + 1 :])
    }
    if len(owners) != 1:
        problem = "names several objects; use a KN ID" if owners else "is unknown"
        raise ValueError(f"the KN ID or qualified identifier {problem}")
    return owners.pop()


def members(state: State, terminals: Collection[str]) -> set[str]:
    """The terminal objects and every object whose successors lead to them."""
    parents: dict[str, list[str]] = {}
    for item in state.objects.values():
        for successor in item.successors:
            parents.setdefault(successor, []).append(item.kn_id)
    found: set[str] = set()
    pending = list(terminals)
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(parents.get(current, ()))
    return found


def lineage(
    state: State,
    rows: EvidenceRows,
    reference: str,
    *,
    field_id: str | None = None,
    audience: Audience | None = None,
) -> View:
    """The lineage view; the same keys and values in every locale."""
    audience = audience or Audience()
    kn_id = target(state, reference)
    terminals = state.resolve(kn_id)
    scope = members(state, terminals)
    held = [holding for holding in state.holdings.values() if holding.kn_id in scope]
    linked = {
        payload.record.record_id
        for holding in held
        if isinstance(payload := holding.event.payload, Link)
    }

    belongs, unplaced = _placement(state, linked)
    found = evidence_view(
        rows, scope, terminals, field_id=field_id, audience=audience, belongs=belongs
    )
    claims = found.sections["claims"]
    open_view = audience.rights is None
    if open_view:
        found.gaps.extend(gap("claim_successor_missing", key) for key in sorted(unplaced))
    identity = _identity(state, scope, held, linked, field_id, open_view, found.withheld)
    cited = linked | {row["record_id"] for row in claims}
    return {
        "action": "lineage",
        "reference": reference,
        "kn_id": kn_id,
        "terminals": list(terminals),
        "field_id": field_id,
        "audience": audience.name,
        "permitted": None if open_view else sorted(audience.rights or ()),
        **identity,
        "records": records(state, cited, field_id),
        **found.sections,
        "withheld": {name: count for name, count in sorted(found.withheld.items()) if count},
        "gaps": [*_claim_gaps(state, claims), *found.gaps],
    }


def _placement(state: State, linked: set[str]) -> tuple[Callable[[Row], bool], list[str]]:
    """Which claims the view holds, and the claims no split successor holds, as they are read."""
    unplaced: list[str] = []

    def belongs(row: Row) -> bool:
        # A split object's claim follows the source record to the successor that holds it.
        if len(state.resolve(row["kn_id"])) == 1 or row["record_id"] in linked:
            return True
        if not held_by_successor(state, row["record_id"], row["kn_id"]):
            unplaced.append(row["claim_key"])
        return False

    return belongs, unplaced


def _identity(
    state: State,
    scope: set[str],
    held: list[Holding],
    linked: set[str],
    field_id: str | None,
    open_view: bool,
    withheld: Counter[str],
) -> dict[str, list[dict[str, Any]]]:
    attributes = [
        _attribute(holding)
        for holding in held
        if isinstance(payload := holding.event.payload, Attribute)
        and field_id in (None, payload.field_id)
    ]
    if not open_view:
        withheld["attributes"] += len(attributes)
        attributes = []
    return {
        "objects": [_object(state, key) for key in sorted(scope)],
        "history": [
            event.model_dump(mode="json")
            for event in state.events
            if event.payload.kind not in HELD_KINDS and scope.intersection(participants(event))
        ],
        "identifiers": [
            _identifier(holding)
            for holding in held
            if isinstance(holding.event.payload, Identifier)
        ],
        "attributes": attributes,
        "links": [_link(holding) for holding in held if isinstance(holding.event.payload, Link)],
        "matches": list(_matches(state, scope, linked, open_view, withheld)),
    }


def _object(state: State, kn_id: str) -> dict[str, Any]:
    item = state.objects[kn_id]
    return {
        "kn_id": kn_id,
        "entity_class": item.entity_class,
        "state": item.state,
        "anchor": {**item.anchor.model_dump(mode="json"), "record_id": item.anchor.record_id},
        "mint_event": item.mint_event,
        "successors": list(item.successors),
        "terminals": list(state.resolve(kn_id)),
    }


def _held(holding: Holding, key: str) -> dict[str, Any]:
    entry = holding.event
    payload = entry.payload.model_dump(mode="json", exclude={"kind", "record"})
    return {
        key: entry.event_id,
        "owner": holding.kn_id,
        **payload,
        "recorded_at": entry.model_dump(mode="json")["occurred_at"],
        "actor": entry.actor,
        "evidence": entry.evidence,
        "decision_ref": entry.decision_ref,
    }


def _identifier(holding: Holding) -> dict[str, Any]:
    return _held(holding, "identifier_id")


def _attribute(holding: Holding) -> dict[str, Any]:
    payload = holding.event.payload
    assert isinstance(payload, Attribute)
    record_id = None if payload.record is None else payload.record.record_id
    return {**_held(holding, "attribute_id"), "record_id": record_id}


def _link(holding: Holding) -> dict[str, Any]:
    payload = holding.event.payload
    assert isinstance(payload, Link)
    return {
        **_held(holding, "link_id"),
        "record_id": payload.record.record_id,
        "ended_event": holding.ended_event,
    }


def _matches(
    state: State, scope: set[str], linked: set[str], open_view: bool, withheld: Counter[str]
) -> Iterator[dict[str, Any]]:
    for entry in state.events:
        match = entry.payload
        if not isinstance(match, Match) or not (
            match.record.record_id in linked or scope.intersection(participants(entry))
        ):
            continue
        candidates = [item.model_dump(mode="json") for item in match.candidates]
        if not open_view:
            for item in candidates:
                withheld["match_features"] += len(item["features"])
                item["features"] = []
        yield _match(entry, match, candidates)


def _match(entry: Event, match: Match, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "match_id": entry.event_id,
        "record_id": match.record.record_id,
        "decision": match.decision,
        "selected": match.selected,
        "profile_digest": match.profile_digest,
        "profile_version": match.profile_version,
        "candidates": candidates,
        "trace": None if match.trace is None else match.trace.model_dump(mode="json"),
        "recorded_at": entry.model_dump(mode="json")["occurred_at"],
        "actor": entry.actor,
        "decision_ref": entry.decision_ref,
    }


def _claim_gaps(state: State, claims: list[dict[str, Any]]) -> Iterator[dict[str, str]]:
    """Visible claims whose record, version or change set the identity journal lacks."""
    for row in claims:
        key = row["claim_key"]
        version = state.versions.get(row["source_version_id"])
        if row["record_id"] not in state.records:
            yield gap("claim_record_missing", key)
        if version is None or version.record.record_id != row["record_id"]:
            yield gap("claim_version_missing", key)
        change_set = row["change_set_id"]
        if change_set is not None and (
            state.changes.get(change_set) is None
            or state.changes[change_set].version_id != row["source_version_id"]
        ):
            yield gap("claim_change_set_missing", key)
