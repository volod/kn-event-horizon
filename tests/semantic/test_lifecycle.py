"""Deprecated and replaced concepts stay valid, and every remaining use of them is reported."""

import copy

import pytest

from kn.semantic import validate_model
from kn.semantic.lifecycle import lifecycle_report
from kn.semantic.structure import Snapshot
from tests.semantic.conftest import REFERENCES


def retire(model: Snapshot, concept: str, status: str, successor: str | None = None) -> Snapshot:
    data = copy.deepcopy(model)
    next(row for row in data["terms"] if row["id"] == concept)["status"] = status
    next(row for row in data["concepts"] if row["id"] == concept)["replacement_id"] = successor
    return data


def uses(report: list[dict], concept: str) -> list[tuple[str, str]]:
    finding = next(item for item in report if item["concept_id"] == concept)
    return [(use["kind"], use["id"]) for use in finding["uses"]]


def test_an_unchanged_model_reports_nothing(model: Snapshot) -> None:
    assert lifecycle_report(model) == []


@pytest.mark.parametrize(
    ("concept", "expected"),
    [
        ("space.demo.001", [("child", "space.demo.002")]),
        ("space.demo.002", [("mapping", "space.demo.mapping"), ("entity_tag", "space.demo.tag")]),
        ("space.demo.003", [("mapping", "space.demo.mapping")]),
    ],
)
def test_a_deprecated_concept_in_use_is_reported_with_every_use(
    model: Snapshot, concept: str, expected: list[tuple[str, str]]
) -> None:
    data = retire(model, concept, "deprecated")
    validate_model(data, REFERENCES)
    report = lifecycle_report(data)
    assert [item["concept_id"] for item in report] == [concept]
    assert report[0]["status"] == "deprecated" and report[0]["successor_id"] is None
    assert uses(report, concept) == expected


def test_a_replacement_names_its_active_successor(model: Snapshot) -> None:
    data = retire(model, "space.demo.002", "replaced", "space.demo.003")
    validate_model(data, REFERENCES)
    (finding,) = lifecycle_report(data)
    assert finding["successor_id"] == "space.demo.003" and finding["successor_status"] == "active"


def test_a_replacement_chain_ending_at_a_retired_concept_is_reported(model: Snapshot) -> None:
    data = retire(model, "space.demo.002", "replaced", "space.demo.003")
    data = retire(data, "space.demo.003", "deprecated")
    validate_model(data, REFERENCES)
    report = lifecycle_report(data)
    replaced = next(item for item in report if item["concept_id"] == "space.demo.002")
    assert replaced["successor_id"] == "space.demo.003"
    assert replaced["successor_status"] == "deprecated"


def test_uses_owned_by_other_engines_are_reported(model: Snapshot) -> None:
    data = retire(model, "space.demo.003", "deprecated")
    report = lifecycle_report(data, external_uses={"space.demo.003": ("evidence.claim.42",)})
    assert uses(report, "space.demo.003") == [
        ("mapping", "space.demo.mapping"),
        ("external", "evidence.claim.42"),
    ]
    assert lifecycle_report(model, external_uses={"space.demo.003": ("claim",)}) == []
