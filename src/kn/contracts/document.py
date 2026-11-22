"""Read unambiguous JSON-compatible YAML without executing tags or expanding aliases."""

import json
import math
from collections.abc import Hashable
from pathlib import Path
from typing import Any

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node

from kn.contracts.diagnostics import ContractError, Location

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_DEPTH = 32


class ContractLoader(yaml.SafeLoader):
    """Reject duplicate keys, aliases, and YAML-specific values before schema validation."""

    def compose_node(self, parent: Node | None, index: Any) -> Node | None:
        if self.check_event(AliasEvent):
            raise ContractError((), "alias", "expand YAML aliases explicitly")
        return super().compose_node(parent, index)

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Hashable, Any]:
        result: dict[Hashable, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ContractError((), "key", "use string mapping keys")
            if key in result:
                raise ContractError((), "duplicate", "remove duplicate mapping keys")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


# A date in a contract is a string, not an implicitly constructed Python date.
ContractLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _json_value(value: Any, path: Location = ()) -> None:
    if len(path) > MAX_DOCUMENT_DEPTH:
        raise ContractError(path, "depth", f"limit nesting to {MAX_DOCUMENT_DEPTH} levels")
    if isinstance(value, dict):
        for key, child in value.items():
            _json_value(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _json_value(child, (*path, index))
    elif isinstance(value, float) and not math.isfinite(value):
        raise ContractError(path, "number", "use finite JSON numbers")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ContractError(path, "type", "use JSON-compatible YAML values")


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError((), "duplicate", "remove duplicate mapping keys")
        result[key] = value
    return result


def read_document(path: Path) -> dict[str, Any]:
    """Load exactly one JSON or YAML mapping, with bounded input and safe parse errors."""
    with path.open("rb") as stream:
        content = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ContractError((), "size", f"limit documents to {MAX_DOCUMENT_BYTES} bytes")
    try:
        text = content.decode("utf-8")
        data = (
            json.loads(text, object_pairs_hook=_json_pairs)
            if path.suffix.lower() == ".json"
            else yaml.load(text, Loader=ContractLoader)
        )
        _json_value(data)
    except json.JSONDecodeError as error:
        hint = f"use well-formed JSON; check line {error.lineno}, column {error.colno}"
        raise ContractError((), "syntax", hint) from None
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        hint = "use one well-formed YAML or JSON document"
        if mark:
            hint += f"; check line {mark.line + 1}, column {mark.column + 1}"
        raise ContractError((), "syntax", hint) from None
    except (RecursionError, UnicodeError):
        raise ContractError((), "syntax", "use UTF-8 and reduce document nesting") from None
    if not isinstance(data, dict):
        raise ContractError((), "type", "use a contract object at the document root")
    return data
