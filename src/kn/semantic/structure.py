"""Contract-derived row, key and reference checks for complete semantic snapshots."""

from datetime import datetime
from functools import cache
from typing import Any, Never

from jsonschema import Draft202012Validator, FormatChecker

from kn.contracts import load_contract
from kn.contracts.diagnostics import ContractError, Location, schema_error
from kn.contracts.exports import json_schema
from kn.contracts.model import Contract, Reference, Table
from kn.contracts.names import table_references
from kn.contracts.physical import column_names, extensions
from kn.contracts.schemas import RESOURCES

type Row = dict[str, Any]
type Snapshot = dict[str, list[Row]]


@cache
def semantic_contract() -> Contract:
    """Use the same packaged definition as compilation and deployment."""
    return load_contract(RESOURCES / "semantic" / "1.0.0.json")


def refuse(path: Location, rule: str, hint: str) -> Never:
    raise ContractError(path, "semantic." + rule, hint)


def _timestamp_format(value: object) -> bool:
    # jsonschema's optional RFC3339 dependency is deliberately not needed at runtime.
    return not isinstance(value, str) or datetime.fromisoformat(value.upper()).tzinfo is not None


@cache
def row_validators() -> dict[str, Draft202012Validator]:
    checker = FormatChecker()
    checker.checks("date-time", raises=ValueError)(_timestamp_format)
    return {
        table.name: Draft202012Validator(json_schema(table), format_checker=checker)
        for table in semantic_contract().tables
    }


def validate_rows(data: Snapshot) -> None:
    """Missing datasets mean empty; unknown datasets, extra fields and coercion fail."""
    if not isinstance(data, dict) or set(data) - set(row_validators()):
        refuse((), "dataset", "supply only contracted semantic datasets")
    for name, validator in row_validators().items():
        _rows(data.get(name, []), name, validator)
    for table in semantic_contract().tables:
        _keys(data, table)
        for reference in table_references(table):
            _reference(data, table.name, reference)


def _rows(rows: object, name: str, validator: Draft202012Validator) -> None:
    if not isinstance(rows, list):
        refuse((name,), "dataset", "supply an array of rows")
    for index, row in enumerate(rows):
        error = next(validator.iter_errors(row), None)
        if error:
            raise schema_error(error, (name, index))
        if any(isinstance(value, str) and not value.strip() for value in row.values()):
            refuse((name, index), "empty", "use nonempty strings or null for optional values")


def _keys(data: Snapshot, table: Table) -> None:
    keys = [table.primary_key]
    keys += [
        tuple(column_names(table, index["fields"]))
        for index in extensions(table).get("index", [])
        if index["unique"]
    ]
    for columns in keys:
        _unique(data.get(table.name, []), columns, table.name)


def _unique(rows: list[Row], columns: tuple[str, ...], table: str) -> None:
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        key = tuple(row.get(column) for column in columns)
        if key in seen:
            refuse((table, index), "unique", "keep primary and unique keys distinct")
        seen.add(key)


def _reference(data: Snapshot, table: str, reference: Reference) -> None:
    targets = {
        tuple(row[column] for column in reference.target_fields)
        for row in data.get(reference.table, [])
    }
    for index, row in enumerate(data.get(table, [])):
        key = tuple(row.get(column) for column in reference.fields)
        if not any(value is None for value in key) and key not in targets:
            refuse(
                (table, index, reference.fields[0]),
                "endpoint",
                "reference an existing row in the contracted target dataset",
            )


def indexed(data: Snapshot, table: str) -> dict[str, Row]:
    return {row["id"]: row for row in data.get(table, [])}


def acyclic(rows: dict[str, Row], column: str, table: str) -> None:
    """Iterative linear walk supports hierarchies deeper than Python's recursion limit."""
    finished: set[str] = set()
    for start in rows:
        visiting: set[str] = set()
        current: str | None = start
        while current and current not in finished:
            if current in visiting:
                refuse((table,), "cycle", "keep hierarchies and replacement chains acyclic")
            visiting.add(current)
            current = rows[current].get(column)
        finished.update(visiting)
