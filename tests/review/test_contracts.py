"""Published wire schemas and ODCS coverage metadata match the shared protocol."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError
from kn.review.model import Decision, Request, Stamp, Target
from tests.contracts.test_compiler import compiler_document, write_document
from tests.review.test_protocol import event

SCHEMAS = Path(__file__).resolve().parents[2] / "contracts" / "core" / "evidence"


@pytest.mark.parametrize("model", [Target, Request, Decision, Stamp])
def test_published_wire_schema_is_current_and_valid(model) -> None:
    schema = json.loads((SCHEMAS / f"{model.__name__.lower()}.schema.json").read_text())
    assert schema == model.model_json_schema()
    Draft202012Validator.check_schema(schema)
    if model is Decision:
        Draft202012Validator(schema).validate(event().model_dump(mode="json"))


@pytest.mark.parametrize("mutation", ["unknown", "column_name", "missing_value", "bad_strategy"])
def test_coverage_refuses_unknown_ids_and_unsupported_encodings(tmp_path, mutation) -> None:
    data = compiler_document()
    table = data["schema"][0]
    field_id = next(
        item["value"]
        for item in table["properties"][0]["customProperties"]
        if item["property"] == "kn.fieldId"
    )
    coverage = {
        "strategy": "external",
        "resolver": "contract-v1",
        "recordFields": [field_id],
        "fieldContexts": {field_id: [field_id]},
    }
    if mutation == "unknown":
        coverage["recordFields"] = ["unknown"]
    elif mutation == "column_name":
        coverage["recordFields"] = [table["properties"][0]["name"]]
    elif mutation == "missing_value":
        coverage["fieldContexts"] = {field_id: ["unknown"]}
    else:
        coverage["strategy"] = "implicit"
    table["customProperties"] = [{"property": "kn.humanVerification", "value": coverage}]
    with pytest.raises(ContractError):
        load_contract(write_document(tmp_path, data))
