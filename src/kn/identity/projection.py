"""Translate validated history to the registered SQL storage contract."""

from collections.abc import Iterable
from datetime import datetime

from kn.contracts.model import canonical
from kn.identity.events import Event
from kn.identity.model import Attribute, ChangeSet, Identifier, Link, Match, Version
from kn.identity.state import State

type Value = str | int | float | datetime | None
type Rows = dict[str, list[dict[str, Value]]]


def rows(state: State, after: int | None = None) -> Rows:
    """Project either the whole registry or the suffix tracked by the state."""
    dirty = state.dirty if after is not None else None
    if after is not None and dirty is None:
        raise ValueError("incremental projection requires tracked state changes")
    result: Rows = {
        name: []
        for name in (
            "lifecycle_events",
            "objects",
            "source_records",
            "source_versions",
            "identifiers",
            "attributes",
            "links",
            "matches",
            "change_sets",
            "redirects",
        )
    }
    events = state.events if after is None else state.events[after:]
    _events(events, result)
    _objects(state, result, state.objects if dirty is None else dirty.objects)
    redirect_keys = state.redirects if dirty is None else dirty.redirects
    result["redirects"] = [
        {"kn_id": key, "successor": target}
        for key in redirect_keys
        for target in state.redirects[key]
    ]
    _sources(state, result, state.records if dirty is None else dirty.records)
    _holdings(state, result, state.holdings if dirty is None else dirty.holdings)
    return result


def _events(events: Iterable[Event], result: Rows) -> None:
    for event in events:
        _event_payload(event, result)
        result["lifecycle_events"].append(
            {
                "event_id": event.event_id,
                "sequence": event.sequence,
                "previous": event.previous,
                "kind": event.payload.kind,
                "occurred_at": event.occurred_at,
                "actor": event.actor,
                "reason": event.reason,
                "evidence": event.evidence,
                "decision_ref": event.decision_ref,
                "event_json": canonical(event.model_dump(mode="json")),
            }
        )


def _objects(state: State, result: Rows, keys: Iterable[str]) -> None:
    for key in keys:
        item = state.objects[key]
        successors = state.redirects.get(item.kn_id, ())
        result["objects"].append(
            {
                "kn_id": item.kn_id,
                "entity_class": item.entity_class,
                "state": item.state,
                "anchor_record_id": item.anchor.record_id,
                "mint_event": item.mint_event,
                "current_redirect": successors[0] if len(successors) == 1 else None,
            }
        )


def _sources(state: State, result: Rows, keys: Iterable[str]) -> None:
    for key in keys:
        record = state.records[key]
        result["source_records"].append(
            {
                "record_id": key,
                "source": record.source,
                "native_key": record.key,
                "last_seen": state.last_seen.get(key),
            }
        )


def _holdings(state: State, result: Rows, keys: Iterable[str]) -> None:
    for key in keys:
        holding = state.holdings[key]
        payload = holding.event.payload
        base: dict[str, Value] = {"kn_id": holding.kn_id}
        if isinstance(payload, Link):
            result["links"].append(
                {
                    **base,
                    "link_id": key,
                    "record_id": payload.record.record_id,
                    "method": payload.method,
                    "score": payload.score,
                    "probability": payload.probability,
                    "profile_digest": payload.profile_digest,
                    "profile_version": payload.profile_version,
                    "match_id": payload.match_id,
                    "decision_ref": holding.event.decision_ref,
                    "ended_event": holding.ended_event,
                }
            )
        elif isinstance(payload, Identifier):
            result["identifiers"].append(
                {
                    **base,
                    "identifier_id": key,
                    "namespace": payload.namespace,
                    "value": payload.value,
                    "issuer": payload.issuer,
                    "authority": payload.authority,
                    "valid_from": payload.valid_from,
                    "valid_to": payload.valid_to,
                    "evidence": holding.event.evidence,
                }
            )
        elif isinstance(payload, Attribute):
            result["attributes"].append(
                {
                    **base,
                    "attribute_id": key,
                    "field_id": payload.field_id,
                    "original": payload.original,
                    "normalized": payload.normalized,
                    "normalizer": payload.normalizer,
                    "profile_digest": payload.profile_digest,
                    "evidence": holding.event.evidence,
                }
            )


def _event_payload(event: Event, result: Rows) -> None:
    payload = event.payload
    if isinstance(payload, Version):
        result["source_versions"].append(
            {
                "version_id": event.event_id,
                "record_id": payload.record.record_id,
                "version": payload.version,
                "content_digest": payload.content_digest,
                "field_hashes_json": canonical(
                    [item.model_dump(mode="json") for item in payload.field_hashes]
                ),
                "observed_at": payload.observed_at,
                "source_updated_at": payload.source_updated_at,
                "fetch_id": payload.fetch_id,
                "archive_record_id": payload.archive_record_id,
                "code_digest": payload.code_digest,
            }
        )
    elif isinstance(payload, Match):
        result["matches"].append(
            {
                "match_id": event.event_id,
                "record_id": payload.record.record_id,
                "profile_digest": payload.profile_digest,
                "profile_version": payload.profile_version,
                "candidates_json": canonical(
                    [item.model_dump(mode="json") for item in payload.candidates]
                ),
                "decision": payload.decision,
                "selected": payload.selected,
                "decision_ref": event.decision_ref,
            }
        )
    elif isinstance(payload, ChangeSet):
        result["change_sets"].append(
            {
                "change_set_id": event.event_id,
                "version_id": payload.version_id,
                "changes_json": canonical(
                    [item.model_dump(mode="json") for item in payload.changes]
                ),
            }
        )
