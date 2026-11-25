"""Update policies and ranking criteria use the extension's vocabularies and canonical digests."""

from pathlib import Path
from typing import Any, get_args

import pydantic
import pytest

from kn.contracts import load_contract
from kn.contracts.schemas import pinned_schemas
from kn.evidence import vocabulary
from kn.evidence.policy import (
    EVIDENCE_ORDER,
    RANK_ORDER,
    Criteria,
    PriorityCriterion,
    UpdatePolicy,
    field_policy,
)
from kn.evidence.ranking import RankTable
from tests.contracts.test_references import EXAMPLES, semantic_fixture


def _extension(member: str) -> Any:
    _, registry = pinned_schemas()
    schema = registry["properties"]["kn.updatePolicy"]["properties"][member]
    return tuple(schema.get("items", schema)["enum"])


@pytest.mark.parametrize(
    ("member", "values"),
    [
        ("mode", get_args(vocabulary.Mode.__value__)),
        ("minimumSourceRank", RANK_ORDER),
        ("minimumEvidenceClass", EVIDENCE_ORDER),
        ("priorityCriteria", get_args(PriorityCriterion.__value__)),
    ],
)
def test_orders_and_vocabularies_match_the_update_policy_extension(
    member: str, values: tuple[str, ...]
) -> None:
    assert _extension(member) == values


def test_rank_and_evidence_orders_are_highest_first() -> None:
    assert RANK_ORDER[0] == "owner_entered" and RANK_ORDER[-1] == "unranked"
    assert EVIDENCE_ORDER[0] == "primary" and EVIDENCE_ORDER[-1] == "extracted_candidate"


def test_a_field_policy_is_read_with_a_stable_digest(tmp_path: Path) -> None:
    path, refs = semantic_fixture(tmp_path, "kn.updatePolicy")
    contract = load_contract(path, references=refs)
    field_ids = [field.field_id for field in contract.tables[0].fields]
    declared = field_policy(contract, field_ids[1])
    assert declared == UpdatePolicy.model_validate(EXAMPLES["kn.updatePolicy"])
    assert declared is not None and declared.mode == "priority"
    assert declared.digest == UpdatePolicy.model_validate(EXAMPLES["kn.updatePolicy"]).digest
    changed = UpdatePolicy.model_validate({**EXAMPLES["kn.updatePolicy"], "freshnessSeconds": 1})
    assert changed.digest != declared.digest
    assert field_policy(contract, field_ids[0]) is None
    with pytest.raises(ValueError, match="unknown stable field"):
        field_policy(contract, "space.example.absent")


@pytest.mark.parametrize(
    "change",
    [{"mode": "silently_replace"}, {"valueTolerance": -1}, {"unexpected": True}],
)
def test_invalid_policies_are_refused(change: dict[str, Any]) -> None:
    with pytest.raises(pydantic.ValidationError):
        UpdatePolicy.model_validate({**EXAMPLES["kn.updatePolicy"], **change})


def test_criteria_need_a_ranked_source_and_an_exact_time() -> None:
    with pytest.raises(pydantic.ValidationError, match="UTC offset"):
        Criteria(
            source_id="space:x",
            source_rank="first_party",
            evidence_class="primary",
            data_time="2026-01-01T00:00:00",
        )
    with pytest.raises(pydantic.ValidationError):
        Criteria(source_id="space:x", source_rank="vendor", evidence_class="primary")


def test_high_impact_is_optional_and_part_of_the_digest() -> None:
    declared = UpdatePolicy.model_validate(EXAMPLES["kn.updatePolicy"])
    assert declared.high_impact is False
    marked = UpdatePolicy.model_validate({**EXAMPLES["kn.updatePolicy"], "highImpact": True})
    assert marked.high_impact and marked.digest != declared.digest


def test_the_reviewed_rank_table_ranks_unlisted_sources_unranked() -> None:
    table = RankTable.read()
    assert table.overrides == ()
    assert table.rank("space:row-4", "space.launch.date") == "unranked"
