import hashlib
import json
from pathlib import Path

import pytest

DOMAINS = Path(__file__).resolve().parents[2] / "domains"


@pytest.mark.parametrize("manifest", sorted(DOMAINS.glob("*/seeds/proposals/*/workbook.json")))
def test_proposal_sheets_match_manifest(manifest: Path) -> None:
    sheets = json.loads(manifest.read_bytes())["sheets"]
    expected_files = {sheet["file"] for sheet in sheets}
    assert len(expected_files) == len(sheets)
    assert expected_files == {p.name for p in manifest.parent.glob("*.json") if p != manifest}
    for sheet in sheets:
        path = manifest.parent / sheet["file"]
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == sheet["sha256"], path
        data = json.loads(payload)
        assert data["status"] == "unreviewed_proposal", path
        if sheet["format"] == "kn.seed-proposal.notes":
            assert len(data["rows"]) == sheet["row_count"], path
        else:
            assert len(data["records"]) == sheet["record_count"], path
