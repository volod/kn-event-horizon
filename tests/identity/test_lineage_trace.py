"""A late version and an omitted field, traced from claims through the selected fact to archives."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytest

from kn.evidence.ranking import Audience
from kn.evidence.records import Record
from kn.identity.journal import Journal
from kn.identity.lineage import lineage
from kn.identity.model import Assignment, SourceKey, Split
from tests.identity.lineage_fixtures import S1, S2, MemoryRows, append, facts, mint_object
from tests.identity.test_lineage import assert_complete
from tests.identity.tracking_fixtures import (
    FRAGMENT,
    PACKAGE,
    PRICE,
    RECORD,
    T0,
    MemoryClaims,
    delivery,
    linked_journal,
    package,
    price,
    track,
)


@dataclass(frozen=True)
class Tracked:
    journal: Journal
    kn_id: str
    claims: MemoryClaims
    rows: tuple[Record, ...]
    outcomes: tuple[str, ...]


@pytest.fixture
def late(tmp_path: Path) -> Tracked:
    """Version 3 omits the package, version 2 arrives late, and version 3 is seen again."""
    journal, kn_id = linked_journal(tmp_path)
    claims = MemoryClaims()
    tracked = [
        track(journal, claims, item)
        for item in (
            delivery(price("1.20"), package("SOT-23"), fetch=1, ordering="version", version="1"),
            delivery(price("1.30"), fetch=2, ordering="version", version="3"),
            delivery(price("1.25"), package("SOT-89"), fetch=3, ordering="version", version="2"),
            delivery(price("1.30"), fetch=4, ordering="version", version="3"),
        )
    ]
    rows = tuple(row for _, written, _ in tracked for row in written)
    return Tracked(journal, kn_id, claims, rows, tuple(item.outcome for item, _, _ in tracked))


def _versions(journal: Journal) -> dict[str, str]:
    state = journal.state()
    return {state.versions[key].version: key for key in state.record_versions[RECORD.record_id]}


def test_a_late_version_and_an_omitted_field_keep_the_current_claims(late: Tracked) -> None:
    assert late.outcomes == ("current", "current", "history", "seen")
    current = late.claims.current()
    versions = _versions(late.journal)
    assert {field: claim.source_version_id for field, claim in current.items()} == {
        PRICE: versions["3"],
        PACKAGE: versions["1"],
    }
    assert versions["2"] not in {claim.source_version_id for claim in late.claims.claims.values()}


def test_the_selected_facts_trace_to_their_archives_and_keep_the_late_version(
    late: Tracked,
) -> None:
    rows = MemoryRows((*late.rows, *facts(late.journal, late.claims)))
    result = lineage(late.journal.state(), rows, late.kn_id)
    assert_complete(result)
    current = late.claims.current()
    internal = [fact for fact in result["facts"] if fact["audience"] == "internal"]
    assert {fact["field_id"]: fact["claim_key"] for fact in internal} == {
        field: claim.key for field, claim in current.items()
    }
    (record,) = (item for item in result["records"] if item["record_id"] == RECORD.record_id)
    versions = {item["version"]: item for item in record["versions"]}
    assert versions["2"]["change_set"] is None
    assert versions["2"]["archive_record_id"] == "warc:3"
    assert [item["archive_record_id"] for item in versions["3"]["sightings"]] == ["warc:4"]
    assert [row["claim_key"] for row in result["confirmations"]] == [current[PRICE].key]
    assert record["last_seen"] == "2026-04-01T12:00:00Z"


def test_a_fragment_claim_that_no_split_successor_holds_is_a_gap(tmp_path: Path) -> None:
    """A weak-key fragment has no link of its own, so a split cannot assign its claims."""
    journal, kn_id = linked_journal(tmp_path)
    claims = MemoryClaims()
    rows = [
        *track(journal, claims, delivery(price("1.00"), fetch=1))[1],
        *track(journal, claims, delivery(price("0.90"), fetch=2, record=FRAGMENT, parent=RECORD))[
            1
        ],
    ]
    for successor in (S1, S2):
        mint_object(journal, successor, SourceKey(source="fixture:split", key=successor))
    owned = journal.state().owned(kn_id)
    assignments = tuple(Assignment(item_id=key, successor=S1) for key in owned)
    split = Split(kn_id=kn_id, successors=(S1, S2), assignments=assignments)
    append(journal, split, T0 + timedelta(hours=5), "decision:fixture-split")
    (fragment,) = (row for row in rows if getattr(row, "record_id", None) == FRAGMENT.record_id)
    state = journal.state()
    for successor in (S1, S2):
        result = lineage(state, MemoryRows(rows), successor)
        assert FRAGMENT.record_id not in {row["record_id"] for row in result["claims"]}
        assert {"kind": "claim_successor_missing", "reference": fragment.key} in result["gaps"]
    restricted = lineage(state, MemoryRows(rows), S1, audience=Audience(rights=frozenset()))
    assert restricted["gaps"] == []
