"""Portable field validation shapes shared by generated artifacts."""

from typing import Any

from kn.contracts.model import Field
from kn.contracts.physical import extensions
from kn.contracts.sqlalchemy import PARTIAL_DATE


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
    if field.logical_type in {"date", "timestamp"}:
        item["format"] = "date" if field.logical_type == "date" else "date-time"
    if field.logical_type == "number":
        item["pattern"] = r"^-?[0-9]+(?:\.[0-9]+)?$"
    if field.enum:
        item["enum"] = list(field.enum)
    return item if field.required else {"anyOf": [item, {"type": "null"}]}
