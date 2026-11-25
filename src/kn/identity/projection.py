"""Translate validated history to the registered SQL storage contract."""

from datetime import datetime

from kn.contracts.model import canonical
from kn.identity.model import Attribute, Identifier, Link
from kn.identity.state import State

type Value = str | int | float | datetime | None
type Rows = dict[str, list[dict[str, Value]]]


def rows(state: State) -> Rows:
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
    _lifecycle(state, result)
    _sources(state, result)
    _holdings(state, result)
    _decisions(state, result)
    return result


def _lifecycle(state: State, result: Rows) -> None:
    for event in state.events:
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
    for item in state.objects.values():
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
        result["redirects"].extend({"kn_id": item.kn_id, "successor": key} for key in successors)


def _sources(state: State, result: Rows) -> None:
    for key, record in state.records.items():
        result["source_records"].append(
            {
                "record_id": key,
                "source": record.source,
                "native_key": record.key,
                "last_seen": state.last_seen.get(key),
            }
        )
    for key, version in state.versions.items():
        result["source_versions"].append(
            {
                "version_id": key,
                "record_id": version.record.record_id,
                "version": version.version,
                "content_digest": version.content_digest,
                "field_hashes_json": canonical(
                    [item.model_dump(mode="json") for item in version.field_hashes]
                ),
                "observed_at": version.observed_at,
                "source_updated_at": version.source_updated_at,
                "fetch_id": version.fetch_id,
                "archive_record_id": version.archive_record_id,
                "code_digest": version.code_digest,
            }
        )


def _holdings(state: State, result: Rows) -> None:
    for key, holding in state.holdings.items():
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


def _decisions(state: State, result: Rows) -> None:
    references = {event.event_id: event.decision_ref for event in state.events}
    for key, match in state.matches.items():
        result["matches"].append(
            {
                "match_id": key,
                "record_id": match.record.record_id,
                "profile_digest": match.profile_digest,
                "profile_version": match.profile_version,
                "candidates_json": canonical(
                    [item.model_dump(mode="json") for item in match.candidates]
                ),
                "decision": match.decision,
                "selected": match.selected,
                "decision_ref": references[key],
            }
        )
    for key, change in state.changes.items():
        result["change_sets"].append(
            {
                "change_set_id": key,
                "version_id": change.version_id,
                "changes_json": canonical(
                    [item.model_dump(mode="json") for item in change.changes]
                ),
            }
        )
