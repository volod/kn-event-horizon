"""Expand the registered field-review context declarations."""

from typing import Any

from kn.contracts.model import Table


def field_contexts(table: Table, declaration: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    record = tuple(declaration["recordFields"])
    contexts = {}
    if declaration.get("defaultFieldContext") == "record":
        contexts = {
            field.field_id: record if field.field_id in record else (*record, field.field_id)
            for field in table.fields
        }
    contexts.update(
        {field: tuple(context) for field, context in declaration["fieldContexts"].items()}
    )
    return contexts
