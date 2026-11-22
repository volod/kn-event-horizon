"""Offline schema pins and the shared KN extension registry."""

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator

from kn.contracts.diagnostics import ContractError

RESOURCES = Path(__file__).parent / "resources"
SATCOM = RESOURCES / "satcom" / "1.0.0.json"
PLATFORM = RESOURCES / "platform.json"
SCHEMA_FILES = ("odcs-3.1.0.json", "kn-extensions.json")


def platform_policy() -> dict[str, Any]:
    """The KN schemas and role kinds: the only places a storage contract can deploy to."""
    return dict(json.loads(PLATFORM.read_text(encoding="ascii")))


def pinned_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify both mandatory schema pins even when a document uses no extensions."""
    pins = json.loads((RESOURCES / "pins.json").read_text(encoding="ascii"))
    schemas: list[dict[str, Any]] = []
    for name in SCHEMA_FILES:
        content = (RESOURCES / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != pins.get(name):
            raise ContractError((), "checksum", f"restore the pinned schema: {name}")
        schema = json.loads(content)
        Draft201909Validator.check_schema(schema)
        schemas.append(schema)
    return schemas[0], schemas[1]
