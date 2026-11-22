"""Semantic contracts reject malformed rows, keys, endpoints and hierarchies."""

import copy

import pytest

from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.semantic import Snapshot, validate_model
from kn.semantic.structure import semantic_contract
from tests.semantic.conftest import REFERENCES


def test_complete_model_is_valid_unchanged_and_order_independent(model: Snapshot) -> None:
    original = copy.deepcopy(model)
    validate_model(model, REFERENCES)
    assert model == original
    permuted = {name: list(reversed(rows)) for name, rows in reversed(list(model.items()))}
    validate_model(permuted, REFERENCES)
    validate_model({})


def test_semantic_contract_compiles_every_dataset_and_reference() -> None:
    contract = semantic_contract()
    output = artifacts(contract)
    assert contract.contract_id == "kn.core.semantic"
    assert contract.schema == "semantic"
    assert len(contract.tables) == 18
    assert len(output) == 7 + 3 * len(contract.tables)
    assert "DEFERRABLE INITIALLY DEFERRED" in output["postgresql/schema.sql"]
    assert "Literal['draft', 'active', 'deprecated', 'replaced']" in output["pydantic/models.py"]


@pytest.mark.parametrize("table", ["concepts", "entity_classes"])
def test_primary_hierarchy_cycles_are_rejected(model: Snapshot, table: str) -> None:
    first, second = model[table][:2]
    first["parent_id"] = second["id"]
    second["parent_id"] = first["id"]
    with pytest.raises(ContractError, match=r"semantic\.cycle"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "table,column",
    [
        ("concepts", "parent_id"),
        ("relation_types", "source_class_id"),
        ("relation_types", "target_class_id"),
    ],
)
def test_missing_parents_and_unknown_relation_endpoints_fail(
    model: Snapshot, table: str, column: str
) -> None:
    model[table][0][column] = "space.demo.unknown"
    with pytest.raises(ContractError, match=r"semantic\.endpoint"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize("collision", ["id", "code", "subtype", "namespace"])
def test_identifier_collisions_are_rejected(model: Snapshot, collision: str) -> None:
    if collision == "id":
        model["terms"][1]["id"] = model["terms"][0]["id"]
    elif collision == "code":
        model["terms"][1]["code"] = model["terms"][0]["code"]
    elif collision == "subtype":
        model["relation_types"][0]["id"] = model["entity_classes"][0]["id"]
    else:
        model["terms"][0]["id"] = model["namespaces"][0]["id"]
        # Keep the foreign keys valid so the global namespace collision is exercised.
        model["entity_classes"][0]["id"] = model["terms"][0]["id"]
        model["relation_types"][0]["source_class_id"] = model["terms"][0]["id"]
        for row in model["labels"]:
            if row["term_id"] == "space.demo.Organization":
                row["term_id"] = model["terms"][0]["id"]
    with pytest.raises(ContractError, match=r"semantic\.(unique|kind)"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "dataset,column,value,rule",
    [
        ("namespaces", "id", "demo", "endpoint"),
        ("namespaces", "domain", "Space", "identifier"),
        ("namespaces", "code", "other", "identifier"),
        ("terms", "code", "unqualified code", "identifier"),
        ("terms", "status", "unknown", "enum"),
        ("terms", "status", "replaced", "status"),
        ("terms", "kind", "rubric", "kind"),
        ("terms", "definition", "  ", "empty"),
        ("entity_classes", "extra", "unknown", "additionalProperties"),
    ],
)
def test_invalid_row_fixtures(
    model: Snapshot, dataset: str, column: str, value: str, rule: str
) -> None:
    model[dataset][0][column] = value
    with pytest.raises(ContractError, match=rule):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "bad", [{"unknown": []}, {"terms": {}}, {"terms": [None]}, {"terms": [{}]}]
)
def test_malformed_datasets_fail_with_located_diagnostics(bad: dict) -> None:
    with pytest.raises(ContractError) as error:
        validate_model(bad)
    assert error.value.path.startswith("$")
    assert error.value.rule


def test_missing_subtype_is_rejected(model: Snapshot) -> None:
    model["rubrics"].clear()
    model["rubric_criteria"].clear()
    with pytest.raises(ContractError, match=r"semantic\.kind"):
        validate_model(model, REFERENCES)


def test_deep_primary_hierarchy_does_not_recurse(model: Snapshot) -> None:
    parent = model["concepts"][0]["id"]
    for index in range(1500):
        ident = f"space.demo.deep{index}"
        model["terms"].append(
            dict(
                id=ident,
                namespace_id="space.demo",
                code=f"deep{index}",
                kind="concept",
                status="active",
                definition="Deep hierarchy fixture",
            )
        )
        model["concepts"].append(dict(id=ident, scheme_id="space.demo.scheme", parent_id=parent))
        model["labels"].extend(
            dict(term_id=ident, locale=locale, label=f"deep {index} {locale}")
            for locale in ("en", "uk")
        )
        parent = ident
    validate_model(model, REFERENCES)


def test_codes_and_labels_can_repeat_across_domain_namespaces(model: Snapshot) -> None:
    import json

    other = json.loads(json.dumps(model).replace("space.demo", "microelectronics.demo"))
    other["namespaces"][0]["domain"] = "microelectronics"
    for dataset, rows in other.items():
        model[dataset].extend(rows)
    validate_model(model, REFERENCES)
    assert model["concepts"][0]["id"] != other["concepts"][0]["id"]


@pytest.mark.parametrize("column", ["parent_id", "replacement_id"])
def test_concept_primary_links_cannot_cross_schemes(model: Snapshot, column: str) -> None:
    import json

    other = json.loads(json.dumps(model).replace("space.demo", "microelectronics.demo"))
    other["namespaces"][0]["domain"] = "microelectronics"
    for dataset, rows in other.items():
        model[dataset].extend(rows)
    model["concepts"][0][column] = "microelectronics.demo.001"
    if column == "replacement_id":
        next(row for row in model["terms"] if row["id"] == "space.demo.001")["status"] = "replaced"
    with pytest.raises(ContractError, match=r"semantic\.scheme"):
        validate_model(model, REFERENCES)


def test_extra_subtype_cannot_reclassify_an_existing_term(model: Snapshot) -> None:
    model["entity_classes"].append(dict(id="space.demo.scheme", parent_id=None))
    with pytest.raises(ContractError, match=r"semantic\.kind"):
        validate_model(model, REFERENCES)
