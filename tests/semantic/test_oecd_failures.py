"""Source drift, missing evidence and unsupported crosswalks refuse loading before writes."""

import copy
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import validate_model
from kn.semantic.oecd_reference import publication_references, read_reference
from kn.semantic.proposals import read_proposals
from kn.semantic.seed_model import SeedBuilder, encoded
from kn.semantic.seed_oecd import import_oecd, validate_oecd
from kn.semantic.seeds import RESOURCES, reviewed_snapshot


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate_node",
        "missing_node",
        "duplicate_decision",
        "missing_decision",
        "missing_parent",
        "cycle",
        "unknown_target",
        "unpaired_target",
        "source_match",
        "extension_exact",
        "uncovered_source",
    ],
)
def test_invalid_reviewed_reference_is_refused(tmp_path: Path, damage: str) -> None:
    reference = json.loads((RESOURCES / "oecd_2024.json").read_bytes())
    nodes = reference["nodes"]
    decisions = reference["crosswalks"]
    if damage == "duplicate_node":
        nodes[-1] = nodes[0]
    elif damage == "missing_node":
        nodes.pop()
    elif damage == "duplicate_decision":
        decisions[-1] = decisions[0]
    elif damage == "missing_decision":
        decisions.pop()
    elif damage == "missing_parent":
        nodes[0]["parent_code"] = "MISSING"
    elif damage == "cycle":
        nodes[0]["parent_code"] = nodes[0]["code"]
    elif damage == "unknown_target":
        decisions[0]["target_code"] = "MISSING"
    elif damage == "unpaired_target":
        decisions[0]["target_code"] = None
    elif damage == "source_match":
        decisions[0]["mapping_type"] = "analyst_crosswalk"
    elif damage == "extension_exact":
        next(row for row in decisions if row["code"] == "L.MCU.AI")["mapping_type"] = "exactMatch"
    else:
        next(row for row in decisions if row["code"] == "A")["code"] = "X.NEW"
        next(row for row in decisions if row["code"] == "X.NEW")["mapping_type"] = (
            "analyst_crosswalk"
        )
    (tmp_path / "oecd_2024.json").write_bytes(encoded(reference))
    with pytest.raises((ValueError, ContractError)):
        read_reference(tmp_path)


def test_evidence_registry_resolves_actual_review_bytes() -> None:
    snapshot = reviewed_snapshot()
    with pytest.raises(ContractError, match=r"semantic\.endpoint"):
        validate_model(snapshot)
    validate_model(snapshot, publication_references(RESOURCES))
    snapshot["concept_mappings"][0]["evidence_id"] = "urn:sha256:" + "0" * 64
    with pytest.raises(ContractError, match=r"semantic\.endpoint"):
        validate_model(snapshot, publication_references(RESOURCES))


@pytest.mark.parametrize(
    "damage",
    [
        "evidence",
        "target",
        "kind",
        "missing",
        "extra",
        "parent",
        "label",
        "alternative",
        "scheme",
        "product",
    ],
)
def test_unreviewed_snapshot_changes_are_refused(damage: str) -> None:
    data = copy.deepcopy(reviewed_snapshot())
    mapping = data["concept_mappings"][0]
    if damage == "evidence":
        mapping["evidence_id"] = "unregistered"
    elif damage == "target":
        mapping["target_id"] = "microelectronics.oecd_2024.L"
    elif damage == "kind":
        mapping["mapping_type"] = "analyst_crosswalk"
    elif damage == "missing":
        data["concept_mappings"].pop()
    elif damage == "extra":
        data["concept_mappings"].append(
            {**mapping, "id": "microelectronics.oecd_2024_crosswalk.EXTRA"}
        )
    elif damage == "parent":
        next(row for row in data["concepts"] if row["id"] == "microelectronics.oecd_2024.L.CPU")[
            "parent_id"
        ] = "microelectronics.oecd_2024.M"
    elif damage == "label":
        next(row for row in data["labels"] if row["term_id"] == "microelectronics.oecd_2024.L.CPU")[
            "label"
        ] = "Changed"
    elif damage == "alternative":
        data["alternative_labels"].pop()
    elif damage == "scheme":
        next(
            row
            for row in data["concept_schemes"]
            if row["id"] == "microelectronics.oecd_2024.scheme"
        )["source_sha256"] = "0" * 64
    else:
        data["concepts"] = [
            row for row in data["concepts"] if row["id"] != "microelectronics.product_v1.X"
        ]
    with pytest.raises(ValueError):
        validate_oecd(data, RESOURCES)


def test_changed_or_missing_reference_cannot_bless_old_mapping_evidence(tmp_path: Path) -> None:
    shutil.copytree(RESOURCES, tmp_path / "resources")
    resources = tmp_path / "resources"
    path = resources / "oecd_2024.json"
    reference = json.loads(path.read_bytes())
    reference["crosswalks"][0]["reason"] += " Edited review."
    path.write_bytes(encoded(reference))
    with pytest.raises(ContractError, match=r"semantic\.endpoint"):
        reviewed_snapshot(resources)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        reviewed_snapshot(resources)


@pytest.mark.parametrize("damage", ["label", "parent", "origin", "codes"])
def test_proposal_source_disagreement_requires_review(damage: str) -> None:
    proposals = read_proposals(Path(__file__).resolve().parents[2])
    row = next(
        row
        for row in proposals
        if row.domain == "microelectronics"
        and row.sheet == "03_product_classifier"
        and row.values["kb_node"] == "L"
    )
    values = dict(row.values)
    values[
        {"label": "class", "parent": "parent", "origin": "origin", "codes": "kb_node"}[damage]
    ] = "changed"
    changed = [replace(item, values=values) if item is row else item for item in proposals]
    with pytest.raises(ValueError):
        import_oecd(SeedBuilder("microelectronics"), changed, RESOURCES)


@pytest.mark.parametrize(
    "field",
    [
        "publication_uri",
        "publication_sha256",
        "publication_locator",
        "review_file",
        "review_evidence_id",
    ],
)
def test_publication_provenance_must_match_registered_review(tmp_path: Path, field: str) -> None:
    shutil.copytree(RESOURCES, tmp_path / "resources")
    directory = tmp_path / "resources"
    path = directory / "microelectronics.json"
    document = json.loads(path.read_bytes())
    document["provenance"]["microelectronics.oecd_2024.L"][0][field] = "changed"
    path.write_bytes(encoded(document))
    with pytest.raises(ValueError, match="publication provenance"):
        reviewed_snapshot(directory)
