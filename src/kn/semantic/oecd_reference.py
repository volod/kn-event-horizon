"""Reviewed Figure 9 transcription and authored crosswalk decisions, with explicit evidence IDs."""

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kn.semantic import ExternalReferences
from kn.semantic.structure import acyclic

OECD_NAMESPACE = "oecd_2024"
OECD_PREFIX = "microelectronics." + OECD_NAMESPACE + "."
PRODUCT_PREFIX = "microelectronics.product_v1."
MAPPING_NAMESPACE = "oecd_2024_crosswalk"
MAPPING_PREFIX = "microelectronics." + MAPPING_NAMESPACE + "."
MAPPING_METHOD = "reviewed OECD Figure 9 product crosswalk"
REFERENCE_FILE = "oecd_2024.json"
FIGURE_NODE_COUNT = 29
PRODUCT_NODE_COUNT = 76


class ReviewedRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FigureNode(ReviewedRow):
    code: str = Field(min_length=1)
    parent_code: str | None
    source_label: str = Field(min_length=1)

    @property
    def label(self) -> str:
        return (
            self.source_label + " (" + self.code + ")"
            if self.source_label == "Others"
            else self.source_label
        )


class Crosswalk(ReviewedRow):
    code: str = Field(min_length=1)
    target_code: str | None
    mapping_type: Literal["exactMatch", "broadMatch", "analyst_crosswalk"] | None
    reason: str = Field(min_length=1)


class Publication(ReviewedRow):
    publisher: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FigureReview(ReviewedRow):
    format: Literal["kn.semantic.oecd-figure9.v1"]
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    publication: Publication
    locator: str = Field(min_length=1)
    nodes: list[FigureNode]
    crosswalks: list[Crosswalk]


def read_reference(resources: Path) -> tuple[FigureReview, str]:
    payload = (resources / REFERENCE_FILE).read_bytes()
    review = FigureReview.model_validate_json(payload)
    nodes = {row.code: row for row in review.nodes}
    decisions = {row.code: row for row in review.crosswalks}
    if len(nodes) != len(review.nodes) or len(nodes) != FIGURE_NODE_COUNT:
        raise ValueError("OECD review requires 29 distinct Figure 9 categories")
    if len(decisions) != len(review.crosswalks) or len(decisions) != PRODUCT_NODE_COUNT:
        raise ValueError("OECD review requires 76 distinct product decisions")
    if any(node.parent_code is not None and node.parent_code not in nodes for node in review.nodes):
        raise ValueError("OECD category parent must exist in Figure 9")
    acyclic(
        {code: {"id": code, "parent_id": row.parent_code} for code, row in nodes.items()},
        "parent_id",
        "OECD Figure 9",
    )
    for decision in review.crosswalks:
        _check_decision(decision, nodes)
    if not nodes.keys() <= decisions.keys():
        raise ValueError("OECD category requires an explicit product decision")
    return review, "urn:sha256:" + hashlib.sha256(payload).hexdigest()


def _check_decision(decision: Crosswalk, nodes: dict[str, FigureNode]) -> None:
    if (decision.target_code is None) != (decision.mapping_type is None):
        raise ValueError("unmapped products require null target and mapping type")
    if decision.target_code is not None and decision.target_code not in nodes:
        raise ValueError("crosswalk target must be a Figure 9 category")
    if decision.code in nodes:
        if decision.mapping_type != "exactMatch" or decision.target_code != decision.code:
            raise ValueError("source categories require their corresponding exact match")
    elif decision.mapping_type == "exactMatch":
        raise ValueError("local extensions cannot assert source category equivalence")


def publication_references(resources: Path) -> ExternalReferences:
    """Resolve the actual packaged review artifact, never infer evidence from mapping claims."""
    _, evidence_id = read_reference(resources)
    return ExternalReferences(evidence_ids=frozenset({evidence_id}))
