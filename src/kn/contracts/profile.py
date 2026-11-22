"""Reject ODCS features that this compiler does not yet implement."""

from typing import Any

CONTRACT_KEYS = {
    "apiVersion",
    "kind",
    "id",
    "name",
    "version",
    "status",
    "domain",
    "customProperties",
    "schema",
    "description",
}
TABLE_KEYS = {
    "name",
    "logicalType",
    "physicalType",
    "customProperties",
    "properties",
    "description",
}
FIELD_KEYS = {"name", "logicalType", "required", "primaryKey", "customProperties", "description"}


def _keys(node: dict[str, Any], allowed: set[str], required: set[str]) -> None:
    unknown = set(node) - allowed
    missing = required - set(node)
    if unknown or missing:
        raise ValueError(
            f"unsupported or missing profile keys: unknown={sorted(unknown)}, missing={sorted(missing)}"
        )


def validate_profile(data: dict[str, Any]) -> None:
    """A valid ODCS document is not necessarily within this deliberately narrow compiler profile."""
    _keys(data, CONTRACT_KEYS, {"schema", "customProperties"})
    if not data["schema"]:
        raise ValueError("empty contract schema")
    for table in data["schema"]:
        _keys(table, TABLE_KEYS, {"properties", "logicalType", "physicalType"})
        if table["logicalType"] != "object" or table["physicalType"] != "table":
            raise ValueError("only object/table models are supported")
        for field in table["properties"]:
            _keys(field, FIELD_KEYS, {"logicalType", "customProperties"})
