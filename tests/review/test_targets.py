"""Typed targets preserve key identity and refuse ambiguous scope/version inputs."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from kn.contracts.registry import registered_contracts
from kn.review.model import KeyPart
from kn.review.targets import ContractResolver, content_version, declared_coverage
from tests.review.test_protocol import target


@pytest.mark.parametrize(
    "kind,value",
    [
        ("integer", "01"),
        ("integer", True),
        ("integer", 2**63),
        ("boolean", 1),
        ("string", 1),
        ("number", "NaN"),
        ("number", "1e1000000"),
        ("number", "not a number"),
        ("date", "2026-01"),
        ("date", "2026-02-30"),
        ("timestamp", "2026-01-02T12:00:00"),
    ],
)
def test_key_types_are_not_coerced(kind, value) -> None:
    with pytest.raises(ValueError):
        KeyPart(field_id="id", kind=kind, value=value)


@pytest.mark.parametrize(
    "kind,value,native",
    [
        ("integer", 1, 1),
        ("boolean", True, True),
        ("string", "001", "001"),
        ("date", "2026-01-02", date(2026, 1, 2)),
        ("timestamp", "2026-01-02T14:00:00+02:00", datetime(2026, 1, 2, 12, tzinfo=UTC)),
        ("number", "01.00", Decimal(1)),
    ],
)
def test_typed_keys_have_canonical_native_values(kind, value, native) -> None:
    part = KeyPart(field_id="id", kind=kind, value=value)
    assert part.native() == native
    assert KeyPart.model_validate_json(part.model_dump_json()) == part


def test_target_identity_ignores_key_order_but_retains_scope_locale_and_purpose() -> None:
    original = target()
    assert target(key=list(reversed(original.key))) == original
    assert target(purpose="publication").target_id != original.target_id
    assert target(scope="record", field_id=None).target_id != original.target_id
    key = [part.model_dump() for part in original.key]
    key[1]["value"] = "en"
    assert target(key=key).target_id != original.target_id
    for changes in (
        {"key": []},
        {"key": [key[0], key[0]]},
        {"scope": "record"},
        {"scope": "field", "field_id": None},
        {"version": "v1"},
    ):
        with pytest.raises(ValueError):
            target(**changes)


def test_content_versions_include_types_context_nulls_and_exact_instants() -> None:
    assert content_version({"id": "001"}) != content_version({"id": 1})
    assert content_version({"mass": None}) != content_version({})
    assert content_version({"mass": Decimal("1.25")}) != content_version({"mass": "1.25"})
    assert content_version({"mass": 1, "unit": "kg"}) != content_version({"mass": 1, "unit": "g"})
    assert content_version({"time": datetime(2026, 1, 2, 12, tzinfo=UTC)}) == content_version(
        {"time": datetime.fromisoformat("2026-01-02T14:00:00+02:00")}
    )


def test_coverage_requires_registered_fields_and_the_reviewed_value() -> None:
    contract = registered_contracts()[-1]
    coverage = declared_coverage(contract)[0]
    assert ContractResolver([contract], [coverage])
    assert declared_coverage(registered_contracts()[0]) == ()
    for changed in (
        replace(coverage, contract_id="unknown"),
        replace(coverage, dataset="unknown"),
        replace(coverage, record_fields=()),
        replace(coverage, record_fields=("unknown",)),
        replace(coverage, field_context={coverage.record_fields[0]: coverage.record_fields[1:]}),
    ):
        with pytest.raises(ValueError):
            ContractResolver([contract], [changed])
    with pytest.raises(ValueError):
        ContractResolver([contract], [coverage, coverage])


def test_numeric_zero_keys_have_one_canonical_identity() -> None:
    assert KeyPart(field_id="id", kind="number", value="-0.00") == KeyPart(
        field_id="id", kind="number", value="0"
    )
