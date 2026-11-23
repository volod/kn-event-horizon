"""Changed proposals stage for review: every added, changed and removed term is reported."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from kn.semantic.seeds import import_proposals
from tests.semantic.test_seed_failures import proposal_root  # noqa: F401 (fixture)
from tests.semantic.test_seeds import ROOT

SPACE = "domains/space/seeds/proposals/ontology_and_tags_v1"


def edit_sheet(root: Path, sheet: str, change: Callable[[list[dict[str, Any]]], None]) -> None:
    """Change one converted sheet and its manifest entry, as a new conversion would."""
    directory = root / SPACE
    path = directory / sheet
    data = json.loads(path.read_bytes())
    rows = data["records"] if "records" in data else data["rows"]
    change(rows)
    payload = json.dumps(data, ensure_ascii=True, indent=2).encode()
    path.write_bytes(payload)
    manifest = json.loads((directory / "workbook.json").read_bytes())
    entry = next(item for item in manifest["sheets"] if item["file"] == sheet)
    entry["sha256"] = hashlib.sha256(payload).hexdigest()
    entry["record_count" if "record_count" in entry else "row_count"] = len(rows)
    (directory / "workbook.json").write_text(json.dumps(manifest, indent=2))


def staged(result: dict[str, object], name: str) -> Any:
    return json.loads((Path(str(result["report"])).parent / name).read_bytes())


def test_a_removed_row_stages_and_reports_the_removed_term(
    proposal_root: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    edit_sheet(proposal_root, "07_service_types.json", lambda rows: rows.pop(0))
    result = import_proposals(proposal_root, tmp_path / "data")
    changes = result["changes"]
    assert isinstance(changes, dict)
    assert "space.services.S01" in changes["space"]["removed"]
    assert changes["gdelt"] == {"added": [], "changed": [], "removed": []}
    report = staged(result, "reconciliation.json")
    assert report["changes"] == changes
    assert [item["scheme_id"] for item in report["stale_reviews"]] == ["space.services.scheme"]
    scheme = next(
        row
        for row in staged(result, "space.json")["snapshot"]["concept_schemes"]
        if row["id"] == "space.services.scheme"
    )
    assert scheme["verification_state"] == "unverified"


def test_a_changed_verified_label_stages_unverified_until_a_new_comparison(
    proposal_root: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    def rename(rows: list[dict[str, Any]]) -> None:
        rows[0]["values"]["technology_subdomain"] += " (renamed)"

    edit_sheet(proposal_root, "05_esa_tech_tags.json", rename)
    result = import_proposals(proposal_root, tmp_path / "data")
    stale = {
        item["scheme_id"]: item for item in staged(result, "reconciliation.json")["stale_reviews"]
    }
    assert "space.esa_tt_4_1.scheme" in stale
    assert len(stale["space.esa_tt_4_1.scheme"]["content_sha256"]) == 64
    scheme = next(
        row
        for row in staged(result, "space.json")["snapshot"]["concept_schemes"]
        if row["id"] == "space.esa_tt_4_1.scheme"
    )
    assert scheme["verification_state"] == "unverified"
    assert "new comparison" in scheme["verification_reason"]
    for domain in ("space", "gdelt", "microelectronics"):
        reviewed = ROOT / "domains" / domain / "seeds/semantic.json"
        (proposal_root / "domains" / domain / "seeds/semantic.json").write_bytes(
            reviewed.read_bytes()
        )
    with pytest.raises(ValueError, match="differs"):
        import_proposals(proposal_root, tmp_path / "data", check=True)


def test_unchanged_proposals_report_no_changes(
    proposal_root: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    result = import_proposals(proposal_root, tmp_path / "data")
    assert all(
        value == {"added": [], "changed": [], "removed": []}
        for value in result["changes"].values()  # type: ignore[union-attr]
    )
    assert staged(result, "reconciliation.json")["stale_reviews"] == []
