"""Status, mapping, evidence and comparison-policy failure fixtures."""

import copy

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import ExternalReferences, Snapshot, validate_model
from tests.semantic.conftest import REFERENCES


def test_deprecated_concepts_remain_valid_endpoints_and_replaced_keep_successors(
    model: Snapshot,
) -> None:
    term = next(row for row in model["terms"] if row["id"] == "space.demo.002")
    term["status"] = "deprecated"
    validate_model(model, REFERENCES)
    term["status"] = "replaced"
    model["concepts"][1]["replacement_id"] = "space.demo.003"
    validate_model(model, REFERENCES)


@pytest.mark.parametrize("case", ["missing", "unexpected", "cycle"])
def test_invalid_replacements_and_scheme_links_fail(model: Snapshot, case: str) -> None:
    first = next(row for row in model["terms"] if row["id"] == "space.demo.001")
    if case == "missing":
        first["status"] = "replaced"
    elif case == "unexpected":
        model["concepts"][0]["replacement_id"] = "space.demo.002"
    elif case == "cycle":
        first["status"] = "replaced"
        next(row for row in model["terms"] if row["id"] == "space.demo.002")["status"] = "replaced"
        model["concepts"][0]["replacement_id"] = "space.demo.002"
        model["concepts"][1]["replacement_id"] = "space.demo.001"
    with pytest.raises(ContractError, match=r"semantic\.(replacement|cycle|scheme)"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize("state", ["unreviewed", "official", "mismatch"])
def test_unknown_scheme_verification_states_fail(model: Snapshot, state: str) -> None:
    model["concept_schemes"][0]["verification_state"] = state
    with pytest.raises(ContractError, match="enum"):
        validate_model(model, REFERENCES)


def test_verified_schemes_need_publication_evidence(model: Snapshot) -> None:
    scheme = model["concept_schemes"][0]
    scheme.update(origin="official", verification_state="verified")
    with pytest.raises(ContractError, match=r"semantic\.verification"):
        validate_model(model, REFERENCES)
    scheme.update(
        publisher="Fixture publisher",
        edition="1",
        source_uri="https://example.org/publication",
        source_sha256="a" * 64,
        verification_reason="Compared fixture edition and checksum",
    )
    validate_model(model, REFERENCES)
    assert scheme["origin"] == "official"
    scheme["origin"] = "kb_extension"
    validate_model(model, REFERENCES)
    assert scheme["origin"] == "kb_extension"


@pytest.mark.parametrize(
    "column,value",
    [
        ("source_sha256", "invalid"),
        ("source_uri", "https://user:secret@example.org/x"),
        ("source_uri", "file:///publication"),
        ("source_uri", "https://[invalid"),
    ],
)
def test_invalid_publication_references_fail_without_exposing_values(
    model: Snapshot, column: str, value: str
) -> None:
    model["concept_schemes"][0][column] = value
    with pytest.raises(ContractError, match=r"semantic\.(uri|checksum)") as error:
        validate_model(model, REFERENCES)
    assert value not in str(error.value)


@pytest.mark.parametrize("case", ["self", "duplicate", "reverse", "conflict", "indirect"])
def test_conflicting_mappings_are_rejected(model: Snapshot, case: str) -> None:
    first = model["concept_mappings"][0]
    if case == "self":
        first["target_id"] = first["source_id"]
    else:
        added = {**first, "id": "space.demo.mapping2"}
        if case == "reverse":
            added["source_id"], added["target_id"] = first["target_id"], first["source_id"]
        elif case == "conflict":
            added["mapping_type"] = "exactMatch"
        elif case == "indirect":
            added.update(source_id="space.demo.001", mapping_type="exactMatch")
            extra = {**added, "id": "space.demo.mapping3", "target_id": "space.demo.002"}
            _add_mapping(model, extra)
        _add_mapping(model, added)
    with pytest.raises(ContractError, match=r"semantic\.mapping"):
        validate_model(model, REFERENCES)


def _add_mapping(model: Snapshot, row: dict) -> None:
    term = copy.deepcopy(next(row for row in model["terms"] if row["kind"] == "concept_mapping"))
    term.update(id=row["id"], code=row["id"].rsplit(".", 1)[1])
    model["terms"].append(term)
    model["concept_mappings"].append(row)


def test_analyst_crosswalk_is_separate_and_directional_inverses_conflict(model: Snapshot) -> None:
    mapping = model["concept_mappings"][0]
    _add_mapping(
        model, {**mapping, "id": "space.demo.mapping2", "mapping_type": "analyst_crosswalk"}
    )
    validate_model(model, REFERENCES)
    model["concept_mappings"][0]["mapping_type"] = "broadMatch"
    _add_mapping(
        model,
        {
            **mapping,
            "id": "space.demo.mapping3",
            "source_id": mapping["target_id"],
            "target_id": mapping["source_id"],
            "mapping_type": "narrowMatch",
        },
    )
    with pytest.raises(ContractError, match=r"semantic\.mapping"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "refs",
    [
        ExternalReferences(),
        ExternalReferences(entity_ids=REFERENCES.entity_ids),
        ExternalReferences(evidence_ids=REFERENCES.evidence_ids),
    ],
)
def test_external_entity_and_evidence_endpoints_must_resolve(
    model: Snapshot, refs: ExternalReferences
) -> None:
    with pytest.raises(ContractError, match=r"semantic\.endpoint"):
        validate_model(model, refs)


@pytest.mark.parametrize(
    "start,end,rule",
    [
        ("2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z", "validity"),
        ("2026-03-01T00:00:00Z", "2026-02-01T00:00:00Z", "validity"),
        ("2026-01-01T00:00:00", None, "pattern"),
        ("2026-02-30T00:00:00Z", None, "format"),
    ],
)
def test_invalid_tag_intervals_fail(
    model: Snapshot, start: str, end: str | None, rule: str
) -> None:
    model["entity_tags"][0].update(valid_from=start, valid_to=end)
    with pytest.raises(ContractError, match=rule):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "case", ["attribute_class", "condition_class", "rubric_attribute", "weight"]
)
def test_profiles_and_rubrics_reject_incompatible_attributes(model: Snapshot, case: str) -> None:
    if case == "attribute_class":
        model["attribute_definitions"][0]["entity_class_id"] = "space.demo.Organization"
    elif case == "condition_class":
        model["profile_attributes"].clear()
        model["comparison_profiles"][0]["entity_class_id"] = "space.demo.Organization"
        model["rubric_criteria"].clear()
    elif case == "rubric_attribute":
        model["profile_attributes"].clear()
    else:
        model["rubric_criteria"][0]["weight"] = "0"
    with pytest.raises(ContractError, match=r"semantic\.(profile|rubric)"):
        validate_model(model, REFERENCES)
