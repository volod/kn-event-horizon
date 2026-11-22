"""Fail-closed ODCS profile validation and stable serialization."""

import hashlib
from pathlib import Path
from typing import Any

from kn.contracts.diagnostics import ContractError, Location
from kn.contracts.document import read_document
from kn.contracts.fields import extensions_of, model_field
from kn.contracts.lint import lint_contract
from kn.contracts.model import Contract, Field, Reference, Table, canonical
from kn.contracts.names import IDENTIFIER, MAX_IDENTIFIER
from kn.contracts.physical import validate_physical
from kn.contracts.profile import validate_profile
from kn.contracts.references import resolve_extensions
from kn.contracts.schemas import SATCOM, platform_policy

__all__ = ["IDENTIFIER", "SATCOM", "canonical", "load_contract"]
NAME_HINT = f"use a unique lowercase SQL identifier of at most {MAX_IDENTIFIER} characters"


def _check_references(tables: tuple[Table, ...]) -> None:
    targets = {table.name: table for table in tables}
    for number, table in enumerate(tables):
        for index, field in enumerate(table.fields):
            if field.reference:
                path: Location = ("schema", number, "properties", index)
                _reference(table, field, field.reference, targets, path)


def _reference(
    table: Table, field: Field, ref: Reference, targets: dict[str, Table], path: Location
) -> None:
    target = targets.get(ref.table)
    if target is None or target.primary_key != ref.target_fields:
        raise ContractError(path, "reference", "target an existing table primary key")
    if len(ref.fields) != len(ref.target_fields) or field.name not in ref.fields:
        raise ContractError(
            path, "reference", "match reference column counts and include this field"
        )
    source_types = {item.name: item.logical_type for item in table.fields}
    target_types = {item.name: item.logical_type for item in target.fields}
    for source, dest in zip(ref.fields, ref.target_fields, strict=True):
        if source not in source_types or source_types[source] != target_types[dest]:
            raise ContractError(
                path, "reference", "reference existing fields of matching logical types"
            )


def _catalog(references: Path | None) -> dict[str, Any]:
    return read_document(references) if references is not None else {}


def load_contract(path: Path = SATCOM, *, references: Path | None = None) -> Contract:
    """Validate the pinned standard and supported profile before interpreting any model."""
    data = lint_contract(path)
    validate_profile(data)
    # The deployment target comes first: no reference is resolved for a foreign schema.
    meta = extensions_of(data, {"storageSchema", "sourceProfile"}, ())
    if "storageSchema" not in meta:
        raise ContractError((), "profile", "include kn.storageSchema")
    if meta["storageSchema"] not in platform_policy()["schemas"]:
        position = next(
            index
            for index, item in enumerate(data["customProperties"])
            if item["property"] == "kn.storageSchema"
        )
        raise ContractError(
            ("customProperties", position, "value"),
            "storageSchema",
            "use a KN schema from the platform policy",
        )
    catalog = _catalog(references)
    resolve_extensions(data, catalog)
    tables = tuple(
        Table(
            node["name"],
            tuple(
                model_field(item, catalog, ("schema", number, "properties", index))
                for index, item in enumerate(node["properties"])
            ),
            extensions_of(node, {"csv"}, ("schema", number)).get("csv", False),
            node.get("description", ""),
            canonical(extensions_of(node, {"csv"}, ("schema", number))),
        )
        for number, node in enumerate(data["schema"])
    )
    _check_names(tables)
    validate_physical(tables)
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
    for number, table in enumerate(tables):
        if table.name in table_names or not IDENTIFIER.fullmatch(table.name):
            raise ContractError(("schema", number, "name"), "name", NAME_HINT)
        table_names.add(table.name)
        _check_fields(table, field_ids, ("schema", number))


def _check_fields(table: Table, field_ids: set[str], path: Location) -> None:
    names: set[str] = set()
    if not table.primary_key:
        raise ContractError(path, "key", "mark at least one required field as primaryKey")
    for number, field in enumerate(table.fields):
        location = (*path, "properties", number)
        if field.name in names or not IDENTIFIER.fullmatch(field.name):
            raise ContractError((*location, "name"), "name", NAME_HINT)
        if field.field_id in field_ids:
            raise ContractError(location, "fieldId", "use field IDs unique in the contract")
        if field.primary_key and not field.required:
            raise ContractError(location, "key", "make every primary key field required")
        names.add(field.name)
        field_ids.add(field.field_id)
