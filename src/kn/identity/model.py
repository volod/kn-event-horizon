"""Typed identity payloads. Execution of matching and change detection is separate."""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AfterValidator, Field, model_validator

from kn.review.model import Digest, Frozen, Instant, Text

Authority = Literal["authoritative", "source_qualified", "weak"]
Method = Literal["authoritative_key", "existing_link", "scored_match", "review_decision", "minted"]
MatchDecision = Literal["link", "review", "mint"]
MatchRoute = Literal[
    "authoritative_key", "existing_link", "scored_match", "alias", "conflict", "no_match"
]
MATCH_LINK_METHODS: dict[MatchRoute, Method] = {
    "authoritative_key": "authoritative_key",
    "existing_link": "existing_link",
    "scored_match": "scored_match",
    "no_match": "minted",
}


def uuid7(value: str) -> str:
    parsed = UUID(value.removeprefix("kn:"))
    if parsed.version != 7 or value != f"kn:{parsed}":
        raise ValueError("use a canonical kn: UUIDv7")
    return value


KnId = Annotated[Text, AfterValidator(uuid7)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Score = Annotated[float, Field(allow_inf_nan=False)]


class SourceKey(Frozen):
    source: Text
    key: Text

    @property
    def record_id(self) -> str:
        from kn.review.model import digest

        return digest(self.model_dump(mode="json"))


class Mint(Frozen):
    kind: Literal["minted"] = "minted"
    kn_id: KnId
    entity_class: Text
    anchor: SourceKey


class Link(Frozen):
    kind: Literal["linked"] = "linked"
    record: SourceKey
    kn_id: KnId
    method: Method
    score: Score | None = None
    probability: Probability | None = None
    profile_digest: Digest | None = None
    profile_version: Text | None = None
    match_id: Digest | None = None

    @model_validator(mode="after")
    def scored_context(self) -> Self:
        if self.method == "scored_match" and any(
            value is None
            for value in (
                self.score,
                self.probability,
                self.profile_digest,
                self.profile_version,
                self.match_id,
            )
        ):
            raise ValueError("scored links require a stored match and versioned profile")
        return self


class Unlink(Frozen):
    kind: Literal["unlinked"] = "unlinked"
    record: SourceKey
    kn_id: KnId


class Identifier(Frozen):
    kind: Literal["identifier_recorded"] = "identifier_recorded"
    kn_id: KnId
    namespace: Text
    value: Text
    issuer: Text
    authority: Authority
    valid_from: Instant
    valid_to: Instant | None = None

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("identifier validity must be a nonempty half-open interval")
        return self


class Merge(Frozen):
    kind: Literal["merged"] = "merged"
    kn_id: KnId
    survivor: KnId
    # Preserve the canonical representation and hash of earlier v1 reviewed merges.
    authoritative: Identifier | None = Field(default=None, exclude_if=lambda value: value is None)


class Assignment(Frozen):
    item_id: Digest
    successor: KnId


class Split(Frozen):
    kind: Literal["split"] = "split"
    kn_id: KnId
    successors: tuple[KnId, ...] = Field(min_length=2)
    assignments: tuple[Assignment, ...] = ()


class Reclassify(Frozen):
    kind: Literal["reclassified"] = "reclassified"
    kn_id: KnId
    successor: Mint


class Retire(Frozen):
    kind: Literal["retired"] = "retired"
    kn_id: KnId


class Restore(Frozen):
    kind: Literal["restored"] = "restored"
    kn_id: KnId


class Attribute(Frozen):
    kind: Literal["attribute_recorded"] = "attribute_recorded"
    kn_id: KnId
    field_id: Text
    original: Text
    normalized: Text
    normalizer: Text
    profile_digest: Digest


class FieldHash(Frozen):
    field_id: Text
    digest: Digest


class Version(Frozen):
    kind: Literal["version_recorded"] = "version_recorded"
    record: SourceKey
    version: Text
    content_digest: Digest
    field_hashes: tuple[FieldHash, ...]
    observed_at: Instant
    source_updated_at: Instant | None = None
    fetch_id: Text
    archive_record_id: Text
    code_digest: Digest

    @model_validator(mode="after")
    def unique_fields(self) -> Self:
        if len({item.field_id for item in self.field_hashes}) != len(self.field_hashes):
            raise ValueError("duplicate field hashes")
        return self


class Feature(Frozen):
    field_id: Text
    left: Text | None
    right: Text | None
    comparator: Text
    outcome: Text
    weight: Score


class Candidate(Frozen):
    kn_id: KnId
    features: tuple[Feature, ...]
    score: Score
    probability: Probability


class MatchTrace(Frozen):
    request_digest: Digest
    source_version: Text
    route: MatchRoute
    prior: Probability
    minted_id: KnId | None = None
    followup_count: int = Field(default=0, ge=0, strict=True)


class Match(Frozen):
    kind: Literal["match_recorded"] = "match_recorded"
    record: SourceKey
    profile_digest: Digest
    profile_version: Text
    candidates: tuple[Candidate, ...]
    decision: MatchDecision
    selected: KnId | None = None
    # Earlier events must retain their canonical v1 bytes and hashes.
    trace: MatchTrace | None = Field(default=None, exclude_if=lambda value: value is None)


class FieldChange(Frozen):
    field_id: Text
    change: Literal["added", "changed", "unchanged", "emptied", "not_stated"]
    previous_hash: Digest | None = None
    current_hash: Digest | None = None


class ChangeSet(Frozen):
    kind: Literal["changes_recorded"] = "changes_recorded"
    version_id: Digest
    changes: tuple[FieldChange, ...]


Payload = Annotated[
    Mint
    | Link
    | Unlink
    | Merge
    | Split
    | Reclassify
    | Retire
    | Restore
    | Identifier
    | Attribute
    | Version
    | Match
    | ChangeSet,
    Field(discriminator="kind"),
]
