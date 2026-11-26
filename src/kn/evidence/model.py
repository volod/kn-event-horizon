"""Claims and their provenance: immutable rows with deterministic keys.

A claim embeds its evidence, so the claim-level origin URI, fetch time and fetch ID always
equal the evidence row's. A rerun of the same raw record with the same code yields the same
evidence ID and claim key.
"""

import re
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Self

from pydantic import Field, JsonValue, model_validator

from kn.evidence.records import (
    CONFIDENCE_SCALE,
    Record,
    SourceString,
    Time,
    exact,
    json_object,
    time_columns,
    validity,
)
from kn.evidence.values import Missing, Value, value_columns
from kn.evidence.vocabulary import AssertionType, ChangeKind, EvidenceClass, LocatorKind
from kn.i18n.data import TextVariant
from kn.identity.model import KnId
from kn.review.model import Digest, Instant, Text

# userinfo with a password, as in scheme://user:secret@host; never stored.
_CREDENTIALS = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/?#@]*:[^/?#@]*@")


def _redacted(uri: str) -> str:
    if _CREDENTIALS.match(uri):
        raise ValueError("store origin URIs after credential redaction")
    return uri


OriginUri = Annotated[Text, Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*:\S+$")]


class Evidence(Record):
    TABLE: ClassVar[str] = "evidence_records"
    KEY: ClassVar[str] = "evidence_id"

    source_id: Text
    fetch_id: Text
    archive_record_id: Text | None = None
    origin_uri: OriginUri
    fetched_at: Instant
    locator_kind: LocatorKind
    locator: Text
    excerpt: SourceString | None = None
    excerpt_rights: Text | None = None
    rights: Text
    code_digest: Digest
    contract_digest: Digest
    curator: Text | None = None
    recorded_at: Instant

    @model_validator(mode="after")
    def _provenance(self) -> Self:
        _redacted(self.origin_uri)
        if (self.excerpt is None) != (self.excerpt_rights is None):
            raise ValueError("store an excerpt only with the rights that permit it")
        if self.fetched_at > self.recorded_at:
            raise ValueError("evidence cannot be recorded before it was fetched")
        return self

    def columns(self) -> dict[str, Any]:
        return self.model_dump()


class Claim(Record):
    TABLE: ClassVar[str] = "claims"
    KEY: ClassVar[str] = "claim_key"

    kn_id: KnId
    field_id: Text
    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    source_id: Text
    record_id: Digest
    source_version_id: Digest
    change_set_id: Digest | None = None
    change_kind: ChangeKind
    supersedes: Digest | None = None
    decision_ref: Text | None = None
    evidence: Evidence
    original_value: SourceString | None = None
    original_unit: Text | None = None
    value: Value
    assertion_type: AssertionType
    evidence_class: EvidenceClass
    extraction_confidence: Decimal | None = None
    source_verification_label: Text | None = None
    event: Time | None = None
    published: Time | None = None
    valid_from: Time | None = None
    valid_to: Time | None = None
    observed_at: Instant
    recorded_at: Instant

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.extraction_confidence is not None:
            confidence = exact(self.extraction_confidence, CONFIDENCE_SCALE, 1)
            if not Decimal(0) <= confidence <= Decimal(1):
                raise ValueError("extraction confidence lies between 0 and 1")
            object.__setattr__(self, "extraction_confidence", confidence)
        empty = isinstance(self.value, Missing) and self.value.reason == "source_empty"
        if empty != (self.change_kind == "emptied"):
            raise ValueError("an emptied field, and only it, gives a source_empty claim")
        if (self.change_kind == "decided") != (self.decision_ref is not None):
            raise ValueError("a decided claim, and only it, names its review decision")
        if (self.change_kind in {"changed", "emptied"}) != (self.supersedes is not None):
            raise ValueError("a changed or emptied claim, and only it, names its predecessor")
        if self.source_id != self.evidence.source_id:
            raise ValueError("a claim and its evidence name one source")
        if self.evidence.fetched_at > self.recorded_at:
            raise ValueError("a claim cannot be recorded before its evidence was fetched")
        validity(self.valid_from, self.valid_to)
        return self

    def columns(self) -> dict[str, Any]:
        return {
            "kn_id": self.kn_id,
            "field_id": self.field_id,
            "conditions_json": json_object(self.conditions),
            "source_id": self.source_id,
            "record_id": self.record_id,
            "source_version_id": self.source_version_id,
            "change_set_id": self.change_set_id,
            "change_kind": self.change_kind,
            "supersedes": self.supersedes,
            "decision_ref": self.decision_ref,
            "evidence_id": self.evidence.key,
            "fetch_id": self.evidence.fetch_id,
            "origin_uri": self.evidence.origin_uri,
            "fetched_at": self.evidence.fetched_at,
            "original_value": self.original_value,
            "original_unit": self.original_unit,
            **value_columns(self.value),
            "assertion_type": self.assertion_type,
            "evidence_class": self.evidence_class,
            "extraction_confidence": self.extraction_confidence,
            "source_verification_label": self.source_verification_label,
            **time_columns("event", self.event),
            **time_columns("published", self.published),
            **time_columns("valid_from", self.valid_from),
            **time_columns("valid_to", self.valid_to),
            "observed_at": self.observed_at,
            "recorded_at": self.recorded_at,
        }


class Confirmation(Record):
    """An unchanged value observed again; it never adds rank or a new claim."""

    TABLE: ClassVar[str] = "claim_confirmations"
    KEY: ClassVar[str] = "confirmation_id"
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset({"recorded_at", "evidence_id", "observed_at"})

    claim_key: Digest
    source_version_id: Digest
    evidence: Evidence
    observed_at: Instant
    recorded_at: Instant

    def columns(self) -> dict[str, Any]:
        return {
            "claim_key": self.claim_key,
            "source_version_id": self.source_version_id,
            "evidence_id": self.evidence.key,
            "fetch_id": self.evidence.fetch_id,
            "observed_at": self.observed_at,
            "recorded_at": self.recorded_at,
        }


class Alias(Record):
    TABLE: ClassVar[str] = "aliases"
    KEY: ClassVar[str] = "alias_id"

    kn_id: KnId
    alias: SourceString
    language: Text
    normalized_key: Text
    normalizer: Text
    claim_key: Digest
    recorded_at: Instant

    @model_validator(mode="after")
    def _language(self) -> Self:
        TextVariant(self.alias, self.language, self.claim_key)
        return self

    def columns(self) -> dict[str, Any]:
        return self.model_dump()
