"""Candidate values: agreement within tolerance, pairwise agreement and reviewed representatives."""

from datetime import timedelta
from itertools import permutations

from tests.evidence.selection_fixtures import (
    MAKER,
    MAKER_THREE,
    MAKER_TWO,
    OWNER,
    T0,
    choose,
    policy,
    reviewed,
    stated,
)

LATER = T0 + timedelta(days=1)


def test_values_within_tolerance_support_one_candidate() -> None:
    first, second = stated(MAKER, "1250"), stated(MAKER_TWO, "1250.4")
    selection = choose([first, second], policy(valueTolerance=0.5))
    assert selection is not None and selection.fact.verification_state == "corroborated"
    assert choose([first, second]).fact.unresolved_reason == "conflict"  # type: ignore[union-attr]


def test_equal_rank_values_beyond_tolerance_conflict_whatever_their_dates() -> None:
    # 10.8 agrees with both neighbours, but 10 and 11.6 differ by more than the tolerance.
    values = {MAKER: "10", MAKER_TWO: "10.8", MAKER_THREE: "11.6"}
    for days in permutations(range(len(values))):
        claims = [
            stated(source, number, valid=T0 - timedelta(days=10 - day))
            for (source, number), day in zip(values.items(), days, strict=True)
        ]
        selection = choose(claims, policy(valueTolerance=1))
        assert selection is not None and selection.fact.unresolved_reason == "conflict"
        (item,) = selection.items
        assert set(item.candidates) == {claim.key for claim in claims}


def test_a_reviewed_claim_represents_the_value_it_verifies() -> None:
    accepted, owner = stated(MAKER_TWO, "1300", record="r3"), stated(OWNER, "1300")
    context = reviewed(selected={accepted.key: LATER})
    selection = choose([owner, accepted], context=context)
    assert selection is not None and selection.fact.claim_key == accepted.key
    assert selection.fact.deciding_criterion == "review_decision"
    assert selection.fact.verification_state == "verified"
    # When evidence class ranks first, the owner's primary claim represents the value instead;
    # the review accepted another claim version, so the fact is not verified.
    secondary = stated(MAKER_TWO, "1300", record="r4", evidence_class="secondary")
    rule = policy(priorityCriteria=["evidence_class", "source_rank", "data_time"])
    context = reviewed(selected={secondary.key: LATER})
    other = choose([owner, secondary], rule, context)
    assert other is not None and other.fact.claim_key == owner.key
    assert other.fact.verification_state == "corroborated"
