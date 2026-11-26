"""Lineage views: complete chains, merge and split successors, partial updates and conflicts."""

from pathlib import Path
from typing import Any

import pytest

from kn.contracts.model import canonical
from kn.evidence.ranking import Audience
from kn.identity.journal import Journal
from kn.identity.lineage import lineage
from kn.identity.model import Identifier, SourceKey
from tests.identity.lineage_fixtures import (
    OPEN,
    PARTNER,
    QUALIFIED,
    RESTRICTED,
    S1,
    S2,
    SPLIT_FIRST,
    SPLIT_SECOND,
    X1,
    X2,
    Fixture,
    MemoryRows,
    S,
    append,
    build,
    mint_object,
)
from tests.identity.tracking_fixtures import PACKAGE, PRICE, RECORD, T0

OPEN_ONLY = Audience(rights=frozenset({OPEN}))


@pytest.fixture
def fixture(tmp_path: Path) -> Fixture:
    return build(tmp_path)


def view(fixture: Fixture, reference: str, **options: Any) -> dict[str, Any]:
    return lineage(fixture.journal.state(), fixture.rows, reference, **options)


def assert_complete(result: dict[str, Any]) -> None:
    """Every fact, claim and confirmation reaches its version, change set and archive record."""
    versions = {
        version["version_id"]: version
        for record in result["records"]
        for version in record["versions"]
    }
    evidence = {row["evidence_id"]: row for row in result["evidence"]}
    claims = {row["claim_key"]: row for row in result["claims"]}
    assert result["gaps"] == []
    for fact in result["facts"]:
        selected = [fact["claim_key"]] if fact["claim_key"] else []
        for key in selected + [row["claim_key"] for row in result["outcomes"]]:
            assert key in claims
    for claim in claims.values():
        version = versions[claim["source_version_id"]]
        assert version["change_set"]["change_set_id"] == claim["change_set_id"]
        archive = evidence[claim["evidence_id"]]["archive_record_id"]
        assert archive == version["archive_record_id"]
        assert claim["fetch_id"] == version["fetch_id"]
    for confirmation in result["confirmations"]:
        version = versions[confirmation["source_version_id"]]
        sightings = {item["archive_record_id"] for item in version["sightings"]}
        assert evidence[confirmation["evidence_id"]]["archive_record_id"] in sightings


@pytest.mark.parametrize("reference", [X1, X2, S, S1, S2, QUALIFIED])
def test_every_fixture_returns_the_complete_chain_to_archive_records(
    fixture: Fixture, reference: str
) -> None:
    result = view(fixture, reference)
    assert result["claims"] and result["records"]
    assert_complete(result)


def test_a_merged_id_shows_its_survivors_lineage_with_the_merge_event(fixture: Fixture) -> None:
    merged, survivor = view(fixture, X2), view(fixture, X1)
    assert merged["kn_id"] == X2 and merged["terminals"] == [X1]
    ignored = {"reference", "kn_id"}
    assert {k: v for k, v in merged.items() if k not in ignored} == {
        k: v for k, v in survivor.items() if k not in ignored
    }
    (merge,) = [item for item in merged["history"] if item["payload"]["kind"] == "merged"]
    assert merge["payload"] == {"kind": "merged", "kn_id": X2, "survivor": X1}
    assert merge["decision_ref"] == "decision:fixture-merge"
    moved = next(link for link in merged["links"] if link["kn_id"] == X2)
    assert moved["owner"] == X1 and moved["ended_event"] is None
    (match,) = merged["matches"]
    assert match["decision"] == "review" and match["record_id"] == moved["record_id"]


def test_a_partial_update_changes_and_confirms_only_the_stated_field(fixture: Fixture) -> None:
    result = view(fixture, X1, field_id=PRICE)
    record = next(item for item in result["records"] if item["record_id"] == RECORD.record_id)
    changes = [
        [change["change"] for change in version["change_set"]["changes"]]
        for version in record["versions"]
    ]
    assert changes == [["added"], ["changed"]]
    assert [len(version["sightings"]) for version in record["versions"]] == [0, 1]
    own = [row for row in result["claims"] if row["record_id"] == RECORD.record_id]
    assert [row["change_kind"] for row in own] == ["added", "changed"]
    assert own[1]["supersedes"] == own[0]["claim_key"]
    (confirmation,) = result["confirmations"]
    assert confirmation["claim_key"] == own[1]["claim_key"]
    assert {row["field_id"] for row in result["claims"]} == {PRICE}
    package = view(fixture, X1, field_id=PACKAGE)
    record = next(item for item in package["records"] if item["record_id"] == RECORD.record_id)
    assert [
        [change["change"] for change in version["change_set"]["changes"]]
        for version in record["versions"]
    ] == [["added"], ["not_stated"]]


def test_a_conflict_shows_both_claims_and_its_review_item(fixture: Fixture) -> None:
    result = view(fixture, X1, field_id=PRICE)
    (fact,) = result["facts"]
    assert fact["claim_key"] is None and fact["unresolved_reason"] == "conflict"
    (item,) = result["review_items"]
    assert item["kind"] == "fact_conflict" and item["item_id"] == fact["review_item_id"]
    current = {row["claim_key"] for row in result["outcomes"]}
    assert set(item["candidates"]) == current
    assert {row["outcome"] for row in result["outcomes"]} == {"conflict"}
    values = {row["value_number"] for row in result["claims"] if row["claim_key"] in current}
    assert values == {"1.25", "1.3"}


def test_a_split_successor_holds_only_the_records_and_claims_it_received(
    fixture: Fixture,
) -> None:
    first, whole = view(fixture, S1), view(fixture, S)
    assert [link["record_id"] for link in first["links"]] == [SPLIT_FIRST.record_id]
    assert {row["record_id"] for row in first["claims"]} == {SPLIT_FIRST.record_id}
    assert {row["kn_id"] for row in first["claims"]} == {S, S1}
    assert whole["terminals"] == sorted([S1, S2])
    assert {row["record_id"] for row in whole["claims"]} == {
        SPLIT_FIRST.record_id,
        SPLIT_SECOND.record_id,
    }
    assert {fact["kn_id"] for fact in whole["facts"]} == {S1, S2}
    (split,) = [item for item in first["history"] if item["payload"]["kind"] == "split"]
    assert split["decision_ref"] == "decision:fixture-split"


def test_restricted_evidence_is_withheld_and_counted(fixture: Fixture) -> None:
    result = view(fixture, S2, audience=OPEN_ONLY)
    assert result["claims"] == result["evidence"] == result["facts"] == []
    assert result["withheld"] == {"claims": 2, "facts": 1}
    assert result["permitted"] == [OPEN]
    text = canonical(result)
    assert RESTRICTED not in text and "2.1" not in text and "2.2" not in text
    assert_complete(result)
    internal = view(fixture, S2)
    assert {row["value_number"] for row in internal["claims"]} == {"2.1", "2.2"}
    assert internal["withheld"] == {}


def test_an_audience_sees_its_facts_and_no_identity_values_without_rights(
    fixture: Fixture,
) -> None:
    result = view(fixture, X1, audience=PARTNER)
    assert {fact["audience"] for fact in result["facts"]} == {"partner"}
    assert result["attributes"] == []
    assert [candidate["features"] for candidate in result["matches"][0]["candidates"]] == [[]]
    assert result["withheld"] == {"attributes": 1, "match_features": 1}
    assert_complete(result)


def test_a_restricted_excerpt_is_withheld_from_permitted_evidence(fixture: Fixture) -> None:
    rows = fixture.rows
    evidence = rows.tables["evidence_records"]
    key = next(
        row["evidence_id"]
        for row in rows.tables["claims"].values()
        if row["record_id"] == RECORD.record_id
    )
    evidence[key] = {**evidence[key], "excerpt": "secret", "excerpt_rights": RESTRICTED}
    state = fixture.journal.state()
    result = lineage(state, rows, X1, audience=OPEN_ONLY)
    shown = next(row for row in result["evidence"] if row["evidence_id"] == key)
    assert shown["excerpt"] is None and result["withheld"]["excerpts"] == 1
    internal = lineage(state, rows, X1)
    assert next(row for row in internal["evidence"] if row["evidence_id"] == key)["excerpt"]


def test_a_qualified_identifier_names_its_holder(fixture: Fixture) -> None:
    assert view(fixture, QUALIFIED)["kn_id"] == X1
    for reference in ("inventree:vl-itree:part:43", "unknown", "kn:not-a-uuid"):
        with pytest.raises(ValueError):
            view(fixture, reference)
    with pytest.raises(ValueError, match="unknown KN ID"):
        view(fixture, "kn:019b76da-a800-7000-8000-0000000000ff")


def test_broken_references_are_reported_as_gaps(fixture: Fixture) -> None:
    rows = fixture.rows
    claims, facts = rows.tables["claims"], rows.tables["canonical_facts"]
    selected = next(
        row for row in facts.values() if row["claim_key"] and row["audience"] == "internal"
    )
    orphan = {**claims[selected["claim_key"]], "claim_key": "f" * 64, "source_version_id": "e" * 64}
    claims[orphan["claim_key"]] = orphan
    del claims[selected["claim_key"]]
    stale = {**selected, "fact_version_id": "d" * 64, "kn_id": X2, "claim_key": None}
    stale.update(unresolved_reason="no_eligible_claim")
    facts[stale["fact_version_id"]] = stale
    state = fixture.journal.state()
    gaps = lineage(state, rows, X1)["gaps"]
    assert {(item["kind"], item["reference"]) for item in gaps} == {
        ("claim_version_missing", orphan["claim_key"]),
        ("claim_change_set_missing", orphan["claim_key"]),
        ("fact_claim_missing", selected["fact_version_id"]),
        ("fact_subject_superseded", stale["fact_version_id"]),
    }
    # The rights of a claim the view does not hold are unknown, so its fact is withheld.
    restricted = lineage(state, rows, X1, audience=OPEN_ONLY)
    assert selected["fact_version_id"] not in {
        row["fact_version_id"] for row in restricted["facts"]
    }
    assert restricted["withheld"]["facts"] == 1


def test_a_claim_without_evidence_is_a_gap_and_withheld_from_a_restricted_audience(
    fixture: Fixture,
) -> None:
    rows = fixture.rows
    claim = next(
        row for row in rows.tables["claims"].values() if row["record_id"] == RECORD.record_id
    )
    del rows.tables["evidence_records"][claim["evidence_id"]]
    state = fixture.journal.state()
    result = lineage(state, rows, X1)
    assert claim["claim_key"] in {row["claim_key"] for row in result["claims"]}
    assert {"kind": "evidence_missing", "reference": claim["evidence_id"]} in result["gaps"]
    restricted = lineage(state, rows, X1, audience=OPEN_ONLY)
    assert claim["claim_key"] not in {row["claim_key"] for row in restricted["claims"]}
    assert restricted["withheld"]["claims"] == 1


def test_a_qualified_identifier_split_two_ways_between_objects_is_ambiguous(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    for kn_id, namespace, value in ((X1, "ns", "a:b"), (X2, "ns:a", "b")):
        mint_object(journal, kn_id, SourceKey(source="fixture:anchor", key=kn_id))
        identifier = Identifier(
            kn_id=kn_id,
            namespace=namespace,
            value=value,
            issuer="fixture:issuer",
            authority="weak",
            valid_from=T0,
        )
        append(journal, identifier, T0)
    state = journal.state()
    with pytest.raises(ValueError, match="several objects"):
        lineage(state, MemoryRows(()), "ns:a:b")
