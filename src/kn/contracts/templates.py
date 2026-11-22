"""Small typed-model, dbt, and documentation templates for the supported profile."""

import keyword
from typing import Any

from pydantic import BaseModel

from kn.contracts.diagnostics import ContractError
from kn.contracts.model import Contract, Field, Table
from kn.contracts.physical import extensions
from kn.contracts.sqlalchemy import PARTIAL_DATE


def model_name(table: Table) -> str:
    return "".join(part.capitalize() for part in table.name.split("_"))


def pydantic_models(contract: Contract) -> str:
    """Native strict values; JSON mode retains Pydantic's decimal and date encodings."""
    lines = [
        '"""Generated from the contract. Regenerate instead of editing."""',
        "import builtins as _kn_builtins",
        "import datetime as _kn_datetime",
        "import decimal as _kn_decimal",
        "import typing as _kn_typing",
        "",
        "import pydantic as _kn_pydantic",
        "",
    ]
    names: set[str] = set()
    for table in sorted(contract.tables, key=lambda item: item.name):
        name = model_name(table)
        if name in names or name in {
            "BaseModel",
            "Field",
            "Literal",
            "Decimal",
            "Annotated",
            "ConfigDict",
            "AwareDatetime",
        }:
            raise ContractError((), "model", "table names must produce distinct Python class names")
        names.add(name)
        lines += [
            "",
            f"class {name}(_kn_pydantic.BaseModel):",
            "    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)",
        ]
        for index, field in enumerate(table.fields):
            lines.append(_model_field(table, field, index))
    return "\n".join(lines) + "\n"


def _model_field(table: Table, field: Field, index: int) -> str:
    attribute = field.name
    if (
        keyword.iskeyword(attribute)
        or hasattr(BaseModel, attribute)
        or attribute.startswith("model_")
    ):
        attribute = f"kn_field_{index}"
    if attribute != field.name and any(other.name == attribute for other in table.fields):
        raise ContractError((), "model", "rename fields that collide with generated Python aliases")
    annotation = _annotation(field)
    default = "" if field.required else "default=None, "
    if not field.required:
        annotation += " | None"
    info = {"x-kn": extensions(field)}
    return (
        f"    {attribute}: {annotation} = _kn_pydantic.Field({default}alias={field.name!r}, "
        f"description={field.description!a}, json_schema_extra={info!a})"
    )


def _annotation(field: Field) -> str:
    if field.enum:
        return "_kn_typing.Literal[" + ", ".join(ascii(value) for value in field.enum) + "]"
    if field.partial_date:
        return (
            f"_kn_typing.Annotated[_kn_builtins.str, _kn_pydantic.Field(pattern={PARTIAL_DATE!r})]"
        )
    if field.logical_type == "number":
        return (
            f"_kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits={field.precision}, "
            f"decimal_places={field.scale}, allow_inf_nan=False)]"
        )
    return {
        "string": "_kn_builtins.str",
        "integer": "_kn_builtins.int",
        "boolean": "_kn_builtins.bool",
        "date": "_kn_datetime.date",
        "timestamp": "_kn_pydantic.AwareDatetime",
    }[field.logical_type]


def dbt_sources(contract: Contract) -> dict[str, Any]:
    return {
        "version": 2,
        "sources": [
            {
                "name": contract.schema,
                "schema": contract.schema,
                "meta": {"contract_id": contract.contract_id, "contract_digest": contract.digest},
                "tables": [
                    {
                        "name": table.name,
                        "description": table.description,
                        "meta": extensions(table),
                        "columns": [
                            {
                                "name": field.name,
                                "description": field.description,
                                "meta": extensions(field),
                            }
                            for field in table.fields
                        ],
                    }
                    for table in sorted(contract.tables, key=lambda item: item.name)
                ],
            }
        ],
    }


def _cell(value: str) -> str:
    return (
        value.encode("ascii", "backslashreplace").decode().replace("|", "\\|").replace("\n", "<br>")
    )


def contract_docs(contract: Contract) -> str:
    lines = [
        f"# {_cell(contract.contract_id)}",
        "",
        f"Version: {contract.version}",
        "",
        f"Digest: `{contract.digest}`",
        "",
        f"Storage schema: `{contract.schema}`",
        "",
    ]
    for table in sorted(contract.tables, key=lambda item: item.name):
        lines += [
            f"## {table.name}",
            "",
            _cell(table.description),
            "",
            "| Field | Stable ID | Type | Required | Primary key | Description |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for field in table.fields:
            cells = [
                field.name,
                field.field_id,
                field.logical_type,
                str(field.required),
                str(field.primary_key),
                field.description,
            ]
            lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " |")
        lines += [""]
    lines += [
        "## Contract metadata",
        "",
        "All ODCS and KN metadata is retained in `contract.json`.",
        "Reference definitions used for compilation are in `references.json`.",
        "",
    ]
    return "\n".join(lines)
