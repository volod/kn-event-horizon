"""Update-policy modes: how ranked candidates become one explained fact plan.

A plan names the selected claim or the unresolved reason, the outcome and deciding criterion of
the change, the claims whose criteria explain it, and the outcome of every evaluated claim.
"""

from dataclasses import dataclass, field
from datetime import datetime

from kn.evidence.candidates import Candidate, difference, rank
from kn.evidence.policy import Criteria, UpdatePolicy
from kn.evidence.ranking import Assessed, Reviews
from kn.evidence.vocabulary import (
    Criterion,
    FactOutcome,
    FactVerification,
    Outcome,
    ReviewKind,
    UnresolvedReason,
)


@dataclass(frozen=True)
class Opened:
    """A review item the plan opens: its kind, candidate claims and stable reason code."""

    kind: ReviewKind
    candidates: tuple[str, ...]
    reason: str


@dataclass
class Plan:
    shown: Assessed
    outcome: FactOutcome
    criterion: Criterion
    claim: Assessed | None = None
    runner_up: Assessed | None = None
    unresolved: UnresolvedReason | None = None
    verification: FactVerification = "unreviewed"
    owner_override: bool = False
    members: tuple[Assessed, ...] = ()
    support: tuple[Assessed, ...] = ()
    opened: list[Opened] = field(default_factory=list)
    outcomes: dict[str, tuple[Outcome, Criterion, Criteria]] = field(default_factory=dict)

    def explain(self, items: tuple[Assessed, ...], outcome: Outcome, criterion: Criterion) -> None:
        for item in items:
            self.outcomes[item.key] = (outcome, criterion, item.criteria)


def verification_of(candidate: Candidate) -> FactVerification:
    """Independent support only; repeated claims of one source are one source."""
    if any(item.reviewed for item in candidate.claims):
        return "verified"
    return "corroborated" if len(candidate.sources) > 1 else "unreviewed"


def _selected(winner: Candidate, runner_up: Candidate | None, criterion: Criterion) -> Plan:
    best = winner.best
    if best.reviewed:
        criterion = "review_decision"
    if runner_up is not None:
        outcome: FactOutcome = "replaced"
    else:
        outcome = "corroborated" if len(winner.sources) > 1 else "filled"
    plan = Plan(
        shown=best,
        outcome=outcome,
        criterion=criterion,
        claim=best,
        runner_up=None if runner_up is None else runner_up.best,
        verification=verification_of(winner),
        members=(best,),
        support=winner.claims,
    )
    plan.explain(winner.claims[1:], "corroborated", criterion)
    plan.explain((best,), "replaced" if runner_up else "filled", criterion)
    return plan


def ranked(candidates: list[Candidate], policy: UpdatePolicy) -> Plan:
    """`priority` and `latest_observed`: the best candidate wins, or the top candidates conflict."""
    result = rank(candidates, policy)
    if result.winner is None:
        tied = result.tied
        plan = Plan(
            shown=tied[0].best,
            outcome="conflict",
            criterion="tie",
            runner_up=tied[1].best,
            unresolved="conflict",
            verification="disputed",
        )
        keys = tuple(key for candidate in tied for key in candidate.keys)
        plan.opened.append(Opened("fact_conflict", keys, "equal_rank_disagreement"))
        for candidate in tied:
            plan.explain(candidate.claims, "conflict", "tie")
        losers = [candidate for candidate in candidates if candidate not in tied]
        _ignore(plan, tied[0], losers, policy)
        return plan
    plan = _selected(result.winner, result.runner_up, result.criterion)
    _ignore(plan, result.winner, [c for c in candidates if c is not result.winner], policy)
    return plan


def _ignore(plan: Plan, leader: Candidate, losers: list[Candidate], policy: UpdatePolicy) -> None:
    for loser in losers:
        lost = difference(leader.best, loser.best, policy) or "data_time"
        plan.explain(loser.claims, "ignored", "review_decision" if leader.best.reviewed else lost)


def accumulate(candidates: list[Candidate]) -> Plan:
    """The union of eligible items; each candidate value is one member."""
    plan = _selected(candidates[0], None, "first_eligible")
    plan.outcome = "filled"
    plan.members = tuple(candidate.best for candidate in candidates)
    for candidate in candidates:
        plan.explain(candidate.claims[1:], "corroborated", "first_eligible")
        plan.explain((candidate.best,), "filled", "first_eligible")
    return plan


def fixed(candidates: list[Candidate], reviews: Reviews) -> Plan:
    """The first authoritative value holds; a different value opens review and never applies."""
    reviewed = [c for c in candidates if any(item.reviewed for item in c.claims)]
    holder = min(reviewed or candidates, key=_first)
    plan = _selected(holder, None, "first_eligible")
    decided = _settled_at(holder, reviews)
    contested: list[Candidate] = []
    for challenger in (candidate for candidate in candidates if candidate is not holder):
        if _seen(challenger, decided):
            plan.explain(challenger.claims, "ignored", "review_decision")
        else:
            contested.append(challenger)
    if contested:
        _contest(plan, contested)
    return plan


def _contest(plan: Plan, contested: list[Candidate]) -> None:
    for candidate in contested:
        plan.explain(candidate.claims, "conflict", "fixed_value")
    plan.outcome, plan.criterion, plan.verification = "conflict", "fixed_value", "disputed"
    plan.runner_up = contested[0].best
    keys = tuple(key for candidate in contested for key in candidate.keys)
    plan.opened.append(Opened("fixed_value_change", keys, "fixed_value_differs"))


def _settled_at(holder: Candidate, reviews: Reviews) -> datetime | None:
    """When a review decision chose the held value; claims recorded by then are settled."""
    times = [_decided_at(item, reviews) for item in holder.claims]
    return max((time for time in times if time is not None), default=None)


def _seen(challenger: Candidate, decided: datetime | None) -> bool:
    """A review that chose the held value settled every claim recorded before it."""
    if decided is None:
        return False
    return all(item.claim.recorded_at <= decided for item in challenger.claims)


def _first(candidate: Candidate) -> tuple[datetime, str]:
    """Earliest stated or observed time; the claim key breaks a tie without arrival order."""
    first = min(item.criteria.data_time or item.claim.observed_at for item in candidate.claims)
    return (first, candidate.best.key)


def _decided_at(item: Assessed, reviews: Reviews) -> datetime | None:
    if not item.reviewed:
        return None
    reference = item.claim.decision_ref
    if reference is not None and reference in reviews.decisions:
        return reviews.decisions[reference]
    return reviews.selected.get(item.key)
