"""Hash-chained v1 events, including provenance and lifecycle decision references."""

from typing import Literal, Self

from pydantic import Field, model_validator

from kn.identity.model import Payload
from kn.review.model import Digest, Frozen, Instant, Text, digest


class Event(Frozen):
    schema_version: Literal[1] = 1
    sequence: int = Field(ge=1, strict=True)
    previous: Digest | None
    event_id: Digest
    occurred_at: Instant
    actor: Text
    reason: Text
    evidence: Text
    decision_ref: Text | None = None
    payload: Payload

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if self.event_id != digest(self.model_dump(mode="json", exclude={"event_id"})):
            raise ValueError("identity event digest mismatch")
        if (
            self.payload.kind in {"merged", "split", "restored", "reclassified"}
            and not self.decision_ref
        ):
            raise ValueError("lifecycle transition requires a decision reference")
        if (
            self.payload.kind == "linked"
            and self.payload.method == "review_decision"
            and not self.decision_ref
        ):
            raise ValueError("review link requires a decision reference")
        return self


def event(
    payload: Payload,
    *,
    previous: Event | None,
    occurred_at: Instant,
    actor: str,
    reason: str,
    evidence: str,
    decision_ref: str | None = None,
) -> Event:
    values: dict[str, object] = {
        "schema_version": 1,
        "sequence": previous.sequence + 1 if previous else 1,
        "previous": previous.event_id if previous else None,
        "occurred_at": occurred_at,
        "actor": actor,
        "reason": reason,
        "evidence": evidence,
        "decision_ref": decision_ref,
        "payload": payload,
    }
    # Validate timestamps and payload before hashing their normalized JSON representation.
    from kn.contracts.model import canonical
    from kn.review.model import utc

    values["occurred_at"] = utc(occurred_at).isoformat().replace("+00:00", "Z")
    values["payload"] = payload.model_dump(mode="json")
    values["event_id"] = digest(values)
    return Event.model_validate_json(canonical(values))
