"""Priority selection ranks candidate values by their best claim and explains each claim."""

from datetime import timedelta
from typing import Any

import pytest

from kn.evidence.ranking import Audience, Context
from tests.evidence.selection_fixtures import (
    AGGREGATOR,
    AGGREGATOR_TWO,
    CONTEXT,
    DISTRIBUTOR,
    MAKER,
    MAKER_TWO,
    OWNER,
    PRICE,
    RANKS,
    SIGNAL,
    T0,
    UNLISTED,
    choose,
    operator,
    outcome_of,
    policy,
    reviewed,
    stated,
)

LATER = T0 + timedelta(days=1)


def test_a_value_a_higher_ranked_source_also_supports_wins() -> None:
    third = stated(AGGREGATOR, "1250", evidence_class="secondary")
    maker = stated(MAKER, "1250")
    channel = stated(DISTRIBUTOR, "1300")
    selection = choose([channel, third, maker])
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == maker.key and fact.deciding_criterion == "source_rank"
    assert fact.winner_criteria.source_rank == "first_party"
    assert fact.runner_up_criteria is not None
    assert fact.runner_up_criteria.source_rank == "authorized_channel"
    assert fact.verification_state == "corroborated"
    assert outcome_of(selection, third) == ("corroborated", "source_rank")
    assert outcome_of(selection, channel) == ("ignored", "source_rank")


def test_repeated_claims_from_one_source_add_no_rank_and_no_corroboration() -> None:
    repeats = [stated(AGGREGATOR, "1300", record=str(n)) for n in range(3)]
    channel = stated(DISTRIBUTOR, "1250")
    selection = choose([*repeats, channel])
    assert selection is not None and selection.fact.claim_key == channel.key
    alone = choose(repeats)
    assert alone is not None and alone.fact.verification_state == "unreviewed"


def test_an_owner_value_outranks_the_maker_and_is_flagged_for_review() -> None:
    owner = stated(OWNER, "1200")
    maker = stated(MAKER, "1250")
    selection = choose([maker, owner])
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == owner.key and fact.owner_override
    assert [item.kind for item in selection.items] == ["owner_override"]
    assert selection.items[0].candidates == (owner.key,)
    assert fact.review_item_id == selection.items[0].key
    agreeing = choose([stated(OWNER, "1250"), maker])
    assert agreeing is not None and not agreeing.fact.owner_override


def test_an_accepted_owner_override_is_still_flagged_but_needs_no_review() -> None:
    owner = stated(OWNER, "1200")
    context = reviewed(selected={owner.key: LATER})
    selection = choose([owner, stated(MAKER, "1250")], context=context)
    assert selection is not None
    assert selection.fact.owner_override and selection.items == ()
    assert selection.fact.verification_state == "verified"


def test_equal_rank_and_evidence_from_two_sources_conflict() -> None:
    first, second = stated(MAKER, "1250"), stated(MAKER_TWO, "1300")
    selection = choose([second, first])
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key is None and fact.unresolved_reason == "conflict"
    assert fact.outcome == "conflict" and fact.deciding_criterion == "tie"
    assert fact.verification_state == "disputed"
    (item,) = selection.items
    assert item.kind == "fact_conflict" and set(item.candidates) == {first.key, second.key}
    assert outcome_of(selection, first) == outcome_of(selection, second) == ("conflict", "tie")


def test_evidence_class_decides_between_equal_ranks() -> None:
    primary = stated(MAKER, "1250")
    secondary = stated(MAKER_TWO, "1300", evidence_class="secondary")
    selection = choose([secondary, primary])
    assert selection is not None
    assert selection.fact.claim_key == primary.key
    assert selection.fact.deciding_criterion == "evidence_class"


def test_a_newer_datasheet_revision_from_the_same_source_replaces_the_older() -> None:
    old = stated(MAKER, "1250", record="rev-a", valid=T0 - timedelta(days=400))
    new = stated(MAKER, "1300", record="rev-b", valid=T0 - timedelta(days=30))
    selection = choose([new, old])
    assert selection is not None
    assert selection.fact.claim_key == new.key
    assert selection.fact.deciding_criterion == "data_time"
    assert outcome_of(selection, old) == ("ignored", "data_time")
    undated = stated(MAKER, "1300", record="rev-b")
    assert choose([old, undated]).fact.unresolved_reason == "conflict"  # type: ignore[union-attr]


def test_a_different_source_never_wins_by_being_newer() -> None:
    old = stated(MAKER, "1250", valid=T0 - timedelta(days=400))
    new = stated(MAKER_TWO, "1300", valid=T0 - timedelta(days=30))
    selection = choose([old, new])
    assert selection is not None and selection.fact.unresolved_reason == "conflict"


def test_a_contradictory_ownership_claim_stays_conflicted() -> None:
    rule = policy(highImpact=True)
    first = stated(MAKER, operator("kn:0190a5f0-0000-7000-8000-0000000000b1"))
    second = stated(MAKER_TWO, operator("kn:0190a5f0-0000-7000-8000-0000000000b2"))
    selection = choose([first, second], rule)
    assert selection is not None
    assert selection.fact.unresolved_reason == "conflict"
    assert {each.claim_key for each in selection.explained} == {first.key, second.key}


def test_a_high_impact_value_needs_primary_evidence_or_review() -> None:
    rule = policy(highImpact=True)
    secondary = stated(MAKER, "1250", evidence_class="secondary")
    pending = choose([secondary], rule)
    assert pending is not None
    assert pending.fact.claim_key is None and pending.fact.unresolved_reason == "review_pending"
    assert [item.kind for item in pending.items] == ["high_impact"]
    assert outcome_of(pending, secondary) == ("ignored", "evidence_class")
    accepted = choose([secondary], rule, reviewed(selected={secondary.key: LATER}))
    assert accepted is not None and accepted.fact.claim_key == secondary.key
    assert accepted.fact.verification_state == "verified"
    primary = choose([stated(MAKER_TWO, "1250")], rule)
    assert primary is not None and primary.fact.claim_key is not None


def test_a_review_decision_ranks_as_owner_entered_and_verifies_only_its_claim() -> None:
    first, second = stated(MAKER, "1250"), stated(MAKER_TWO, "1300")
    context = reviewed(selected={second.key: LATER})
    selection = choose([first, second], context=context)
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == second.key and fact.deciding_criterion == "review_decision"
    assert fact.winner_criteria.source_rank == "owner_entered"
    assert fact.verification_state == "verified" and not fact.owner_override
    other = choose([first, second], context=reviewed(selected={"0" * 64: LATER}))
    assert other is not None and other.fact.unresolved_reason == "conflict"


def test_source_labels_and_unaccepted_decisions_never_verify_or_rank() -> None:
    labeled = stated(AGGREGATOR, "1250", source_verification_label="verified")
    selection = choose([labeled])
    assert selection is not None and selection.fact.verification_state == "unreviewed"
    decided = stated(AGGREGATOR_TWO, "1300", change_kind="decided", decision_ref="review:d1")
    unaccepted = choose([labeled, decided])
    assert unaccepted is not None and unaccepted.fact.claim_key == labeled.key
    assert outcome_of(unaccepted, decided) == ("ignored", "review_decision")
    accepted = choose([labeled, decided], context=reviewed(decisions={"review:d1": LATER}))
    assert accepted is not None and accepted.fact.claim_key == decided.key
    assert accepted.fact.verification_state == "verified"


def test_rejected_claims_are_never_eligible() -> None:
    maker, channel = stated(MAKER, "1250"), stated(DISTRIBUTOR, "1300")
    selection = choose([maker, channel], context=reviewed(rejected={maker.key: LATER}))
    assert selection is not None and selection.fact.claim_key == channel.key
    assert outcome_of(selection, maker) == ("ignored", "review_decision")


def test_signals_never_fill_canonical_fields() -> None:
    signal = stated(SIGNAL, "1250")
    assert choose([signal]) is None
    selection = choose([signal, stated(UNLISTED, "1300")])
    assert selection is not None and selection.fact.winner_criteria.source_id == UNLISTED
    assert outcome_of(selection, signal) == ("ignored", "source_rank")


@pytest.mark.parametrize(
    ("changes", "rule", "criterion"),
    [
        (
            {"evidence_class": "extracted_candidate"},
            {"minimumEvidenceClass": "extracted_candidate"},
            "evidence_class",
        ),
        ({"evidence_class": "derived"}, {"minimumEvidenceClass": "secondary"}, "evidence_class"),
        ({}, {"minimumSourceRank": "authorized_channel"}, "source_rank"),
    ],
)
def test_claims_below_the_field_minimums_are_ignored(
    changes: dict[str, Any], rule: dict[str, Any], criterion: str
) -> None:
    weak = stated(AGGREGATOR, "1300", **changes)
    strong = stated(MAKER, "1250")
    selection = choose([weak, strong], policy(**rule))
    assert selection is not None and selection.fact.claim_key == strong.key
    assert outcome_of(selection, weak) == ("ignored", criterion)
    assert choose([weak], policy(**rule)) is None


def test_selection_is_audience_specific_and_hides_restricted_evidence() -> None:
    licensed = stated(MAKER, "1250", rights="license:vendor-terms")
    public = stated(DISTRIBUTOR, "1300")
    audience = Audience(name="public", rights=frozenset({"license:fixture-open"}))
    selection = choose([licensed, public], context=Context(ranks=RANKS, audience=audience))
    assert selection is not None
    assert selection.fact.claim_key == public.key and selection.fact.audience == "public"
    assert {each.claim_key for each in selection.explained} == {public.key}
    internal = choose([licensed, public])
    assert internal is not None and internal.fact.claim_key == licensed.key
    assert internal.fact.fact_key != selection.fact.fact_key


def test_field_groups_rank_one_source_differently_per_field() -> None:
    assert RANKS.rank(DISTRIBUTOR, PRICE) == "first_party"
    assert RANKS.rank(DISTRIBUTOR, "microelectronics.part.mass") == "authorized_channel"
    assert RANKS.rank(DISTRIBUTOR, "microelectronics.offering") == "authorized_channel"
    assert RANKS.rank(UNLISTED, PRICE) == "unranked"
    assert CONTEXT.ranks is RANKS
