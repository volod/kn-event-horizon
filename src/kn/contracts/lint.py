"""Validate ODCS and all registered KN families independently of compiler support."""

import re
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, FormatChecker

from kn.contracts.diagnostics import ContractError, Location, schema_error
from kn.contracts.document import read_document
from kn.contracts.schemas import SATCOM, pinned_schemas

SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _scope(path: Location) -> str:
    if not path:
        return "contract"
    if len(path) == 2 and path[0] == "schema":
        return "table"
    if len(path) >= 4 and path[-2] == "properties" and path[0] == "schema":
        return "field"
    return "other"


def _extensions(items: list[dict[str, Any]], path: Location, registry: dict[str, Any]) -> None:
    seen: set[str] = set()
    validator = Draft201909Validator(registry, format_checker=FormatChecker())
    for index, item in enumerate(items):
        location = (*path, "customProperties", index)
        name = item["property"]
        schema = registry["properties"].get(name)
        if schema is None:
            raise ContractError((*location, "property"), "extension", "use a registered kn.* name")
        if name in seen:
            raise ContractError((*location, "property"), "duplicate", "declare each extension once")
        seen.add(name)
        if _scope(path) not in schema["x-kn-scopes"]:
            scopes = ", ".join(schema["x-kn-scopes"])
            raise ContractError(location, "scope", f"place {name} on: {scopes}")
        errors = validator.iter_errors({name: item["value"]})
        if error := next(errors, None):
            # Replace the registry's property name with the actual ODCS value location.
            error.path.popleft()
            raise schema_error(error, (*location, "value"))


def _walk(node: Any, path: Location, registry: dict[str, Any]) -> None:
    if isinstance(node, list):
        for index, child in enumerate(node):
            _walk(child, (*path, index), registry)
    elif isinstance(node, dict):
        if "customProperties" in node:
            _extensions(node["customProperties"], path, registry)
        for key, child in node.items():
            if key != "customProperties":
                _walk(child, (*path, key), registry)


def lint_contract(path: Path = SATCOM) -> dict[str, Any]:
    """Return validated source metadata; lint does not claim it can be compiled."""
    odcs, registry = pinned_schemas()
    data = read_document(path)
    validator = Draft201909Validator(odcs, format_checker=FormatChecker())
    if error := next(validator.iter_errors(data), None):
        raise schema_error(error)
    if data["apiVersion"] != "v3.1.0":
        raise ContractError(("apiVersion",), "version", "use pinned ODCS v3.1.0")
    if not SEMVER.fullmatch(data["version"]):
        raise ContractError(("version",), "version", "use a major.minor.patch contract version")
    _walk(data, (), registry)
    return data
