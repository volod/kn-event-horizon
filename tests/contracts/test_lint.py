"""Pinned standard, every KN extension family, and actionable offline lint failures."""

import copy
import json
import logging
import shutil
from pathlib import Path

import pytest
import yaml

from kn import cli
from kn.contracts import load_contract, schemas
from kn.contracts.diagnostics import ContractError
from kn.contracts.lint import lint_contract
from kn.contracts.loader import SATCOM

FIXTURES = Path(__file__).with_name("fixtures")
EXAMPLES = json.loads((FIXTURES / "extensions.json").read_text())


def write_contract(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data), encoding="ascii")
    return path


def test_yaml_and_json_have_the_same_validated_metadata(tmp_path: Path) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    assert lint_contract(write_contract(tmp_path, data)) == data
    assert lint_contract()["id"] == load_contract().contract_id


@pytest.mark.parametrize("name", EXAMPLES)
def test_each_registered_extension_accepts_its_documented_value_and_rejects_bad_types(
    tmp_path: Path, name: str
) -> None:
    _, registry = schemas.pinned_schemas()
    assert set(EXAMPLES) == set(registry["properties"])
    scope = registry["properties"][name]["x-kn-scopes"][0]
    data = lint_contract(FIXTURES / "valid.yaml")
    nodes = {
        "contract": data,
        "table": data["schema"][0],
        "field": data["schema"][0]["properties"][0],
    }
    nodes[scope]["customProperties"] = [{"property": name, "value": EXAMPLES[name]}]
    assert lint_contract(write_contract(tmp_path, data)) == data
    nodes[scope]["customProperties"][0]["value"] = None
    with pytest.raises(ContractError, match="value"):
        lint_contract(write_contract(tmp_path, data))


@pytest.mark.parametrize(
    ("fixture", "rule", "location", "hint"),
    [
        ("unknown-extension.yaml", "extension", "/property", "registered kn.*"),
        ("missing-required.yaml", "required", "$", "id"),
        ("bad-type.yaml", "type", "/value", "string"),
    ],
)
@pytest.mark.parametrize("locale", ["en", "uk"])
def test_invalid_fixtures_report_paths_and_rules_without_input_values(
    fixture: str,
    rule: str,
    location: str,
    hint: str,
    locale: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    args = ["contract", "lint", str(FIXTURES / fixture), "--locale", locale]
    assert cli.main(args) == 1
    assert rule in caplog.records[-1].message and hint in caplog.records[-1].message
    assert cli.main([*args, "--json"]) == 1
    error = json.loads(caplog.records[-1].message)["error"]
    assert error["code"] == "E_CONTRACT"
    assert error["rule"] == rule and location in error["path"]
    assert hint in error["hint"]


@pytest.mark.parametrize(
    "mutation", ["duplicate", "misplaced", "nested", "old_version", "top_level"]
)
def test_closed_extensions_and_exact_standard_version(tmp_path: Path, mutation: str) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    field = data["schema"][0]["properties"][0]
    if mutation == "duplicate":
        field["customProperties"] *= 2
    elif mutation == "misplaced":
        data["customProperties"] = copy.deepcopy(field["customProperties"])
    elif mutation == "nested":
        field["properties"] = [copy.deepcopy(field)]
        field["properties"][0]["customProperties"][0]["property"] = "kn.typo"
    elif mutation == "old_version":
        data["apiVersion"] = "v3.0.2"
    elif mutation == "top_level":
        data["kn.entityClass"] = "satellite"
    with pytest.raises(ContractError):
        lint_contract(write_contract(tmp_path, data))


def test_lint_acceptance_does_not_silently_expand_compiler_support(tmp_path: Path) -> None:
    data = json.loads(SATCOM.read_text())
    data["schema"][0]["customProperties"].append(
        {"property": "kn.entityClass", "value": "space.satellite"}
    )
    path = write_contract(tmp_path, data)
    lint_contract(path)
    with pytest.raises(ValueError, match="extension"):
        load_contract(path)


def test_update_policy_accepts_the_specified_accumulate_mode(tmp_path: Path) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    policy = copy.deepcopy(EXAMPLES["kn.updatePolicy"])
    policy["mode"] = "accumulate"
    data["schema"][0]["properties"][0]["customProperties"] = [
        {"property": "kn.updatePolicy", "value": policy}
    ]
    assert lint_contract(write_contract(tmp_path, data)) == data


@pytest.mark.parametrize("name", schemas.SCHEMA_FILES)
@pytest.mark.parametrize("mutation", ["tamper", "missing_pin"])
def test_each_schema_is_mandatory_and_checksum_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, mutation: str
) -> None:
    resources = tmp_path / "resources"
    shutil.copytree(schemas.RESOURCES, resources)
    if mutation == "tamper":
        (resources / name).write_text("{}")
    else:
        pins = json.loads((resources / "pins.json").read_text())
        del pins[name]
        (resources / "pins.json").write_text(json.dumps(pins))
    monkeypatch.setattr(schemas, "RESOURCES", resources)
    with pytest.raises(ContractError, match="checksum"):
        lint_contract(FIXTURES / "valid.yaml")


def test_cli_validates_supplied_yaml_and_does_not_leak_rejected_values(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["contract", "lint", str(FIXTURES / "valid.yaml"), "--json"]) == 0
    assert json.loads(caplog.records[-1].message)["contract_id"] == "space.satellites"
    data = lint_contract(FIXTURES / "valid.yaml")
    data["schema"][0]["properties"][0]["customProperties"][0]["value"] = {
        "password": "private-secret"
    }
    path = write_contract(tmp_path, data)
    assert cli.main(["contract", "lint", str(path), "--json"]) == 1
    assert "private-secret" not in caplog.text


def test_closed_objects_reject_unrecognized_members(tmp_path: Path) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    data["customProperties"] = [
        {
            "property": "kn.interchange",
            "value": {"exposed": True, "compatibility": "stable", "typo": 1},
        }
    ]
    with pytest.raises(ContractError, match="additionalProperties"):
        lint_contract(write_contract(tmp_path, data))


@pytest.mark.parametrize(
    "name", [name for name, value in EXAMPLES.items() if isinstance(value, dict)]
)
def test_structured_families_require_their_declared_members(tmp_path: Path, name: str) -> None:
    _, registry = schemas.pinned_schemas()
    scope = registry["properties"][name]["x-kn-scopes"][0]
    data = lint_contract(FIXTURES / "valid.yaml")
    nodes = {
        "contract": data,
        "table": data["schema"][0],
        "field": data["schema"][0]["properties"][0],
    }
    nodes[scope]["customProperties"] = [{"property": name, "value": {}}]
    with pytest.raises(ContractError, match="required"):
        lint_contract(write_contract(tmp_path, data))


@pytest.mark.parametrize(
    ("name", "member", "value"),
    [
        ("kn.spatialProfile", "srid", 3857),
        ("kn.updatePolicy", "mode", "silently_replace"),
        ("kn.updatePolicy", "valueTolerance", -1),
        ("kn.interchange", "compatibility", "unknown"),
        ("kn.partition", "fields", ["id", "id"]),
    ],
)
def test_family_constraints_reject_invalid_values(
    tmp_path: Path, name: str, member: str, value: object
) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    _, registry = schemas.pinned_schemas()
    scope = registry["properties"][name]["x-kn-scopes"][0]
    nodes = {
        "contract": data,
        "table": data["schema"][0],
        "field": data["schema"][0]["properties"][0],
    }
    invalid = copy.deepcopy(EXAMPLES[name])
    invalid[member] = value
    nodes[scope]["customProperties"] = [{"property": name, "value": invalid}]
    with pytest.raises(ContractError):
        lint_contract(write_contract(tmp_path, data))


def test_yaml_timestamp_is_a_string(tmp_path: Path) -> None:
    data = lint_contract(FIXTURES / "valid.yaml")
    data["contractCreatedTs"] = "2026-11-22T12:00:00Z"
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(data).replace("'2026-11-22T12:00:00Z'", "2026-11-22T12:00:00Z"))
    assert lint_contract(path)["contractCreatedTs"] == data["contractCreatedTs"]
