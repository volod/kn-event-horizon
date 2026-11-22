"""Located cycle diagnostics and IRI-safe publication URIs."""

import copy

import pytest

from kn.contracts.diagnostics import ContractError
from kn.semantic import validate_model
from kn.semantic.structure import Snapshot
from tests.semantic.conftest import REFERENCES


def test_a_cycle_names_a_concept_row_on_the_cycle(model: Snapshot) -> None:
    data = copy.deepcopy(model)
    concepts = {row["id"]: row for row in data["concepts"]}
    concepts["space.demo.001"]["parent_id"] = "space.demo.002"
    with pytest.raises(ContractError) as error:
        validate_model(data, REFERENCES)
    assert error.value.rule == "semantic.cycle"
    assert error.value.path in {"$/concepts/0/parent_id", "$/concepts/1/parent_id"}


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.org/a b.pdf",
        'https://example.org/"quoted"',
        "https://example.org/<x>",
        "https://example.org/a\\b",
        "https://example.org/{x}",
    ],
)
def test_a_publication_uri_must_be_a_valid_iri(model: Snapshot, uri: str) -> None:
    data = copy.deepcopy(model)
    data["concept_schemes"][0]["source_uri"] = uri
    with pytest.raises(ContractError, match="uri"):
        validate_model(data, REFERENCES)


def test_a_publication_uri_may_use_percent_encoding_and_non_ascii(model: Snapshot) -> None:
    data = copy.deepcopy(model)
    data["concept_schemes"][0]["source_uri"] = (
        "https://example.org/a%20b/\u0434\u043e\u043a.pdf?x=1#p"
    )
    validate_model(data, REFERENCES)
