"""Record keys, versions and stated fields read through a reviewed crawler mapping."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from kn.contracts.model import canonical
from kn.identity.model import SourceKey
from kn.identity.tracking.delivery import Ordering

type Native = Mapping[str, Any]
UPDATED = "updated_at"


def ordering(mapping: Native) -> Ordering:
    """A version field orders versions, unless it is the record's updated time."""
    updated = {item["native"] for item in mapping.get("time_fields", ()) if _updated(item)}
    version = mapping.get("version_field")
    if version is not None and version not in updated:
        return "version"
    return "updated" if updated else "fetch"


def record_key(mapping: Native, source_id: str, native: Native) -> SourceKey:
    """One key field keeps its exact text; several form a canonical JSON array."""
    parts = [_text(native.get(name)) for name in mapping["record_key"]]
    if any(part is None for part in parts):
        raise ValueError("record_key_missing")
    key = parts[0] if len(parts) == 1 else canonical(parts)
    assert key is not None
    return SourceKey(source=source_id, key=key)


def version(mapping: Native, native: Native) -> str | None:
    name = mapping.get("version_field")
    return None if name is None else _text(native.get(name))


def updated_at(mapping: Native, native: Native) -> datetime | None:
    """The source updated time; a naive value needs the mapping's declared time zone."""
    for item in mapping.get("time_fields", ()):
        if _updated(item) and (value := _text(native.get(item["native"]))) is not None:
            parsed = (
                datetime.strptime(value, item["format"])
                if "format" in item
                else datetime.fromisoformat(value)
            )
            if parsed.tzinfo is None:
                if "timezone" not in item:
                    raise ValueError("time_invalid")
                parsed = parsed.replace(tzinfo=ZoneInfo(item["timezone"]))
            return parsed
    return None


def stated(mapping: Native, native: Native) -> dict[str, Any]:
    """Mapped fields the record states, by field ID. An omitted field is not stated.

    None marks a field stated empty: null, a blank string, or an empty list or object.
    """
    result: dict[str, Any] = {}
    for item in mapping["fields"]:
        if item["native"] in native:
            value = native[item["native"]]
            result[item["field_id"]] = None if _empty(value) else value
    return result


def _updated(item: Native) -> bool:
    return item.get("semantics") == UPDATED


def _empty(value: object) -> bool:
    if isinstance(value, str):
        return not value.strip()
    return value is None or (isinstance(value, list | dict) and not value)


def _text(value: object) -> str | None:
    if isinstance(value, bool) or _empty(value):
        return None
    if isinstance(value, int | str):
        return str(value)
    raise ValueError("record keys and versions are text or integers")
