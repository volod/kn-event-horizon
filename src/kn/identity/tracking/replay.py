"""Validate source version, change set and sighting events during identity replay."""

from typing import TYPE_CHECKING

from kn.identity.events import Event
from kn.identity.model import ChangeSet, Seen, Version

if TYPE_CHECKING:
    from kn.identity.state import State


def record_change_set(state: "State", payload: ChangeSet, event: Event) -> None:
    version = state.versions.get(payload.version_id)
    if version is None:
        raise ValueError("change set requires a known source version")
    if payload.version_id in state.version_changes:
        raise ValueError("source version already has a change set")
    if len({item.field_id for item in payload.changes}) != len(payload.changes):
        raise ValueError("duplicate field changes")
    hashes = {item.field_id: item.digest for item in version.field_hashes}
    if any(
        item.current_hash is not None and hashes.get(item.field_id) != item.current_hash
        for item in payload.changes
    ):
        raise ValueError("change set hashes must equal its version's field hashes")
    state.changes[event.event_id] = payload
    state.version_changes[payload.version_id] = event.event_id
    state.positions[event.event_id] = event.sequence


def record_sighting(state: "State", payload: Seen, event: Event) -> None:
    version = state.versions.get(payload.version_id)
    if version is None:
        raise ValueError("a sighting requires a known source version")
    sighting = (payload.version_id, payload.fetch_id)
    if payload.fetch_id == version.fetch_id or sighting in state.sightings:
        raise ValueError("source version was already seen in this fetch")
    state.sightings[sighting] = event.sequence
    state.saw(version.record, payload.observed_at)


def record_version(state: "State", payload: Version, event: Event) -> None:
    version_key = (payload.record.source, payload.record.key, payload.version)
    if version_key in state.version_keys:
        raise ValueError("source record version already exists")
    state.record(payload.record)
    state.versions[event.event_id] = payload
    state.version_keys[version_key] = event.event_id
    state.record_versions.setdefault(payload.record.record_id, []).append(event.event_id)
    state.positions[event.event_id] = event.sequence
    state.saw(payload.record, payload.observed_at)
