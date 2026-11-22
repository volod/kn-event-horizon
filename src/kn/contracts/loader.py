"""Fail-closed ODCS profile validation and stable serialization."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from kn.contracts.lint import lint_contract
from kn.contracts.model import Contract, Field, LogicalType, Reference, Table
from kn.contracts.profile import validate_profile
from kn.contracts.schemas import SATCOM

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
FIELD_EXTENSIONS = {"fieldId", "foreignKey", "enum", "partialDate", "precision", "scale"}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _extensions(node: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in node.get("customProperties", []):
        name = item["property"]
        short = name.removeprefix("kn.")
        if name != f"kn.{short}" or short not in allowed or short in result:
            raise ValueError(f"unknown, misplaced, or repeated extension: {name}")
        result[short] = item["value"]
    return result


def _field(node: dict[str, Any]) -> Field:
    meta = _extensions(node, FIELD_EXTENSIONS)
    if "fieldId" not in meta:
        raise ValueError("kn.fieldId extension is required")
    logical = node["logicalType"]
    if logical not in {"string", "integer", "number", "boolean", "date"}:
        raise ValueError(f"unsupported logical type: {logical}")
    if meta.get("scale", 18) > meta.get("precision", 38):
        raise ValueError("decimal scale exceeds precision")
    if ("enum" in meta or "partialDate" in meta) and logical != "string":
        raise ValueError("enum and partialDate require string fields")
    if {"precision", "scale"} & set(meta) and logical != "number":
        raise ValueError("precision and scale require number fields")
    ref = meta.get("foreignKey")
    return Field(
        node["name"],
        meta["fieldId"],
        cast(LogicalType, logical),
        node.get("required", False),
        node.get("primaryKey", False),
        node.get("description", ""),
        Reference(ref["table"], tuple(ref["fields"]), tuple(ref["targetFields"])) if ref else None,
        tuple(meta.get("enum", [])),
        meta.get("partialDate", False),
        meta.get("precision", 38),
        meta.get("scale", 18),
    )


def _check_references(tables: tuple[Table, ...]) -> None:
    targets = {table.name: table for table in tables}
    for table in tables:
        for field in table.fields:
            if field.reference:
                _reference(table, field, targets)


def _reference(table: Table, field: Field, targets: dict[str, Table]) -> None:
    ref = field.reference
    assert ref is not None
    target = targets.get(ref.table)
    if target is None or target.primary_key != ref.target_fields:
        raise ValueError(f"{table.name}.{field.name}: unresolved unique reference {ref}")
    if len(ref.fields) != len(ref.target_fields) or field.name not in ref.fields:
        raise ValueError(f"{table.name}.{field.name}: invalid reference columns")
    source_types = {item.name: item.logical_type for item in table.fields}
    target_types = {item.name: item.logical_type for item in target.fields}
    for source, dest in zip(ref.fields, ref.target_fields, strict=True):
        if source not in source_types or source_types[source] != target_types[dest]:
            raise ValueError(f"{table.name}.{field.name}: reference type mismatch")


def load_contract(path: Path = SATCOM) -> Contract:
    """Validate the pinned standard and supported profile before interpreting any model."""
    data = lint_contract(path)
    validate_profile(data)
    meta = _extensions(data, {"storageSchema", "sourceProfile"})
    if set(meta) != {"storageSchema", "sourceProfile"}:
        raise ValueError("storageSchema and sourceProfile extensions are required")
    for table in data["schema"]:
        if "csv" not in _extensions(table, {"csv"}):
            raise ValueError("kn.csv extension is required")
    tables = tuple(
        Table(
            node["name"],
            tuple(_field(f) for f in node["properties"]),
            _extensions(node, {"csv"})["csv"],
        )
        for node in data["schema"]
    )
    _check_names(tables)
    _check_references(tables)
    return Contract(
        data["id"],
        data["version"],
        hashlib.sha256(canonical(data).encode()).hexdigest(),
        meta["storageSchema"],
        meta["sourceProfile"],
        tables,
    )


def _check_names(tables: tuple[Table, ...]) -> None:
    table_names: set[str] = set()
    field_ids: set[str] = set()
    for table in tables:
        if table.name in table_names or not IDENTIFIER.fullmatch(table.name):
            raise ValueError(f"invalid or duplicate table: {table.name}")
        table_names.add(table.name)
        _check_fields(table, field_ids)


def _check_fields(table: Table, field_ids: set[str]) -> None:
    names: set[str] = set()
    if not table.primary_key:
        raise ValueError(f"{table.name}: missing primary key")
    for field in table.fields:
        if field.name in names or not IDENTIFIER.fullmatch(field.name):
            raise ValueError(f"{table.name}: invalid or duplicate field: {field.name}")
        if field.field_id in field_ids or (field.primary_key and not field.required):
            raise ValueError(f"{table.name}: duplicate field ID or nullable primary key")
        names.add(field.name)
        field_ids.add(field.field_id)
