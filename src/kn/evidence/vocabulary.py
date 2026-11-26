"""Closed value sets of the evidence contract; tests keep them equal to its enums."""

from typing import Literal

type MissingReason = Literal[
    "source_empty",
    "not_found",
    "not_disclosed",
    "requires_vendor_quote",
    "cannot_verify",
    "not_applicable",
]
type AssertionType = Literal["declared", "observed", "derived", "reported"]
# Highest first: selection ranks a primary declaration above a secondary report.
type EvidenceClass = Literal["primary", "secondary", "derived", "extracted_candidate"]
type ChangeKind = Literal["added", "changed", "emptied", "decided"]
type TimePrecision = Literal["year", "month", "day", "hour", "minute", "second", "subsecond"]
type LocatorKind = Literal["json_pointer", "row", "page", "offset"]
type TranslationMethod = Literal["source", "human", "machine"]
type Mode = Literal["priority", "latest_observed", "accumulate", "fixed"]
type FactOutcome = Literal["filled", "replaced", "corroborated", "conflict"]
type Outcome = Literal["filled", "replaced", "ignored", "corroborated", "conflict"]
type Criterion = Literal[
    "first_eligible",
    "source_rank",
    "evidence_class",
    "data_time",
    "tie",
    "fixed_value",
    "review_decision",
]
type FactVerification = Literal["unreviewed", "corroborated", "verified", "disputed"]
type UnresolvedReason = Literal["no_eligible_claim", "conflict", "review_pending", "cleared"]
type RelationReviewState = Literal["unreviewed", "accepted", "disputed", "rejected"]
type CloseReason = Literal["rejected", "retracted", "superseded"]
type ReviewKind = Literal[
    "fact_conflict",
    "fixed_value_change",
    "empty_claim",
    "high_impact",
    "owner_override",
    "relation_candidate",
    "quarantine",
    "identity_match",
    "identity_drift",
]
type ReviewOutcome = Literal["select", "reject", "accept", "defer", "dismiss"]

# Review kinds about one canonical fact must name it.
FACT_REVIEW_KINDS = frozenset(
    {"fact_conflict", "fixed_value_change", "empty_claim", "high_impact", "owner_override"}
)
