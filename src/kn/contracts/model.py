"""Small immutable model shared by validators, engines, and import adapters."""

import json
from dataclasses import dataclass
from typing import Literal

LogicalType = Literal["string", "integer", "number", "boolean", "date", "timestamp"]
LOGICAL_TYPES: tuple[LogicalType, ...] = (
    "string",
    "integer",
    "number",
    "boolean",
    "date",
    "timestamp",
)


def canonical(value: object) -> str:
    """Sorted, compact ASCII JSON: the serialization behind every digest and stored document."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Reference:
    table: str
    fields: tuple[str, ...]
    target_fields: tuple[str, ...]


@dataclass(frozen=True)
class Field:
    name: str
    field_id: str
    logical_type: LogicalType
    required: bool
    primary_key: bool
    description: str = ""
    reference: Reference | None = None
    enum: tuple[str, ...] = ()
    partial_date: bool = False
    precision: int = 38
    scale: int = 18
    extensions_json: str = "{}"


@dataclass(frozen=True)
class Table:
    name: str
    fields: tuple[Field, ...]
    csv: bool
    description: str = ""
    extensions_json: str = "{}"

    @property
    def primary_key(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields if field.primary_key)


@dataclass(frozen=True)
class Contract:
    contract_id: str
    version: str
    digest: str
    schema: str
    source_profile: str
    tables: tuple[Table, ...]
    document_json: str = "{}"
    references_json: str = "{}"

    def table(self, name: str) -> Table:
        return next(table for table in self.tables if table.name == name)
