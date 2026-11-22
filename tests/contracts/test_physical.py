"""Generated PostgreSQL names are unique, fit the server limit, and agree in every artifact."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from tests.contracts.test_compiler import compiler_document, write_document

POSTGRES_NAME_BYTES = 63
LONG_TABLE = "t" * 48
LONG_FIELD = "f" * 48


def field(name: str, logical: str = "integer", *, key: bool = False, **extensions: Any) -> dict:
    node: dict = {
        "name": name,
        "logicalType": logical,
        "customProperties": [{"property": "kn.fieldId", "value": f"example.{name}"}],
    }
    if key:
        node["required"] = node["primaryKey"] = True
    node["customProperties"] += [
        {"property": f"kn.{extension}", "value": value} for extension, value in extensions.items()
    ]
    return node


def contract_with(*tables: tuple[str, list[dict]]) -> dict:
    data = compiler_document()
    data["schema"] = [
        {"name": name, "logicalType": "object", "physicalType": "table", "properties": fields}
        for name, fields in tables
    ]
    for table in data["schema"]:
        for node in table["properties"]:
            node["customProperties"][0]["value"] = f"example.{table['name']}.{node['name']}"
    return data


def constraint_names(ddl: str) -> list[str]:
    return re.findall(r"CONSTRAINT (\S+)", ddl)


def reference(*fields: str) -> dict:
    return {"table": "parent", "fields": list(fields), "targetFields": ["a", "b", "c"]}


def test_references_sharing_leading_columns_get_distinct_names(tmp_path: Path) -> None:
    parent = [field(name, key=True) for name in ("a", "b", "c")]
    child = [
        field("k", key=True),
        field("a2"),
        field("b2"),
        field("c2", foreignKey=reference("a2", "b2", "c2")),
        field("d2", foreignKey=reference("a2", "b2", "d2")),
    ]
    data = contract_with(("parent", parent), ("child", child))
    contract = load_contract(write_document(tmp_path, data))
    result = artifacts(contract)
    names = re.findall(r"ADD CONSTRAINT (\S+) FOREIGN KEY", result["postgresql/schema.sql"])
    assert len(names) == len(set(names)) == 2
    metadata = json.loads(result["postgresql/metadata.json"])
    assert sorted(key["name"] for key in metadata["tables"]["child"]["foreign_keys"]) == sorted(
        names
    )


def test_long_derived_names_fit_postgresql_and_agree_with_metadata(tmp_path: Path) -> None:
    fields = [
        field("id", key=True),
        field(LONG_FIELD, "string", enum=["x", "y"]),
        field("g" * 47, "string", partialDate=True),
    ]
    contract = load_contract(write_document(tmp_path, contract_with((LONG_TABLE, fields))))
    result = artifacts(contract)
    rendered = constraint_names(result["postgresql/schema.sql"])
    assert rendered and all(len(name.encode()) <= POSTGRES_NAME_BYTES for name in rendered)
    checks = json.loads(result["postgresql/metadata.json"])["tables"][LONG_TABLE]["checks"]
    assert {check["name"] for check in checks} <= set(rendered)
    assert len({check["name"] for check in checks}) == len(checks) == 2


def test_table_named_like_another_primary_key_index_is_refused(tmp_path: Path) -> None:
    data = contract_with(("foo", [field("id", key=True)]), ("pk_foo", [field("id", key=True)]))
    with pytest.raises(ContractError, match="name"):
        load_contract(write_document(tmp_path, data))


def test_references_that_derive_one_constraint_name_are_refused(tmp_path: Path) -> None:
    # Both references would be named fk_child_a_b: (a, b) to parent and (a_b) to single.
    composite = {"table": "parent", "fields": ["a", "b"], "targetFields": ["a", "b"]}
    single = {"table": "single", "fields": ["a_b"], "targetFields": ["id"]}
    data = contract_with(
        ("parent", [field("a", key=True), field("b", key=True)]),
        ("child", [field("k", key=True), field("a"), field("b", foreignKey=composite)]),
        ("single", [field("id", key=True)]),
    )
    data["schema"][1]["properties"].append(field("a_b", foreignKey=single))
    with pytest.raises(ContractError, match="name"):
        load_contract(write_document(tmp_path, data))


def test_one_identifier_rule_serves_the_loader_registry_and_physical_names() -> None:
    from kn.contracts import loader, physical
    from kn.contracts.schemas import pinned_schemas

    _, registry = pinned_schemas()
    assert registry["properties"]["kn.storageSchema"]["pattern"] == physical.IDENTIFIER.pattern
    assert loader.IDENTIFIER is physical.IDENTIFIER
