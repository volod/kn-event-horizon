"""Portable field validation shapes shared by generated artifacts.

Wire values accept only what PostgreSQL stores unchanged: BIGINT integers, decimals within their
precision and scale, and timestamps with an explicit offset at most at microsecond precision.
Patterns use the ECMA-262 subset that JSON Schema recommends, so `format` stays an annotation.
"""

from typing import Any

from kn.contracts.model import Field
from kn.contracts.physical import extensions
from kn.contracts.sqlalchemy import INTEGER_MAX, INTEGER_MIN, PARTIAL_DATE

DATE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
# PostgreSQL, Avro timestamp-micros, and Pydantic keep microseconds; finer digits are refused.
TIMESTAMP_FRACTION_DIGITS = 6
TIMESTAMP_PATTERN = (
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
    rf"(?:\.[0-9]{{1,{TIMESTAMP_FRACTION_DIGITS}}})?(?:[Zz]|[+-][0-9]{{2}}:[0-9]{{2}})$"
)


def decimal_pattern(precision: int, scale: int) -> str:
    """Leading and trailing zeros keep the value, as in PostgreSQL and Pydantic."""
    whole = precision - scale
    integer = f"0*[0-9]{{1,{whole}}}" if whole else "0+"
    fraction = rf"(?:\.[0-9]{{1,{scale}}}0*)?" if scale else r"(?:\.0+)?"
    return f"^-?{integer}{fraction}$"


def json_field(field: Field) -> dict[str, Any]:
    types = {
        "string": "string",
        "integer": "integer",
        "boolean": "boolean",
        "date": "string",
        "timestamp": "string",
        "number": "string",
    }
    item: dict[str, Any] = {"type": types[field.logical_type], "x-kn": extensions(field)}
    if field.partial_date:
        item["pattern"] = PARTIAL_DATE
    if field.logical_type == "date":
        item.update(format="date", pattern=DATE_PATTERN)
    if field.logical_type == "timestamp":
        item.update(format="date-time", pattern=TIMESTAMP_PATTERN)
    if field.logical_type == "integer":
        item.update(minimum=INTEGER_MIN, maximum=INTEGER_MAX)
    if field.logical_type == "number":
        item["pattern"] = decimal_pattern(field.precision, field.scale)
    if field.enum:
        item["enum"] = list(field.enum)
    return item if field.required else {"anyOf": [item, {"type": "null"}]}
