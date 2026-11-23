"""Real source variants use the shared selector and retain language and review provenance."""

from copy import deepcopy

import pytest
from rdflib import Literal
from rdflib.namespace import RDFS, SKOS

from kn.semantic import Snapshot
from kn.semantic.skos import KN, LABEL_SELECTION, skos_graph, term_uri
from kn.semantic.text import select_label
from tests.semantic.conftest import REFERENCES

TERM = "space.demo.001"


def test_missing_translation_reports_english_fallback_without_inventing_a_label(
    model: Snapshot,
) -> None:
    model["labels"] = [row for row in model["labels"] if row["locale"] != "uk"]
    original = deepcopy(model)
    chosen = select_label(model, TERM, "uk")
    assert chosen.variant.language == "en" and chosen.variant.text == "001 en"
    assert chosen.fallback and chosen.is_original
    assert chosen.variant.provenance == f"semantic.labels:{TERM}:en"
    graph = skos_graph(model, "space.demo.scheme", references=REFERENCES)
    selection = LABEL_SELECTION[TERM + ":uk"]
    assert (term_uri(TERM), KN.labelSelection, selection) in graph
    assert (selection, RDFS.label, Literal("001 en", lang="en")) in graph
    assert (selection, KN.selectedLanguage, Literal("en")) in graph
    assert (selection, KN.fallback, Literal(True)) in graph
    assert (term_uri(TERM), SKOS.prefLabel, Literal("001 en", lang="en")) in graph
    assert (term_uri(TERM), SKOS.prefLabel, Literal("001 en", lang="uk")) not in graph
    assert model == original


def test_reviewed_translation_is_selected_with_its_review_reference(model: Snapshot) -> None:
    row = next(row for row in model["labels"] if row["term_id"] == TERM and row["locale"] == "uk")
    row.update(
        label="\u041f\u0435\u0440\u0448\u0435 \u043f\u043e\u043d\u044f\u0442\u0442\u044f",
        review_reference="fixture:reviewed-uk",
    )
    chosen = select_label(model, TERM, "UK")
    assert chosen.variant.text == row["label"]
    assert chosen.variant.provenance == "fixture:reviewed-uk"
    assert not chosen.fallback and not chosen.is_original
    graph = skos_graph(model, "space.demo.scheme", references=REFERENCES)
    assert (LABEL_SELECTION[TERM + ":uk"], KN.fallback, Literal(False)) in graph
    assert (term_uri(TERM), SKOS.prefLabel, Literal(row["label"], lang="uk")) in graph


def test_english_translation_and_other_original_languages_are_preserved() -> None:
    snapshot = {
        "labels": [
            {"term_id": TERM, "locale": "zh", "label": "\u539f\u6587"},
            {
                "term_id": TERM,
                "locale": "en",
                "label": "Original text",
                "review_reference": "fixture:en-review",
            },
        ]
    }
    english = select_label(snapshot, TERM, "uk")
    assert english.variant.language == "en" and english.fallback and not english.is_original
    snapshot["labels"].pop()
    original = select_label(snapshot, TERM, "uk")
    assert original.variant.language == "zh" and original.fallback and original.is_original
    with pytest.raises(ValueError, match="preferred label"):
        select_label(snapshot, "missing", "uk")
    with pytest.raises(ValueError, match="language tag"):
        select_label(snapshot, TERM, "invalid!")
