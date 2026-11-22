"""Keep the official OECD tree beside the mixed product vocabulary and apply reviewed mappings."""

from pathlib import Path
from typing import Any

from kn.semantic.oecd_reference import (
    MAPPING_METHOD,
    MAPPING_NAMESPACE,
    MAPPING_PREFIX,
    OECD_NAMESPACE,
    OECD_PREFIX,
    PRODUCT_PREFIX,
    REFERENCE_FILE,
    Crosswalk,
    FigureNode,
    FigureReview,
    read_reference,
)
from kn.semantic.proposals import Proposal
from kn.semantic.seed_model import SeedBuilder
from kn.semantic.structure import Snapshot


def import_oecd(
    builder: SeedBuilder, proposals: list[Proposal], resources: Path
) -> dict[tuple[str, int], list[str]]:
    """Use authored decisions; neither row flags nor an ancestor walk invent an official node."""
    review, evidence_id = read_reference(resources)
    sources = {
        row.values["kb_node"]: row
        for row in proposals
        if row.domain == "microelectronics"
        and row.sheet == "03_product_classifier"
        and row.workbook == "ontology_and_tags_v1"
    }
    if sources.keys() != {row.code for row in review.crosswalks}:
        raise ValueError("product proposal codes differ from reviewed OECD decisions")
    additions: dict[tuple[str, int], list[str]] = {}
    for node in review.nodes:
        source = sources[node.code]
        identifier = _import_node(builder, node, source, review, evidence_id)
        _record(additions, source, identifier)
    _publication_provenance(builder, OECD_PREFIX + "scheme", review, evidence_id)
    for decision in review.crosswalks:
        if decision.target_code is None:
            continue
        source = sources[decision.code]
        identifier = builder.term(
            MAPPING_NAMESPACE,
            decision.code,
            "concept_mapping",
            "OECD crosswalk " + decision.code,
            decision.reason,
            source,
            origin="kb_normalized",
            **_mapping(decision, evidence_id),
        )
        _publication_provenance(builder, identifier, review, evidence_id)
        _record(additions, source, identifier)
    return additions


def _import_node(
    builder: SeedBuilder, node: FigureNode, source: Proposal, review: FigureReview, evidence_id: str
) -> str:
    if (
        source.values["origin"] != "OECD_NODE"
        or source.values["class"] != node.source_label
        or source.values["parent"] != node.parent_code
    ):
        raise ValueError("product source category differs from reviewed Figure 9")
    identifier = builder.concept(
        OECD_NAMESPACE,
        node.code,
        node.label,
        source,
        origin="official",
        parent=node.parent_code,
    )
    _publication_provenance(builder, identifier, review, evidence_id)
    for locale in ("en", "uk"):
        if node.label != node.source_label:
            builder.add(
                "alternative_labels",
                {"term_id": identifier, "locale": locale, "label": node.source_label},
            )
    return identifier


def _record(additions: dict[tuple[str, int], list[str]], row: Proposal, identifier: str) -> None:
    additions.setdefault((row.provenance["file"], row.row), []).append(identifier)


def _mapping(decision: Crosswalk, evidence_id: str) -> dict[str, Any]:
    assert decision.target_code is not None
    return dict(
        source_id=PRODUCT_PREFIX + decision.code,
        target_id=OECD_PREFIX + decision.target_code,
        mapping_type=decision.mapping_type,
        method=MAPPING_METHOD,
        evidence_id=evidence_id,
    )


def _publication_provenance(
    builder: SeedBuilder, identifier: str, review: FigureReview, evidence_id: str
) -> None:
    for source in builder.lineage[identifier]:
        source.update(_publication_fields(review, evidence_id))


def _publication_fields(review: FigureReview, evidence_id: str) -> dict[str, str]:
    return dict(
        publication_uri=review.publication.source_uri,
        publication_sha256=review.publication.source_sha256,
        publication_locator=review.locator,
        review_file="domains/microelectronics/seeds/" + REFERENCE_FILE,
        review_evidence_id=evidence_id,
        label_policy="review-derived display label; source Others retained as alternatives; uk source fallback",
    )


def validate_oecd_provenance(document: dict[str, Any], resources: Path) -> None:
    review, evidence_id = read_reference(resources)
    fields = _publication_fields(review, evidence_id)
    sources = [
        source
        for identifier, rows in document["provenance"].items()
        if identifier.startswith((OECD_PREFIX, MAPPING_PREFIX))
        for source in rows
    ]
    if any(any(source.get(key) != value for key, value in fields.items()) for source in sources):
        raise ValueError("OECD publication provenance differs from registered review")


def validate_oecd(snapshot: Snapshot, resources: Path) -> None:
    """Require the stored official tree and mapping rows to match their publication review."""
    review, evidence_id = read_reference(resources)
    scheme = next(
        (row for row in snapshot.get("concept_schemes", []) if row["id"] == OECD_PREFIX + "scheme"),
        None,
    )
    if scheme is None or any(
        scheme.get(key) != value for key, value in review.publication.model_dump().items()
    ):
        raise ValueError("OECD scheme requires the reviewed publication metadata")
    _validate_nodes(snapshot, review.nodes)
    expected = {
        MAPPING_PREFIX + row.code: dict(id=MAPPING_PREFIX + row.code, **_mapping(row, evidence_id))
        for row in review.crosswalks
        if row.target_code is not None
    }
    actual = {
        row["id"]: row
        for row in snapshot.get("concept_mappings", [])
        if row["source_id"].startswith(PRODUCT_PREFIX)
        or row["target_id"].startswith(OECD_PREFIX)
        or row["id"].startswith(MAPPING_PREFIX)
    }
    if actual != expected:
        raise ValueError("OECD mappings differ from reviewed product decisions or evidence")
    products = {
        row["id"].removeprefix(PRODUCT_PREFIX)
        for row in snapshot.get("concepts", [])
        if row["scheme_id"] == PRODUCT_PREFIX + "scheme"
    }
    if products != {row.code for row in review.crosswalks}:
        raise ValueError("every product requires a reviewed mapping or explicit unmapped reason")


def _validate_nodes(snapshot: Snapshot, nodes: list[FigureNode]) -> None:
    expected = {
        OECD_PREFIX + row.code: dict(
            id=OECD_PREFIX + row.code,
            scheme_id=OECD_PREFIX + "scheme",
            parent_id=OECD_PREFIX + row.parent_code if row.parent_code else None,
        )
        for row in nodes
    }
    actual = {
        row["id"]: row
        for row in snapshot.get("concepts", [])
        if row["scheme_id"] == OECD_PREFIX + "scheme"
    }
    if actual != expected:
        raise ValueError("OECD nodes or primary parents differ from Figure 9 review")
    expected_labels = {
        (OECD_PREFIX + row.code, locale, row.label) for row in nodes for locale in ("en", "uk")
    }
    actual_labels = {
        (row["term_id"], row["locale"], row["label"])
        for row in snapshot.get("labels", [])
        if row["term_id"] in expected
    }
    expected_alternatives = {
        (OECD_PREFIX + row.code, locale, row.source_label)
        for row in nodes
        if row.label != row.source_label
        for locale in ("en", "uk")
    }
    actual_alternatives = {
        (row["term_id"], row["locale"], row["label"])
        for row in snapshot.get("alternative_labels", [])
        if row["term_id"] in expected
    }
    if actual_labels != expected_labels or actual_alternatives != expected_alternatives:
        raise ValueError("OECD source labels or explicit display disambiguation differ from review")


def enrich_report(
    report: list[dict[str, Any]], additions: dict[tuple[str, int], list[str]]
) -> None:
    """Keep each generated concept and crosswalk traceable to its original proposal row."""
    for row in report:
        key = (row["provenance"]["file"], row["provenance"]["row"])
        row["term_ids"] = sorted(set(row["term_ids"]) | set(additions.get(key, [])))
