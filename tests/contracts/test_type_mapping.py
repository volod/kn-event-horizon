"""Wire and native validators accept only values that PostgreSQL stores without change."""

from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError, validate
from pydantic import ValidationError as ModelError

from kn.contracts import Field, load_contract
from kn.contracts.exports import artifacts
from kn.contracts.field_exports import json_field
from tests.contracts.test_compiler import compiler_document, write_document

BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1


def accepts(field: Field, value: Any) -> bool:
    try:
        validate(value, json_field(field))
    except ValidationError:
        return False
    return True


def number(precision: int, scale: int) -> Field:
    return Field("n", "example.n", "number", True, False, precision=precision, scale=scale)


def test_wire_integers_have_the_bigint_range() -> None:
    integer = Field("i", "example.i", "integer", True, False)
    assert accepts(integer, BIGINT_MIN) and accepts(integer, BIGINT_MAX)
    assert not accepts(integer, BIGINT_MAX + 1) and not accepts(integer, BIGINT_MIN - 1)


@pytest.mark.parametrize(
    ("precision", "scale", "value", "expected"),
    [
        (38, 18, "1" * 20, True),
        (38, 18, "1" * 21, False),  # PostgreSQL: numeric field overflow
        (38, 18, "0." + "0" * 17 + "1", True),
        (38, 18, "0." + "0" * 18 + "1", False),  # PostgreSQL rounds it to zero
        (38, 18, "-0012.5" + "0" * 30, True),  # leading and trailing zeros keep the value
        (5, 5, "0.12345", True),
        (5, 5, "1.2", False),
        (4, 0, "1234", True),
        (4, 0, "1.0", True),
        (4, 0, "1.5", False),
        (38, 18, "1e3", False),
        (38, 18, "1.", False),
    ],
)
def test_wire_decimals_fit_their_precision_and_scale(
    precision: int, scale: int, value: str, expected: bool
) -> None:
    assert accepts(number(precision, scale), value) is expected


@pytest.mark.parametrize(
    ("logical", "value", "expected"),
    [
        ("timestamp", "2026-01-01T00:00:00Z", True),
        ("timestamp", "2026-01-01T00:00:00.123456+02:00", True),
        ("timestamp", "2026-01-01T00:00:00", False),  # PostgreSQL would apply the session zone
        ("timestamp", "2026-01-01T00:00:00.1234567Z", False),  # finer than microseconds
        ("timestamp", "yesterday", False),
        ("date", "2026-01-01", True),
        ("date", "soon", False),
        ("date", "2026-1-1", False),
    ],
)
def test_wire_times_carry_a_shape_and_an_offset(logical: str, value: str, expected: bool) -> None:
    assert accepts(Field("t", "example.t", logical, True, False), value) is expected  # type: ignore[arg-type]


def test_native_integers_have_the_bigint_range() -> None:
    contract = load_contract()
    table = next(
        table for table in contract.tables if any(f.logical_type == "integer" for f in table.fields)
    )
    namespace: dict = {}
    exec(compile(artifacts(contract)["pydantic/models.py"], "models.py", "exec"), namespace)
    model = namespace["".join(part.capitalize() for part in table.name.split("_"))]
    integer = next(field for field in table.fields if field.logical_type == "integer")
    values = {field.name: "x" for field in table.fields if field.required}
    values.update({field.name: field.enum[0] for field in table.fields if field.enum})
    assert getattr(model(**{**values, integer.name: BIGINT_MAX}), integer.name) == BIGINT_MAX
    with pytest.raises(ModelError):
        model(**{**values, integer.name: BIGINT_MAX + 1})


def test_integer_primary_keys_take_no_server_generated_values(tmp_path: Path) -> None:
    # KN identifiers come from durable inputs, never from a sequence in load order.
    data = compiler_document()
    data["schema"][0]["customProperties"] = []
    ddl = artifacts(load_contract(write_document(tmp_path, data)))["postgresql/schema.sql"]
    assert "id BIGINT NOT NULL" in ddl
    assert "SERIAL" not in ddl and "nextval" not in ddl
