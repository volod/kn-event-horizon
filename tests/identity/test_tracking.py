"""Field-level change sets of partial records: one case per change-table row, then the gates."""

from datetime import timedelta
from pathlib import Path

import pytest

from kn.evidence.model import Claim, Confirmation
from kn.evidence.values import Missing
from kn.identity.model import ChangeSet, Seen, Version
from kn.identity.tracking.changes import prepare
from tests.identity.tracking_fixtures import (
    FRAGMENT,
    PACKAGE,
    PRICE,
    RECORD,
    T0,
    VOLTAGE,
    MemoryClaims,
    delivery,
    link,
    linked_journal,
    merge,
    package,
    price,
    track,
    voltage,
)

FULL = (price("1.20"), package("SOT-23"), voltage("5.5"))


@pytest.fixture
def tracker(tmp_path: Path):
    journal, kn_id = linked_journal(tmp_path)
    claims = MemoryClaims()
    track(journal, claims, delivery(*FULL, fetch=1))
    return journal, claims, kn_id


def _changes(tracked) -> dict[str, str]:
    return {item.field_id: item.change for item in tracked.changes}


def test_a_first_delivery_adds_one_claim_per_stated_field(tmp_path: Path) -> None:
    journal, kn_id = linked_journal(tmp_path)
    claims = MemoryClaims()
    tracked, rows, written = track(journal, claims, delivery(*FULL, fetch=1))
    assert tracked.outcome == "current" and tracked.kn_id == kn_id
    assert _changes(tracked) == {PRICE: "added", PACKAGE: "added", VOLTAGE: "added"}
    assert written == 3 and all(isinstance(row, Claim) for row in rows)
    assert {row.supersedes for row in rows if isinstance(row, Claim)} == {None}
    state = journal.state()
    (version,) = (e.payload for e in state.events if isinstance(e.payload, Version))
    assert (version.fetch_id, version.archive_record_id) == ("fetch-1", "warc:1")
    assert state.last_seen[RECORD.record_id] == T0 + timedelta(hours=1)


@pytest.mark.parametrize(
    "statements,field,expected,claims,confirmations",
    [
        pytest.param((price("1.25"),), PRICE, "changed", 1, 0, id="changed"),
        pytest.param((price("1.20"),), PRICE, "unchanged", 0, 1, id="unchanged"),
        pytest.param((package(None),), PACKAGE, "emptied", 1, 0, id="emptied"),
        pytest.param((voltage("5.5"),), PRICE, "not_stated", 0, 1, id="not_stated"),
    ],
)
def test_each_change_class_has_its_effect_on_claims(
    tracker, statements, field, expected, claims, confirmations
) -> None:
    journal, store, _ = tracker
    tracked, rows, _ = track(journal, store, delivery(*statements, fetch=2))
    assert _changes(tracked)[field] == expected
    assert sum(isinstance(row, Claim) for row in rows) == claims
    assert sum(isinstance(row, Confirmation) for row in rows) == confirmations


def test_a_price_only_record_leaves_parameter_claims_untouched(tracker) -> None:
    journal, claims, _ = tracker
    before = claims.current()
    tracked, rows, _ = track(journal, claims, delivery(price("1.25"), fetch=2))
    assert _changes(tracked) == {PRICE: "changed", PACKAGE: "not_stated", VOLTAGE: "not_stated"}
    (claim,) = rows
    assert isinstance(claim, Claim) and claim.supersedes == before[PRICE].key
    after = claims.current()
    assert after[PACKAGE] == before[PACKAGE] and after[VOLTAGE] == before[VOLTAGE]
    assert after[PRICE] == claim and claim.change_set_id == tracked.change_set_id


def test_an_emptied_field_claims_source_empty_and_clears_nothing(tracker) -> None:
    journal, claims, _ = tracker
    previous = claims.current()[PACKAGE]
    _, rows, _ = track(journal, claims, delivery(package(""), fetch=2))
    (claim,) = rows
    assert isinstance(claim, Claim) and claim.change_kind == "emptied"
    assert claim.value == Missing(reason="source_empty") and claim.supersedes == previous.key
    assert previous.key in claims.claims and len(claims.claims) == 4
    # A later empty statement confirms the empty claim; a value then changes it.
    _, rows, _ = track(journal, claims, delivery(package(None), fetch=3))
    assert [type(row) for row in rows] == [Confirmation] and rows[0].claim_key == claim.key
    _, rows, _ = track(journal, claims, delivery(package("SOT-23"), fetch=4))
    assert rows[0].change_kind == "changed" and rows[0].supersedes == claim.key


def test_an_omitted_field_changes_nothing(tracker) -> None:
    journal, claims, _ = tracker
    before = dict(claims.claims)
    tracked, rows, written = track(journal, claims, delivery(fetch=2))
    assert set(_changes(tracked).values()) == {"not_stated"} and rows == () and written == 0
    assert claims.claims == before


def test_a_field_first_stated_empty_has_nothing_to_clear(tmp_path: Path) -> None:
    journal, _ = linked_journal(tmp_path)
    claims = MemoryClaims()
    tracked, rows, _ = track(journal, claims, delivery(package(None), fetch=1))
    assert _changes(tracked) == {PACKAGE: "not_stated"} and rows == ()
    tracked, rows, _ = track(journal, claims, delivery(package("SOT-23"), fetch=2))
    assert _changes(tracked) == {PACKAGE: "added"} and rows[0].supersedes is None


def test_a_record_that_stops_appearing_keeps_its_claims(tracker) -> None:
    journal, claims, _ = tracker
    last_seen = journal.state().last_seen[RECORD.record_id]
    other = RECORD.model_copy(update={"key": "OFFER-00043"})
    link(journal, other)
    before = dict(claims.claims)
    for fetch in (2, 3):
        track(journal, claims, delivery(price("9.99"), fetch=fetch, record=other))
    state = journal.state()
    assert state.last_seen[RECORD.record_id] == last_seen
    assert state.last_seen[other.record_id] == T0 + timedelta(hours=3)
    assert {key: claims.claims[key] for key in before} == before
    assert set(claims.current()) == {PRICE, PACKAGE, VOLTAGE}
    assert len(state.objects) == 2 and all(
        item.state == "active" for item in state.objects.values()
    )


@pytest.mark.parametrize("ordering", ["fetch", "version"])
def test_an_identical_redelivery_confirms_and_adds_no_claim(tmp_path: Path, ordering) -> None:
    journal, _ = linked_journal(tmp_path)
    claims = MemoryClaims()
    version = "7" if ordering == "version" else None
    first = {"version": version, "ordering": ordering}
    track(journal, claims, delivery(*FULL, fetch=1, **first))
    tracked, rows, _ = track(journal, claims, delivery(*FULL, fetch=2, **first))
    assert tracked.outcome == "seen" and set(_changes(tracked).values()) == {"unchanged"}
    assert len(rows) == 3 and all(isinstance(row, Confirmation) for row in rows)
    assert len(claims.claims) == 3
    state = journal.state()
    assert sum(isinstance(e.payload, Version) for e in state.events) == 1
    assert [type(e.payload) for e in state.events][-1] is Seen
    assert state.last_seen[RECORD.record_id] == T0 + timedelta(hours=2)


def test_a_late_older_version_is_history_and_never_current(tmp_path: Path) -> None:
    journal, _ = linked_journal(tmp_path)
    claims = MemoryClaims()
    newer = {"ordering": "updated", "source_updated_at": T0 + timedelta(days=2)}
    older = {"ordering": "updated", "source_updated_at": T0 + timedelta(days=1)}
    track(journal, claims, delivery(price("1.30"), fetch=1, version="r2", **newer))
    current = claims.current()
    tracked, rows, written = track(journal, claims, delivery(price("1.10"), fetch=2, **older))
    assert tracked.outcome == "history" and tracked.changes == () and rows == ()
    assert written == 0 and claims.current() == current
    state = journal.state()
    assert len(state.record_versions[RECORD.record_id]) == 2
    assert tracked.version_id not in state.version_changes
    assert state.last_seen[RECORD.record_id] == T0 + timedelta(hours=2)
    # A later delivery still compares with the newer version, not the late one.
    tracked, _, _ = track(journal, claims, delivery(price("1.30"), fetch=3, **newer))
    assert _changes(tracked) == {PRICE: "unchanged"}


def test_numeric_source_versions_order_before_fetch_time(tmp_path: Path) -> None:
    journal, _ = linked_journal(tmp_path)
    claims = MemoryClaims()
    numbered = {"ordering": "version"}
    track(journal, claims, delivery(price("1.00"), fetch=1, version="9", **numbered))
    tracked, _, _ = track(
        journal, claims, delivery(price("2.00"), fetch=2, version="10", **numbered)
    )
    assert tracked.outcome == "current"
    tracked, _, _ = track(
        journal, claims, delivery(price("1.50"), fetch=3, version="8", **numbered)
    )
    assert tracked.outcome == "history" and claims.current()[PRICE].original_value == "2.00"
    with pytest.raises(ValueError, match="ordered by updated"):
        track(journal, claims, delivery(fetch=4, ordering="updated", source_updated_at=T0))


def test_a_retried_delivery_appends_and_writes_nothing_new(tracker) -> None:
    journal, claims, _ = tracker
    item = delivery(price("1.25"), package(None), fetch=2)
    first, rows, _ = track(journal, claims, item)
    count = len(journal.read())
    again, repeated, written = track(journal, claims, item)
    assert len(rows) == 2 and again == first and len(journal.read()) == count
    assert repeated == () and written == 0


def test_an_interrupted_version_without_its_change_set_is_finished(tracker) -> None:
    journal, claims, _ = tracker
    item = delivery(price("1.25"), fetch=2)
    with journal.locked() as locked:
        _, events = prepare(locked, item, actor="engine:fixture")
        locked.append_batch(events[:1])
    tracked, rows, _ = track(journal, claims, item)
    assert tracked.outcome == "current" and _changes(tracked)[PRICE] == "changed"
    assert [type(e.payload) for e in journal.read()][-1] is ChangeSet and len(rows) == 1


def test_a_weak_key_fragment_resolves_through_its_parent(tracker) -> None:
    journal, claims, kn_id = tracker
    item = delivery(price("0.95", "/breaks/0/price"), fetch=2, record=FRAGMENT, parent=RECORD)
    tracked, rows, _ = track(journal, claims, item)
    assert tracked.kn_id == kn_id and rows[0].record_id == FRAGMENT.record_id
    assert not any(e.payload.kind == "match_recorded" for e in journal.read())


def test_unlinked_records_and_changed_content_under_one_version_are_refused(
    tmp_path: Path,
) -> None:
    journal, _ = linked_journal(tmp_path)
    claims = MemoryClaims()
    with pytest.raises(ValueError, match="link the record"):
        track(journal, claims, delivery(price("1"), fetch=1, record=FRAGMENT))
    numbered = {"ordering": "version", "version": "3"}
    track(journal, claims, delivery(price("1"), fetch=2, **numbered))
    count = len(journal.read())
    with pytest.raises(ValueError, match="different content"):
        track(journal, claims, delivery(price("2"), fetch=3, **numbered))
    assert len(journal.read()) == count


def test_a_rerun_after_a_merge_keeps_the_claims_the_version_made(tracker) -> None:
    journal, claims, kn_id = tracker
    survivor = link(journal, RECORD.model_copy(update={"key": "OFFER-00099"}))
    merge(journal, kn_id, survivor)
    before = dict(claims.claims)
    tracked, rows, written = track(journal, claims, delivery(*FULL, fetch=1))
    assert tracked.kn_id == survivor and rows == () and written == 0
    assert claims.claims == before
    # New evidence after the merge claims about the survivor and supersedes the old claim.
    _, rows, _ = track(journal, claims, delivery(price("1.25"), fetch=2))
    assert rows[0].kn_id == survivor and rows[0].supersedes == before_key(before, PRICE)


def before_key(claims: dict[str, Claim], field: str) -> str:
    return next(key for key, item in claims.items() if item.field_id == field)


def test_tracking_the_deliveries_again_restores_identical_evidence(tmp_path: Path) -> None:
    journal, _ = linked_journal(tmp_path)
    sequence = (
        delivery(*FULL, fetch=1),
        delivery(price("1.25"), fetch=2),
        delivery(package(None), fetch=3),
        delivery(package(None), fetch=4),
        delivery(price("0.90"), fetch=0, fetched_at=T0 + timedelta(minutes=30)),
        delivery(voltage("6.0"), package("SOT-23"), fetch=5),
    )
    original = MemoryClaims()
    for item in sequence:
        track(journal, original, item)
    count = len(journal.read())
    # A rebuild drops the evidence tables; the journal keeps every version and change set.
    restored = MemoryClaims()
    for item in sequence:
        track(journal, restored, item)
    assert len(journal.read()) == count
    assert set(restored.claims) == set(original.claims)
    assert set(restored.confirmations) == set(original.confirmations)
    assert restored.current() == {
        key: value.model_copy(update={"recorded_at": restored.current()[key].recorded_at})
        for key, value in original.current().items()
    }
