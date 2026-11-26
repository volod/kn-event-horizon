"""Claim ranks and eligibility: the inputs canonical selection compares.

A claim takes the rank of its source from the reviewed rank table. A field-group override applies
to the group's stable field IDs; the longest matching group wins over a source-wide override, and
an unlisted source is `unranked`. Claims a review decision accepted rank as `owner_entered`.
Signals and AI candidates are never eligible, whatever the field's minimums say.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import Field

from kn.evidence.model import Claim
from kn.evidence.policy import EVIDENCE_ORDER, RANK_ORDER, Criteria, UpdatePolicy
from kn.evidence.values import Missing, ObjectValue, Value
from kn.evidence.vocabulary import Criterion
from kn.review.model import Frozen, Instant, Text
from kn.sources.ranks import Override, Policy, Rank
from kn.sources.seeds import RESOURCES
from kn.sources.validation import read_model

RANK_TABLE = RESOURCES / "source-ranks.yaml"
# Discovery-signal domains: media records never fill canonical fields (integrity rule 8).
SIGNAL_DOMAINS = frozenset({"gdelt"})
NEVER_ELIGIBLE_CLASS = "extracted_candidate"
FIELD_SEPARATOR = "."
SOURCE_SEPARATOR = ":"
type Exclusion = Literal[
    "rights",
    "signal",
    "extracted_candidate",
    "rejected",
    "unaccepted_decision",
    "below_minimum_rank",
    "below_minimum_evidence_class",
    "missing_value",
]
# The criterion an ignored claim's outcome names; restricted claims are not shown at all.
EXCLUSION_CRITERIA: dict[Exclusion, Criterion] = {
    "rights": "first_eligible",
    "signal": "source_rank",
    "extracted_candidate": "evidence_class",
    "rejected": "review_decision",
    "unaccepted_decision": "review_decision",
    "below_minimum_rank": "source_rank",
    "below_minimum_evidence_class": "evidence_class",
    "missing_value": "first_eligible",
}


@dataclass(frozen=True)
class RankTable:
    overrides: tuple[Override, ...] = ()

    @classmethod
    def read(cls, path: Path = RANK_TABLE) -> Self:
        return cls(tuple(read_model(path, Policy).overrides))

    def rank(self, source_id: str, field_id: str) -> Rank:
        """The rank class of a source for one stable field ID."""
        best: tuple[int, Rank] | None = None
        for item in self.overrides:
            if item.source_id != source_id:
                continue
            group = item.field_group
            if group is None:
                matched = 0
            elif field_id == group or field_id.startswith(group + FIELD_SEPARATOR):
                matched = len(group)
            else:
                continue
            if best is None or matched > best[0]:
                best = (matched, item.rank)
        return "unranked" if best is None else best[1]


def is_signal(source_id: str) -> bool:
    return source_id.partition(SOURCE_SEPARATOR)[0] in SIGNAL_DOMAINS


DEFAULT_AUDIENCE = "internal"


class Audience(Frozen):
    """Whose selection this is; `rights` None permits every rights statement."""

    name: Text = DEFAULT_AUDIENCE
    rights: frozenset[Text] | None = None

    def permits(self, rights: str) -> bool:
        return self.rights is None or rights in self.rights


class ReviewSnapshot(Frozen):
    at: Instant
    selected: dict[Text, Instant]
    rejected: dict[Text, Instant]
    decisions: dict[Text, Instant]


class Reviews(Frozen):
    """Accepted review outcomes by claim key, each with the time KN recorded the decision."""

    snapshots: tuple[ReviewSnapshot, ...] = ()
    selected: dict[Text, Instant] = Field(default_factory=dict)
    rejected: dict[Text, Instant] = Field(default_factory=dict)
    decisions: dict[Text, Instant] = Field(default_factory=dict)

    def at(self, instant: datetime) -> Self:
        """Only decisions recorded by the instant; a later decision never rewrites history."""

        if self.snapshots:
            visible = [state for state in self.snapshots if state.at <= instant]
            if not visible:
                return type(self)()
            state = visible[-1]
            return type(self)(
                selected=state.selected, rejected=state.rejected, decisions=state.decisions
            )

        def known(values: dict[str, datetime]) -> dict[str, datetime]:
            return {key: time for key, time in values.items() if time <= instant}

        return type(self)(
            selected=known(self.selected),
            rejected=known(self.rejected),
            decisions=known(self.decisions),
        )

    def times(self) -> set[datetime]:
        return {state.at for state in self.snapshots} | {
            *self.selected.values(),
            *self.rejected.values(),
            *self.decisions.values(),
        }


type Resolve = Callable[[str], tuple[str, ...]]


@dataclass(frozen=True)
class Context:
    """Ranks, audience and reviews; `resolve` maps a KN ID to its terminal successors."""

    ranks: RankTable = field(default_factory=RankTable)
    audience: Audience = field(default_factory=Audience)
    reviews: Reviews = field(default_factory=Reviews)
    resolve: Resolve | None = None


@dataclass(frozen=True)
class Assessed:
    """One claim with its effective criteria and, when ineligible, why."""

    claim: Claim
    value: Value
    criteria: Criteria
    table_rank: Rank
    reviewed: bool
    exclusion: Exclusion | None

    @property
    def key(self) -> str:
        return self.claim.key

    @property
    def empty(self) -> bool:
        value = self.claim.value
        return isinstance(value, Missing) and value.reason == "source_empty"


def data_time(claim: Claim, policy: UpdatePolicy) -> datetime | None:
    if policy.time_basis == "observed":
        return claim.observed_at
    stated = claim.valid_from if policy.time_basis == "valid_from" else claim.published
    return None if stated is None else stated.at


def assess(claims: Iterable[Claim], policy: UpdatePolicy, context: Context) -> list[Assessed]:
    return [_assess(claim, policy, context) for claim in claims]


def _assess(claim: Claim, policy: UpdatePolicy, context: Context) -> Assessed:
    reviews = context.reviews
    decided = claim.decision_ref is not None and claim.decision_ref in reviews.decisions
    reviewed = decided or claim.key in reviews.selected
    table_rank = context.ranks.rank(claim.source_id, claim.field_id)
    rank: Rank = "owner_entered" if reviewed else table_rank
    criteria = Criteria(
        source_id=claim.source_id,
        source_rank=rank,
        evidence_class=claim.evidence_class,
        data_time=data_time(claim, policy),
    )
    exclusion = _exclusion(claim, criteria, policy, context)
    value = _survivor(claim.value, context.resolve)
    return Assessed(claim, value, criteria, table_rank, reviewed, exclusion)


def _survivor(value: Value, resolve: Resolve | None) -> Value:
    """An object value names its merge survivor; a split object keeps the stated ID."""
    if resolve is None or not isinstance(value, ObjectValue):
        return value
    targets = resolve(value.kn_id)
    return ObjectValue(kn_id=targets[0]) if len(targets) == 1 else value


def _exclusion(
    claim: Claim, criteria: Criteria, policy: UpdatePolicy, context: Context
) -> Exclusion | None:
    rank = RANK_ORDER.index(criteria.source_rank)
    evidence = EVIDENCE_ORDER.index(claim.evidence_class)
    checks: tuple[tuple[bool, Exclusion], ...] = (
        (not context.audience.permits(claim.evidence.rights), "rights"),
        (is_signal(claim.source_id), "signal"),
        (claim.evidence_class == NEVER_ELIGIBLE_CLASS, "extracted_candidate"),
        (claim.key in context.reviews.rejected, "rejected"),
        (
            claim.change_kind == "decided" and claim.decision_ref not in context.reviews.decisions,
            "unaccepted_decision",
        ),
        (rank > RANK_ORDER.index(policy.minimum_source_rank), "below_minimum_rank"),
        (
            evidence > EVIDENCE_ORDER.index(policy.minimum_evidence_class),
            "below_minimum_evidence_class",
        ),
        (
            isinstance(claim.value, Missing) and claim.value.reason != "source_empty",
            "missing_value",
        ),
    )
    return next((reason for failed, reason in checks if failed), None)
