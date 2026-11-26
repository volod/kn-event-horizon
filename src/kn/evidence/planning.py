"""Selection plans for one claim set: empty claims, high-impact facts and owner overrides.

An empty claim that outranks the current value keeps its predecessor as a candidate and opens
review, unless the policy or an accepting review decision allows clearing. Under review handling,
so does one that retracts a value the current value neither outranks nor agrees with. A rejected
empty claim restores its predecessor quietly. A high-impact value without primary evidence or
review stays unresolved, and an owner-entered value that beats a differing first-party value is
flagged.
"""

from dataclasses import dataclass, field
from typing import Literal

from kn.evidence.candidates import Candidate, agree, difference, group, outranks, rank
from kn.evidence.model import Claim
from kn.evidence.modes import Opened, Plan, accumulate, fixed, ranked
from kn.evidence.policy import UpdatePolicy
from kn.evidence.ranking import Assessed, Context, assess
from kn.evidence.vocabulary import Criterion


@dataclass
class _Empties:
    """What the empty claims of a claim set do to its current value."""

    restored: list[Assessed] = field(default_factory=list)
    held: list[tuple[Assessed, Criterion]] = field(default_factory=list)
    lost: list[tuple[Assessed, Criterion]] = field(default_factory=list)
    clearing: tuple[Assessed, Criterion] | None = None


def planned(
    visible: list[Assessed], known: dict[str, Claim], policy: UpdatePolicy, context: Context
) -> Plan | None:
    values = [item for item in visible if item.exclusion is None and not item.empty]
    if policy.mode == "accumulate":
        candidates = group(values, policy)
        return accumulate(candidates) if candidates else None
    leader = _leader(group(values, policy), policy)
    empties = _empties(visible, leader, known, policy, context)
    if empties.clearing is not None:
        return _cleared(empties.clearing, values, leader, known)
    candidates = group([*values, *empties.restored], policy)
    if not candidates:
        return None
    plan = (
        fixed(candidates, context.reviews) if policy.mode == "fixed" else ranked(candidates, policy)
    )
    for empty, criterion in empties.lost:
        plan.explain((empty,), "ignored", criterion)
    if empties.held:
        held = tuple(item for item, _ in empties.held)
        criterion = empties.held[0][1]
        plan.explain(held, "conflict", criterion)
        keys = tuple(item.key for item in held)
        plan.opened.append(Opened("empty_claim", keys, "outranking_empty_claim"))
        plan.outcome, plan.criterion, plan.verification = "conflict", criterion, "disputed"
    _high_impact(plan, policy)
    _owner_override(plan, candidates)
    return plan


type Effect = Literal["restore", "skip", "lose", "clear", "hold"]


def _empties(
    visible: list[Assessed],
    leader: Assessed | None,
    known: dict[str, Claim],
    policy: UpdatePolicy,
    context: Context,
) -> _Empties:
    result = _Empties()
    for empty in (item for item in visible if item.empty):
        retracted = _predecessor(empty, known, policy, context)
        effect, criterion = _effect(empty, leader, retracted, policy)
        if effect in {"restore", "hold"}:
            result.restored += retracted
        if effect == "hold":
            result.held.append((empty, criterion))
        elif effect == "lose":
            result.lost.append((empty, criterion))
        elif effect == "clear" and result.clearing is None:
            result.clearing = (empty, criterion)
    return result


def _effect(
    empty: Assessed, leader: Assessed | None, retracted: list[Assessed], policy: UpdatePolicy
) -> tuple[Effect, Criterion]:
    """What an empty claim does to its predecessor: restore, skip, lose, clear or hold it.

    A rejected empty claim restores its predecessor. An eligible one can change the value when it
    outranks the leader; it then clears or holds. Under review handling it also holds when the
    value it retracts still competes with the leader, so an equal-rank retraction never settles a
    conflict. A policy that allows clearing lets such a retraction take effect instead.
    """
    if empty.exclusion == "rejected":
        return "restore", "review_decision"
    if empty.exclusion is not None:
        return "skip", "first_eligible"
    beaten: Criterion | None = "first_eligible"
    if leader is not None:
        beaten = outranks(empty, leader, policy)
        if beaten is None:
            allowed = policy.empty_value_handling == "allow_clear" and not empty.reviewed
            if allowed or not _competes(retracted, leader, policy):
                return "lose", difference(leader, empty, policy) or "data_time"
            beaten = outranks(retracted[0], leader, policy) or "tie"
    if empty.reviewed:
        return "clear", "review_decision"
    effect: Effect = "clear" if policy.empty_value_handling == "allow_clear" else "hold"
    return effect, beaten or "first_eligible"


def _competes(retracted: list[Assessed], leader: Assessed, policy: UpdatePolicy) -> bool:
    """The retracted value differs from the leader's and the leader does not outrank it."""
    if not retracted:
        return False
    value = retracted[0]
    if agree(value.value, leader.value, policy.value_tolerance):
        return False
    return outranks(leader, value, policy) is None


def _leader(candidates: list[Candidate], policy: UpdatePolicy) -> Assessed | None:
    if not candidates:
        return None
    result = rank(candidates, policy)
    return (result.winner or result.tied[0]).best


def _predecessor(
    empty: Assessed, known: dict[str, Claim], policy: UpdatePolicy, context: Context
) -> list[Assessed]:
    """The value an empty claim may not clear without review stays a candidate."""
    claim = known.get(empty.claim.supersedes or "")
    if claim is None:
        return []
    items = assess([claim], policy, context)
    return [item for item in items if item.exclusion is None and not item.empty]


def _cleared(
    clearing: tuple[Assessed, Criterion],
    values: list[Assessed],
    leader: Assessed | None,
    known: dict[str, Claim],
) -> Plan | None:
    empty, criterion = clearing
    if leader is None and (empty.claim.supersedes or "") not in known:
        return None
    plan = Plan(
        shown=empty,
        outcome="replaced",
        criterion=criterion,
        runner_up=leader,
        unresolved="cleared",
        verification="verified" if empty.reviewed else "unreviewed",
    )
    plan.explain(tuple(values), "ignored", criterion)
    plan.explain((empty,), "replaced", criterion)
    return plan


def _high_impact(plan: Plan, policy: UpdatePolicy) -> None:
    """Rule 6: a high-impact value needs primary evidence or a review decision."""
    support = plan.support
    if not policy.high_impact or plan.claim is None:
        return
    if any(item.reviewed or item.claim.evidence_class == "primary" for item in support):
        return
    plan.claim, plan.unresolved, plan.members = None, "review_pending", ()
    plan.criterion, plan.verification = "evidence_class", "unreviewed"
    plan.explain(support, "ignored", "evidence_class")
    keys = tuple(item.key for item in support)
    plan.opened.append(Opened("high_impact", keys, "high_impact_without_primary_evidence"))


def _owner_override(plan: Plan, candidates: list[Candidate]) -> None:
    """An owner-entered value that beats a differing first-party value is flagged for review."""
    owner = tuple(item for item in plan.support if item.table_rank == "owner_entered")
    if plan.claim is None or not owner:
        return
    others = (c for c in candidates if plan.claim not in c.claims)
    if not any(item.criteria.source_rank == "first_party" for c in others for item in c.claims):
        return
    plan.owner_override = True
    if not any(item.reviewed for item in plan.support):
        keys = tuple(item.key for item in owner)
        plan.opened.append(Opened("owner_override", keys, "owner_value_differs_from_first_party"))
