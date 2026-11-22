"""Strict CSV cell conversion shared with the contract's engine model."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from kn.contracts.model import Field, Table
from kn.contracts.sqlalchemy import PARTIAL_DATE

Cell = str | int | bool | Decimal | date | None
Row = dict[str, Cell]
INTEGER = re.compile(r"^-?(0|[1-9][0-9]*)$")
DECIMAL = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1


def cell(field: Field, value: str) -> Cell:
    """A blank remains a missing value, and false and zero remain observed values."""
    if value == "":
        if field.required:
            raise ValueError("required value is blank")
        return None
    if field.enum and value not in field.enum:
        raise ValueError("value is outside the contract enum")
    if field.partial_date:
        _partial_date(value)
    match field.logical_type:
        case "integer":
            if not INTEGER.fullmatch(value) or not MIN_INTEGER <= int(value) <= MAX_INTEGER:
                raise ValueError("expected a signed 64-bit integer")
            return int(value)
        case "number":
            return _decimal(field, value)
        case "boolean":
            if value not in {"true", "false"}:
                raise ValueError("expected true or false")
            return value == "true"
        case "date":
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("expected an ISO calendar date")
            return date.fromisoformat(value)
        case _:
            return value


def _partial_date(value: str) -> None:
    if not re.fullmatch(PARTIAL_DATE, value):
        raise ValueError("expected year, year-month, or full ISO calendar date")
    date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])


def _decimal(field: Field, value: str) -> Decimal:
    if not DECIMAL.fullmatch(value):
        raise ValueError("expected an exact finite base-10 decimal")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal") from error
    _, digits, exponent = number.as_tuple()
    scale = max(0, -int(exponent))
    integer_digits = max(0, len(digits) + int(exponent))
    if scale > field.scale or integer_digits > field.precision - field.scale:
        raise ValueError("decimal exceeds contract precision or scale")
    return number


def row(table: Table, raw: dict[str, str], import_id: str, line: int) -> Row:
    result: Row = {"import_id": import_id}
    for field in table.fields:
        if field.name == "import_id":
            continue
        try:
            result[field.name] = cell(field, raw[field.name])
        except ValueError as error:
            raise ValueError(f"{table.name}:{line}:{field.name}: {error}") from error
    return result
