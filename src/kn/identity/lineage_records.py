"""Source records in a lineage view: versions, change sets and sightings down to archive IDs."""

from collections.abc import Collection
from typing import Any

from kn.evidence.lineage import instant
from kn.identity.model import ChangeSet, Seen
from kn.identity.state import State


def records(
    state: State, record_ids: Collection[str], field_id: str | None
) -> list[dict[str, Any]]:
    """Known records in record ID order; their versions in journal order.

    With a field, each version keeps only that field's hash and change. Versions stay listed, so
    a version that did not state the field still shows the record's history.
    """
    sightings: dict[str, list[dict[str, Any]]] = {}
    for (version_id, _), sequence in sorted(state.sightings.items(), key=lambda item: item[1]):
        entry = state.events[sequence - 1]
        assert isinstance(entry.payload, Seen)
        sightings.setdefault(version_id, []).append(
            {"event_id": entry.event_id, **entry.payload.model_dump(mode="json", exclude={"kind"})}
        )
    result = []
    for record_id in sorted(set(record_ids) & state.records.keys()):
        key = state.records[record_id]
        versions = [
            _version(state, version_id, field_id, sightings.get(version_id, []))
            for version_id in state.record_versions.get(record_id, ())
        ]
        seen = state.last_seen.get(record_id)
        result.append(
            {
                "record_id": record_id,
                **key.model_dump(mode="json"),
                "last_seen": None if seen is None else instant(seen),
                "versions": versions,
            }
        )
    return result


def _version(
    state: State, version_id: str, field_id: str | None, sightings: list[dict[str, Any]]
) -> dict[str, Any]:
    version = state.versions[version_id]
    data = version.model_dump(mode="json", exclude={"kind", "record"})
    data["field_hashes"] = [
        item for item in data["field_hashes"] if field_id in (None, item["field_id"])
    ]
    change_set = state.version_changes.get(version_id)
    return {
        "version_id": version_id,
        **data,
        "change_set": None if change_set is None else _changes(state, change_set, field_id),
        "sightings": sightings,
    }


def _changes(state: State, change_set_id: str, field_id: str | None) -> dict[str, Any]:
    change_set: ChangeSet = state.changes[change_set_id]
    return {
        "change_set_id": change_set_id,
        "changes": [
            item.model_dump(mode="json")
            for item in change_set.changes
            if field_id in (None, item.field_id)
        ],
    }


def held_by_successor(state: State, record_id: str, kn_id: str) -> bool:
    """Whether a terminal successor of `kn_id` holds a current link of the record."""
    record = state.records.get(record_id)
    successors = state.resolve(kn_id)
    return record is not None and any(
        item.ended_event is None and item.kn_id in successors for item in state.links(record)
    )
