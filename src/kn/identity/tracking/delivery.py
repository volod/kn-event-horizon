"""One mapped delivery of a source record: the fields it states and where it came from."""

import re
from typing import Literal, Self

from pydantic import Field, JsonValue, model_validator

from kn.evidence.model import Evidence
from kn.evidence.records import SourceString
from kn.evidence.values import Missing, TextValue, Value
from kn.evidence.vocabulary import AssertionType, EvidenceClass, LocatorKind
from kn.identity.model import FieldHash, SourceKey, Version
from kn.review.model import Digest, Frozen, Instant, Text, digest

# Versions of one record order by this basis, then by fetch time, then by version text.
type Ordering = Literal["version", "updated", "fetch"]
_NUMERIC = re.compile(r"[0-9]+")


class Statement(Frozen):
    """A mapped field that the record states; a null value means the source stated it empty."""

    field_id: Text
    value: Value | None = None
    original_value: SourceString | None = None
    original_unit: Text | None = None
    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    locator: Text

    @model_validator(mode="after")
    def _tracker_owns_empty(self) -> Self:
        if isinstance(self.value, Missing) and self.value.reason == "source_empty":
            raise ValueError("state an empty field with a null value; tracking records it")
        if isinstance(self.value, TextValue) and not self.value.text.strip():
            raise ValueError("state blank text as an empty field with a null value")
        return self

    @property
    def digest(self) -> str:
        """The field hash: an empty statement hashes alike whatever its original text."""
        context = {"conditions": self.conditions, "unit": self.original_unit}
        if self.value is None:
            return digest({**context, "empty": True})
        value = self.value.model_dump(mode="json")
        return digest({**context, "value": value, "original": self.original_value})


class Delivery(Frozen):
    """A record as one fetch delivered it. Fields it omits are not stated."""

    record: SourceKey
    # A fragment with only a weak key resolves through its parent record's link.
    parent: SourceKey | None = None
    version: Text | None = None
    source_updated_at: Instant | None = None
    ordering: Ordering
    fetch_id: Text
    archive_record_id: Text
    fetched_at: Instant
    origin_uri: Text
    locator_kind: LocatorKind
    rights: Text
    code_digest: Digest
    contract_digest: Digest
    assertion_type: AssertionType
    evidence_class: EvidenceClass
    statements: tuple[Statement, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len({item.field_id for item in self.statements}) != len(self.statements):
            raise ValueError("a delivery states each field once")
        if self.parent is not None and (
            self.parent == self.record or self.parent.source != self.record.source
        ):
            raise ValueError("a parent record is another record of the same source")
        if self.ordering == "version" and not (
            self.version is not None and _NUMERIC.fullmatch(self.version)
        ):
            raise ValueError("ordering by source version requires a numeric version")
        if self.ordering == "updated" and self.source_updated_at is None:
            raise ValueError("ordering by updated time requires the source updated time")
        # Refuse unusable provenance before anything reaches the durable journal.
        self.evidence(self.statements[0].locator if self.statements else "/", self.fetched_at)
        return self

    @property
    def version_text(self) -> str:
        """A record without a source version gets one version per fetch."""
        return self.version if self.version is not None else self.fetch_id

    @property
    def field_hashes(self) -> tuple[FieldHash, ...]:
        return tuple(
            FieldHash(field_id=item.field_id, digest=item.digest)
            for item in sorted(self.statements, key=lambda item: item.field_id)
        )

    @property
    def content_digest(self) -> str:
        return digest([item.model_dump(mode="json") for item in self.field_hashes])

    def version_payload(self) -> Version:
        return Version(
            record=self.record,
            version=self.version_text,
            content_digest=self.content_digest,
            field_hashes=self.field_hashes,
            observed_at=self.fetched_at,
            source_updated_at=self.source_updated_at,
            fetch_id=self.fetch_id,
            archive_record_id=self.archive_record_id,
            code_digest=self.code_digest,
        )

    def evidence(self, locator: str, recorded_at: Instant) -> Evidence:
        return Evidence(
            source_id=self.record.source,
            fetch_id=self.fetch_id,
            archive_record_id=self.archive_record_id,
            origin_uri=self.origin_uri,
            fetched_at=self.fetched_at,
            locator_kind=self.locator_kind,
            locator=locator,
            rights=self.rights,
            code_digest=self.code_digest,
            contract_digest=self.contract_digest,
            recorded_at=recorded_at,
        )
