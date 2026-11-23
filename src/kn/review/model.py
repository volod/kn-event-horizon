"""Versioned, immutable wire contracts; imported text never supplies trusted authority."""

import hashlib
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from kn.contracts.model import LogicalType, canonical
from kn.contracts.sqlalchemy import INTEGER_MAX, INTEGER_MIN

Text = Annotated[StrictStr, StringConstraints(min_length=1, pattern=r"\S")]
Digest = Annotated[StrictStr, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Purpose = Literal["factual", "publication", "terminology", "integrity", "workflow"]
Outcome = Literal["accept", "reject", "revoke", "supersede"]


def utc(value: object) -> datetime:
    """Require an actual instant; never infer midnight, a timezone or epoch seconds."""
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("use an exact timestamp with an explicit UTC offset")
    return value.astimezone(UTC)


Instant = Annotated[datetime, BeforeValidator(utc)]


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KeyPart(Frozen):
    field_id: Text
    kind: LogicalType
    value: StrictStr | StrictInt | StrictBool

    @model_validator(mode="after")
    def typed_value(self) -> Self:
        expected = {"integer": int, "boolean": bool}.get(self.kind, str)
        if type(self.value) is not expected:
            raise ValueError("key value must match its declared logical type")
        if self.kind == "integer" and not INTEGER_MIN <= int(self.value) <= INTEGER_MAX:
            raise ValueError("integer key outside BIGINT range")
        if isinstance(self.value, str):
            object.__setattr__(self, "value", self._string_value(self.value))
        return self

    def _string_value(self, value: str) -> str:
        if self.kind == "timestamp":
            return utc(value).isoformat()
        if self.kind == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("use a complete ISO date key")
            return date.fromisoformat(value).isoformat()
        if self.kind == "number":
            try:
                number = Decimal(value)
            except InvalidOperation:
                raise ValueError("use an exact decimal key") from None
            if not number.is_finite() or abs(number.adjusted()) > 38:
                raise ValueError("use a finite bounded decimal key")
            if number.is_zero():
                return "0"
            result = format(number, "f")
            return result.rstrip("0").rstrip(".") if "." in result else result
        return value

    def native(self) -> str | int | bool | date | datetime | Decimal:
        if self.kind == "timestamp":
            return utc(self.value)
        if self.kind == "date":
            return date.fromisoformat(str(self.value))
        if self.kind == "number":
            return Decimal(str(self.value))
        return self.value


class Target(Frozen):
    contract_id: Text
    dataset: Text
    key: tuple[KeyPart, ...] = Field(min_length=1)
    scope: Literal["record", "field"]
    field_id: Text | None = None
    version: Digest
    purpose: Purpose

    @model_validator(mode="after")
    def complete_scope(self) -> Self:
        if (self.scope == "field") != (self.field_id is not None):
            raise ValueError("only a field target names a stable field ID")
        if len({part.field_id for part in self.key}) != len(self.key):
            raise ValueError("key fields must be unique")
        object.__setattr__(self, "key", tuple(sorted(self.key, key=lambda part: part.field_id)))
        return self

    @property
    def target_id(self) -> str:
        return digest(self.model_dump(mode="json"))


class Request(Frozen):
    request_id: Text
    target: Target
    outcome: Outcome
    performed_at: Instant
    reason: Text
    evidence: Text
    predecessors: tuple[Digest, ...] = ()

    @field_validator("predecessors")
    @classmethod
    def unique_predecessors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("predecessor decisions must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def causal_outcome(self) -> Self:
        if self.outcome in {"revoke", "supersede"} and not self.predecessors:
            raise ValueError("revocation and supersession require predecessor decisions")
        if len(self.predecessors) > 1 and self.outcome != "supersede":
            raise ValueError(
                "resolving multiple branches requires an explicit superseding decision"
            )
        return self


class Decision(Request):
    schema_version: Literal[1]
    decision_id: Digest
    reviewer: Text
    recorded_at: Instant

    @model_validator(mode="after")
    def valid_event(self) -> Self:
        if self.performed_at > self.recorded_at:
            raise ValueError("human performed time cannot be in the future of recorded time")
        if self.decision_id != digest(self.model_dump(mode="json", exclude={"decision_id"})):
            raise ValueError("decision ID does not match canonical event content")
        return self


class Stamp(Frozen):
    human_verified_at: Instant | None = None
    human_verified_by: Text | None = None
    human_verification_decision_id: Digest | None = None

    @model_validator(mode="after")
    def all_or_none(self) -> Self:
        values = tuple(self.model_dump().values())
        if any(value is not None for value in values) and any(value is None for value in values):
            raise ValueError("human verification metadata must be all null or all present")
        return self


class Projection(Frozen):
    state: Literal["unreviewed", "accepted", "rejected", "revoked", "conflict"]
    stamp: Stamp = Field(default_factory=Stamp)
    heads: tuple[Digest, ...] = ()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()
