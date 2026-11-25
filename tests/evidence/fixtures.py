"""Deterministic evidence rows shared by the unit and database suites."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from kn.evidence.facts import CanonicalFact, SelectionOutcome
from kn.evidence.model import Alias, Claim, Confirmation, Evidence
from kn.evidence.policy import Criteria
from kn.evidence.records import Record, Time
from kn.evidence.relations import RelationAssertion, RelationSupport
from kn.evidence.reviews import ReviewDecision, ReviewItem
from kn.evidence.text import Translation
from kn.evidence.values import ConceptValue, Missing, NumberValue, TextValue
from kn.review.model import digest

T0 = datetime(2026, 3, 1, 12, tzinfo=UTC)
SPACECRAFT = "kn:0190a5f0-0000-7000-8000-000000000001"
OPERATOR = "kn:0190a5f0-0000-7000-8000-000000000002"
RECORD = digest(["space:fixture", "SAT-1"])
VERSION_1 = digest(["version", 1])
VERSION_2 = digest(["version", 2])
MASS = "space.spacecraft.mass"
NAME = "space.spacecraft.name"
ORBIT = "space.spacecraft.orbit_regime"
CODE = digest("parser-v1")
CONTRACT = digest("contract-v1")


def evidence(**changes: Any) -> Evidence:
    data: dict[str, Any] = {
        "source_id": "space:fixture",
        "fetch_id": "fetch-1",
        "archive_record_id": "warc:1",
        "origin_uri": "https://example.org/sat-1.json",
        "fetched_at": T0,
        "locator_kind": "json_pointer",
        "locator": "/mass",
        "rights": "license:fixture-open",
        "code_digest": CODE,
        "contract_digest": CONTRACT,
        "recorded_at": T0 + timedelta(minutes=1),
    }
    return Evidence.model_validate({**data, **changes})


def claim(**changes: Any) -> Claim:
    data: dict[str, Any] = {
        "kn_id": SPACECRAFT,
        "field_id": MASS,
        "source_id": "space:fixture",
        "record_id": RECORD,
        "source_version_id": VERSION_1,
        "change_kind": "added",
        "evidence": evidence(),
        "original_value": "1250 kg",
        "original_unit": "kg",
        "value": NumberValue(
            number=Decimal("1250"), normalized_unit="kg", conversion_rule="identity"
        ),
        "assertion_type": "declared",
        "evidence_class": "primary",
        "valid_from": Time(at=datetime(2025, 1, 1, tzinfo=UTC), precision="year"),
        "observed_at": T0,
        "recorded_at": T0 + timedelta(minutes=1),
    }
    return Claim.model_validate({**data, **changes})


def changed_mass(previous: Claim, number: str = "1300", **changes: Any) -> Claim:
    """The next version of the same record changes the value."""
    later = T0 + timedelta(days=30)
    return claim(
        source_version_id=VERSION_2,
        change_kind="changed",
        supersedes=previous.key,
        evidence=evidence(fetch_id="fetch-2", fetched_at=later, recorded_at=later),
        original_value=f"{number} kg",
        value=NumberValue(number=Decimal(number), normalized_unit="kg", conversion_rule="identity"),
        valid_from=Time(at=datetime(2026, 2, 1, tzinfo=UTC), precision="month"),
        observed_at=later,
        recorded_at=later,
        **changes,
    )


def name_claim() -> Claim:
    return claim(
        field_id=NAME,
        evidence=evidence(locator="/name"),
        original_value="\u536b\u661f\u4e00\u53f7",
        original_unit=None,
        value=TextValue(text="\u536b\u661f\u4e00\u53f7", language="zh"),
        valid_from=None,
    )


def orbit_claim(concept: str = "space.demo.002") -> Claim:
    return claim(
        field_id=ORBIT,
        evidence=evidence(locator="/orbit"),
        original_value="LEO",
        original_unit=None,
        value=ConceptValue(concept=concept),
        assertion_type="reported",
        evidence_class="secondary",
    )


def undisclosed_claim() -> Claim:
    return claim(
        field_id="space.spacecraft.power",
        evidence=evidence(locator="/power"),
        original_value="",
        original_unit=None,
        value=Missing(reason="not_disclosed"),
        valid_from=None,
    )


def one_of_each() -> list[Record]:
    """At least one row of every evidence table, all consistent with each other."""
    mass = claim()
    name = name_claim()
    later = T0 + timedelta(days=1)
    item = ReviewItem(
        kind="fact_conflict",
        kn_id=SPACECRAFT,
        field_id=MASS,
        fact_key=fact(mass).fact_key,
        candidates=(mass.key,),
        reason_code="equal_rank_disagreement",
        opened_by="selection:fixture",
        opened_at=later,
    )
    current = fact(mass, review_item_id=item.key)
    relation = RelationAssertion(
        subject_kn_id=OPERATOR,
        relation_type="space.operates",
        object_kn_id=SPACECRAFT,
        opened_by=mass.key,
        opened_at=later,
    )
    return [
        mass,
        name,
        Confirmation(
            claim_key=mass.key,
            source_version_id=VERSION_2,
            evidence=evidence(fetch_id="fetch-3", fetched_at=later, recorded_at=later),
            observed_at=later,
            recorded_at=later,
        ),
        Alias(
            kn_id=SPACECRAFT,
            alias="Sat One",
            language="en",
            normalized_key="sat one",
            normalizer="casefold",
            claim_key=name.key,
            recorded_at=later,
        ),
        Translation(
            claim_key=name.key,
            language="en",
            text="Satellite One",
            method="human",
            provenance="review:fixture-translation",
            recorded_at=later,
        ),
        relation,
        RelationSupport(assertion_id=relation.key, claim_key=mass.key, recorded_at=later),
        item,
        current,
        SelectionOutcome(
            fact_key=current.fact_key,
            claim_key=mass.key,
            fact_version_id=current.key,
            outcome="filled",
            criterion="first_eligible",
            criteria=criteria(mass),
            recorded_at=later,
        ),
        ReviewDecision(
            item_id=item.key,
            outcome="select",
            selected_claim_key=mass.key,
            reviewer="person:fixture-reviewer",
            reason="Manufacturer datasheet",
            performed_at=later,
            recorded_at=later + timedelta(minutes=5),
        ),
    ]


def criteria(selected: Claim) -> Criteria:
    return Criteria(
        source_id=selected.source_id,
        source_rank="first_party",
        evidence_class=selected.evidence_class,
        data_time=selected.valid_from.at if selected.valid_from else None,
    )


def fact(selected: Claim, **changes: Any) -> CanonicalFact:
    data: dict[str, Any] = {
        "kn_id": selected.kn_id,
        "field_id": selected.field_id,
        "audience": "internal",
        "claim_key": selected.key,
        "mode": "priority",
        "policy_digest": digest("policy:priority-default"),
        "outcome": "filled",
        "deciding_criterion": "first_eligible",
        "winner_criteria": criteria(selected),
        "verification_state": "unreviewed",
        "valid_from": selected.valid_from,
        "knowledge_from": selected.recorded_at,
    }
    return CanonicalFact.model_validate({**data, **changes})
