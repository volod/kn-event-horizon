"""Refuse conversion drift and invalid reviewed seeds before loading content."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import seeds
from kn.semantic.proposals import read_proposals
from kn.semantic.seed_model import encoded
from kn.semantic.seeds import RESOURCES, import_proposals, reconcile, reviewed_snapshot
from tests.semantic.test_seeds import ROOT


@pytest.fixture
def proposal_root(tmp_path: Path) -> Path:
    for domain in ("space", "gdelt", "microelectronics"):
        source = ROOT / "domains" / domain / "seeds/proposals"
        shutil.copytree(source, tmp_path / "domains" / domain / "seeds/proposals")
    return tmp_path


@pytest.mark.parametrize(
    "damage", ["digest", "count", "source", "duplicate_row", "extra_file", "path"]
)
def test_proposal_manifest_failures(proposal_root: Path, damage: str) -> None:
    directory = proposal_root / "domains/space/seeds/proposals/ontology_and_tags_v1"
    manifest = directory / "workbook.json"
    document = json.loads(manifest.read_bytes())
    sheet = document["sheets"][1]
    path = directory / sheet["file"]
    data = json.loads(path.read_bytes())
    if damage == "count":
        sheet["record_count"] += 1
    elif damage == "source":
        data["source"]["sha256"] = "0" * 64
    elif damage == "duplicate_row":
        data["records"][1]["source_row"] = data["records"][0]["source_row"]
    elif damage == "extra_file":
        (directory / "extra.json").write_text("{}")
    elif damage == "path":
        sheet["file"] = "../elsewhere.json"
    path.write_bytes(encoded(data))
    if damage != "digest":
        sheet["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_bytes(encoded(document))
    with pytest.raises(ValueError):
        read_proposals(proposal_root)


@pytest.mark.parametrize(
    "damage", ["cycle", "parent", "label", "identifier", "endpoint", "envelope", "provenance"]
)
def test_reviewed_seed_integrity(tmp_path: Path, damage: str) -> None:
    shutil.copytree(RESOURCES, tmp_path / "resources")
    directory = tmp_path / "resources"
    path = directory / "space.json"
    document = json.loads(path.read_bytes())
    data = document["snapshot"]
    if damage == "cycle":
        data["concepts"][0]["parent_id"] = data["concepts"][0]["id"]
    elif damage == "parent":
        data["concepts"][0]["parent_id"] = "space.esa_gpt_1_1.MISSING"
    elif damage == "label":
        data["labels"][1] = data["labels"][0]
    elif damage == "identifier":
        data["terms"][0]["id"] = data["namespaces"][0]["id"]
    elif damage == "endpoint":
        data["relation_types"][0]["source_class_id"] = "space.ontology.MISSING"
    elif damage == "provenance":
        document["provenance"] = {}
    else:
        document["domain"] = "other"
    path.write_bytes(encoded(document))
    with pytest.raises((ValueError, ContractError)):
        reviewed_snapshot(directory)


def test_identifier_stability_when_proposals_are_reordered(monkeypatch: pytest.MonkeyPatch) -> None:
    before, *_ = reconcile(ROOT)
    proposals = read_proposals(ROOT)
    monkeypatch.setattr(seeds, "read_proposals", lambda _: list(reversed(proposals)))
    after, *_ = reconcile(ROOT)
    for domain in before:
        assert {r["id"] for r in before[domain]["snapshot"]["terms"]} == {
            r["id"] for r in after[domain]["snapshot"]["terms"]
        }


def test_reviewed_drift_preserves_staged_report(proposal_root: Path, tmp_path: Path) -> None:
    (proposal_root / "domains/space/seeds/semantic.json").write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        import_proposals(proposal_root, tmp_path / "artifacts", check=True)
    assert len(list((tmp_path / "artifacts/seed-import").glob("*/reconciliation.json"))) == 1


def test_unknown_sheet_stays_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    proposals = read_proposals(ROOT)
    extra = replace(proposals[0], sheet="01_unknown", workbook="new_workbook")
    monkeypatch.setattr(seeds, "read_proposals", lambda _: [*proposals, extra])
    _, report, *_ = reconcile(ROOT)
    assert report[-1]["status"] == "needs_mapping"
    assert report[-1]["term_ids"] == []


def test_esa_domain_only_rows_do_not_create_null_subdomains() -> None:
    snapshot = reviewed_snapshot()
    assert "space.esa_tt_4_1.TD25" in {row["id"] for row in snapshot["concepts"]}
    assert all(".None" not in row["id"] for row in snapshot["terms"])
    fixtures = json.loads((ROOT / seeds.FIXTURE_PATH).read_bytes())
    templates = [row for row in fixtures if row["formulas_not_evaluated"]]
    assert len(templates) == 2
    assert all("runtime_days" in row["formulas_not_evaluated"] for row in templates)


@pytest.mark.parametrize("damage", ["digest", "row", "path", "missing", "type", "empty_sources"])
def test_reviewed_provenance_refuses_bad_locators(tmp_path: Path, damage: str) -> None:
    shutil.copytree(RESOURCES, tmp_path / "resources")
    directory = tmp_path / "resources"
    path = directory / "space.json"
    document = json.loads(path.read_bytes())
    sources = next(iter(document["provenance"].values()))
    if damage == "empty_sources":
        sources.clear()
    elif damage == "type":
        sources[0] = 42
    elif damage == "digest":
        sources[0]["sha256"] = "not-a-sha256"
    elif damage == "row":
        sources[0]["row"] = -1
    elif damage == "path":
        sources[0]["file"] = "../outside"
    else:
        del sources[0]["sheet"]
    path.write_bytes(encoded(document))
    with pytest.raises(ValueError, match="provenance"):
        reviewed_snapshot(directory)
