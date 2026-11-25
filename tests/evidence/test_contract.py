"""The registered evidence contract, its generated validators and the Python shapes agree."""

import json
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, get_args

import jsonschema
import pydantic
import pytest

from kn.contracts.registry import registered_contracts
from kn.evidence import vocabulary
from kn.evidence.records import Record
from kn.evidence.store import evidence_contract, evidence_tables
from kn.evidence.values import VALUE_COLUMNS
from kn.review.targets import declared_coverage
from tests.evidence.fixtures import claim, one_of_each

GENERATED = Path(__file__).parents[2] / "generated" / "contracts" / "kn.core.evidence"
ENUMS = {
    ("claims", "missing_reason"): vocabulary.MissingReason,
    ("claims", "assertion_type"): vocabulary.AssertionType,
    ("claims", "evidence_class"): vocabulary.EvidenceClass,
    ("claims", "change_kind"): vocabulary.ChangeKind,
    ("claims", "event_precision"): vocabulary.TimePrecision,
    ("evidence_records", "locator_kind"): vocabulary.LocatorKind,
    ("text_translations", "method"): vocabulary.TranslationMethod,
    ("canonical_facts", "mode"): vocabulary.Mode,
    ("canonical_facts", "outcome"): vocabulary.FactOutcome,
    ("canonical_facts", "deciding_criterion"): vocabulary.Criterion,
    ("canonical_facts", "verification_state"): vocabulary.FactVerification,
    ("canonical_facts", "unresolved_reason"): vocabulary.UnresolvedReason,
    ("selection_outcomes", "outcome"): vocabulary.Outcome,
    ("relation_assertions", "review_state"): vocabulary.RelationReviewState,
    ("relation_assertions", "close_reason"): vocabulary.CloseReason,
    ("review_items", "kind"): vocabulary.ReviewKind,
    ("review_decisions", "outcome"): vocabulary.ReviewOutcome,
}


def _values(alias: Any) -> tuple[str, ...]:
    return get_args(alias.__value__)


def _rows() -> list[Record]:
    rows = one_of_each()
    return [rows[0].evidence, *rows]  # type: ignore[attr-defined]


def _wire(row: dict[str, Any]) -> dict[str, Any]:
    return json.loads(pydantic.TypeAdapter(dict[str, Any]).dump_json(row))


def _models() -> ModuleType:
    module = ModuleType("generated_evidence")
    exec((GENERATED / "pydantic" / "models.py").read_text(), module.__dict__)
    return module


def test_the_evidence_contract_is_registered_in_the_evidence_schema() -> None:
    contract = next(
        item for item in registered_contracts() if item.contract_id == "kn.core.evidence"
    )
    assert contract.digest == evidence_contract().digest
    assert contract.schema == "evidence"
    assert {table.name for table in contract.tables} == set(evidence_tables())


@pytest.mark.parametrize(("location", "alias"), ENUMS.items(), ids=lambda item: str(item))
def test_python_value_sets_equal_the_contract_enums(location: tuple[str, str], alias: Any) -> None:
    table, name = location
    field = next(item for item in evidence_contract().table(table).fields if item.name == name)
    assert field.enum == _values(alias)


def test_every_table_declares_record_human_verification_over_stable_ids() -> None:
    coverage = {item.dataset: item for item in declared_coverage(evidence_contract())}
    assert set(coverage) == set(evidence_tables())
    claims = coverage["claims"]
    stable = {field.field_id for field in evidence_contract().table("claims").fields}
    assert set(claims.record_fields) == stable
    assert "evidence.claims.source_verification_label" in claims.record_fields


def test_every_table_has_a_representative_row() -> None:
    assert {row.TABLE for row in _rows()} == set(evidence_tables())


@pytest.mark.parametrize("record", _rows(), ids=lambda record: record.TABLE)
def test_rows_pass_the_generated_wire_validators(record: Record) -> None:
    row = record.row()
    schema = json.loads((GENERATED / "jsonschema" / f"{record.TABLE}.json").read_text())
    jsonschema.validate(_wire(row), schema)
    model = getattr(_models(), "".join(part.capitalize() for part in record.TABLE.split("_")))
    model.model_validate(row)
    assert set(row) == {column.name for column in evidence_tables()[record.TABLE].columns}


@pytest.mark.parametrize(
    "change",
    [
        {"value_number": None},
        {"missing_reason": "not_found"},
        {"value_text": "1250"},
        {"normalized_unit": None},
        {"valid_from_precision": None},
        {"origin_uri": None},
        {"fetched_at": None},
    ],
    ids=[
        "no-value",
        "value-and-reason",
        "two-values",
        "unit-without-rule",
        "time-without-precision",
        "no-origin",
        "no-fetch-time",
    ],
)
def test_wire_validators_reject_rows_the_database_rejects(change: dict[str, Any]) -> None:
    row = {**claim().row(), **change}
    schema = json.loads((GENERATED / "jsonschema" / "claims.json").read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_wire(row), schema)
    with pytest.raises(pydantic.ValidationError):
        _models().Claims.model_validate(row)


def test_value_columns_are_the_contract_value_or_reason_group() -> None:
    rules = json.loads(evidence_contract().table("claims").extensions_json)["presence"]
    group = next(rule for rule in rules if rule["name"] == "value_or_reason")
    assert set(group["fields"]) <= set(VALUE_COLUMNS)
    assert isinstance(claim().row()["value_number"], Decimal)
