"""Knowledge-time fact versions: explained changes, arrival-order independence and survivors."""

from datetime import timedelta
from itertools import permutations

import pytest

from kn.evidence.facts import CanonicalFact, SelectionOutcome
from kn.evidence.model import Claim
from kn.evidence.projection import Version, history, subjects
from kn.evidence.ranking import Context
from kn.evidence.reviews import ReviewItem
from kn.evidence.selection import Subject
from tests.evidence.selection_fixtures import (
    AGGREGATOR,
    CONTEXT,
    DISTRIBUTOR,
    MAKER,
    MAKER_TWO,
    OWNER,
    RANKS,
    T0,
    emptied,
    name,
    operator,
    policy,
    reviewed,
    stated,
)

STEP = timedelta(hours=1)
SURVIVOR = "kn:0190a5f0-0000-7000-8000-0000000000c1"
MERGED = "kn:0190a5f0-0000-7000-8000-0000000000c2"
SPLIT = "kn:0190a5f0-0000-7000-8000-0000000000c3"
CLASSES = ("organization", "model", "spacecraft", "constellation", "program", "service")
NAME = "space.object.name"
OPERATOR = "space.spacecraft.operator"


def _arrive(claims: list[Claim]) -> list[Claim]:
    """Record the claims in the given order, one step apart."""
    return [
        item.model_copy(
            update={
                "recorded_at": T0 + index * STEP,
                "evidence": item.evidence.model_copy(update={"recorded_at": T0 + index * STEP}),
            }
        )
        for index, item in enumerate(claims)
    ]


def _versions(claims: list[Claim], **changes: object) -> list[Version]:
    return history(Subject.of(claims[0]), claims, policy(**changes), CONTEXT)


def _outcomes(version: Version) -> dict[str, tuple[str, str]]:
    return {
        row.claim_key: (row.outcome, row.criterion)
        for row in version.records
        if isinstance(row, SelectionOutcome)
    }


def _canonical(fact: CanonicalFact) -> dict[str, object]:
    excluded = {"outcome", "deciding_criterion", "runner_up_criteria", "knowledge_from"}
    return fact.model_dump(exclude=excluded)


def test_the_first_eligible_claim_fills_and_a_higher_ranked_value_replaces() -> None:
    channel, maker = _arrive([stated(DISTRIBUTOR, "1300"), stated(MAKER, "1250")])
    first, second = _versions([channel, maker])
    assert first.fact.outcome == "filled" and first.fact.deciding_criterion == "first_eligible"
    assert first.fact.knowledge_to == second.fact.knowledge_from == maker.recorded_at
    assert second.fact.outcome == "replaced" and second.fact.claim_key == maker.key
    assert second.fact.deciding_criterion == "source_rank"
    assert second.fact.knowledge_to is None
    assert _outcomes(second)[maker.key] == ("replaced", "source_rank")
    assert _outcomes(second)[channel.key] == ("ignored", "source_rank")


def test_a_lower_ranked_value_leaves_no_version_and_stays_visible() -> None:
    maker, channel = _arrive([stated(MAKER, "1250"), stated(DISTRIBUTOR, "1300")])
    (only,) = _versions([maker, channel])
    assert only.fact.claim_key == maker.key and only.fact.knowledge_to is None
    ignored = next(row for row in only.records if getattr(row, "claim_key", "") == channel.key)
    assert isinstance(ignored, SelectionOutcome)
    assert (ignored.outcome, ignored.fact_version_id) == ("ignored", only.fact.key)
    assert ignored.recorded_at == only.fact.knowledge_from


def test_support_from_another_source_corroborates_in_a_new_version() -> None:
    third, maker = _arrive([stated(AGGREGATOR, "1250"), stated(MAKER, "1250")])
    first, second = _versions([third, maker])
    assert second.fact.outcome == "corroborated" and second.fact.claim_key == maker.key
    assert second.fact.verification_state == "corroborated"
    assert _outcomes(second)[third.key] == ("corroborated", "first_eligible")
    assert first.fact.verification_state == "unreviewed"


def test_a_rejection_recorded_later_does_not_rewrite_earlier_versions() -> None:
    maker, channel = _arrive([stated(MAKER, "1250"), stated(DISTRIBUTOR, "1300")])
    decided = T0 + 5 * STEP
    context = reviewed(rejected={maker.key: decided})
    first, second = history(Subject.of(maker), [maker, channel], policy(), context)
    assert first.fact.claim_key == maker.key and first.fact.knowledge_to == decided
    assert second.fact.claim_key == channel.key and second.fact.outcome == "replaced"


def test_a_field_without_eligible_claims_closes_its_version() -> None:
    maker = _arrive([stated(MAKER, "1250")])[0]
    context = reviewed(rejected={maker.key: T0 + STEP})
    (only,) = history(Subject.of(maker), [maker], policy(), context)
    assert only.fact.knowledge_to == T0 + STEP


ARRIVALS = [
    stated(MAKER, "1250", record="rev-a", valid=T0 - timedelta(days=400)),
    stated(MAKER, "1300", record="rev-b", valid=T0 - timedelta(days=30)),
    stated(DISTRIBUTOR, "1200"),
    stated(AGGREGATOR, "1300", evidence_class="secondary"),
    stated(OWNER, "1300"),
]


@pytest.mark.parametrize("rule", [{}, {"mode": "fixed"}, {"mode": "accumulate"}])
def test_every_arrival_order_gives_identical_canonical_values(rule: dict[str, str]) -> None:
    results = set()
    for order in permutations(ARRIVALS):
        final = _versions(_arrive(list(order)), **rule)[-1]
        results.add((repr(_canonical(final.fact)), final.selection.members))
    assert len(results) == 1


def test_an_empty_claim_gives_the_same_value_in_every_arrival_order() -> None:
    value = stated(MAKER, "1250")
    claims = [value, emptied(value, T0), stated(MAKER_TWO, "1250"), stated(DISTRIBUTOR, "1300")]
    finals = {
        repr(_canonical(_versions(_arrive(list(order)))[-1].fact)) for order in permutations(claims)
    }
    assert len(finals) == 1


def test_claims_about_a_merged_object_are_selected_under_its_survivor() -> None:
    redirects = {MERGED: (SURVIVOR,), SPLIT: (SURVIVOR, MERGED)}

    def resolve(kn_id: str) -> tuple[str, ...]:
        return redirects.get(kn_id, (kn_id,))

    own = stated(MAKER_TWO, "1250", kn_id=SURVIVOR)
    merged = stated(MAKER, "1250", kn_id=MERGED)
    split = stated(DISTRIBUTOR, "1300", kn_id=SPLIT)
    grouped, unattributed = subjects([own, merged, split], resolve)
    assert unattributed == [split]
    ((subject, claims),) = grouped.items()
    assert subject.kn_id == SURVIVOR and claims == [own, merged]
    final = history(subject, claims, policy(), CONTEXT)[-1]
    assert final.fact.kn_id == SURVIVOR and final.fact.verification_state == "corroborated"


def test_distinct_entity_classes_with_one_name_stay_distinct_facts() -> None:
    objects = [f"kn:0190a5f0-0000-7000-8000-0000000000d{index}" for index in range(len(CLASSES))]
    claims = [
        stated(MAKER, name("Aurora"), kn_id=kn_id, field_id=NAME, record=kind)
        for kn_id, kind in zip(objects, CLASSES, strict=True)
    ]
    grouped, _ = subjects(claims, lambda kn_id: (kn_id,))
    facts = [
        history(subject, items, policy(), CONTEXT)[-1].fact for subject, items in grouped.items()
    ]
    assert sorted(fact.kn_id for fact in facts) == sorted(objects)
    assert len({fact.fact_key for fact in facts}) == len(CLASSES)
    assert {fact.claim_key for fact in facts} == {item.key for item in claims}


def test_review_items_name_the_fact_and_keep_their_key_across_versions() -> None:
    first, second, third = _arrive(
        [stated(MAKER, "1250"), stated(MAKER_TWO, "1300"), stated(AGGREGATOR, "1100")]
    )
    versions = _versions([first, second, third])
    _, conflict = versions
    items = [row for row in conflict.records if isinstance(row, ReviewItem)]
    assert [item.fact_key for item in items] == [conflict.fact.fact_key]
    assert conflict.fact.review_item_id == items[0].key


def test_object_values_naming_a_merged_object_support_its_survivor() -> None:
    redirects = {MERGED: (SURVIVOR,), SPLIT: (SURVIVOR, MERGED)}
    context = Context(ranks=RANKS, resolve=lambda kn_id: redirects.get(kn_id, (kn_id,)))
    first = stated(MAKER, operator(MERGED), field_id=OPERATOR)
    second = stated(MAKER_TWO, operator(SURVIVOR), field_id=OPERATOR)
    unresolved = history(Subject.of(first), [first, second], policy(), CONTEXT)[-1]
    assert unresolved.fact.unresolved_reason == "conflict"
    final = history(Subject.of(first), [first, second], policy(), context)[-1]
    assert final.fact.claim_key is not None
    assert final.fact.verification_state == "corroborated"
    split = stated(MAKER_TWO, operator(SPLIT), field_id=OPERATOR)
    kept = history(Subject.of(first), [first, split], policy(), context)[-1]
    assert kept.fact.unresolved_reason == "conflict"
