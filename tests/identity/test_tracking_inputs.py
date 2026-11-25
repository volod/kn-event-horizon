"""Crawler mapping inputs, delivery validation and replay checks of tracked history."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from kn.evidence.values import Missing, TextValue
from kn.identity.events import event
from kn.identity.model import ChangeSet, FieldChange, Seen
from kn.identity.state import replay
from kn.identity.tracking import mapping
from kn.identity.tracking.delivery import Statement
from kn.review.model import digest
from tests.identity.tracking_fixtures import (
    PRICE,
    RECORD,
    SOURCE,
    T0,
    MemoryClaims,
    delivery,
    linked_journal,
    price,
    track,
)

MAPPING = {
    "record_key": ["publisher", "id"],
    "version_field": "updated",
    "fields": [
        {"native": "price", "field_id": PRICE},
        {"native": "package", "field_id": "part.package"},
        {"native": "notes", "field_id": "part.notes"},
    ],
    "time_fields": [{"native": "updated", "semantics": "updated_at", "timezone": "UTC"}],
}


def test_mapping_reads_keys_versions_times_and_stated_fields() -> None:
    native = {
        "publisher": "acme",
        "id": "00042",
        "updated": "2026-04-01T08:00:00",
        "price": "1.20",
        "package": "  ",
        "ignored": "x",
    }
    key = mapping.record_key(MAPPING, SOURCE, native)
    assert key.key == '["acme","00042"]' and key.source == SOURCE
    single = {**MAPPING, "record_key": ["id"]}
    assert mapping.record_key(single, SOURCE, native).key == "00042"
    assert mapping.version(MAPPING, native) == "2026-04-01T08:00:00"
    assert mapping.updated_at(MAPPING, native) == datetime(2026, 4, 1, 8, tzinfo=UTC)
    assert mapping.stated(MAPPING, native) == {PRICE: "1.20", "part.package": None}
    assert mapping.ordering(MAPPING) == "updated"
    assert mapping.ordering({**MAPPING, "version_field": "revision"}) == "version"
    assert mapping.ordering({"record_key": ["id"], "fields": []}) == "fetch"


@pytest.mark.parametrize(
    "native,error",
    [
        ({"publisher": "acme", "id": ""}, "record_key_missing"),
        ({"publisher": "acme"}, "record_key_missing"),
        ({"publisher": "acme", "id": True}, "record_key_missing"),
        ({"publisher": "acme", "id": 1.5}, "text or integers"),
    ],
)
def test_mapping_refuses_missing_or_untyped_keys(native, error) -> None:
    with pytest.raises(ValueError, match=error):
        mapping.record_key(MAPPING, SOURCE, native)


def test_a_naive_updated_time_needs_a_declared_zone() -> None:
    fields = [{"native": "updated", "semantics": "updated_at"}]
    with pytest.raises(ValueError, match="time_invalid"):
        mapping.updated_at({**MAPPING, "time_fields": fields}, {"updated": "2026-04-01T08:00"})
    formatted = [{"native": "updated", "semantics": "updated_at", "format": "%d.%m.%Y %z"}]
    value = mapping.updated_at(
        {**MAPPING, "time_fields": formatted}, {"updated": "01.04.2026 +0300"}
    )
    assert value == datetime(2026, 3, 31, 21, tzinfo=UTC)


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"ordering": "version"}, "numeric version"),
        ({"ordering": "version", "version": "v7"}, "numeric version"),
        ({"ordering": "updated"}, "updated time"),
        ({"parent": RECORD}, "parent record"),
        ({"origin_uri": "https://user:secret@example.test/a"}, "credential"),
        ({"statements": (price("1"), price("2"))}, "each field once"),
    ],
)
def test_deliveries_refuse_unusable_inputs(changes, error) -> None:
    with pytest.raises(ValidationError, match=error):
        delivery(fetch=1, **changes)


def test_statements_leave_empty_values_to_tracking() -> None:
    with pytest.raises(ValidationError, match="null value"):
        Statement(field_id=PRICE, value=Missing(reason="source_empty"), locator="/p")
    with pytest.raises(ValidationError, match="blank text"):
        Statement(field_id=PRICE, value=TextValue(text=" ", language="und"), locator="/p")
    # A stated, disclosed absence is a value; only tracking records `source_empty`.
    assert Statement(field_id=PRICE, value=Missing(reason="not_disclosed"), locator="/p")
    empty = Statement(field_id=PRICE, original_value="", locator="/p")
    assert empty.digest == Statement(field_id=PRICE, original_value="n/a", locator="/q").digest
    assert empty.digest != price("1").digest != price("1.0").digest


A, B = digest("a"), digest("b")


@pytest.mark.parametrize(
    "change,previous,current",
    [
        ("added", A, B),
        ("added", None, None),
        ("changed", A, A),
        ("changed", None, B),
        ("emptied", A, None),
        ("unchanged", A, B),
        ("unchanged", None, None),
        ("not_stated", A, B),
    ],
)
def test_field_changes_refuse_inconsistent_hashes(change, previous, current) -> None:
    with pytest.raises(ValidationError, match="inconsistent hashes"):
        FieldChange(field_id=PRICE, change=change, previous_hash=previous, current_hash=current)


def _append(events, payload):
    return (
        *events,
        event(
            payload,
            previous=events[-1],
            occurred_at=T0 + timedelta(days=1),
            actor="engine:fixture",
            reason="Test",
            evidence="archive:test",
        ),
    )


def test_replay_checks_change_set_hashes_and_sightings(tmp_path: Path) -> None:
    journal, _ = linked_journal(tmp_path)
    track(journal, MemoryClaims(), delivery(price("1"), fetch=1))
    events = journal.read()
    state = replay(events)
    (version_id,) = state.record_versions[RECORD.record_id]
    with pytest.raises(ValueError, match="already has a change set"):
        replay(_append(events, ChangeSet(version_id=version_id, changes=())))
    wrong = FieldChange(field_id=PRICE, change="added", current_hash=A)
    with pytest.raises(ValueError, match="field hashes"):
        replay(_append(events[:-1], ChangeSet(version_id=version_id, changes=(wrong,))))
    seen = {"archive_record_id": "warc:2", "observed_at": T0}
    with pytest.raises(ValueError, match="known source version"):
        replay(_append(events, Seen(version_id=A, fetch_id="fetch-2", **seen)))
    with pytest.raises(ValueError, match="already seen"):
        replay(_append(events, Seen(version_id=version_id, fetch_id="fetch-1", **seen)))
    twice = _append(events, Seen(version_id=version_id, fetch_id="fetch-2", **seen))
    assert replay(twice).last_seen[RECORD.record_id] == T0 + timedelta(hours=1)
    with pytest.raises(ValueError, match="already seen"):
        replay(_append(twice, Seen(version_id=version_id, fetch_id="fetch-2", **seen)))
