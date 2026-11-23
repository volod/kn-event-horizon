"""The text cleanup preserves publication outcomes, provenance and explicit review rules."""

import json
from pathlib import Path

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import Snapshot, validate_model
from kn.semantic.proposals import read_proposals
from kn.semantic.seed_provenance import validate_provenance
from kn.semantic.seeds import RESOURCES
from tests.semantic.conftest import REFERENCES


def test_all_publication_comparisons_are_unchanged_under_new_digests() -> None:
    before = json.loads(
        (Path(__file__).parent / "fixtures/text_revision_reviews.json").read_bytes()
    )
    current = {
        row["scheme_id"]: row
        for path in RESOURCES.glob("*-verification.json")
        for row in json.loads(path.read_bytes())["schemes"]
    }
    assert len(before) == len(current) == 16
    for previous in before:
        review = current[previous["scheme_id"]]
        assert review["content_sha256"] != previous["content_sha256"]
        assert review["text_revision"]["previous_content_sha256"] == previous["content_sha256"]
        assert review["text_revision"]["comparison_unchanged"] is True
        assert Path(review["text_revision"]["record"]).is_file()
        assert {key: review.get(key) for key in previous if key != "content_sha256"} == {
            key: value for key, value in previous.items() if key != "content_sha256"
        }


def test_provenance_retains_exact_original_columns_and_formulas() -> None:
    proposals = {(row.provenance["file"], row.row): row for row in read_proposals(Path.cwd())}
    for domain in ("space", "gdelt", "microelectronics"):
        document = json.loads((RESOURCES / f"{domain}.json").read_bytes())
        for sources in document["provenance"].values():
            for source in sources:
                proposal = proposals[source["file"], source["row"]]
                assert source["source_language"] == "en"
                assert source["values"] == proposal.values
                assert source["formulas_not_evaluated"] == proposal.formulas


@pytest.mark.parametrize(
    "damage", ["unreviewed_uk", "missing_english", "source_language", "values"]
)
def test_packaged_proposal_text_requires_original_language_and_review(damage: str) -> None:
    document = json.loads((RESOURCES / "space.json").read_bytes())
    if damage in {"unreviewed_uk", "missing_english"}:
        row = document["snapshot"]["labels"][0]
        document["snapshot"]["labels"].append({**row, "locale": "uk", "label": "Translation"})
        if damage == "missing_english":
            row["locale"] = "fr"
            row["review_reference"] = "fixture:fr"
            document["snapshot"]["labels"][-1]["review_reference"] = "fixture:uk"
    else:
        source = next(iter(document["provenance"].values()))[0]
        source[damage] = None
    with pytest.raises(ValueError):
        validate_provenance(document)


@pytest.mark.parametrize("dataset", ["labels", "namespace_labels", "alternative_labels"])
def test_identical_copy_requires_an_explicit_identity_review(model: Snapshot, dataset: str) -> None:
    english = next(row for row in model[dataset] if row["locale"] == "en")
    key = "namespace_id" if dataset == "namespace_labels" else "term_id"
    model[dataset] = [row for row in model[dataset] if row["locale"] != "uk"]
    copy = {**english, "locale": "uk", "review_reference": "fixture:identical-term"}
    model[dataset].append(copy)
    with pytest.raises(ContractError, match=r"semantic\.translation"):
        validate_model(model, REFERENCES)
    copy["reviewed_identical"] = True
    validate_model(model, REFERENCES)
    assert copy[key] == english[key]


@pytest.mark.parametrize("definition", ["[]", '"metadata"', "123", "null", "true"])
def test_json_is_not_a_prose_definition(model: Snapshot, definition: str) -> None:
    model["terms"][4]["definition"] = definition
    with pytest.raises(ContractError, match=r"semantic\.definition"):
        validate_model(model, REFERENCES)


def test_alternative_cannot_copy_an_english_preferred_label_without_identity_review(
    model: Snapshot,
) -> None:
    model["alternative_labels"].append(
        {"term_id": "space.demo.001", "locale": "uk", "label": "001 en"}
    )
    with pytest.raises(ContractError, match=r"semantic\.translation"):
        validate_model(model, REFERENCES)


def test_deep_json_definition_has_a_structured_diagnostic(model: Snapshot) -> None:
    model["terms"][4]["definition"] = "[" * 2000 + "0" + "]" * 2000
    with pytest.raises(ContractError, match=r"semantic\.definition"):
        validate_model(model, REFERENCES)
