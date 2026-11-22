"""Compile PostgreSQL metadata from the engine-neutral contract."""

from typing import Any

import sqlalchemy as sa

from kn.contracts.model import Contract, Field, Table
from kn.contracts.physical import column_names, extensions

PARTIAL_DATE = r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$"
NAMING = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


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
    result = sa.MetaData(schema=target or None, naming_convention=NAMING)
    for model in sorted(contract.tables, key=lambda item: item.name):
        table = sa.Table(
            model.name,
            result,
            *[
                sa.Column(
                    field.name,
                    column_type(field),
                    nullable=not field.required,
                    primary_key=field.primary_key,
                    comment=field.description or None,
                    info={"field_id": field.field_id},
                )
                for field in model.fields
            ],
            info={"contract_version": contract.version, "contract_digest": contract.digest},
            comment=model.description or None,
            **_table_options(model),
        )
        for index in extensions(model).get("index", []):
            sa.Index(
                index["name"],
                *(table.c[name] for name in column_names(model, index["fields"])),
                unique=index["unique"],
                postgresql_using=index["method"],
            )
        for field in model.fields:
            _constraints(table, field, target)
    return result


def _table_options(model: Table) -> dict[str, Any]:
    partition = extensions(model).get("partition")
    if not partition:
        return {}
    # Always quote identifiers; no contract text is executable SQL.
    columns = ", ".join('"' + name + '"' for name in column_names(model, partition["fields"]))
    return {"postgresql_partition_by": f"{partition['strategy'].upper()} ({columns})"}


def _constraints(table: sa.Table, field: Field, target: str) -> None:
    spatial = extensions(field).get("spatialProfile")
    if spatial:
        valid: sa.ColumnElement[bool] = sa.func.ST_IsValid(table.c[field.name])
        if spatial["validity"] == "required":
            valid = sa.and_(valid, ~sa.func.ST_IsEmpty(table.c[field.name]))
        table.append_constraint(sa.CheckConstraint(valid, name=f"{field.name}_geometry"))
    if field.enum:
        table.append_constraint(
            sa.CheckConstraint(table.c[field.name].in_(field.enum), name=f"{field.name}_enum")
        )
    if field.partial_date:
        table.append_constraint(
            sa.CheckConstraint(
                table.c[field.name].op("~")(PARTIAL_DATE), name=f"{field.name}_precision"
            ).ddl_if(dialect="postgresql")
        )
    if field.reference:
        ref = field.reference
        columns = list(ref.fields)
        targets = [
            f"{target + '.' if target else ''}{ref.table}.{name}" for name in ref.target_fields
        ]
        if not any(
            list(key.column_keys) == columns
            and [element.target_fullname for element in key.elements] == targets
            for key in table.foreign_key_constraints
        ):
            table.append_constraint(
                sa.ForeignKeyConstraint(columns, targets, deferrable=True, initially="DEFERRED")
            )
