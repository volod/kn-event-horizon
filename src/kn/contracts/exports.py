"""Engine artifacts derived from one supported logical profile."""

import hashlib
from typing import Any

from kn.contracts.ddl import postgresql_ddl
from kn.contracts.diagnostics import ContractError
from kn.contracts.field_exports import json_field
from kn.contracts.model import Contract, Field, Table, canonical
from kn.contracts.physical import EXACTLY_ONE, column_names, extensions, presence_rules
from kn.contracts.postgresql import manifest as postgresql_manifest
from kn.contracts.templates import contract_docs, dbt_sources, pydantic_models


def _avro_type(field: Field) -> object:
    types: dict[str, object] = {
        "string": "string",
        "integer": "long",
        "boolean": "boolean",
        "date": {"type": "int", "logicalType": "date"},
        "timestamp": {"type": "long", "logicalType": "timestamp-micros"},
        "number": {
            "type": "bytes",
            "logicalType": "decimal",
            "precision": field.precision,
            "scale": field.scale,
        },
    }
    return types[field.logical_type]


# Avro forbids defining a named type with a primitive type name, in any namespace.
AVRO_PRIMITIVES = frozenset(
    {"null", "boolean", "int", "long", "float", "double", "bytes", "string"}
)


def avro(contract: Contract, table: Table) -> dict[str, Any]:
    if table.name in AVRO_PRIMITIVES:
        number = next(i for i, item in enumerate(contract.tables) if item.name == table.name)
        raise ContractError(
            ("schema", number, "name"),
            "avro",
            "rename tables named after Avro primitive types; those names are reserved",
        )
    fields: list[dict[str, Any]] = []
    for field in table.fields:
        item: dict[str, Any] = {
            "name": field.name,
            "type": _avro_type(field),
            "kn.fieldId": field.field_id,
            "kn.extensions": extensions(field),
        }
        if not field.required:
            item.update(type=["null", item["type"]], default=None)
        fields.append(item)
    return {
        "type": "record",
        "name": table.name,
        "namespace": f"kn.{contract.schema}",
        "kn.contractVersion": contract.version,
        "kn.contractDigest": contract.digest,
        "kn.extensions": extensions(table),
        "fields": fields,
    }


def elasticsearch(contract: Contract, table: Table) -> dict[str, Any]:
    types = {
        "string": "keyword",
        "integer": "long",
        "boolean": "boolean",
        "date": "date",
        "timestamp": "date",
        "number": "keyword",
    }
    properties = {}
    for field in table.fields:
        item = {"type": types[field.logical_type]}
        if field.logical_type in {"date", "timestamp"}:
            item["format"] = "strict_date" if field.logical_type == "date" else "strict_date_time"
        properties[field.name] = item
    return {
        "dynamic": "strict",
        "date_detection": False,
        "numeric_detection": False,
        "_meta": {
            "contract_version": contract.version,
            "contract_digest": contract.digest,
            "decimal_encoding": "exact base-10 strings",
        },
        "properties": properties,
    }


def json_schema(table: Table) -> dict[str, Any]:
    """Portable wire validation uses exact decimal strings, never JSON floating point."""
    result = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [field.name for field in table.fields if field.required],
        "properties": {field.name: json_field(field) for field in table.fields},
        "x-kn": extensions(table),
    }
    rules = [_json_presence(table, rule) for rule in presence_rules(table)]
    return {**result, "allOf": rules} if rules else result


def _json_presence(table: Table, rule: dict[str, Any]) -> dict[str, Any]:
    """An absent optional property is null, as in SQL and the Pydantic models."""
    present = [
        {"required": [name], "properties": {name: {"not": {"type": "null"}}}}
        for name in column_names(table, rule["fields"])
    ]
    if rule["rule"] == EXACTLY_ONE:
        return {"oneOf": present}
    return {"anyOf": [{"allOf": present}, {"not": {"anyOf": present}}]}


def artifacts(contract: Contract) -> dict[str, str]:
    """Canonical content is independent of input object order and machine paths."""
    result = {
        "postgresql/metadata.json": canonical(postgresql_manifest(contract)) + "\n",
        "postgresql/schema.sql": postgresql_ddl(contract),
        "pydantic/models.py": pydantic_models(contract),
        # JSON is a YAML 1.2 subset, giving dbt a deterministic, escaped YAML document.
        "dbt/sources.yaml": canonical(dbt_sources(contract)) + "\n",
        "docs/contract.md": contract_docs(contract),
        "contract.json": contract.document_json + "\n",
        "references.json": contract.references_json + "\n",
    }
    for table in sorted(contract.tables, key=lambda table: table.name):
        for engine, content in [
            ("avro", avro(contract, table)),
            ("elasticsearch", elasticsearch(contract, table)),
            ("jsonschema", json_schema(table)),
        ]:
            result[f"{engine}/{table.name}.json"] = canonical(content) + "\n"
    return result


def artifact_digests(contract: Contract) -> dict[str, str]:
    return {
        name: hashlib.sha256(content.encode()).hexdigest()
        for name, content in artifacts(contract).items()
    }
