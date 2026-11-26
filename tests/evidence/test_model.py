"""Claims carry their provenance, have deterministic keys and refuse incomplete content."""

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pydantic
import pytest

from kn.evidence.records import Time
from kn.evidence.values import Missing, NumberValue
from tests.evidence.fixtures import T0, VERSION_2, changed_mass, claim, evidence, fact


def test_a_rerun_of_the_same_record_and_code_gives_the_same_keys() -> None:
    first = claim()
    later = claim(
        recorded_at=T0 + timedelta(days=3), evidence=evidence(recorded_at=T0 + timedelta(days=3))
    )
    assert later.key == first.key
    assert later.evidence.key == first.evidence.key
    assert later.row()["recorded_at"] != first.row()["recorded_at"]


@pytest.mark.parametrize(
    "change",
    [
        {"evidence": evidence(code_digest="0" * 64)},
        {"evidence": evidence(locator="/mass/0")},
        {"source_version_id": VERSION_2},
        {"conditions": {"temperature_c": 25}},
        {
            "value": NumberValue(
                number=Decimal("1250.5"), normalized_unit="kg", conversion_rule="identity"
            )
        },
    ],
    ids=["code", "locator", "version", "conditions", "value"],
)
def test_any_content_or_provenance_change_gives_a_new_claim_key(change: dict[str, Any]) -> None:
    assert claim(**change).key != claim().key


def test_claim_columns_copy_the_evidence_provenance() -> None:
    row = claim().row()
    source = evidence()
    assert (row["evidence_id"], row["fetch_id"], row["origin_uri"], row["fetched_at"]) == (
        source.key,
        source.fetch_id,
        source.origin_uri,
        source.fetched_at,
    )


@pytest.mark.parametrize("missing", ["origin_uri", "fetched_at", "fetch_id", "locator", "rights"])
def test_evidence_without_its_provenance_is_rejected(missing: str) -> None:
    data = evidence().model_dump()
    del data[missing]
    with pytest.raises(pydantic.ValidationError, match=missing):
        claim(evidence=data)


def test_a_claim_without_a_value_or_missing_reason_is_rejected() -> None:
    data = claim().model_dump()
    del data["value"]
    with pytest.raises(pydantic.ValidationError, match="value"):
        type(claim()).model_validate(data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"evidence": {"origin_uri": "https://user:secret@example.org/x"}}, "redaction"),
        ({"evidence": {"origin_uri": "not a uri"}}, "pattern"),
        ({"evidence": {"excerpt": "1250 kg"}}, "rights"),
        ({"evidence": {"recorded_at": T0 - timedelta(seconds=1)}}, "before it was fetched"),
        ({"evidence": {"fetched_at": "2026-03-01"}}, "explicit UTC offset"),
        ({"evidence": {"fetched_at": "2026-03-01T12:00:00"}}, "explicit UTC offset"),
        ({"change_kind": "emptied", "supersedes": "a" * 64}, "source_empty"),
        ({"value": Missing(reason="source_empty")}, "source_empty"),
        ({"change_kind": "changed"}, "predecessor"),
        ({"supersedes": "a" * 64}, "predecessor"),
        ({"change_kind": "decided"}, "review decision"),
        ({"source_id": "space:other"}, "one source"),
        ({"extraction_confidence": Decimal("1.5")}, "between 0 and 1"),
        ({"extraction_confidence": Decimal("0.12345")}, "never rounded"),
        ({"value": {"kind": "number", "number": "1E-19"}}, "never rounded"),
        ({"value": {"kind": "number", "number": "1E+20"}}, "integer digits"),
        ({"value": {"kind": "number", "number": "NaN"}}, "finite"),
        ({"value": {"kind": "number", "number": "1", "normalized_unit": "kg"}}, "conversion rule"),
        ({"value": {"kind": "text", "text": "x", "language": "english language"}}, "BCP-47"),
        ({"value": {"kind": "text", "text": "a\x00b", "language": "en"}}, "NUL"),
        ({"value": {"kind": "date", "date": "2026-1"}}, "pattern"),
        ({"kn_id": "kn:not-a-uuid"}, "UUID"),
        ({"valid_to": Time(at=T0.replace(year=2024), precision="day")}, "half-open"),
    ],
)
def test_inconsistent_claims_are_rejected(changes: dict[str, Any], message: str) -> None:
    if "evidence" in changes:
        changes = {**changes, "evidence": {**evidence().model_dump(), **changes["evidence"]}}
    with pytest.raises((pydantic.ValidationError, ValueError), match=message):
        claim(**changes)


def test_values_keep_exact_text_decimal_and_reason() -> None:
    original = claim(original_value="  1 250,00 kg ")
    assert original.row()["original_value"] == "  1 250,00 kg "
    assert claim().row()["value_number"] == Decimal("1250.000000000000000000")
    stated = claim(value=Missing(reason="not_disclosed"))
    row = stated.row()
    assert row["missing_reason"] == "not_disclosed"
    assert all(row[name] is None for name in ("value_number", "normalized_unit", "conversion_rule"))


def test_an_emptied_field_is_a_source_empty_claim_that_supersedes_its_value() -> None:
    previous = claim()
    emptied = claim(
        source_version_id=VERSION_2,
        change_kind="emptied",
        supersedes=previous.key,
        value=Missing(reason="source_empty"),
        original_value="",
    )
    assert emptied.row()["missing_reason"] == "source_empty"
    assert emptied.row()["supersedes"] == previous.key


def test_a_fact_selects_a_claim_or_states_why_not() -> None:
    selected = claim()
    assert fact(selected).row()["claim_key"] == selected.key
    with pytest.raises(pydantic.ValidationError, match="states why"):
        fact(selected, unresolved_reason="conflict", review_item_id="b" * 64)
    with pytest.raises(pydantic.ValidationError, match="review item"):
        fact(selected, claim_key=None, unresolved_reason="conflict")
    with pytest.raises(pydantic.ValidationError, match="half-open"):
        fact(selected, knowledge_to=selected.recorded_at)
    unresolved = fact(selected, claim_key=None, unresolved_reason="no_eligible_claim")
    assert unresolved.row()["claim_key"] is None


def test_a_fact_key_ignores_locale_and_version_while_the_version_id_does_not() -> None:
    selected = claim()
    first = fact(selected)
    second = fact(changed_mass(selected), outcome="replaced", deciding_criterion="data_time")
    assert first.fact_key == second.fact_key
    assert first.key != second.key
    closed = fact(selected, knowledge_to=second.knowledge_from)
    assert closed.key == first.key
