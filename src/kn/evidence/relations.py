"""Typed relations between objects, supported by claims, with no active duplicates."""

from typing import Any, ClassVar, Self

from pydantic import Field, JsonValue, model_validator

from kn.evidence.records import Record, Time, json_object, time_columns, validity
from kn.evidence.vocabulary import CloseReason, RelationReviewState
from kn.identity.model import KnId
from kn.review.model import Digest, Instant, Text, digest
from kn.review.targets import content_version


class RelationAssertion(Record):
    TABLE: ClassVar[str] = "relation_assertions"
    KEY: ClassVar[str] = "assertion_id"
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset({"opened_at"})
    MUTABLE: ClassVar[frozenset[str]] = frozenset(
        {"review_state", "decision_ref", "closed_at", "close_reason"}
    )

    subject_kn_id: KnId
    relation_type: Text
    object_kn_id: KnId
    qualifiers: dict[str, JsonValue] = Field(default_factory=dict)
    valid_from: Time | None = None
    valid_to: Time | None = None
    review_state: RelationReviewState = "unreviewed"
    decision_ref: Text | None = None
    opened_by: Digest
    opened_at: Instant
    closed_at: Instant | None = None
    close_reason: CloseReason | None = None

    @model_validator(mode="after")
    def _interval(self) -> Self:
        if (self.closed_at is None) != (self.close_reason is None):
            raise ValueError("a closed assertion states when and why it closed")
        if self.closed_at is not None and self.closed_at <= self.opened_at:
            raise ValueError("an assertion closes after it opened")
        validity(self.valid_from, self.valid_to)
        return self

    @property
    def relation_key(self) -> str:
        """Two active assertions with this key would be duplicates."""
        return content_version(
            {
                "subject_kn_id": self.subject_kn_id,
                "relation_type": self.relation_type,
                "object_kn_id": self.object_kn_id,
                "qualifiers_json": json_object(self.qualifiers),
                **time_columns("valid_from", self.valid_from),
                **time_columns("valid_to", self.valid_to),
            }
        )

    @property
    def key(self) -> str:
        return digest([self.relation_key, self.opened_by])

    def columns(self) -> dict[str, Any]:
        return {
            "relation_key": self.relation_key,
            "subject_kn_id": self.subject_kn_id,
            "relation_type": self.relation_type,
            "object_kn_id": self.object_kn_id,
            "qualifiers_json": json_object(self.qualifiers),
            **time_columns("valid_from", self.valid_from),
            **time_columns("valid_to", self.valid_to),
            "review_state": self.review_state,
            "decision_ref": self.decision_ref,
            "opened_by": self.opened_by,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "close_reason": self.close_reason,
        }


class RelationSupport(Record):
    """A claim supporting an assertion; the pair is the composite primary key."""

    TABLE: ClassVar[str] = "relation_supports"
    KEY: ClassVar[str] = "assertion_id"

    assertion_id: Digest
    claim_key: Digest
    recorded_at: Instant

    def columns(self) -> dict[str, Any]:
        return self.model_dump()

    def row(self) -> dict[str, Any]:
        return self.columns()
