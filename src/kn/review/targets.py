"""Explicit coverage and resolver interfaces; no dataset is implicitly reviewable."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import Contract
from kn.contracts.physical import extensions
from kn.contracts.sqlalchemy import metadata
from kn.review.model import Target, digest


class TargetResolver(Protocol):
    def resolve(self, connection: Connection, target: Target) -> None:
        """Refuse unknown/incomplete targets and stale content, locking the reviewed row."""
        ...


@dataclass(frozen=True)
class Coverage:
    """Stable content fields include value, unit, locale, conditions and meaningful context.

    Omitting a field excludes it from independent review. Callers must name every
    allowed field and its context; presentation and verification annotations stay excluded.
    """

    contract_id: str
    dataset: str
    record_fields: tuple[str, ...]
    field_context: Mapping[str, tuple[str, ...]]


class ContractResolver:
    def __init__(self, contracts: Sequence[Contract], coverage: Sequence[Coverage]) -> None:
        self.tables: dict[tuple[str, str], sa.Table] = {}
        self.coverage: dict[tuple[str, str], Coverage] = {}
        for item in coverage:
            key = (item.contract_id, item.dataset)
            if key in self.coverage:
                raise ValueError("coverage requires one registered contract/dataset")
            table = _coverage_table(contracts, item)
            _validate_fields(table, item)
            self.tables[key], self.coverage[key] = table, item

    def resolve(self, connection: Connection, target: Target) -> None:
        key = (target.contract_id, target.dataset)
        if key not in self.tables:
            raise ValueError("unknown target dataset or missing verification coverage")
        table, coverage = self.tables[key], self.coverage[key]
        columns = {column.info["field_id"]: column for column in table.columns}
        primary = {column.info["field_id"] for column in table.primary_key.columns}
        if {part.field_id for part in target.key} != primary:
            raise ValueError("target requires the complete typed primary key")
        clauses = []
        for part in target.key:
            column = columns[part.field_id]
            if part.kind != column.info["logical_type"]:
                raise ValueError("target key type differs from the registered field")
            clauses.append(column == part.native())
        fields = coverage.record_fields
        if target.scope == "field":
            if target.field_id is None or target.field_id not in coverage.field_context:
                raise ValueError("unknown or unsupported target field")
            fields = coverage.field_context[target.field_id]
        row = (
            connection.execute(sa.select(table).where(*clauses).with_for_update())
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ValueError("unknown target record")
        content = {field: row[columns[field].name] for field in fields}
        if content_version(content) != target.version:
            raise ValueError("stale target content version")


def _coverage_table(contracts: Sequence[Contract], item: Coverage) -> sa.Table:
    contract = next((c for c in contracts if c.contract_id == item.contract_id), None)
    if contract is None:
        raise ValueError("coverage requires one registered contract/dataset")
    table = metadata(contract).tables.get(f"{contract.schema}.{item.dataset}")
    if table is None:
        raise ValueError("coverage names an unknown dataset")
    return table


def _validate_fields(table: sa.Table, item: Coverage) -> None:
    fields = {column.info["field_id"] for column in table.columns}
    declared = set(item.record_fields) | set(item.field_context)
    declared.update(field for context in item.field_context.values() for field in context)
    if not item.record_fields or not declared <= fields:
        raise ValueError("coverage requires known stable content field IDs")
    if any(field not in context for field, context in item.field_context.items()):
        raise ValueError("field review context must include the reviewed value")


def declared_coverage(contract: Contract) -> tuple[Coverage, ...]:
    """Read explicit kn.humanVerification declarations; absent coverage grants nothing."""
    return tuple(
        Coverage(
            contract.contract_id,
            table.name,
            tuple(value["recordFields"]),
            {field: tuple(context) for field, context in value["fieldContexts"].items()},
        )
        for table in contract.tables
        if (value := extensions(table).get("humanVerification")) is not None
    )


def content_version(content: Mapping[str, object]) -> str:
    """Hash a declared projection keyed by stable field IDs, including explicit nulls."""
    return digest({field: _wire(value) for field, value in content.items()})


def _wire(value: object) -> object:
    """Include native value types in hashes; decimals/dates never become lossy floats."""
    from datetime import date, datetime
    from decimal import Decimal

    from kn.review.model import utc

    if isinstance(value, datetime):
        return {"timestamp": utc(value).isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, Decimal):
        return {"number": str(value)}
    return value
