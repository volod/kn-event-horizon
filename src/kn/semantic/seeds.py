"""Reconcile proposals for review and load only explicitly packaged reviewed snapshots."""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import MetaData, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.statements import SetConstraints
from kn.semantic import validate_model
from kn.semantic.proposals import DOMAINS, Proposal, read_proposals
from kn.semantic.seed_model import SeedBuilder, encoded
from kn.semantic.seed_ontology import CLASS_SHEETS, import_classes, import_relation
from kn.semantic.seed_vocabulary import import_concepts
from kn.semantic.structure import Snapshot, semantic_contract

RESOURCES = Path(__file__).with_name("resources")
FIXTURE_PATH = Path("tests/semantic/fixtures/proposal_examples.json")
EXAMPLE_SHEETS = {
    "08_tagging_examples",
    "10_tagging_examples",
    "11_tagging_examples",
    "13_energy_template",
}
POLICY_REASON = "Policy or schema proposal needs typed attribute, condition, evidence, or profile mapping; no executable policy inferred."


def reconcile(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
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
    documents = {domain: builder.document() for domain, builder in builders.items()}
    validate_model(merge_snapshots([document["snapshot"] for document in documents.values()]))
    return documents, report, fixtures


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
        reason = "Controlled vocabulary with domain/scheme qualification; original metadata retained, publication unverified."
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
    documents, report, fixtures = reconcile(root)
    destination = data_dir / "seed-import" / uuid4().hex
    destination.mkdir(parents=True)
    for domain, document in documents.items():
        (destination / f"{domain}.json").write_bytes(encoded(document))
    (destination / "fixtures.json").write_bytes(encoded(fixtures))
    counts = dict(sorted(Counter(row["status"] for row in report).items()))
    (destination / "reconciliation.json").write_bytes(encoded({"counts": counts, "rows": report}))
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
    }


def reviewed_snapshot(resources: Path = RESOURCES) -> Snapshot:
    """Explicit filenames, independent of cwd; proposals and examples are never runtime inputs."""
    snapshots: list[Snapshot] = []
    for domain in DOMAINS:
        document = json.loads((resources / f"{domain}.json").read_bytes())
        if (
            not isinstance(document, dict)
            or set(document) != {"format", "domain", "snapshot", "provenance"}
            or document.get("format") != "kn.semantic.reviewed-seeds.v1"
            or document.get("domain") != domain
        ):
            raise ValueError("invalid reviewed seed envelope")
        validate_model(document["snapshot"])
        _validate_provenance(document)
        snapshots.append(document["snapshot"])
    snapshot = merge_snapshots(snapshots)
    validate_model(snapshot)
    return snapshot


def load_reviewed_seeds(connection: Connection) -> None:
    """Idempotent inserts; a changed row requires a rebuild, never a silent overwrite."""
    if not connection.in_transaction():
        raise ValueError("reviewed seed loading requires a caller-owned transaction")
    snapshot = reviewed_snapshot()
    model = metadata(semantic_contract())
    with connection.begin_nested():
        for name, rows in snapshot.items():
            _load_table(connection, model.tables["semantic." + name], rows)
        _check_references(connection, model)


def _load_table(connection: Connection, table: Table, rows: list[dict[str, Any]]) -> None:
    # Explicit nulls give all parameter sets one shape; the semantic contract has no SQL defaults.
    native = [{column.name: row.get(column.name) for column in table.columns} for row in rows]
    if not native:
        return
    connection.execute(insert(table).on_conflict_do_nothing(), native)
    keys = [column.name for column in table.primary_key.columns]
    stored = {
        tuple(row[key] for key in keys): dict(row)
        for row in connection.execute(select(table)).mappings()
    }
    for row in native:
        if stored.get(tuple(row[key] for key in keys)) != row:
            raise ValueError("reviewed seed conflicts with stored content; rebuild required")


def _check_references(connection: Connection, model: MetaData) -> None:
    """Drain deferred seed triggers so another rebuild can drop these tables in this transaction."""
    names = tuple(
        sorted(
            str(reference.name)
            for table in model.tables.values()
            for reference in table.foreign_key_constraints
        )
    )
    connection.execute(SetConstraints("semantic", names, deferred=False))
    connection.execute(SetConstraints("semantic", names, deferred=True))


def _validate_provenance(document: dict[str, Any]) -> None:
    provenance = document["provenance"]
    identifiers = {row["id"] for row in document["snapshot"].get("terms", [])}
    if not isinstance(provenance, dict) or set(provenance) != identifiers:
        raise ValueError("every reviewed term requires provenance")
    for sources in provenance.values():
        if not isinstance(sources, list) or not sources:
            raise ValueError("reviewed provenance requires source rows")
        for source in sources:
            _validate_locator(source)


def _validate_locator(source: object) -> None:
    if not isinstance(source, dict):
        raise ValueError("reviewed provenance requires a source locator object")
    for key in ("file", "sheet", "workbook_file", "sha256", "workbook_sha256"):
        required = source.get(key)
        if not isinstance(required, str) or not required.strip():
            raise ValueError("reviewed provenance requires source file, digest, sheet, and row")
    for key in ("sha256", "workbook_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", source[key]) is None:
            raise ValueError("reviewed provenance requires SHA-256 digests")
    if type(source.get("row")) is not int or source["row"] < 1:
        raise ValueError("reviewed provenance requires a positive row locator")
    path = Path(source["file"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("reviewed provenance file must be repository-relative")
