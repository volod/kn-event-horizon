"""Latest-observed, fixed and accumulate modes, and empty claims that never fill or clear."""

from datetime import timedelta

from kn.evidence.projection import stale
from kn.evidence.values import Missing
from tests.evidence.selection_fixtures import (
    AGGREGATOR,
    DISTRIBUTOR,
    MAKER,
    MAKER_TWO,
    PRICE,
    T0,
    choose,
    emptied,
    name,
    outcome_of,
    policy,
    reviewed,
    stated,
)

DAY = timedelta(days=1)
PRICES = policy(
    mode="latest_observed",
    timeBasis="observed",
    minimumSourceRank="authorized_channel",
    freshnessSeconds=86400,
)
FIXED = policy(mode="fixed")
ITEMS = policy(mode="accumulate")


def test_a_newer_price_wins_and_an_old_winner_shows_stale() -> None:
    old = stated(DISTRIBUTOR, "1.00", record="a", field_id=PRICE, fetched_at=T0 - 3 * DAY)
    new = stated(MAKER, "1.10", record="b", field_id=PRICE, fetched_at=T0 - 2 * DAY)
    selection = choose([new, old], PRICES)
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == new.key and fact.deciding_criterion == "data_time"
    assert outcome_of(selection, old) == ("ignored", "data_time")
    assert stale(fact, PRICES, T0 - 2 * DAY + timedelta(hours=1)) is None
    assert stale(fact, PRICES, T0) == 2 * DAY
    assert stale(fact, policy(), T0) is None


def test_latest_observed_skips_claims_below_its_minimum_rank() -> None:
    old = stated(DISTRIBUTOR, "1.00", record="a", field_id=PRICE, fetched_at=T0 - 3 * DAY)
    newer = stated(AGGREGATOR, "0.90", record="b", field_id=PRICE, fetched_at=T0 - DAY)
    selection = choose([old, newer], PRICES)
    assert selection is not None and selection.fact.claim_key == old.key
    assert outcome_of(selection, newer) == ("ignored", "source_rank")


def test_latest_observed_ranks_equal_times_by_rank_then_conflicts() -> None:
    # The distributor issues its own prices: a field-group override ranks it first party.
    channel = stated(DISTRIBUTOR, "1.00", record="a", field_id=PRICE)
    maker = stated(MAKER, "1.10", record="b", field_id=PRICE, evidence_class="secondary")
    selection = choose([maker, channel], PRICES)
    assert selection is not None
    assert selection.fact.claim_key == channel.key
    assert selection.fact.deciding_criterion == "evidence_class"
    other = stated(MAKER_TWO, "1.20", record="c", field_id=PRICE)
    tied = choose([channel, other], PRICES)
    assert tied is not None and tied.fact.unresolved_reason == "conflict"


def test_a_different_value_on_a_fixed_field_opens_review_and_never_applies() -> None:
    first = stated(AGGREGATOR, name("Acme"), fetched_at=T0 - 3 * DAY)
    later = stated(MAKER, name("Acme Corp"), fetched_at=T0 - DAY)
    selection = choose([later, first], FIXED)
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == first.key and fact.outcome == "conflict"
    assert fact.deciding_criterion == "fixed_value" and fact.verification_state == "disputed"
    (item,) = selection.items
    assert item.kind == "fixed_value_change" and item.candidates == (later.key,)
    assert outcome_of(selection, later) == ("conflict", "fixed_value")
    agreeing = choose([first, stated(MAKER, name("Acme"), fetched_at=T0 - DAY)], FIXED)
    assert agreeing is not None and agreeing.items == ()
    assert agreeing.fact.verification_state == "corroborated"


def test_a_fixed_field_review_settles_the_claims_it_saw() -> None:
    first = stated(AGGREGATOR, name("Acme"), fetched_at=T0 - 3 * DAY)
    later = stated(MAKER, name("Acme Corp"), fetched_at=T0 - DAY)
    decided = T0 + DAY
    chosen = choose([first, later], FIXED, reviewed(selected={later.key: decided}))
    assert chosen is not None
    assert chosen.fact.claim_key == later.key and chosen.items == ()
    assert outcome_of(chosen, first) == ("ignored", "review_decision")
    kept = choose([first, later], FIXED, reviewed(rejected={later.key: decided}))
    assert kept is not None and kept.fact.claim_key == first.key and kept.items == ()
    newcomer = stated(MAKER_TWO, name("ACME Inc"), at=decided + DAY)
    reopened = choose([first, later, newcomer], FIXED, reviewed(selected={later.key: decided}))
    assert reopened is not None and reopened.fact.claim_key == later.key
    assert [item.candidates for item in reopened.items] == [(newcomer.key,)]


def test_an_outranking_empty_claim_opens_review_and_does_not_clear() -> None:
    value = stated(MAKER, "1250")
    empty = emptied(value, T0 + DAY)
    channel = stated(DISTRIBUTOR, "1300")
    selection = choose([value, empty, channel])
    assert selection is not None
    fact = selection.fact
    assert fact.claim_key == value.key and fact.outcome == "conflict"
    assert fact.verification_state == "disputed"
    (item,) = selection.items
    assert item.kind == "empty_claim" and item.candidates == (empty.key,)
    assert fact.review_item_id == item.key
    assert outcome_of(selection, empty)[0] == "conflict"


def test_an_empty_claim_clears_only_when_the_policy_or_a_review_allows_it() -> None:
    value = stated(MAKER, "1250")
    empty = emptied(value, T0 + DAY)
    cleared = choose([value, empty], policy(emptyValueHandling="allow_clear"))
    assert cleared is not None
    assert cleared.fact.claim_key is None and cleared.fact.unresolved_reason == "cleared"
    assert outcome_of(cleared, empty) == ("replaced", "first_eligible")
    accepted = choose([value, empty], context=reviewed(selected={empty.key: T0 + 2 * DAY}))
    assert accepted is not None and accepted.fact.unresolved_reason == "cleared"
    assert accepted.fact.verification_state == "verified"
    rejected = choose([value, empty], context=reviewed(rejected={empty.key: T0 + 2 * DAY}))
    assert rejected is not None and rejected.fact.claim_key == value.key
    assert rejected.items == ()


def test_an_empty_claim_never_fills_and_a_lower_ranked_one_is_ignored() -> None:
    value = stated(AGGREGATOR, "1250")
    alone = emptied(value, T0 + DAY)
    assert choose([alone]) is None
    maker = stated(MAKER, "1300")
    selection = choose([value, alone, maker])
    assert selection is not None and selection.fact.claim_key == maker.key
    assert selection.items == ()
    assert outcome_of(selection, alone) == ("ignored", "source_rank")
    undisclosed = stated(MAKER_TWO, Missing(reason="not_disclosed"))
    assert choose([undisclosed]) is None


def test_accumulate_keeps_the_union_of_supported_items() -> None:
    first = stated(MAKER, name("ACM-1"), record="a")
    second = stated(DISTRIBUTOR, name("ACM-1-T"), record="b")
    again = stated(AGGREGATOR, name("ACM-1"), record="c")
    selection = choose([first, second, again], ITEMS)
    assert selection is not None
    assert set(selection.members) == {first.key, second.key}
    assert outcome_of(selection, again) == ("corroborated", "first_eligible")
    removed = emptied(second, T0 + DAY)
    left = choose([first, second, removed, again], ITEMS)
    assert left is not None and left.members == (first.key,)
    rejected = choose([first, second], ITEMS, reviewed(rejected={second.key: T0 + DAY}))
    assert rejected is not None and rejected.members == (first.key,)
