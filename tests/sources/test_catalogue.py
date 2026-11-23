"""Independently reconcile the reviewed catalogue against the proposal sheets."""

import json
from collections import Counter
from pathlib import Path

import pytest

from kn.contracts.diagnostics import ContractError
from kn.sources.seeds import read_seed, reviewed_catalogue

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHEETS = {
    "space": "data_sources_v1/01_data_sources.json",
    "microelectronics": "data_sources_v1/01_data_sources.json",
    "gdelt": "ontology_and_tags_v1/12_sources_ingestion.json",
}
ACCESS_FIELDS = {
    "space": {"access_format", "api_machine_access", "authentication_cost", "key_limitation"},
    "microelectronics": {"machine_format", "access_conditions", "limit_rule"},
    "gdelt": {"access", "review_status", "limitation"},
}


def test_catalogue_contains_only_unique_unverified_candidates() -> None:
    catalogue = reviewed_catalogue()
    assert Counter(row["domain"] for row in catalogue) == {
        "space": 37,
        "microelectronics": 65,
        "gdelt": 17,
    }
    assert len({row["source_id"] for row in catalogue}) == len(catalogue)
    assert {row["lifecycle_state"] for row in catalogue} == {"candidate"}
    assert {row["access_verification"] for row in catalogue} == {"unverified"}


@pytest.mark.parametrize(("domain", "sheet"), SOURCE_SHEETS.items())
def test_proposal_rows_match_reviewed_seeds(domain: str, sheet: str) -> None:
    folder = ROOT / "domains" / domain / "seeds"
    proposal = json.loads((folder / "proposals" / sheet).read_text(encoding="ascii"))
    reviewed = [row for row in reviewed_catalogue() if row["domain"] == domain]
    assert read_seed(domain, folder / "sources.json") == reviewed
    records = {row["proposal_row"]: row for row in reviewed}
    assert set(records) == {row["source_row"] for row in proposal["records"]}
    for original in proposal["records"]:
        row = records[original["source_row"]]
        values = original["values"]
        local_id = values.get("id") or f"row-{original['source_row']}"
        assert row["source_id"] == f"{domain}:{local_id}"
        assert row["original_id"] == values.get("id")
        assert row["label"] == values["resource"]
        assert row["priority"] == values["priority"]
        assert row["cadence"] == values["cadence"]
        assert json.loads(row["access_notes_json"]) == {
            key: values[key] for key in ACCESS_FIELDS[domain]
        }
        assert json.loads(row["proposal_values_json"]) == values
        assert row["proposal_workbook"] == proposal["source"]["file_name"]
        assert row["proposal_sheet"] == proposal["source"]["sheet_name"]
        assert row["proposal_sha256"] == proposal["source"]["sha256"]


@pytest.mark.parametrize(
    ("change", "rule", "location"),
    [
        ("duplicate", "duplicate", "/records/1"),
        ("incorrect-id", "sourceId", "/records/0/source_id"),
        ("invalid-priority", "sourceValue", "/records/0/values/priority"),
        ("missing-access", "sourceValue", "/records/0/values/access"),
        ("enabled", "extra_forbidden", "/records/0/lifecycle_state"),
        ("empty", "too_short", "/records"),
    ],
)
def test_malformed_seeds_have_a_row_or_field_reason(
    tmp_path: Path, change: str, rule: str, location: str
) -> None:
    path = ROOT / "domains/gdelt/seeds/sources.json"
    document = json.loads(path.read_text(encoding="ascii"))
    row = document["records"][0]
    if change == "duplicate":
        document["records"].insert(1, row)
    elif change == "incorrect-id":
        row["source_id"] = "space:row-5"
    elif change == "invalid-priority":
        row["values"]["priority"] = "P9"
    elif change == "missing-access":
        del row["values"]["access"]
    elif change == "enabled":
        row["lifecycle_state"] = "enabled"
    else:
        document["records"] = []
    target = tmp_path / "sources.json"
    target.write_text(json.dumps(document), encoding="ascii")
    with pytest.raises(ContractError) as error:
        read_seed("gdelt", target)
    assert error.value.rule == rule
    assert error.value.path == f"$/gdelt{location}"
