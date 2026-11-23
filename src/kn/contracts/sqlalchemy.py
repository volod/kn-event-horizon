"""Compile PostgreSQL metadata from the engine-neutral contract."""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from kn.contracts.model import Contract, Field, Table
from kn.contracts.names import check_name, foreign_key_name, primary_key_name, table_references
from kn.contracts.physical import (
    ENUM_CHECK,
    GEOMETRY_CHECK,
    check_kinds,
    column_names,
    extensions,
)

PARTIAL_DATE = r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$"
# Integer fields are BIGINT; wire and native validators accept the same range.
INTEGER_MIN = -(2**63)
INTEGER_MAX = 2**63 - 1


class Geometry(sa.types.UserDefinedType[Any]):
    """A narrow PostGIS typmod; WKT is passed to PostgreSQL without client execution."""

    cache_ok = True

    def __init__(self, geometry_type: str, srid: int) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: Any) -> str:
        return f"geometry({self.geometry_type},{self.srid})"


def column_type(field: Field) -> sa.types.TypeEngine[Any]:
    """Never coerce exact source decimals into binary floats."""
    spatial = extensions(field).get("spatialProfile")
    if spatial:
        return Geometry(spatial["geometryType"], spatial["srid"])
    types: dict[str, sa.types.TypeEngine[Any]] = {
        "string": sa.Text(),
        "integer": sa.BigInteger(),
        "boolean": sa.Boolean(),
        "date": sa.Date(),
        "timestamp": sa.DateTime(timezone=True),
        "number": sa.Numeric(field.precision, field.scale),
    }
    return types[field.logical_type]


def metadata(contract: Contract, schema: str | None = None) -> sa.MetaData:
    """Create fresh metadata; snapshot references remain deferrable across cyclic tables."""
    target = schema if schema is not None else contract.schema
    result = sa.MetaData(schema=target or None)
    _add_tables(result, contract, target)
    return result


def deployment_metadata(contracts: Sequence[Contract]) -> sa.MetaData:
    """Every deployed contract in one metadata, as Alembic and verification compare it."""
    result = sa.MetaData()
    for contract in contracts:
        _add_tables(result, contract, contract.schema)
    return result


def _add_tables(result: sa.MetaData, contract: Contract, target: str) -> None:
    for model in sorted(contract.tables, key=lambda item: item.name):
        table = sa.Table(
            model.name,
            result,
            *[
                # No sequence: identifiers come from durable inputs, never from load order.
                sa.Column(
                    field.name,
                    column_type(field),
                    nullable=not field.required,
                    primary_key=field.primary_key,
                    autoincrement=False,
                    comment=field.description or None,
                    info={"field_id": field.field_id, "logical_type": field.logical_type},
                )
                for field in model.fields
            ],
            info={
                "contract_id": contract.contract_id,
                "contract_version": contract.version,
                "contract_digest": contract.digest,
            },
            comment=model.description or None,
            schema=target or None,
            **_table_options(model),
        )
        table.primary_key.name = primary_key_name(model)
        for index in extensions(model).get("index", []):
            sa.Index(
                index["name"],
                *(table.c[name] for name in column_names(model, index["fields"])),
                unique=index["unique"],
                postgresql_using=index["method"],
            )
        for field in model.fields:
            for kind in check_kinds(field):
                table.append_constraint(_check(table, model, field, kind))
        for ref in table_references(model):
            table.append_constraint(
                sa.ForeignKeyConstraint(
                    list(ref.fields),
                    [
                        f"{target + '.' if target else ''}{ref.table}.{name}"
                        for name in ref.target_fields
                    ],
                    name=foreign_key_name(model, ref),
                    deferrable=True,
                    initially="DEFERRED",
                )
            )


def _table_options(model: Table) -> dict[str, Any]:
    partition = extensions(model).get("partition")
    if not partition:
        return {}
    # Always quote identifiers; no contract text is executable SQL.
    columns = ", ".join('"' + name + '"' for name in column_names(model, partition["fields"]))
    return {"postgresql_partition_by": f"{partition['strategy'].upper()} ({columns})"}


def _check(table: sa.Table, model: Table, field: Field, kind: str) -> sa.CheckConstraint:
    column = table.c[field.name]
    name = check_name(model, field, kind)
    if kind == GEOMETRY_CHECK:
        valid: sa.ColumnElement[bool] = sa.func.ST_IsValid(column)
        if extensions(field)["spatialProfile"]["validity"] == "required":
            valid = sa.and_(valid, ~sa.func.ST_IsEmpty(column))
        return sa.CheckConstraint(valid, name=name)
    if kind == ENUM_CHECK:
        return sa.CheckConstraint(column.in_(field.enum), name=name)
    return sa.CheckConstraint(column.op("~")(PARTIAL_DATE), name=name).ddl_if(dialect="postgresql")
