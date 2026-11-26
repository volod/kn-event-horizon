"""Contract-declared targets shared by submission, replay and reads."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Protocol, Self

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import Contract, Field, Table
from kn.contracts.physical import extensions
from kn.contracts.sqlalchemy import deployment_metadata
from kn.contracts.verification import field_contexts
from kn.review.model import KeyPart, Purpose, Target, digest, utc

type Row = Mapping[str, object]
type Unavailable = Literal["missing", "stale", "incompatible"]


class TargetUnavailable(ValueError):
    def __init__(self, state: Unavailable, message: str) -> None:
        super().__init__(message)
        self.state = state


class TargetResolver(Protocol):
    def resolve(self, connection: Connection, target: Target) -> None:
        """Refuse unknown/incomplete targets and stale content, locking the reviewed row."""
        ...


@dataclass(frozen=True)
class Coverage:
    """Stable content fields include value, unit, locale, conditions and meaningful context."""

    contract_id: str
    dataset: str
    record_fields: tuple[str, ...]
    field_context: Mapping[str, tuple[str, ...]]


class Dataset:
    def __init__(self, table: sa.Table, model: Table, coverage: Coverage) -> None:
        self.table = table
        self.coverage = coverage
        self.fields = {field.field_id: field for field in model.fields}
        self.primary_key = {field.field_id: field for field in model.fields if field.primary_key}
        self._validate()

    def _validate(self) -> None:
        coverage = self.coverage
        declared = set(coverage.record_fields) | set(coverage.field_context)
        declared.update(field for context in coverage.field_context.values() for field in context)
        if not coverage.record_fields or not declared <= self.fields.keys():
            raise ValueError("coverage requires known stable content field IDs")
        if any(field not in context for field, context in coverage.field_context.items()):
            raise ValueError("field review context must include the reviewed value")

    def key(self, row: Row) -> tuple[KeyPart, ...]:
        """Encode a stored row's full primary key without losing types or leading zeroes."""
        return tuple(_key_part(field, row[field.name]) for field in self.primary_key.values())

    def fetch(
        self, connection: Connection, key: tuple[KeyPart, ...], *, lock: bool = False
    ) -> Row | None:
        if (
            len(key) != len(self.primary_key)
            or {part.field_id for part in key} != self.primary_key.keys()
        ):
            raise TargetUnavailable(
                "incompatible", "target requires the complete typed primary key"
            )
        clauses = []
        for part in key:
            field = self.primary_key[part.field_id]
            if part.kind != field.logical_type:
                raise TargetUnavailable(
                    "incompatible", "target key type differs from the registered field"
                )
            clauses.append(self.table.c[field.name] == part.native())
        query = sa.select(self.table).where(*clauses)
        row = (
            connection.execute(query.with_for_update() if lock else query).mappings().one_or_none()
        )
        return None if row is None else dict(row)

    def context(self, field_id: str | None) -> tuple[str, ...]:
        if field_id is None:
            return self.coverage.record_fields
        if field_id not in self.coverage.field_context:
            raise TargetUnavailable("incompatible", "unknown or unsupported target field")
        return self.coverage.field_context[field_id]

    def version(self, row: Row, fields: tuple[str, ...]) -> str:
        return content_version({field: row[self.fields[field].name] for field in fields})

    def target(self, row: Row, purpose: Purpose, field_id: str | None = None) -> Target:
        """Build the target of a typed row with the same declaration used during resolution."""
        return self._target(
            self.key(row), purpose, field_id, self.version(row, self.context(field_id))
        )

    def targets(
        self, row: Row, key: tuple[KeyPart, ...], purpose: Purpose, visible: set[str]
    ) -> dict[str | None, Target]:
        """Targets whose entire reviewed content is visible to the caller."""
        versions: dict[tuple[str, ...], str] = {}
        result = {}
        for field in (None, *self.coverage.field_context):
            fields = self.context(field)
            if (field is None or field in visible) and visible.issuperset(fields):
                if fields not in versions:
                    versions[fields] = self.version(row, fields)
                result[field] = self._target(key, purpose, field, versions[fields])
        return result

    def _target(
        self, key: tuple[KeyPart, ...], purpose: Purpose, field_id: str | None, version: str
    ) -> Target:
        return Target(
            contract_id=self.coverage.contract_id,
            dataset=self.coverage.dataset,
            key=key,
            scope="record" if field_id is None else "field",
            field_id=field_id,
            version=version,
            purpose=purpose,
        )


class ContractResolver:
    def __init__(self, contracts: Sequence[Contract], coverage: Sequence[Coverage]) -> None:
        self._datasets: dict[tuple[str, str], Dataset] = {}
        models = {
            (contract.contract_id, table.name): (contract.schema, table)
            for contract in contracts
            for table in contract.tables
        }
        tables = deployment_metadata(contracts).tables
        for item in coverage:
            key = (item.contract_id, item.dataset)
            if key in self._datasets or key not in models:
                raise ValueError("coverage requires one registered contract/dataset")
            schema, model = models[key]
            name = f"{schema}.{model.name}" if schema else model.name
            self._datasets[key] = Dataset(tables[name], model, item)

    @classmethod
    def registered(cls, contracts: Sequence[Contract]) -> Self:
        return cls(
            contracts, [item for contract in contracts for item in declared_coverage(contract)]
        )

    def dataset(self, contract_id: str, dataset: str) -> Dataset:
        found = self._datasets.get((contract_id, dataset))
        if found is None:
            raise TargetUnavailable(
                "incompatible", "unknown target dataset or missing verification coverage"
            )
        return found

    def resolve(self, connection: Connection, target: Target) -> None:
        dataset = self.dataset(target.contract_id, target.dataset)
        fields = dataset.context(target.field_id)
        row = dataset.fetch(connection, target.key, lock=True)
        if row is None:
            raise TargetUnavailable("missing", "unknown target record")
        if dataset.version(row, fields) != target.version:
            raise TargetUnavailable("stale", "stale target content version")


def _key_part(field: Field, value: object) -> KeyPart:
    if isinstance(value, datetime):
        value = utc(value).isoformat()
    elif isinstance(value, date | Decimal):
        value = str(value)
    if not isinstance(value, str | int | bool):
        raise ValueError("target requires a typed primary key value")
    return KeyPart(field_id=field.field_id, kind=field.logical_type, value=value)


def declared_coverage(contract: Contract) -> tuple[Coverage, ...]:
    """Read explicit kn.humanVerification declarations; absent coverage grants nothing."""
    return tuple(
        Coverage(
            contract.contract_id,
            table.name,
            tuple(value["recordFields"]),
            field_contexts(table, value),
        )
        for table in contract.tables
        if (value := extensions(table).get("humanVerification")) is not None
    )


def content_version(content: Row) -> str:
    """Hash a declared projection keyed by stable field IDs, including explicit nulls."""
    return digest({field: _wire(value) for field, value in content.items()})


def _wire(value: object) -> object:
    """Include native value types in hashes; decimals/dates never become lossy floats."""
    if isinstance(value, datetime):
        return {"timestamp": utc(value).isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, Decimal):
        return {"number": str(value)}
    return value
