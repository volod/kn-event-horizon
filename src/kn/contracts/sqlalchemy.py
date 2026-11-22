"""Compile PostgreSQL metadata from the engine-neutral contract."""

from typing import Any

import sqlalchemy as sa

from kn.contracts.model import Contract, Field

PARTIAL_DATE = r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$"
NAMING = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


def column_type(field: Field) -> sa.types.TypeEngine[Any]:
    """Never coerce exact source decimals into binary floats."""
    types: dict[str, sa.types.TypeEngine[Any]] = {
        "string": sa.Text(),
        "integer": sa.BigInteger(),
        "boolean": sa.Boolean(),
        "date": sa.Date(),
        "number": sa.Numeric(field.precision, field.scale),
    }
    return types[field.logical_type]


def metadata(contract: Contract, schema: str | None = None) -> sa.MetaData:
    """Create fresh metadata; snapshot references remain deferrable across cyclic tables."""
    target = schema if schema is not None else contract.schema
    result = sa.MetaData(schema=target or None, naming_convention=NAMING)
    for model in contract.tables:
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
        )
        for field in model.fields:
            _constraints(table, field, target)
    return result


def _constraints(table: sa.Table, field: Field, target: str) -> None:
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
        table.append_constraint(
            sa.ForeignKeyConstraint(columns, targets, deferrable=True, initially="DEFERRED")
        )
