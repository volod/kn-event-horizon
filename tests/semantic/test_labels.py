"""Preferred and alternative labels preserve bilingual text and reject ambiguity."""

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import Snapshot, validate_model
from tests.semantic.conftest import REFERENCES


def test_duplicate_preferred_labels_in_a_scheme_are_rejected(model: Snapshot) -> None:
    labels = [
        row
        for row in model["labels"]
        if row["locale"] == "en" and row["term_id"] in {"space.demo.001", "space.demo.002"}
    ]
    labels[0]["label"] = "  D\u00e9mo   one  "
    labels[1]["label"] = "DE\u0301MO ONE"
    with pytest.raises(ContractError, match=r"semantic\.label"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize("dataset", ["labels", "namespace_labels"])
def test_named_terms_and_namespaces_need_a_preferred_label(model: Snapshot, dataset: str) -> None:
    model[dataset] = (
        [row for row in model[dataset] if row["term_id"] != "space.demo.003"]
        if dataset == "labels"
        else []
    )
    with pytest.raises(ContractError, match=r"semantic\.locale"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize("dataset", ["labels", "namespace_labels", "alternative_labels"])
def test_invalid_language_tags_are_rejected(model: Snapshot, dataset: str) -> None:
    model[dataset][0]["locale"] = "english!"
    with pytest.raises(ContractError, match=r"semantic\.locale"):
        validate_model(model, REFERENCES)


def test_duplicate_preferred_locale_is_rejected(model: Snapshot) -> None:
    model["labels"].append({**model["labels"][0], "label": "Different preferred label"})
    with pytest.raises(ContractError, match=r"semantic\.unique"):
        validate_model(model, REFERENCES)


@pytest.mark.parametrize(
    "case", ["preferred", "duplicate", "missing_locale", "inverse_missing", "inverse_on_class"]
)
def test_invalid_alternative_and_inverse_labels_fail(model: Snapshot, case: str) -> None:
    alternative = model["alternative_labels"][0]
    if case == "preferred":
        alternative["label"] = "001 en"
    elif case == "duplicate":
        model["alternative_labels"].append({**alternative, "label": "FIRST CONCEPT"})
    elif case == "missing_locale":
        alternative["locale"] = "fr"
    elif case == "inverse_missing":
        next(row for row in model["labels"] if row["term_id"] == "space.demo.operates")[
            "inverse_label"
        ] = None
    else:
        model["labels"][0]["inverse_label"] = "inverse"
    with pytest.raises(ContractError, match=r"semantic\.(label|inverse)"):
        validate_model(model, REFERENCES)


def test_additional_locale_and_original_unicode_are_preserved(model: Snapshot) -> None:
    label = "\u0421\u0443\u043f\u0443\u0442\u043d\u0438\u043a"
    row = next(
        row
        for row in model["labels"]
        if row["term_id"] == "space.demo.Satellite" and row["locale"] == "uk"
    )
    row["label"] = label
    model["labels"].append(dict(term_id="space.demo.Satellite", locale="fr", label="Satellite"))
    validate_model(model, REFERENCES)
    assert row["label"] == label


def test_language_tag_case_does_not_allow_two_preferred_labels(model: Snapshot) -> None:
    model["labels"].extend(
        [
            dict(term_id="space.demo.Satellite", locale="en-GB", label="Satellite GB"),
            dict(term_id="space.demo.Satellite", locale="en-gb", label="Other satellite GB"),
        ]
    )
    with pytest.raises(ContractError, match=r"semantic\.locale"):
        validate_model(model, REFERENCES)
