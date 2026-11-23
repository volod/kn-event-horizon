"""Offline publication reviews bound to exact seed content, never inferred from origin."""

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from kn.semantic.seed_model import encoded
from kn.semantic.structure import Snapshot

SCHEME_FIELDS = (
    "verification_state",
    "verification_reason",
    "publisher",
    "edition",
    "source_uri",
    "source_sha256",
)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: Literal["mismatch", "missing_leaf", "local_extension", "access_limit"]
    locator: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class Publication(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    publisher: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    source_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    comparison: str = Field(min_length=1)


class TextRevision(BaseModel):
    """A recorded text cleanup preserves the existing publication comparison outcome."""

    model_config = ConfigDict(extra="forbid", strict=True)

    previous_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record: str = Field(min_length=1)
    note: str = Field(min_length=1)
    comparison_unchanged: Literal[True]


class SchemeReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    scheme_id: str
    origin: Literal["official", "kb_normalized", "kb_extension", "service_extension", "native"]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_state: Literal["verified", "unverified"]
    verification_reason: str = Field(min_length=1)
    publisher: str | None = None
    edition: str | None = None
    source_uri: str | None = None
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    scope: str = Field(min_length=1)
    comparison: str = Field(min_length=1)
    findings: list[Finding]
    text_revision: TextRevision | None = None


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    format: Literal["kn.semantic.verification.v1"]
    domain: str
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    schemes: list[SchemeReview]
    related_publications: list[Publication] = Field(default_factory=list)


def content_digest(snapshot: Snapshot, scheme_id: str) -> str:
    """Bind reviewed codes, statuses, hierarchy and labels, independent of proposal ordering."""
    concepts = [row for row in snapshot.get("concepts", []) if row["scheme_id"] == scheme_id]
    identifiers = {row["id"] for row in concepts} | {scheme_id}
    content = {
        name: sorted(
            (row for row in snapshot.get(name, []) if row[key] in identifiers), key=encoded
        )
        for name, key in (
            ("concepts", "id"),
            ("labels", "term_id"),
            ("alternative_labels", "term_id"),
        )
    }
    # Proposal-row definitions are provenance, not publication definitions. Structural parents
    # inherit their first contributing row, which can change when proposals are reordered.
    content["terms"] = sorted(
        (
            {key: row[key] for key in ("id", "namespace_id", "code", "kind", "status")}
            for row in snapshot.get("terms", [])
            if row["id"] in identifiers
        ),
        key=encoded,
    )
    return hashlib.sha256(encoded(content)).hexdigest()


def review_schemes(
    snapshot: Snapshot, path: Path, domain: str, *, check: bool = False
) -> list[dict[str, str]]:
    """Project reviewed metadata during staging; require identical metadata when loading seeds.

    Loading (`check`) refuses a review whose content digest no longer matches. Staging keeps
    going so the change can be reviewed: a stale scheme is staged `unverified`, never with its
    old verification, and is returned with its new digest for the next comparison.
    """
    report = VerificationReport.model_validate_json(path.read_bytes())
    schemes = {row["id"]: row for row in snapshot.get("concept_schemes", [])}
    ids = [review.scheme_id for review in report.schemes]
    if report.domain != domain or len(ids) != len(set(ids)) or set(ids) != schemes.keys():
        raise ValueError("verification review must cover each scheme exactly once")
    stale: list[dict[str, str]] = []
    for review in report.schemes:
        _check_review(schemes[review.scheme_id], review)
        digest = content_digest(snapshot, review.scheme_id)
        if digest != review.content_sha256:
            if check:
                raise ValueError(
                    f"verification review of {review.scheme_id} is stale; "
                    "compare the changed content again"
                )
            stale.append(
                {
                    "scheme_id": review.scheme_id,
                    "reviewed_sha256": review.content_sha256,
                    "content_sha256": digest,
                }
            )
    changed = {item["scheme_id"] for item in stale}
    for review in report.schemes:
        _metadata(
            schemes[review.scheme_id],
            review,
            check=check,
            stale_since=report.reviewed_on if review.scheme_id in changed else None,
        )
    return stale


def _metadata(
    row: dict[str, Any], review: SchemeReview, *, check: bool, stale_since: str | None = None
) -> None:
    metadata = {
        key: getattr(review, key) for key in SCHEME_FIELDS if getattr(review, key) is not None
    }
    if check:
        if {key: row[key] for key in SCHEME_FIELDS if key in row} != metadata:
            raise ValueError("reviewed scheme metadata differs from verification review")
        return
    for key in SCHEME_FIELDS:
        row.pop(key, None)
    row.update(metadata)
    if stale_since is not None:
        row["verification_state"] = "unverified"
        row["verification_reason"] = (
            f"Content changed after the {stale_since} review; a new comparison is required. "
            f"Previous review: {review.verification_reason}"
        )


def _check_review(row: dict[str, Any], review: SchemeReview) -> None:
    if row["origin"] != review.origin:
        raise ValueError(f"reviewed origin of {review.scheme_id} differs from the seed")
    if review.verification_state == "verified" and (
        review.origin != "official"
        or any(
            finding.kind in {"mismatch", "access_limit", "local_extension"}
            for finding in review.findings
        )
        or not all(
            getattr(review, key) for key in ("publisher", "edition", "source_uri", "source_sha256")
        )
    ):
        raise ValueError(
            "verified scheme requires official publication evidence without mismatches"
        )
