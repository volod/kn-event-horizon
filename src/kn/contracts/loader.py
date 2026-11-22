"""Fail-closed ODCS profile validation and stable serialization."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from kn.contracts.diagnostics import ContractError
from kn.contracts.document import read_document
from kn.contracts.lint import lint_contract
from kn.contracts.model import Contract, Field, LogicalType, Reference, Table
from kn.contracts.physical import validate_physical
from kn.contracts.profile import validate_profile
from kn.contracts.references import resolve_extensions
from kn.contracts.schemas import SATCOM

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
SEMANTIC_EXTENSIONS = {
    "entityClass",
    "relation",
    "identity",
    "updatePolicy",
    "interchange",
    "units",
    "comparisonProfile",
    "temporalProfile",
    "spatialProfile",
    "evidence",
    "licensePolicy",
    "enumRef",
    "vocabularyRefs",
    "index",
    "partition",
    "i18nKey",
    "lineageRefs",
}
FIELD_EXTENSIONS = {"fieldId", "foreignKey", "enum", "partialDate", "precision", "scale"}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _extensions(node: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in node.get("customProperties", []):
        name = item["property"]
        short = name.removeprefix("kn.")
        if name != f"kn.{short}" or short not in allowed | SEMANTIC_EXTENSIONS or short in result:
            raise ValueError(f"unknown, misplaced, or repeated extension: {name}")
        result[short] = item["value"]
    return result


def _field(node: dict[str, Any], catalog: dict[str, Any]) -> Field:
    meta = _extensions(node, FIELD_EXTENSIONS)
    if "fieldId" not in meta:
        raise ValueError("kn.fieldId extension is required")
    logical = node["logicalType"]
    if logical not in {"string", "integer", "number", "boolean", "date", "timestamp"}:
        raise ValueError(f"unsupported logical type: {logical}")
    if meta.get("scale", 18) > meta.get("precision", 38):
        raise ValueError("decimal scale exceeds precision")
    if ("enum" in meta or "partialDate" in meta) and logical != "string":
        raise ValueError("enum and partialDate require string fields")
    if {"precision", "scale"} & set(meta) and logical != "number":
        raise ValueError("precision and scale require number fields")
    enum = _enum(meta, catalog, logical)
    ref = meta.get("foreignKey")
    return Field(
        node["name"],
        meta["fieldId"],
        cast(LogicalType, logical),
        node.get("required", False),
        node.get("primaryKey", False),
        node.get("description", ""),
        Reference(ref["table"], tuple(ref["fields"]), tuple(ref["targetFields"])) if ref else None,
        enum,
        meta.get("partialDate", False),
        meta.get("precision", 38),
        meta.get("scale", 18),
        canonical(meta),
    )


def _enum(meta: dict[str, Any], catalog: dict[str, Any], logical: str) -> tuple[str, ...]:
    if "enumRef" in meta:
        vocabulary = catalog["vocabulary"][meta["enumRef"]].get("values")
        if (
            not isinstance(vocabulary, list)
            or not vocabulary
            or any(not isinstance(value, str) for value in vocabulary)
        ):
            raise ContractError(
                (), "enumRef", "define a nonempty string values array for the vocabulary"
            )
        if len(vocabulary) != len(set(vocabulary)) or (
            "enum" in meta and meta["enum"] != vocabulary
        ):
            raise ContractError(
                (), "enumRef", "use unique vocabulary values consistent with kn.enum"
            )
        if logical != "string":
            raise ContractError((), "enumRef", "enumerated vocabularies require string fields")
        return tuple(vocabulary)
    return tuple(meta.get("enum", []))


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
        raise ContractError(
            ("schema", table.name, "properties", field.name),
            "reference",
            "target an existing table primary key",
        )
    if len(ref.fields) != len(ref.target_fields) or field.name not in ref.fields:
        raise ContractError(
            ("schema", table.name, "properties", field.name),
            "reference",
            "match reference column counts and include this field",
        )
    source_types = {item.name: item.logical_type for item in table.fields}
    target_types = {item.name: item.logical_type for item in target.fields}
    for source, dest in zip(ref.fields, ref.target_fields, strict=True):
        if source not in source_types or source_types[source] != target_types[dest]:
            raise ContractError(
                ("schema", table.name, "properties", field.name),
                "reference",
                "reference existing fields of matching logical types",
            )


def load_contract(path: Path = SATCOM, *, references: Path | None = None) -> Contract:
    """Validate the pinned standard and supported profile before interpreting any model."""
    data = lint_contract(path)
    validate_profile(data)
    catalog = read_document(references) if references is not None else {}
    resolve_extensions(data, catalog)
    meta = _extensions(data, {"storageSchema", "sourceProfile"})
    if "storageSchema" not in meta:
        raise ContractError((), "profile", "include kn.storageSchema")
    tables = tuple(
        Table(
            node["name"],
            tuple(_field(f, catalog) for f in node["properties"]),
            _extensions(node, {"csv"}).get("csv", False),
            node.get("description", ""),
            canonical(_extensions(node, {"csv"})),
        )
        for node in data["schema"]
    )
    validate_physical(tables)
    _check_names(tables)
    _check_references(tables)
    return Contract(
        data["id"],
        data["version"],
        hashlib.sha256(
            canonical({"contract": data, "references": catalog} if catalog else data).encode()
        ).hexdigest(),
        meta["storageSchema"],
        meta.get("sourceProfile", ""),
        tables,
        canonical(data),
        canonical(catalog),
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
