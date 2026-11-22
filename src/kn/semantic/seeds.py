"""Reconcile proposals for review and load only explicitly packaged reviewed snapshots."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple
from uuid import uuid4

from kn.semantic import validate_model
from kn.semantic.lifecycle import lifecycle_report
from kn.semantic.oecd_reference import publication_references
from kn.semantic.proposals import DOMAINS, Proposal, read_proposals
from kn.semantic.seed_changes import term_changes
from kn.semantic.seed_model import SeedBuilder, encoded
from kn.semantic.seed_oecd import (
    enrich_report,
    import_oecd,
    validate_oecd,
    validate_oecd_provenance,
)
from kn.semantic.seed_ontology import CLASS_SHEETS, import_classes, import_relation
from kn.semantic.seed_provenance import validate_provenance
from kn.semantic.seed_vocabulary import import_concepts
from kn.semantic.structure import Snapshot
from kn.semantic.verification import review_schemes

RESOURCES = Path(__file__).with_name("resources")
FIXTURE_PATH = Path("tests/semantic/fixtures/proposal_examples.json")
EXAMPLE_SHEETS = {
    "08_tagging_examples",
    "10_tagging_examples",
    "11_tagging_examples",
    "13_energy_template",
}
POLICY_REASON = "Policy or schema proposal needs typed attribute, condition, evidence, or profile mapping; no executable policy inferred."


class Reconciliation(NamedTuple):
    documents: dict[str, dict[str, Any]]
    report: list[dict[str, Any]]
    fixtures: list[dict[str, Any]]
    # Schemes whose content changed after their publication review, staged as unverified.
    stale_reviews: list[dict[str, str]]
    # Deprecated or replaced concepts that children, mappings or tags still use.
    lifecycle: list[dict[str, Any]]


def reconcile(root: Path) -> Reconciliation:
    """Build in memory and validate the complete result before emitting any artifact."""
    proposals = read_proposals(root)
    builders = {domain: SeedBuilder(domain) for domain in DOMAINS}
    for builder in builders.values():
        import_classes(builder, [row for row in proposals if row.domain == builder.domain])
    report: list[dict[str, Any]] = []
    fixtures: list[dict[str, Any]] = []
    for row in proposals:
        builder = builders[row.domain]
        status, reason, identifiers = _decision(builder, row)
        if row.workbook == "ontology_and_tags_v1" and row.sheet in EXAMPLE_SHEETS:
            fixtures.append(
                {
                    "provenance": row.provenance,
                    "values": row.values,
                    "formulas_not_evaluated": row.formulas,
                }
            )
        report.append(
            {
                "provenance": row.provenance,
                "status": status,
                "reason": reason,
                "term_ids": sorted(identifiers),
                "values": row.values,
                "formulas_not_evaluated": row.formulas,
            }
        )
    enrich_report(report, import_oecd(builders["microelectronics"], proposals, RESOURCES))
    documents = {domain: builder.document() for domain, builder in builders.items()}
    stale = [
        item
        for domain, document in documents.items()
        for item in review_schemes(
            document["snapshot"], RESOURCES / f"{domain}-verification.json", domain
        )
    ]
    snapshot = merge_snapshots([document["snapshot"] for document in documents.values()])
    validate_model(snapshot, publication_references(RESOURCES))
    validate_oecd(snapshot, RESOURCES)
    return Reconciliation(documents, report, fixtures, stale, lifecycle_report(snapshot))


def _class_identifiers(builder: SeedBuilder, row: Proposal) -> list[str]:
    return [
        key
        for key, sources in builder.lineage.items()
        if any(
            source["file"] == row.provenance["file"] and source["row"] == row.row
            for source in sources
        )
    ]


def _decision(builder: SeedBuilder, row: Proposal) -> tuple[str, str, list[str]]:
    if row.sheet == "00_readme":
        return "rejected", "Workbook explanatory notes, not vocabulary content.", []
    if row.workbook == "data_sources_v1" or row.sheet == "12_sources_ingestion":
        return (
            "needs_mapping",
            "Deferred to source-catalogue-import; candidate sources are not enabled by vocabulary import.",
            [],
        )
    if row.sheet in EXAMPLE_SHEETS:
        return (
            "rejected",
            "Example or hypothetical template retained only as a fixture; no entity or tag created.",
            [],
        )
    if row.workbook == "ontology_and_tags_v1" and row.sheet == CLASS_SHEETS[row.domain]:
        return (
            "accepted",
            "Entity class definition only; illustrative names and outgoing relation hints are not instantiated.",
            _class_identifiers(builder, row),
        )
    before = set(builder.lineage)
    if row.sheet == "02_relations":
        identifiers, reason = import_relation(builder, row)
    else:
        identifiers = import_concepts(builder, row)
        reason = "Controlled vocabulary with domain/scheme qualification; original metadata retained, publication state and scope recorded in verification review."
    if not identifiers:
        return "needs_mapping", reason if row.sheet == "02_relations" else POLICY_REASON, []
    status = "duplicate" if set(identifiers) <= before else "accepted"
    return status, reason, identifiers


def merge_snapshots(snapshots: list[Snapshot]) -> Snapshot:
    result: Snapshot = {}
    for snapshot in snapshots:
        for name, rows in snapshot.items():
            result.setdefault(name, []).extend(rows)
    return result


def import_proposals(root: Path, data_dir: Path, *, check: bool = False) -> dict[str, object]:
    """Stage a review diff under DATA_DIR; never overwrite reviewed repository files."""
    documents, report, fixtures, stale, lifecycle = reconcile(root)
    changes = {
        domain: term_changes(
            document["snapshot"],
            json.loads((RESOURCES / f"{domain}.json").read_bytes())["snapshot"],
        )
        for domain, document in documents.items()
    }
    destination = data_dir / "seed-import" / uuid4().hex
    destination.mkdir(parents=True)
    for domain, document in documents.items():
        (destination / f"{domain}.json").write_bytes(encoded(document))
    (destination / "fixtures.json").write_bytes(encoded(fixtures))
    counts = dict(sorted(Counter(row["status"] for row in report).items()))
    (destination / "reconciliation.json").write_bytes(
        encoded(
            {
                "counts": counts,
                "changes": changes,
                "stale_reviews": stale,
                "lifecycle": lifecycle,
                "rows": report,
            }
        )
    )
    if check:
        for domain, document in documents.items():
            reviewed = root / "domains" / domain / "seeds/semantic.json"
            if reviewed.read_bytes() != encoded(document):
                raise ValueError("reviewed vocabulary differs from staged proposals")
        if (root / FIXTURE_PATH).read_bytes() != encoded(fixtures):
            raise ValueError("proposal fixtures differ from staged examples")
    return {
        "status": "reconciled",
        "report": str(destination / "reconciliation.json"),
        "rows": len(report),
        "counts": counts,
        "changes": changes,
        "stale_reviews": [item["scheme_id"] for item in stale],
        "lifecycle": len(lifecycle),
    }


def reviewed_snapshot(resources: Path = RESOURCES) -> Snapshot:
    """Explicit filenames, independent of cwd; proposals and examples are never runtime inputs."""
    snapshots: list[Snapshot] = []
    references = publication_references(resources)
    for domain in DOMAINS:
        document = json.loads((resources / f"{domain}.json").read_bytes())
        if (
            not isinstance(document, dict)
            or set(document) != {"format", "domain", "snapshot", "provenance"}
            or document.get("format") != "kn.semantic.reviewed-seeds.v1"
            or document.get("domain") != domain
        ):
            raise ValueError("invalid reviewed seed envelope")
        validate_model(document["snapshot"], references)
        validate_provenance(document)
        if domain == "microelectronics":
            validate_oecd_provenance(document, resources)
        review_schemes(
            document["snapshot"], resources / f"{domain}-verification.json", domain, check=True
        )
        snapshots.append(document["snapshot"])
    snapshot = merge_snapshots(snapshots)
    validate_model(snapshot, references)
    validate_oecd(snapshot, resources)
    return snapshot
