"""Candidate values: claims that agree within tolerance, ranked so repetition never adds rank.

Every order here is total over claim content and ends in the claim key, so the input order of
claims never changes a result. A candidate ranks by its best supporting claim.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from kn.evidence.policy import EVIDENCE_ORDER, RANK_ORDER, UpdatePolicy
from kn.evidence.ranking import Assessed
from kn.evidence.values import NumberValue, Value
from kn.evidence.vocabulary import Criterion

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
type Strength = tuple[int, ...]


def agree(first: Value, second: Value, tolerance: Decimal) -> bool:
    """Values support one candidate: equal, or numbers in one unit within the tolerance."""
    if isinstance(first, NumberValue) and isinstance(second, NumberValue):
        same_unit = first.normalized_unit == second.normalized_unit
        return same_unit and abs(first.number - second.number) <= tolerance
    return first == second


@dataclass(frozen=True)
class Candidate:
    claims: tuple[Assessed, ...]

    @property
    def best(self) -> Assessed:
        return self.claims[0]

    @property
    def sources(self) -> frozenset[str]:
        return frozenset(item.claim.source_id for item in self.claims)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.claims)


@dataclass(frozen=True)
class Ranked:
    """The winner and runner-up, or the candidates that tie on every criterion."""

    winner: Candidate | None
    runner_up: Candidate | None
    tied: tuple[Candidate, ...]
    criterion: Criterion


def _named(policy: UpdatePolicy) -> tuple[Criterion, ...]:
    return tuple(name for name in policy.priority_criteria if name != "data_time")


def strength(item: Assessed, policy: UpdatePolicy) -> Strength:
    """Source rank and evidence class in the declared order; lower is stronger."""
    criteria = item.criteria
    position = {
        "source_rank": RANK_ORDER.index(criteria.source_rank),
        "evidence_class": EVIDENCE_ORDER.index(criteria.evidence_class),
    }
    return tuple(position[name] for name in _named(policy))


def newest(time: datetime | None) -> tuple[bool, timedelta]:
    """Newer first; an unknown time sorts last."""
    return (time is None, timedelta(0) if time is None else EPOCH - time)


def order(item: Assessed, policy: UpdatePolicy) -> tuple[object, ...]:
    recency = newest(item.criteria.data_time)
    if policy.mode == "latest_observed":
        return (recency, strength(item, policy), item.key)
    return (strength(item, policy), recency, item.key)


def group(items: Iterable[Assessed], policy: UpdatePolicy) -> list[Candidate]:
    """Candidates in rank order; each claim joins the strongest candidate it agrees with."""
    members: list[list[Assessed]] = []
    for item in sorted(items, key=lambda each: order(each, policy)):
        target = next(
            (
                claims
                for claims in members
                if agree(claims[0].value, item.value, policy.value_tolerance)
            ),
            None,
        )
        if target is None:
            members.append([item])
        else:
            target.append(item)
    return [Candidate(tuple(claims)) for claims in members]


def difference(first: Assessed, second: Assessed, policy: UpdatePolicy) -> Criterion | None:
    """The first criterion on which the claims differ, in the mode's comparison order."""
    named = _named(policy)
    strengths = zip(strength(first, policy), strength(second, policy), strict=True)
    ranked = next((name for name, (a, b) in zip(named, strengths, strict=True) if a != b), None)
    timed = first.criteria.data_time != second.criteria.data_time
    if policy.mode == "latest_observed":
        return "data_time" if timed else ranked
    return ranked


def outranks(item: Assessed, other: Assessed, policy: UpdatePolicy) -> Criterion | None:
    """The criterion on which the claim beats the other claim, or None when it does not."""
    own, theirs = strength(item, policy), strength(other, policy)
    mine, its = item.criteria.data_time, other.criteria.data_time
    if policy.mode == "latest_observed":
        if mine is not None and (its is None or mine > its):
            return "data_time"
        return difference(item, other, policy) if mine == its and own < theirs else None
    if own != theirs:
        return difference(item, other, policy) if own < theirs else None
    same_source = item.criteria.source_id == other.criteria.source_id
    if not same_source or "data_time" not in policy.priority_criteria:
        return None
    return "data_time" if mine is not None and its is not None and mine > its else None


def rank(candidates: list[Candidate], policy: UpdatePolicy) -> Ranked:
    if not candidates:
        raise ValueError("rank needs at least one candidate")
    if policy.mode == "latest_observed":
        first_latest = _latest(candidates[0], policy)
        top = [c for c in candidates if _latest(c, policy) == first_latest]
    else:
        first = strength(candidates[0].best, policy)
        top = [c for c in candidates if strength(c.best, policy) == first]
    if len(top) == 1:
        return _decided(candidates, policy)
    if policy.mode == "priority" and "data_time" in policy.priority_criteria:
        timed = _same_source_newest(top, policy)
        if timed is not None:
            rest = [*timed[1:], *(c for c in candidates if c not in timed)]
            return Ranked(timed[0], rest[0], (), "data_time")
    return Ranked(None, None, tuple(top), "tie")


def _latest(candidate: Candidate, policy: UpdatePolicy) -> tuple[object, ...]:
    best = candidate.best
    return (newest(best.criteria.data_time), strength(best, policy))


def _decided(candidates: list[Candidate], policy: UpdatePolicy) -> Ranked:
    winner = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    if runner_up is None:
        return Ranked(winner, None, (), "first_eligible")
    criterion = difference(winner.best, runner_up.best, policy) or "data_time"
    return Ranked(winner, runner_up, (), criterion)


def _same_source_newest(top: list[Candidate], policy: UpdatePolicy) -> list[Candidate] | None:
    """Tied candidates ordered newest first, when one source states all of them."""
    level = strength(top[0].best, policy)
    leading = [[item for item in c.claims if strength(item, policy) == level] for c in top]
    sources = {item.claim.source_id for claims in leading for item in claims}
    times = [claims[0].criteria.data_time for claims in leading]
    if len(sources) != 1 or None in times:
        return None
    ordered = sorted(zip(times, top, strict=True), key=lambda pair: newest(pair[0]))
    if ordered[0][0] == ordered[1][0]:
        return None
    return [candidate for _, candidate in ordered]
