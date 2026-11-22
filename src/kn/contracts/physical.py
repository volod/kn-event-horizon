"""Validate the bounded PostgreSQL template inputs before building metadata."""

import json
from typing import Any

from kn.contracts.diagnostics import ContractError, Location
from kn.contracts.model import Field, Table
from kn.contracts.names import (
    IDENTIFIER,
    check_name,
    foreign_key_name,
    primary_key_name,
    table_references,
)

UNIQUE_METHOD = "btree"
GEOMETRY_CHECK = "geometry"
ENUM_CHECK = "enum"
PRECISION_CHECK = "precision"


def extensions(node: Field | Table) -> dict[str, Any]:
    return dict(json.loads(node.extensions_json))


def check_kinds(field: Field) -> tuple[str, ...]:
    """The generated check constraints of a field, in the order the templates emit them."""
    kinds = [GEOMETRY_CHECK] if extensions(field).get("spatialProfile") else []
    if field.enum:
        kinds.append(ENUM_CHECK)
    if field.partial_date:
        kinds.append(PRECISION_CHECK)
    return tuple(kinds)


def column_names(table: Table, refs: list[str], path: Location = ()) -> list[str]:
    names = {field.name: field.name for field in table.fields}
    names.update({field.field_id: field.name for field in table.fields})
    if any(ref not in names for ref in refs):
        raise ContractError(
            path, "reference", "physical design must reference existing table fields"
        )
    result = [names[ref] for ref in refs]
    if len(result) != len(set(result)):
        raise ContractError(path, "reference", "physical design must not repeat a column")
    return result


def validate_physical(tables: tuple[Table, ...]) -> None:
    """Fail closed for combinations PostgreSQL cannot implement without more intent."""
    # Tables and indexes, including primary key indexes, share one namespace per schema.
    relations: dict[str, Location] = {}
    for number, table in enumerate(tables):
        _unique(relations, table.name, ("schema", number, "name"))
        _unique(relations, primary_key_name(table), ("schema", number, "name"))
    for number, table in enumerate(tables):
        path: Location = ("schema", number)
        meta = extensions(table)
        for index in meta.get("index", []):
            _index(table, index, relations, path)
        partition = meta.get("partition")
        if partition:
            keys = column_names(table, partition["fields"], path)
            if not set(keys) <= set(table.primary_key):
                raise ContractError(
                    path, "partition", "include partition columns in the primary key"
                )
        _constraints(table, path)


def _unique(seen: dict[str, Location], name: str, path: Location) -> None:
    if name in seen:
        raise ContractError(
            path, "name", "rename objects whose generated PostgreSQL names coincide"
        )
    seen[name] = path


def _constraints(table: Table, path: Location) -> None:
    """Primary, foreign, and check constraint names are unique within their table."""
    names: dict[str, Location] = {primary_key_name(table): path}
    for reference in table_references(table):
        _unique(names, foreign_key_name(table, reference), path)
    for number, field in enumerate(table.fields):
        location = (*path, "properties", number)
        for kind in check_kinds(field):
            _unique(names, check_name(table, field, kind), location)
        if extensions(field).get("spatialProfile"):
            _spatial(field, location)


def _index(table: Table, index: dict[str, Any], names: dict[str, Location], path: Location) -> None:
    if not IDENTIFIER.fullmatch(index["name"]):
        raise ContractError(path, "index", "use an SQL index name of at most 48 characters")
    _unique(names, index["name"], path)
    columns = column_names(table, index["fields"], path)
    if index["unique"] and index["method"] != UNIQUE_METHOD:
        raise ContractError(path, "index", "unique indexes require btree")
    if index["method"] in {"hash", "spgist"} and len(columns) != 1:
        raise ContractError(path, "index", "hash and spgist indexes require one column")
    partition = extensions(table).get("partition")
    if (
        partition
        and index["unique"]
        and not set(column_names(table, partition["fields"], path)) <= set(columns)
    ):
        raise ContractError(path, "partition", "unique indexes must include partition columns")


def _spatial(field: Field, path: Location) -> None:
    if field.logical_type != "string" or field.primary_key or field.enum or field.partial_date:
        raise ContractError(
            path, "spatialProfile", "use WKT string fields without scalar checks or primary keys"
        )
