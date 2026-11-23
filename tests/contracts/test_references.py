"""Each semantic family resolves offline and preserves its declared intent in exports."""

import copy
import json
from pathlib import Path

import pytest

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.schemas import pinned_schemas
from tests.contracts.test_compiler import compiler_document, write_document

EXAMPLES = json.loads((Path(__file__).with_name("fixtures") / "extensions.json").read_text())
CATALOG = {
    "entityClass": {"space.satellite": {}, "core.organization": {}},
    "relation": {
        "space.operates": {"sourceClass": "core.organization", "targetClass": "space.satellite"}
    },
    "matchProfile": {"space.satellite-match": {}},
    "normalizer": {"casefold": {}},
    "comparator": {"exact": {}},
    "mapping": {"inventree.part": {}, "satellite-projection": {}},
    "unit": {"g": {}, "kg": {}},
    "quantityType": {"mass": {}},
    "conversionRule": {"gram-to-kilogram": {}},
    "comparisonProfile": {"space.mass-comparison": {}},
    "licensePolicy": {"owner-reviewed": {}},
    "vocabulary": {"space.orbit-regime": {"values": ["active", "retired"]}},
    "dataset": {"space.source-satellites": {}},
}
SEMANTIC = [
    name
    for name in EXAMPLES
    if name
    not in {
        "kn.fieldId",
        "kn.storageSchema",
        "kn.sourceProfile",
        "kn.csv",
        "kn.foreignKey",
        "kn.enum",
        "kn.partialDate",
        "kn.precision",
        "kn.scale",
        "kn.index",
        "kn.partition",
    }
]


def semantic_fixture(tmp_path: Path, name: str) -> tuple[Path, Path]:
    data = compiler_document()
    table = data["schema"][0]
    table["customProperties"] = []
    field = table["properties"][1]
    field["customProperties"] = field["customProperties"][:1]
    value = copy.deepcopy(EXAMPLES[name])
    if name == "kn.identity":
        value["sourceVersionField"] = "id"
        value["attributes"][0]["fieldId"] = "space.example.coverage"
    if name == "kn.temporalProfile":
        value = {
            "recordedTime": "space.example.id",
            "asOf": "knowledge_time",
            "nullSemantics": "unknown",
        }
    if name == "kn.evidence":
        value["referenceFields"] = ["space.example.id"]
    if name == "kn.humanVerification":
        value["recordFields"] = ["space.example.id"]
        value["fieldContexts"] = {"space.example.id": ["space.example.id"]}
    if name == "kn.i18nKey":
        value = "cli.contract_help"
    _, registry = pinned_schemas()
    scope = registry["properties"][name]["x-kn-scopes"][0]
    node = {"contract": data, "table": table, "field": field}[scope]
    node.setdefault("customProperties", []).append({"property": name, "value": value})
    refs = tmp_path / "references.json"
    refs.write_text(json.dumps(CATALOG))
    return write_document(tmp_path, data), refs


@pytest.mark.parametrize("name", SEMANTIC)
def test_every_semantic_extension_compiles_and_is_retained(tmp_path: Path, name: str) -> None:
    path, refs = semantic_fixture(tmp_path, name)
    result = artifacts(load_contract(path, references=refs))
    assert name in result["contract.json"]
    if name == "kn.enumRef":
        assert "active" in result["postgresql/schema.sql"]
        assert "Literal" in result["pydantic/models.py"]


@pytest.mark.parametrize("kind", CATALOG)
def test_each_external_reference_kind_must_resolve(tmp_path: Path, kind: str) -> None:
    for name in SEMANTIC:
        path, refs = semantic_fixture(tmp_path, name)
        reduced = copy.deepcopy(CATALOG)
        reduced[kind] = {}
        refs.write_text(json.dumps(reduced))
        try:
            load_contract(path, references=refs)
        except ContractError as error:
            assert error.rule == "reference"
            break
    else:
        pytest.fail(f"no extension checked {kind}")


@pytest.mark.parametrize("name", ["kn.temporalProfile", "kn.identity", "kn.evidence"])
def test_local_reference_must_name_existing_field(tmp_path: Path, name: str) -> None:
    path, refs = semantic_fixture(tmp_path, name)
    data = json.loads(path.read_text())
    # Remove the id target; other primary key errors must not hide reference resolution.
    data["schema"][0]["properties"] = data["schema"][0]["properties"][1:]
    path.write_text(json.dumps(data))
    with pytest.raises(ContractError, match="reference"):
        load_contract(path, references=refs)


def test_relation_endpoint_and_catalog_shape_fail_closed(tmp_path: Path) -> None:
    path, refs = semantic_fixture(tmp_path, "kn.relation")
    catalog = copy.deepcopy(CATALOG)
    catalog["relation"]["space.operates"]["targetClass"] = "wrong"
    refs.write_text(json.dumps(catalog))
    with pytest.raises(ContractError, match="endpoint"):
        load_contract(path, references=refs)
    refs.write_text('{"typo": {}}')
    with pytest.raises(ContractError, match="reference kinds"):
        load_contract(path, references=refs)
    refs.write_text('{"entityClass": []}')
    with pytest.raises(ContractError, match="symbol IDs"):
        load_contract(path, references=refs)
