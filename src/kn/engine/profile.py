"""Admit the single-response snapshot profile supported by this engine."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never
from urllib.parse import urlsplit

from kn.archive.model import MAX_WARC_BODY, Limits
from kn.engine.checkpoints import DEFAULT_SCOPE, LIVE_NAMESPACE, StreamKey
from kn.review.model import digest
from kn.sources.config import load_runtime_config
from kn.sources.config.schema import CrawlerConfigError


@dataclass(frozen=True, slots=True)
class SnapshotProfile:
    stream: StreamKey
    entry_point: str
    schema_fingerprint: str
    config_digest: str
    endpoint: str
    port: int
    path: str
    timeout: int
    limits: Limits
    request_budget: int
    retention_days: int
    content_types: frozenset[str]
    record_key: tuple[str, ...]
    fields: tuple[tuple[str, str], ...]
    required_fields: frozenset[str]
    min_records: int
    max_records: int


def snapshot_profile(path: Path) -> SnapshotProfile:
    config = load_runtime_config(path)
    access, cursor, raw, mapping, quality = (
        config[key] for key in ("access", "cursor", "raw", "mapping", "quality")
    )
    if access["method"] != "http_json" or len(access["endpoints"]) != 1:
        _unsupported(("access",), "declare one http_json endpoint")
    if access.keys() & {"auth_env", "pagination", "watches"} or access["redirect_policy"] != "deny":
        _unsupported(("access",), "use an unauthenticated endpoint with redirects denied")
    if any(access["conditional_requests"].values()):
        _unsupported(("access", "conditional_requests"), "disable conditional requests")
    if cursor["strategy"] != "snapshot_hash" or raw["format"] != "warc":
        _unsupported(("cursor",), "use a snapshot_hash cursor with WARC captures")
    _check_mapping(mapping, quality)

    endpoint = access["endpoints"][0]
    port, request_path = _loopback_target(endpoint)
    budget = access["request_budget"]
    return SnapshotProfile(
        stream=StreamKey(config["identity"]["source_id"], DEFAULT_SCOPE, LIVE_NAMESPACE),
        entry_point=config["parse"]["entry_point"],
        schema_fingerprint=config["parse"]["schema_fingerprint"],
        config_digest=digest(config),
        endpoint=endpoint,
        port=port,
        path=request_path,
        timeout=budget["timeout_seconds"],
        limits=Limits(
            min(budget["max_response_bytes"], MAX_WARC_BODY), budget["max_decoded_bytes"]
        ),
        request_budget=budget["max_requests"],
        retention_days=raw["retention_days"],
        content_types=frozenset(access["content_types"]),
        record_key=tuple(mapping["record_key"]),
        fields=tuple((entry["native"], entry["field_id"]) for entry in mapping["fields"]),
        required_fields=frozenset(quality["required_fields"]),
        min_records=quality["expected_volume"]["min"],
        max_records=quality["expected_volume"]["max"],
    )


def _loopback_target(endpoint: str) -> tuple[int, str]:
    target = urlsplit(endpoint)
    try:
        port = target.port
    except ValueError:
        port = None
    if (
        not target.hostname
        or not target.hostname.endswith(".localhost")
        or not port
        or "?" in endpoint
        or not endpoint.isascii()
        or "\\" in endpoint
    ):
        _unsupported(
            ("access", "endpoints", 0), "use HTTPS on a .localhost name with an explicit port"
        )
    return port, target.path or "/"


def _check_mapping(mapping: dict[str, Any], quality: dict[str, Any]) -> None:
    fields = mapping["fields"]
    if (
        any(mapping[name] for name in mapping.keys() - {"record_key", "fields"})
        or not fields
        or any("unit" in entry for entry in fields)
        or len({entry["field_id"] for entry in fields}) != len(fields)
    ):
        _unsupported(("mapping",), "declare unique text fields and a native record key")
    if quality["ranges"]:
        _unsupported(("quality", "ranges"), "use text-only snapshot validation")


def _unsupported(location: tuple[str | int, ...], hint: str) -> Never:
    raise CrawlerConfigError(location, "unsupportedProfile", hint)
