"""Table null rules compile to one meaning in SQL, JSON Schema and the Pydantic models."""

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import jsonschema
import pydantic
import pytest
from sqlalchemy.dialects import postgresql

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.model import Contract
from kn.contracts.sqlalchemy import metadata
from tests.contracts.test_compiler import write_document
from tests.contracts.test_physical import contract_with, field

RULES = [
    {"name": "value_or_reason", "rule": "exactly_one", "fields": ["value", "reason"]},
    {"name": "unit_pair", "rule": "all_or_none", "fields": ["unit", "rule"]},
]
VALID = [
    {"id": 1, "value": 3},
    {"id": 1, "reason": 5},
    {"id": 1, "value": 3, "unit": 7, "rule": 8},
    {"id": 1, "reason": 5, "unit": None, "rule": None},
]
INVALID = [
    {"id": 1},
    {"id": 1, "value": 3, "reason": 5},
    {"id": 1, "value": None, "reason": None},
    {"id": 1, "value": 3, "unit": 7},
    {"id": 1, "reason": 5, "rule": 8},
]


def _document(rules: list[dict[str, Any]], *, required: str | None = None) -> dict:
    fields = [field("id", key=True), *(field(name) for name in ("value", "reason", "unit", "rule"))]
    if required:
        next(node for node in fields if node["name"] == required)["required"] = True
    data = contract_with(("facts", fields))
    data["schema"][0]["customProperties"] = [{"property": "kn.presence", "value": rules}]
    return data


def _contract(tmp_path: Path, rules: list[dict[str, Any]] = RULES, **options: str) -> Contract:
    return load_contract(write_document(tmp_path, _document(rules, **options)))


def _models(contract: Contract) -> ModuleType:
    module = ModuleType("generated_presence")
    exec(artifacts(contract)["pydantic/models.py"], module.__dict__)
    return module


def test_rules_compile_to_named_postgresql_checks(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    table = metadata(contract).tables["space.facts"]
    checks = {
        str(check.name): str(
            check.sqltext.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        for check in table.constraints
        if check.name and str(check.name).startswith("ck_")
    }
    assert checks == {
        "ck_facts_value_or_reason_presence": "num_nonnulls(space.facts.value, space.facts.reason)"
        " = 1",
        "ck_facts_unit_pair_presence": "num_nonnulls(space.facts.unit, space.facts.rule) IN (0, 2)",
    }
    result = artifacts(contract)
    assert "ck_facts_value_or_reason_presence" in result["postgresql/schema.sql"]
    names = json.loads(result["postgresql/metadata.json"])["tables"]["facts"]["checks"]
    assert {item["name"] for item in names} == set(checks)


@pytest.mark.parametrize("row", VALID)
def test_valid_rows_pass_every_wire_validator(tmp_path: Path, row: dict) -> None:
    contract = _contract(tmp_path)
    schema = json.loads(artifacts(contract)["jsonschema/facts.json"])
    jsonschema.validate(row, schema)
    _models(contract).Facts.model_validate(row)


@pytest.mark.parametrize("row", INVALID)
def test_invalid_rows_fail_every_wire_validator(tmp_path: Path, row: dict) -> None:
    contract = _contract(tmp_path)
    schema = json.loads(artifacts(contract)["jsonschema/facts.json"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(row, schema)
    with pytest.raises(pydantic.ValidationError, match="presence rule"):
        _models(contract).Facts.model_validate(row)


def test_tables_without_rules_keep_their_generated_artifacts(tmp_path: Path) -> None:
    data = _document(RULES)
    data["schema"][0]["customProperties"] = []
    result = artifacts(load_contract(write_document(tmp_path, data)))
    assert "allOf" not in json.loads(result["jsonschema/facts.json"])
    assert "_kn_presence" not in result["pydantic/models.py"]


@pytest.mark.parametrize(
    ("rules", "options"),
    [
        ([{"name": "bad", "rule": "exactly_one", "fields": ["value", "missing"]}], {}),
        (
            [{"name": "bad", "rule": "exactly_one", "fields": ["value", "reason"]}],
            {"required": "value"},
        ),
        ([RULES[0], {**RULES[1], "name": RULES[0]["name"]}], {}),
        (
            [
                {
                    "name": "bad",
                    "rule": "exactly_one",
                    "fields": ["value", "space.example.facts.value"],
                }
            ],
            {},
        ),
    ],
    ids=["unknown-field", "required-field", "duplicate-name", "repeated-column"],
)
def test_ambiguous_rules_are_refused(tmp_path: Path, rules: list, options: dict) -> None:
    with pytest.raises(ContractError):
        _contract(tmp_path, rules, **options)


@pytest.mark.parametrize(
    "rule",
    [
        {"name": "one", "rule": "exactly_one", "fields": ["value"]},
        {"name": "Bad-Name", "rule": "exactly_one", "fields": ["value", "reason"]},
        {"name": "x", "rule": "at_most_one", "fields": ["value", "reason"]},
    ],
)
def test_lint_bounds_the_rule_shape(tmp_path: Path, rule: dict) -> None:
    with pytest.raises(ContractError):
        _contract(tmp_path, [rule])
