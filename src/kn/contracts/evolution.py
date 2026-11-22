"""Conservative, explicit evolution: breaking or ambiguous changes are refused."""

from dataclasses import replace

import sqlalchemy as sa
from alembic.operations import Operations

from kn.contracts.model import Contract, Field, Table, canonical
from kn.contracts.physical import extensions
from kn.contracts.registry import marker_table
from kn.contracts.sqlalchemy import column_type, metadata


def additions(previous: Contract, current: Contract) -> dict[str, tuple[str, ...]]:
    """Validate compatibility before any DDL, including a genuine semantic version advance."""
    old_version = tuple(map(int, previous.version.split(".")))
    new_version = tuple(map(int, current.version.split(".")))
    if current.contract_id != previous.contract_id or current.schema != previous.schema:
        raise ValueError("contract identity or storage schema changed")
    if new_version <= old_version:
        raise ValueError("evolution requires a newer contract version")
    if (
        previous.references_json != current.references_json
        or previous.source_profile != current.source_profile
    ):
        raise ValueError("reference or source profile changes require a reviewed migration")
    changes: dict[str, tuple[str, ...]] = {}
    new_tables = {table.name: table for table in current.tables}
    for old in previous.tables:
        new = new_tables.get(old.name)
        if new is None or old.csv != new.csv:
            raise ValueError(f"breaking table change: {old.name}")
        added = _table_additions(old, new)
        if added:
            changes[old.name] = added

    return changes


def _table_additions(old: Table, new: Table) -> tuple[str, ...]:
    if old.extensions_json != new.extensions_json:
        raise ValueError("table metadata changes require a reviewed migration")
    fields = {field.name: field for field in new.fields}
    for field in old.fields:
        candidate = fields.get(field.name)
        if candidate is None or replace(candidate, description=field.description) != field:
            raise ValueError(f"breaking field change: {old.name}.{field.name}")
    old_names = {field.name for field in old.fields}
    added = tuple(field for field in new.fields if field.name not in old_names)
    if any(_needs_review(field) for field in added):
        raise ValueError(f"new fields need a reviewed backfill/constraint migration: {old.name}")
    return tuple(field.name for field in added)


def _needs_review(field: Field) -> bool:
    return bool(
        field.required
        or field.primary_key
        or field.reference
        or field.enum
        or field.partial_date
        or (extensions(field).keys() - {"fieldId"})
    )


def evolve(
    operations: Operations,
    previous: Contract,
    current: Contract,
    *,
    marker_schema: str | None = None,
) -> None:
    """Called only by reviewed revisions referencing immutable old and new snapshots."""
    changes = additions(previous, current)
    model = metadata(current)
    marker = marker_table(marker_schema)
    installed = (
        operations.get_bind()
        .execute(
            sa.select(marker.c.version, marker.c.digest).where(
                marker.c.contract_id == previous.contract_id
            )
        )
        .one_or_none()
    )
    if installed != (previous.version, previous.digest):
        raise ValueError("installed contract does not match the previous migration snapshot")
    old_tables = {table.name for table in previous.tables}
    new_tables = [table for table in model.tables.values() if table.name not in old_tables]
    model.create_all(operations.get_bind(), tables=new_tables, checkfirst=False)
    for name, columns in changes.items():
        table = current.table(name)
        for field in table.fields:
            if field.name in columns:
                operations.add_column(
                    name,
                    sa.Column(
                        field.name,
                        column_type(field),
                        nullable=True,
                        comment=field.description or None,
                    ),
                    schema=current.schema,
                )
    _apply_comments(operations, previous, current)
    operations.get_bind().execute(
        marker.update()
        .where(marker.c.contract_id == current.contract_id)
        .values(
            version=current.version,
            digest=current.digest,
            managed_tables_json=canonical([table.name for table in current.tables]),
        )
    )


def _apply_comments(operations: Operations, previous: Contract, current: Contract) -> None:
    """Descriptions are the only accepted change to existing tables and fields."""
    for old in previous.tables:
        new = current.table(old.name)
        if new.description != old.description:
            if new.description:
                operations.create_table_comment(
                    old.name,
                    new.description,
                    existing_comment=old.description or None,
                    schema=current.schema,
                )
            else:
                operations.drop_table_comment(
                    old.name, existing_comment=old.description, schema=current.schema
                )
        fields = {field.name: field for field in new.fields}
        for field in old.fields:
            if fields[field.name].description != field.description:
                operations.alter_column(
                    old.name,
                    field.name,
                    comment=fields[field.name].description or None,
                    existing_comment=field.description or None,
                    existing_type=column_type(field),
                    existing_nullable=not field.required,
                    schema=current.schema,
                )
