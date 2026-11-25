"""Canonical fact versions and selection outcomes: the shapes the selector writes.

Selection itself comes later. These shapes fix the fact key, knowledge-time versions and the
explanation of every change, so the selector adds no other state layout.
"""

from typing import Any, ClassVar, Self

from pydantic import Field, JsonValue, model_validator

from kn.contracts.model import canonical
from kn.evidence.policy import Criteria
from kn.evidence.records import Record, Time, json_object, time_columns, validity
from kn.evidence.vocabulary import (
    Criterion,
    FactOutcome,
    FactVerification,
    Mode,
    Outcome,
    UnresolvedReason,
)
from kn.identity.model import KnId
from kn.review.model import Digest, Instant, Text, digest


def fact_key(kn_id: str, field_id: str, conditions: dict[str, JsonValue], audience: str) -> str:
    """One canonical fact per object, field, condition set and audience; never per locale."""
    return digest([kn_id, field_id, json_object(conditions), audience])


class CanonicalFact(Record):
    """One knowledge-time version of a field's selected value or its unresolved reason."""

    TABLE: ClassVar[str] = "canonical_facts"
    KEY: ClassVar[str] = "fact_version_id"
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset()
    MUTABLE: ClassVar[frozenset[str]] = frozenset({"knowledge_to"})

    kn_id: KnId
    field_id: Text
    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    audience: Text
    claim_key: Digest | None = None
    unresolved_reason: UnresolvedReason | None = None
    mode: Mode
    policy_digest: Digest
    outcome: FactOutcome
    deciding_criterion: Criterion
    winner_criteria: Criteria
    runner_up_criteria: Criteria | None = None
    verification_state: FactVerification
    owner_override: bool = False
    review_item_id: Digest | None = None
    valid_from: Time | None = None
    valid_to: Time | None = None
    knowledge_from: Instant
    knowledge_to: Instant | None = None

    @model_validator(mode="after")
    def _explained(self) -> Self:
        if (self.claim_key is None) == (self.unresolved_reason is None):
            raise ValueError("a fact selects a claim or states why it cannot")
        if self.owner_override and self.claim_key is None:
            raise ValueError("an owner override flags a selected claim")
        needs_review = self.outcome == "conflict" or self.unresolved_reason in {
            "conflict",
            "review_pending",
        }
        if needs_review and self.review_item_id is None:
            raise ValueError("a conflict or pending review names its review item")
        if self.knowledge_to is not None and self.knowledge_to <= self.knowledge_from:
            raise ValueError("knowledge intervals are half-open and nonempty")
        validity(self.valid_from, self.valid_to)
        return self

    @property
    def fact_key(self) -> str:
        return fact_key(self.kn_id, self.field_id, self.conditions, self.audience)

    def columns(self) -> dict[str, Any]:
        runner_up = self.runner_up_criteria
        return {
            "fact_key": self.fact_key,
            "kn_id": self.kn_id,
            "field_id": self.field_id,
            "conditions_json": json_object(self.conditions),
            "audience": self.audience,
            "claim_key": self.claim_key,
            "unresolved_reason": self.unresolved_reason,
            "mode": self.mode,
            "policy_digest": self.policy_digest,
            "outcome": self.outcome,
            "deciding_criterion": self.deciding_criterion,
            "winner_criteria_json": _json(self.winner_criteria),
            "runner_up_criteria_json": None if runner_up is None else _json(runner_up),
            "verification_state": self.verification_state,
            "owner_override": self.owner_override,
            "review_item_id": self.review_item_id,
            **time_columns("valid_from", self.valid_from),
            **time_columns("valid_to", self.valid_to),
            "knowledge_from": self.knowledge_from,
            "knowledge_to": self.knowledge_to,
        }


class SelectionOutcome(Record):
    """Why one evaluated claim filled, replaced, was ignored by, supported or contested a fact."""

    TABLE: ClassVar[str] = "selection_outcomes"
    KEY: ClassVar[str] = "outcome_id"

    fact_key: Digest
    claim_key: Digest
    fact_version_id: Digest
    outcome: Outcome
    criterion: Criterion
    criteria: Criteria
    recorded_at: Instant

    def columns(self) -> dict[str, Any]:
        data = self.model_dump(exclude={"criteria"})
        return {**data, "criteria_json": _json(self.criteria)}


def _json(criteria: Criteria) -> str:
    return canonical(criteria.model_dump(mode="json"))
