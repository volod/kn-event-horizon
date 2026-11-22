"""Reject ODCS features that this compiler does not yet implement."""

from typing import Any

from kn.contracts.diagnostics import ContractError, Location

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


def _keys(node: dict[str, Any], allowed: set[str], required: set[str], path: Location) -> None:
    """Name only the expected properties; rejected names stay at the reported location."""
    unknown = sorted(set(node) - allowed)
    if unknown:
        raise ContractError(
            (*path, unknown[0]), "profile", "remove properties outside the compiler profile"
        )
    missing = sorted(required - set(node))
    if missing:
        raise ContractError(path, "profile", "include required properties: " + ", ".join(missing))


def validate_profile(data: dict[str, Any]) -> None:
    """A valid ODCS document is not necessarily within this deliberately narrow compiler profile."""
    _keys(data, CONTRACT_KEYS, {"schema", "customProperties"}, ())
    if not data["schema"]:
        raise ContractError(("schema",), "profile", "define at least one table")
    for number, table in enumerate(data["schema"]):
        path: Location = ("schema", number)
        _keys(table, TABLE_KEYS, {"properties", "logicalType", "physicalType"}, path)
        if table["logicalType"] != "object" or table["physicalType"] != "table":
            raise ContractError(path, "profile", "use logicalType object with physicalType table")
        for index, field in enumerate(table["properties"]):
            _keys(
                field, FIELD_KEYS, {"logicalType", "customProperties"}, (*path, "properties", index)
            )
