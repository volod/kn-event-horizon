"""Compile-profile refusals name their rule and a JSON Pointer into the supplied document."""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from kn import cli
from kn.contracts.schemas import SATCOM
from tests.contracts.test_compiler import compiler_document

type Mutation = Callable[[dict[str, Any]], None]


def table(data: dict[str, Any]) -> dict[str, Any]:
    return data["schema"][0]


def key(data: dict[str, Any]) -> dict[str, Any]:
    return table(data)["properties"][0]


def add_field(data: dict[str, Any], logical: str, *extensions: tuple[str, Any]) -> None:
    """Add a field; a kn.fieldId among the extensions replaces its unique default."""
    values = {"kn.fieldId": "example.extra", **dict(extensions)}
    if values["kn.fieldId"] == "duplicate":
        values["kn.fieldId"] = "space.example.id"
    node: dict[str, Any] = {
        "name": "extra",
        "logicalType": logical,
        "customProperties": [{"property": name, "value": value} for name, value in values.items()],
    }
    table(data)["properties"].append(node)


MUTATIONS: dict[str, Mutation] = {
    "nullable_key": lambda data: key(data).update(required=False),
    "missing_key": lambda data: key(data).update(primaryKey=False),
    "missing_field_id": lambda data: key(data).update(customProperties=[]),
    "unsupported_type": lambda data: key(data).update(logicalType="time"),
    "unsupported_key": lambda data: key(data).update(quality=[]),
    "unsupported_table": lambda data: table(data).update(physicalType="view"),
    "long_table": lambda data: table(data).update(name="x" * 49),
    "upper_field": lambda data: key(data).update(name="Id"),
    "duplicate_table": lambda data: data["schema"].append(copy.deepcopy(table(data))),
    "duplicate_field_id": lambda data: add_field(data, "string", ("kn.fieldId", "duplicate")),
    "scale_over_precision": lambda data: add_field(data, "number", ("kn.precision", 10)),
    "enum_on_integer": lambda data: add_field(data, "integer", ("kn.enum", ["a"])),
    "precision_on_string": lambda data: add_field(data, "string", ("kn.precision", 4)),
    "unknown_index_field": lambda data: table(data)["customProperties"][1]["value"][0].update(
        fields=["missing"]
    ),
}


def pointer(document: Any, path: str) -> Any:
    assert path.startswith("$")
    node = document
    for part in filter(None, path[1:].split("/")):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def compile_json(tmp_path: Path, data: dict[str, Any], caplog: pytest.LogCaptureFixture) -> dict:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data))
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"entityClass": {"space.satellite": {}}}))
    arguments = ["contract", "compile", str(path), "--references", str(references), "--json"]
    caplog.clear()
    assert cli.main([*arguments, "--output", str(tmp_path / "out")]) == 1
    return json.loads(caplog.records[-1].message)["error"]


@pytest.mark.parametrize("name", MUTATIONS)
def test_profile_refusals_are_located_contract_diagnostics(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, name: str
) -> None:
    data = compiler_document()
    MUTATIONS[name](data)
    error = compile_json(tmp_path, data, caplog)
    assert error["code"] == "E_CONTRACT", error
    assert error["rule"] and error["hint"]
    # Every planted fault is on a table, field, or extension, so the root is not a location.
    assert error["path"].startswith("$/schema/") and pointer(data, error["path"]) is not None
    assert not (tmp_path / "out").exists()


def test_reference_diagnostics_point_at_document_indexes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    data = json.loads(SATCOM.read_text(encoding="ascii"))
    field = data["schema"][4]["properties"][1]
    field["customProperties"].append(
        {
            "property": "kn.foreignKey",
            "value": {"table": "absent", "fields": [field["name"]], "targetFields": ["id"]},
        }
    )
    error = compile_json(tmp_path, data, caplog)
    assert error["rule"] == "reference"
    assert pointer(data, error["path"]) is field
