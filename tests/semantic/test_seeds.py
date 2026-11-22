"""End-to-end reconciliation, reviewed content, and the boundary around proposal examples."""

from collections import Counter
from pathlib import Path

import pytest

from kn.semantic import validate_model
from kn.semantic.proposals import DOMAINS, read_proposals
from kn.semantic.seeds import FIXTURE_PATH, import_proposals, reconcile, reviewed_snapshot

ROOT = Path(__file__).resolve().parents[2]


def test_every_proposal_row_is_reconciled_and_provenance_is_durable() -> None:
    documents, report, fixtures = reconcile(ROOT)
    proposals = read_proposals(ROOT)

    def locators(rows: list[dict]) -> set[tuple[str, int]]:
        return {(r["provenance"]["file"], r["provenance"]["row"]) for r in rows}

    assert len(report) == len(proposals) == 1173
    assert len(locators(report)) == len(report)
    assert {r["status"] for r in report} <= {"accepted", "duplicate", "needs_mapping", "rejected"}
    assert all(r["reason"] for r in report)
    for row in report:
        source = row["provenance"]
        assert len(source["sha256"]) == len(source["workbook_sha256"]) == 64
        assert source["sheet"] and source["workbook_file"] and source["row"] > 0
        assert not Path(source["file"]).is_absolute()
    assert len(fixtures) == 27
    assert all(
        row["status"] == "rejected"
        for row in report
        if (row["provenance"]["file"], row["provenance"]["row"]) in locators(fixtures)
    )
    for document in documents.values():
        snapshot = document["snapshot"]
        assert set(document["provenance"]) == {term["id"] for term in snapshot["terms"]}
        assert not snapshot.get("entity_tags")
        assert all(
            scheme["verification_state"] == "unverified" for scheme in snapshot["concept_schemes"]
        )


def test_conversion_runs_are_identical_and_match_reviewed_files(tmp_path: Path) -> None:
    first = import_proposals(ROOT, tmp_path, check=True)
    second = import_proposals(ROOT, tmp_path, check=True)
    assert first["report"] != second["report"]
    left, right = Path(str(first["report"])).parent, Path(str(second["report"])).parent
    assert {p.name: p.read_bytes() for p in left.iterdir()} == {
        p.name: p.read_bytes() for p in right.iterdir()
    }
    snapshot = reviewed_snapshot()
    validate_model(snapshot)
    assert len(snapshot["terms"]) == 726
    assert (ROOT / FIXTURE_PATH).read_bytes() == (left / "fixtures.json").read_bytes()


def test_qualified_codes_structural_parents_and_normalized_inverse_relations() -> None:
    snapshot = reviewed_snapshot()
    terms = {row["id"]: row for row in snapshot["terms"]}
    for domain in DOMAINS:
        assert terms[f"{domain}.services.S01"]["code"] == "S01"
    assert "gdelt.applications.APP.SCOUT" in terms
    assert "microelectronics.applications.APP.31" in terms
    assert terms["gdelt.cameo_v2.0251"]["code"] == "0251"
    concepts = {row["id"]: row for row in snapshot["concepts"]}
    assert concepts["space.esa_gpt_1_1.II.J"]["parent_id"] == "space.esa_gpt_1_1.II"
    relations = {row["id"]: row for row in snapshot["relation_types"]}
    relation = relations["space.relations.contains_spacecraft.Constellation_Fleet.Spacecraft"]
    assert relation["source_class_id"] == "space.ontology.Constellation_Fleet"
    assert relation["target_class_id"] == "space.ontology.Spacecraft"
    labels = [r for r in snapshot["labels"] if r["term_id"] == relation["id"]]
    assert all(r["inverse_label"].startswith("member_of_constellation") for r in labels)
    assert all(".member_of_constellation." not in key for key in relations)
    assert {
        "space.kb_extension.SpacecraftModel",
        "space.kb_extension.EvidenceClaim",
    } <= terms.keys()
    counts = Counter(row["id"] for row in snapshot["terms"])
    assert all(count == 1 for count in counts.values())


def test_stale_reviewed_content_leaves_report_for_review(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing proposal workbook"):
        # A non-repository destination must not be used as a proposal root.
        import_proposals(tmp_path, tmp_path)
