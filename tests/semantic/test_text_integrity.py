"""Vocabulary text keeps source language, real definitions and explicit translation review."""

import json

import pytest
from rdflib import Literal
from rdflib.namespace import SKOS

from kn.contracts.diagnostics import ContractError
from kn.semantic import Snapshot, validate_model
from kn.semantic.oecd_reference import publication_references
from kn.semantic.seeds import RESOURCES, reviewed_snapshot
from kn.semantic.skos import skos_graph
from tests.semantic.conftest import REFERENCES


def test_reviewed_source_labels_are_not_manufactured_translations() -> None:
    snapshot = reviewed_snapshot()
    for dataset in ("labels", "namespace_labels", "alternative_labels"):
        assert {row["locale"] for row in snapshot.get(dataset, [])} == {"en"}


def test_reviewed_definitions_are_prose_or_absent() -> None:
    snapshot = reviewed_snapshot()
    for row in snapshot["terms"]:
        if row["kind"] == "concept":
            assert row.get("definition") is None
        elif row.get("definition"):
            with pytest.raises(json.JSONDecodeError):
                json.loads(row["definition"])


def test_all_schemes_export_only_real_language_tags_and_definitions() -> None:
    snapshot = reviewed_snapshot()
    for scheme in snapshot["concept_schemes"]:
        graph = skos_graph(snapshot, scheme["id"], references=publication_references(RESOURCES))
        assert not any(
            isinstance(value, Literal) and value.language == "uk" for value in graph.objects()
        )
        for definition in graph.objects(None, SKOS.definition):
            with pytest.raises(json.JSONDecodeError):
                json.loads(str(definition))


def test_missing_translation_is_valid_but_missing_preferred_label_is_not(model: Snapshot) -> None:
    for dataset in ("labels", "namespace_labels", "alternative_labels"):
        model[dataset] = [row for row in model[dataset] if row["locale"] != "uk"]
    validate_model(model, REFERENCES)
    model["labels"] = [row for row in model["labels"] if row["term_id"] != "space.demo.003"]
    with pytest.raises(ContractError, match=r"semantic\.locale"):
        validate_model(model, REFERENCES)


def test_absent_definition_is_valid_and_json_is_rejected(model: Snapshot) -> None:
    model["terms"][4]["definition"] = None
    validate_model(model, REFERENCES)
    model["terms"][4]["definition"] = '{"spreadsheet": "metadata"}'
    with pytest.raises(ContractError, match=r"semantic\.definition"):
        validate_model(model, REFERENCES)


def test_identical_translation_needs_explicit_review(model: Snapshot) -> None:
    label = next(
        row
        for row in model["labels"]
        if row["term_id"] == "space.demo.001" and row["locale"] == "uk"
    )
    label["label"] = "001 en"
    with pytest.raises(ContractError, match=r"semantic\.translation"):
        validate_model(model, REFERENCES)
    label["review_reference"] = "fixture:terminology-review"
    with pytest.raises(ContractError, match=r"semantic\.translation"):
        validate_model(model, REFERENCES)
    label["reviewed_identical"] = True
    validate_model(model, REFERENCES)
