"""Validate the bounded PostgreSQL template inputs before building metadata."""

import json
import re
from typing import Any

from kn.contracts.diagnostics import ContractError
from kn.contracts.model import Field, Table

INDEX_NAME = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
UNIQUE_METHOD = "btree"


def extensions(node: Field | Table) -> dict[str, Any]:
    return dict(json.loads(node.extensions_json))


def column_names(table: Table, refs: list[str]) -> list[str]:
    names = {field.name: field.name for field in table.fields}
    names.update({field.field_id: field.name for field in table.fields})
    if any(ref not in names for ref in refs):
        raise ContractError((), "reference", "physical design must reference existing table fields")
    result = [names[ref] for ref in refs]
    if len(result) != len(set(result)):
        raise ContractError((), "reference", "physical design must not repeat a column")
    return result


def validate_physical(tables: tuple[Table, ...]) -> None:
    """Fail closed for combinations PostgreSQL cannot implement without more intent."""
    index_names = {name for table in tables for name in (table.name, f"pk_{table.name}")}
    for table in tables:
        meta = extensions(table)
        for index in meta.get("index", []):
            _index(table, index, index_names)
        partition = meta.get("partition")
        if partition:
            keys = column_names(table, partition["fields"])
            if not set(keys) <= set(table.primary_key):
                raise ContractError((), "partition", "include partition columns in the primary key")
        for field in table.fields:
            spatial = extensions(field).get("spatialProfile")
            if spatial:
                _spatial(field)


def _index(table: Table, index: dict[str, Any], names: set[str]) -> None:
    if not INDEX_NAME.fullmatch(index["name"]) or index["name"] in names:
        raise ContractError(
            (), "index", "use a unique schema-wide SQL index name, at most 48 characters"
        )
    names.add(index["name"])
    columns = column_names(table, index["fields"])
    if index["unique"] and index["method"] != UNIQUE_METHOD:
        raise ContractError((), "index", "unique indexes require btree")
    if index["method"] in {"hash", "spgist"} and len(columns) != 1:
        raise ContractError((), "index", "hash and spgist indexes require one column")
    partition = extensions(table).get("partition")
    if (
        partition
        and index["unique"]
        and not set(column_names(table, partition["fields"])) <= set(columns)
    ):
        raise ContractError((), "partition", "unique indexes must include partition columns")


def _spatial(field: Field) -> None:
    if field.logical_type != "string" or field.primary_key or field.enum or field.partial_date:
        raise ContractError(
            (), "spatialProfile", "use WKT string fields without scalar checks or primary keys"
        )
