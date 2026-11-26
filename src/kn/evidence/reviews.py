"""Review items and append-only review decisions, the shapes the review queue writes."""

from typing import Any, ClassVar, Literal, Self

from pydantic import Field, model_validator

from kn.contracts.model import canonical
from kn.evidence.records import Record
from kn.evidence.vocabulary import FACT_REVIEW_KINDS, ReviewKind, ReviewOutcome
from kn.identity.model import KnId
from kn.review.model import Digest, Instant, Text, digest


class ReviewItem(Record):
    TABLE: ClassVar[str] = "review_items"
    KEY: ClassVar[str] = "item_id"
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset({"opened_by", "opened_at"})

    kind: ReviewKind
    kn_id: KnId | None = None
    field_id: Text | None = None
    fact_key: Digest | None = None
    candidates: tuple[Text, ...] = Field(min_length=1)
    reason_code: Text
    opened_by: Text
    opened_at: Instant

    @model_validator(mode="after")
    def _subject(self) -> Self:
        if len(set(self.candidates)) != len(self.candidates):
            raise ValueError("review candidates are unique")
        object.__setattr__(self, "candidates", tuple(sorted(self.candidates)))
        if self.kind in FACT_REVIEW_KINDS and None in (self.kn_id, self.field_id, self.fact_key):
            raise ValueError("a fact review item names its object, field and fact")
        return self

    def columns(self) -> dict[str, Any]:
        data = self.model_dump(exclude={"candidates"})
        return {**data, "candidates_json": canonical(list(self.candidates))}


class ReviewDecision(Record):
    """An append-only decision event; the trusted queue writer establishes the reviewer."""

    TABLE: ClassVar[str] = "review_decisions"
    KEY: ClassVar[str] = "decision_id"
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset()

    schema_version: Literal[1] = 1
    item_id: Digest
    outcome: ReviewOutcome
    selected_claim_key: Digest | None = None
    predecessor: Digest | None = None
    reviewer: Text
    reason: Text
    performed_at: Instant
    recorded_at: Instant
    human_verification_decision_id: Digest | None = None

    @model_validator(mode="after")
    def _event(self) -> Self:
        if (self.outcome == "select") != (self.selected_claim_key is not None):
            raise ValueError("a select decision, and only it, names the selected claim")
        if self.performed_at > self.recorded_at:
            raise ValueError("a decision cannot be performed after it was recorded")
        return self

    @property
    def key(self) -> str:
        return digest(self.model_dump(mode="json"))

    def columns(self) -> dict[str, Any]:
        data = self.model_dump(exclude={"schema_version"})
        return {**data, "event_json": canonical(self.model_dump(mode="json"))}
