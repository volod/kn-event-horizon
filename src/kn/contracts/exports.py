"""Engine artifacts derived from one supported logical profile."""

import hashlib
from typing import Any

from kn.contracts.loader import canonical
from kn.contracts.model import Contract, Field, Table
from kn.contracts.postgresql import manifest as postgresql_manifest
from kn.contracts.sqlalchemy import PARTIAL_DATE


def _avro_type(field: Field) -> object:
    types: dict[str, object] = {
        "string": "string",
        "integer": "long",
        "boolean": "boolean",
        "date": {"type": "int", "logicalType": "date"},
        "number": {
            "type": "bytes",
            "logicalType": "decimal",
            "precision": field.precision,
            "scale": field.scale,
        },
    }
    return types[field.logical_type]


def avro(contract: Contract, table: Table) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    for field in table.fields:
        item: dict[str, Any] = {
            "name": field.name,
            "type": _avro_type(field),
            "kn.fieldId": field.field_id,
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
        "fields": fields,
    }


def elasticsearch(contract: Contract, table: Table) -> dict[str, Any]:
    types = {
        "string": "keyword",
        "integer": "long",
        "boolean": "boolean",
        "date": "date",
        "number": "keyword",
    }
    properties = {}
    for field in table.fields:
        item = {"type": types[field.logical_type]}
        if field.logical_type == "date":
            item["format"] = "strict_date"
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
    types = {
        "string": "string",
        "integer": "integer",
        "boolean": "boolean",
        "date": "string",
        "number": "string",
    }
    properties: dict[str, Any] = {}
    for field in table.fields:
        item: dict[str, Any] = {"type": types[field.logical_type]}
        if field.partial_date:
            item["pattern"] = PARTIAL_DATE
        if field.logical_type == "date":
            item["format"] = "date"
        if field.logical_type == "number":
            item["pattern"] = r"^-?[0-9]+(?:\.[0-9]+)?$"
        if field.enum:
            item["enum"] = list(field.enum)
        properties[field.name] = item if field.required else {"anyOf": [item, {"type": "null"}]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [field.name for field in table.fields if field.required],
        "properties": properties,
    }


def artifacts(contract: Contract) -> dict[str, str]:
    """Canonical content is independent of input object order and machine paths."""
    result = {"postgresql/metadata.json": canonical(postgresql_manifest(contract)) + "\n"}
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
