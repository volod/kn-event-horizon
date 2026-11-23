"""Changed seed content or unsupported official claims require a new publication review."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from kn.semantic.seed_model import encoded
from kn.semantic.seeds import RESOURCES, reviewed_snapshot
from kn.semantic.verification import content_digest, review_schemes

SCHEME = "space.esa_tt_4_1.scheme"
TERM = "space.esa_tt_4_1.TD01.A"
CHANGES = ["label", "uk_label", "code", "parent", "status", "removed", "added"]


def changed_space(change: str) -> dict:
    """The reviewed space snapshot with one edit inside the verified ESA technology scheme."""
    data = json.loads((RESOURCES / "space.json").read_bytes())["snapshot"]
    if change == "uk_label":
        data["labels"].append(
            {
                "term_id": TERM,
                "locale": "uk",
                "label": "Reviewed translation",
                "review_reference": "fixture:terminology",
            }
        )
    elif change == "label":
        next(row for row in data["labels"] if row["term_id"] == TERM and row["locale"] == "en")[
            "label"
        ] += " changed"
    elif change in {"code", "status"}:
        next(row for row in data["terms"] if row["id"] == TERM)[change] = "changed"
    elif change == "parent":
        next(row for row in data["concepts"] if row["id"] == TERM)["parent_id"] = (
            "space.esa_tt_4_1.TD02"
        )
    elif change == "removed":
        data["concepts"] = [row for row in data["concepts"] if row["id"] != TERM]
    else:
        data["concepts"].append({"id": "space.esa_tt_4_1.NEW", "scheme_id": SCHEME})
    return data


@pytest.mark.parametrize("change", CHANGES)
def test_content_edits_require_review_before_loading(change: str) -> None:
    data = changed_space(change)
    before = copy.deepcopy(data)
    with pytest.raises(ValueError, match="stale"):
        review_schemes(data, RESOURCES / "space-verification.json", "space", check=True)
    assert data == before  # Loading never applies metadata.


@pytest.mark.parametrize("change", CHANGES)
def test_content_edits_stage_unverified_until_a_new_comparison(change: str) -> None:
    data = changed_space(change)
    stale = review_schemes(data, RESOURCES / "space-verification.json", "space")
    assert [item["scheme_id"] for item in stale] == [SCHEME]
    scheme = next(row for row in data["concept_schemes"] if row["id"] == SCHEME)
    assert scheme["verification_state"] == "unverified"
    assert "new comparison" in scheme["verification_reason"]


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra", "domain", "format", "digest"])
def test_review_manifest_integrity(tmp_path: Path, damage: str) -> None:
    report = json.loads((RESOURCES / "space-verification.json").read_bytes())
    if damage == "missing":
        report["schemes"].pop()
    elif damage == "duplicate":
        report["schemes"].append(report["schemes"][0])
    elif damage == "extra":
        report["schemes"][0]["unknown"] = True
    elif damage == "domain":
        report["domain"] = "other"
    elif damage == "format":
        report["format"] = "unknown"
    else:
        report["schemes"][0]["source_sha256"] = "invalid"
    path = tmp_path / "review.json"
    path.write_bytes(encoded(report))
    data = json.loads((RESOURCES / "space.json").read_bytes())["snapshot"]
    with pytest.raises(ValueError):
        review_schemes(data, path, "space")


@pytest.mark.parametrize(
    "damage", ["mismatch", "access_limit", "local_extension", "local", "missing_evidence", "origin"]
)
def test_unsupported_verified_claims_are_refused(tmp_path: Path, damage: str) -> None:
    data = json.loads((RESOURCES / "space.json").read_bytes())["snapshot"]
    report = json.loads((RESOURCES / "space-verification.json").read_bytes())
    review = next(row for row in report["schemes"] if row["scheme_id"] == "space.euspa_2026.scheme")
    if damage in {"mismatch", "access_limit", "local_extension"}:
        review["findings"].append(
            {"kind": damage, "locator": "fixture", "detail": "Fixture finding"}
        )
    elif damage == "missing_evidence":
        review["source_sha256"] = None
    else:
        review["origin"] = "kb_extension"
        if damage == "local":
            next(row for row in data["concept_schemes"] if row["id"] == review["scheme_id"])[
                "origin"
            ] = review["origin"]
    path = tmp_path / "review.json"
    path.write_bytes(encoded(report))
    with pytest.raises(ValueError):
        review_schemes(data, path, "space")


def test_packaged_loader_refuses_metadata_drift_and_missing_review(tmp_path: Path) -> None:
    shutil.copytree(RESOURCES, tmp_path / "resources")
    directory = tmp_path / "resources"
    path = directory / "space.json"
    doc = json.loads(path.read_bytes())
    doc["snapshot"]["concept_schemes"][0]["verification_reason"] = "Unsupported claim"
    path.write_bytes(encoded(doc))
    with pytest.raises(ValueError, match="metadata differs"):
        reviewed_snapshot(directory)
    path.write_bytes((RESOURCES / "space.json").read_bytes())
    (directory / "space-verification.json").unlink()
    with pytest.raises(FileNotFoundError):
        reviewed_snapshot(directory)


def test_digest_is_order_independent_and_review_does_not_change_concepts() -> None:
    data = json.loads((RESOURCES / "space.json").read_bytes())["snapshot"]
    before = copy.deepcopy(data)
    for rows in data.values():
        rows.reverse()
    assert content_digest(data, "space.esa_tt_4_1.scheme") == content_digest(
        before, "space.esa_tt_4_1.scheme"
    )
    review_schemes(data, RESOURCES / "space-verification.json", "space", check=True)
    assert all(
        sorted(rows, key=encoded) == sorted(before[name], key=encoded)
        for name, rows in data.items()
    )
