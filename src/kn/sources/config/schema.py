"""Load the packaged crawler schema and expose its standard error vocabulary."""

import json
import re
from datetime import datetime
from functools import cache
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from kn.contracts.diagnostics import ContractError, Location

_RETRY_CLASSES = ("transient", "rate_limit", "permanent", "none")
_FORMATS = FormatChecker()
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
_INVALID_URI = re.compile(r"[^!-~]|[\\\"<>^`{|}]|%(?![0-9a-fA-F]{2})")


class CrawlerConfigError(ContractError):
    """A crawler configuration rejected before it can be used by a source consumer."""


@_FORMATS.checks("date-time", raises=ValueError)
def _date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not _TIMESTAMP.fullmatch(value):
        return False
    datetime.fromisoformat(value)
    return value.endswith("Z") or int(value[-2:]) < 60


@_FORMATS.checks("uri", raises=ValueError)
def _uri(value: object) -> bool:
    if not isinstance(value, str):
        return True
    parsed = urlsplit(value)
    port = parsed.port
    return (
        bool(parsed.hostname)
        and not parsed.netloc.endswith(":")
        and port != 0
        and not _INVALID_URI.search(value)
    )


@cache
def _validator() -> Draft202012Validator:
    schema = json.loads(
        files(__package__).joinpath("crawler.schema.json").read_text(encoding="ascii")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=_FORMATS)


def retry_class_for(code: str) -> str:
    """Look up the retry class shared by declarations and later ingestion consumers."""
    schema = _validator().schema
    assert isinstance(schema, dict)
    definitions = schema["$defs"]
    for retry_class in _RETRY_CLASSES:
        if code in definitions[f"{retry_class}Codes"]["enum"]:
            return retry_class
    raise ValueError("unknown standard source error code")


def _forbidden_property(error: ValidationError) -> tuple[str, ...]:
    constraint = error.validator_value
    instance = error.instance
    if error.validator == "not" and isinstance(constraint, dict) and isinstance(instance, dict):
        forbidden = constraint.get("anyOf", ())
        return tuple(
            name for clause in forbidden for name in clause.get("required", ()) if name in instance
        )
    return ()


def _diagnostic(error: ValidationError) -> CrawlerConfigError:
    path: Location = tuple(error.absolute_path)
    rule = str(error.validator)
    constraint = error.validator_value
    instance = error.instance
    if rule == "required" and isinstance(constraint, list) and isinstance(instance, dict):
        missing = next(name for name in constraint if name not in instance)
        return CrawlerConfigError((*path, missing), rule, "include the required property")
    if forbidden := _forbidden_property(error):
        return CrawlerConfigError(
            (*path, forbidden[0]), rule, "remove this property for the selected mode"
        )
    hints = {
        "additionalProperties": "remove unrecognized properties",
        "anyOf": "include a supported alternative",
        "dependentRequired": "include the companion property",
        "format": "use the declared format",
        "uniqueItems": "remove duplicate entries",
    }
    return CrawlerConfigError(
        path, rule, hints.get(rule, "satisfy the crawler configuration schema")
    )


def validate_schema(document: dict[str, Any]) -> None:
    """Reject a schema violation with a JSON Pointer and without echoing values."""
    if error := next(_validator().iter_errors(document), None):
        raise _diagnostic(error) from None
