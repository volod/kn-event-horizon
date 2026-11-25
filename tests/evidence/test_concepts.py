"""A claim citing a deprecated or replaced concept is reported with the concept's successor."""

import copy
import json
from pathlib import Path

import pytest

from kn.evidence.concepts import concept_uses, retired_concept_claims
from kn.evidence.records import CLAIM_REFERENCE
from kn.semantic import validate_model
from kn.semantic.structure import Snapshot
from tests.evidence.fixtures import claim, orbit_claim
from tests.semantic.conftest import REFERENCES
from tests.semantic.test_lifecycle import retire

MODEL = Path(__file__).parents[1] / "semantic" / "fixtures" / "model.json"


@pytest.fixture
def model() -> Snapshot:
    return json.loads(MODEL.read_text())


def test_claims_cite_concepts_only_through_their_concept_value() -> None:
    cited = orbit_claim()
    rows = [cited.row(), claim().row(), cited.row()]
    assert concept_uses(rows) == {"space.demo.002": [CLAIM_REFERENCE + cited.key]}


def test_a_claim_citing_a_replaced_concept_is_an_external_use_with_its_successor(
    model: Snapshot,
) -> None:
    data = retire(model, "space.demo.002", "replaced", "space.demo.003")
    validate_model(data, REFERENCES)
    cited = orbit_claim()
    report = retired_concept_claims(data, [cited.row(), orbit_claim("space.demo.003").row()])
    (finding,) = [item for item in report if item["concept_id"] == "space.demo.002"]
    assert finding["status"] == "replaced"
    assert (finding["successor_id"], finding["successor_status"]) == ("space.demo.003", "active")
    assert {"kind": "external", "id": CLAIM_REFERENCE + cited.key} in finding["uses"]
    assert all(item["concept_id"] != "space.demo.003" for item in report)


def test_a_claim_citing_a_deprecated_concept_is_reported_without_successor(
    model: Snapshot,
) -> None:
    data = retire(copy.deepcopy(model), "space.demo.003", "deprecated")
    validate_model(data, REFERENCES)
    cited = orbit_claim("space.demo.003")
    (finding,) = retired_concept_claims(data, [cited.row()])
    assert finding["successor_id"] is None
    assert {"kind": "external", "id": CLAIM_REFERENCE + cited.key} in finding["uses"]


def test_claims_citing_active_or_unknown_concepts_are_not_reported(model: Snapshot) -> None:
    rows = [orbit_claim().row(), orbit_claim("space.unknown.concept").row()]
    assert retired_concept_claims(model, rows) == []
