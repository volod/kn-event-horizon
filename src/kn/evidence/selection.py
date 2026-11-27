"""Canonical fact selection: each field's value through its update policy.

`select` evaluates every claim recorded for one object, field and condition set together, with
total orders over claim content, so arrival order never decides the value. Superseded claims are
history, also when a claim of another subject supersedes them; an empty claim that outranks the
current value, or retracts a value that still competes with it, restores its predecessor and opens
review unless the policy allows clearing. `previous` is the version the result changes, which
explains the change as filled, replaced or corroborated; ignored and conflicting claims are
explained individually.
"""

import json
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Self

from kn.evidence.candidates import agree
from kn.evidence.facts import CanonicalFact, SelectionOutcome, fact_key
from kn.evidence.model import Claim
from kn.evidence.modes import Plan
from kn.evidence.planning import planned
from kn.evidence.policy import Criteria, UpdatePolicy
from kn.evidence.ranking import EXCLUSION_CRITERIA, Assessed, Context, assess
from kn.evidence.records import Record, json_object
from kn.evidence.reviews import ReviewItem
from kn.evidence.vocabulary import Criterion, FactOutcome, Outcome

SELECTOR = "selection:canonical-v1"
# The fact names the most urgent open item; every opened item is still written.
REVIEW_PRECEDENCE = ("fact_conflict", "fixed_value_change", "empty_claim", "high_impact")
CHANGE_OUTCOMES: frozenset[Outcome] = frozenset({"filled", "replaced"})


@dataclass(frozen=True)
class Subject:
    """One canonical fact per object, field and condition set; KN IDs are resolved survivors."""

    kn_id: str
    field_id: str
    conditions_json: str = "{}"

    @classmethod
    def of(cls, claim: Claim, kn_id: str | None = None) -> Self:
        return cls(kn_id or claim.kn_id, claim.field_id, json_object(claim.conditions))


@dataclass(frozen=True)
class Explained:
    claim_key: str
    outcome: Outcome
    criterion: Criterion
    criteria: Criteria


@dataclass(frozen=True)
class Selection:
    fact: CanonicalFact
    items: tuple[ReviewItem, ...]
    explained: tuple[Explained, ...]
    chosen: tuple[Assessed, ...]
    held: Assessed | None

    @property
    def members(self) -> tuple[str, ...]:
        """Selected claim keys: every item under `accumulate`, else the selected claim."""
        return tuple(item.key for item in self.chosen)

    @property
    def value_claim(self) -> Claim | None:
        """The selected claim, or the value a pending review holds back."""
        return None if self.held is None else self.held.claim

    @property
    def state(self) -> tuple[object, ...]:
        """What makes a new version; an ignored claim or a new runner-up does not."""
        changes = {"outcome", "deciding_criterion", "runner_up_criteria_json"}
        columns = self.fact.columns()
        kept = sorted((k, str(v)) for k, v in columns.items() if not k.startswith("knowledge"))
        return (
            tuple(item for item in kept if item[0] not in changes),
            tuple(item.key for item in self.items),
            self.members,
        )

    def outcomes(
        self, version: CanonicalFact, claims: Collection[str] | None = None
    ) -> tuple[SelectionOutcome, ...]:
        return tuple(
            SelectionOutcome(
                fact_key=version.fact_key,
                claim_key=item.claim_key,
                fact_version_id=version.key,
                outcome=item.outcome,
                criterion=item.criterion,
                criteria=item.criteria,
                recorded_at=version.knowledge_from,
            )
            for item in self.explained
            if claims is None or item.claim_key in claims
        )

    def records(self) -> tuple[Record, ...]:
        return (*self.items, self.fact, *self.outcomes(self.fact))


def select(
    subject: Subject,
    claims: Iterable[Claim],
    policy: UpdatePolicy,
    context: Context,
    knowledge_from: datetime,
    previous: Selection | None = None,
    retired: Collection[str] = (),
) -> Selection | None:
    """The fact version the claims give from `knowledge_from`; None when none is eligible.

    Pass every claim KN had recorded by then for the subject, including superseded ones, and in
    `retired` the keys of those that a claim of another subject superseded by then.
    """
    known = _known(subject, claims)
    superseded = {claim.supersedes for claim in known.values() if claim.supersedes}
    superseded.update(retired)
    current = [known[key] for key in sorted(known) if key not in superseded]
    visible = [item for item in assess(current, policy, context) if item.exclusion != "rights"]
    plan = planned(visible, known, policy, context)
    if plan is None:
        return None
    for item in visible:
        if item.exclusion is not None:
            plan.explain((item,), "ignored", EXCLUSION_CRITERIA[item.exclusion])
    return _build(subject, plan, policy, context, knowledge_from, previous)


def _known(subject: Subject, claims: Iterable[Claim]) -> dict[str, Claim]:
    """Claims by key; an emptied claim states no value, so its condition set may differ."""
    known: dict[str, Claim] = {}
    for claim in claims:
        conditions = json_object(claim.conditions)
        stated = claim.change_kind == "emptied" or conditions == subject.conditions_json
        if claim.field_id != subject.field_id or not stated:
            raise ValueError("select claims of one field and condition set")
        known[claim.key] = claim
    return known


def _build(
    subject: Subject,
    plan: Plan,
    policy: UpdatePolicy,
    context: Context,
    knowledge_from: datetime,
    previous: Selection | None,
) -> Selection:
    conditions = json.loads(subject.conditions_json)
    audience = context.audience.name
    key = fact_key(subject.kn_id, subject.field_id, conditions, audience)
    items = tuple(
        ReviewItem(
            kind=opened.kind,
            kn_id=subject.kn_id,
            field_id=subject.field_id,
            fact_key=key,
            candidates=opened.candidates,
            reason_code=opened.reason,
            opened_by=SELECTOR,
            opened_at=knowledge_from,
        )
        for opened in plan.opened
    )
    ranked_items = sorted(items, key=lambda item: _precedence(item.kind))
    held = plan.claim or (plan.support[0] if plan.support else None)
    outcome = _change(plan, held, previous, policy)
    claim = None if plan.claim is None else plan.claim.claim
    fact = CanonicalFact(
        kn_id=subject.kn_id,
        field_id=subject.field_id,
        conditions=conditions,
        audience=audience,
        claim_key=None if claim is None else claim.key,
        unresolved_reason=plan.unresolved,
        mode=policy.mode,
        policy_digest=policy.digest,
        outcome=outcome,
        deciding_criterion=plan.criterion,
        winner_criteria=plan.shown.criteria,
        runner_up_criteria=None if plan.runner_up is None else plan.runner_up.criteria,
        verification_state=plan.verification,
        owner_override=plan.owner_override,
        review_item_id=ranked_items[0].key if ranked_items else None,
        valid_from=None if claim is None else claim.valid_from,
        valid_to=None if claim is None else claim.valid_to,
        knowledge_from=knowledge_from,
    )
    explained = tuple(
        Explained(claim_key, _claim_change(result, outcome, policy), criterion, criteria)
        for claim_key, (result, criterion, criteria) in sorted(plan.outcomes.items())
    )
    return Selection(fact, items, explained, plan.members, held)


def _precedence(kind: str) -> int:
    return REVIEW_PRECEDENCE.index(kind) if kind in REVIEW_PRECEDENCE else len(REVIEW_PRECEDENCE)


def _change(
    plan: Plan, held: Assessed | None, previous: Selection | None, policy: UpdatePolicy
) -> FactOutcome:
    """The change against the previous version: filled, replaced, corroborated or conflict."""
    if plan.outcome == "conflict":
        return "conflict"
    if plan.unresolved == "cleared":
        return "replaced"
    if policy.mode == "accumulate":
        before = () if previous is None else previous.chosen
        return _set_change(plan.members, before, policy)
    prior = None if previous is None or previous.fact.claim_key is None else previous.held
    if prior is None or held is None:
        return "filled"
    same = agree(prior.value, held.value, policy.value_tolerance)
    return "corroborated" if same else "replaced"


def _set_change(
    members: tuple[Assessed, ...], before: tuple[Assessed, ...], policy: UpdatePolicy
) -> FactOutcome:
    """A new item fills the set; an item that leaves it replaces the set."""

    def missing(items: tuple[Assessed, ...], among: tuple[Assessed, ...]) -> bool:
        tolerance = policy.value_tolerance
        return any(not any(agree(a.value, b.value, tolerance) for b in among) for a in items)

    if missing(members, before):
        return "filled"
    return "replaced" if missing(before, members) else "corroborated"


def _claim_change(result: Outcome, fact: FactOutcome, policy: UpdatePolicy) -> Outcome:
    """The selected claim's outcome is the fact's change; other claims keep their own.

    Under `accumulate` every member keeps `filled`: each item is its own selected value.
    """
    if policy.mode == "accumulate" or result not in CHANGE_OUTCOMES or fact == "conflict":
        return result
    return fact
