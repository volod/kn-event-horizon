"""Check cross-field constraints that the crawler schema cannot express."""

from collections.abc import Hashable, Iterable
from functools import cache
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from kn.contracts.diagnostics import Location
from kn.sources.config.schedule import valid_cron
from kn.sources.config.schema import CrawlerConfigError
from kn.sources.seeds import reviewed_catalogue

_RAW_REDISTRIBUTION = {
    "owner_private": {"forbidden"},
    "forbidden": {"forbidden"},
    "restricted": {"forbidden", "restricted"},
    "permitted": {"forbidden", "restricted", "permitted"},
}


@cache
def _reviewed_ids() -> frozenset[str]:
    return frozenset(row["source_id"] for row in reviewed_catalogue())


def _identity(config: dict[str, Any]) -> str:
    source_id: str = config["identity"]["source_id"]
    domain = source_id.split(":", 1)[0]
    if not config["parse"]["entry_point"].startswith(f"kn.domains.{domain}."):
        raise CrawlerConfigError(
            ("parse", "entry_point"), "parserDomain", "use the source ID's domain namespace"
        )
    if config["approval"]["state"] == "enabled" and source_id not in _reviewed_ids():
        raise CrawlerConfigError(
            ("identity", "source_id"), "catalogueReference", "use an exact reviewed catalogue ID"
        )
    return domain


def _unique(values: Iterable[Hashable], location: Location) -> None:
    seen: set[Hashable] = set()
    for index, value in enumerate(values):
        if value in seen:
            raise CrawlerConfigError((*location, index), "duplicateKey", "use unique keys")
        seen.add(value)


def _ordered(lower: float, upper: float, location: Location) -> None:
    if lower > upper:
        raise CrawlerConfigError(
            location, "range", "keep the lower bound at or below the upper bound"
        )


def _endpoints(access: dict[str, Any]) -> None:
    allowed_hosts = set(access.get("allowed_hosts", ()))
    secret_names = {name.casefold() for name in access.get("secret_query_parameters", ())}
    for index, endpoint in enumerate(access.get("endpoints", ())):
        location = ("access", "endpoints", index)
        parsed = urlsplit(endpoint)
        if parsed.hostname not in allowed_hosts:
            raise CrawlerConfigError(location, "allowedHost", "use an exact allowlisted host")
        if any(
            key.casefold() in secret_names
            for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        ):
            raise CrawlerConfigError(
                location, "secretQuery", "supply secrets through an environment alias"
            )


def _access(config: dict[str, Any], domain: str) -> None:
    access = config["access"]
    _endpoints(access)
    if curated := access.get("curated"):
        location = ("access", "curated")
        if curated["directory"].split("/")[:3] != ["domains", domain, "curation"]:
            raise CrawlerConfigError(
                (*location, "directory"), "curationPath", "use the domain curation directory"
            )
        _unique(
            (curated[field] for field in ("uri_field", "capture_time_field", "curator_field")),
            location,
        )
    if package := access.get("package"):
        location = ("access", "package")
        expected = package["expected_files"]
        _unique((file["path"] for file in expected), (*location, "expected_files"))
        _ordered(len(expected), package["limits"]["max_files"], (*location, "limits", "max_files"))
        if (dialect := package.get("csv_dialect")) and dialect["delimiter"] == dialect["quotechar"]:
            raise CrawlerConfigError(
                (*location, "csv_dialect", "quotechar"),
                "csvDialect",
                "use a quote character distinct from the delimiter",
            )
    _watches(access.get("watches", []), config["cursor"])


def _watches(watches: list[dict[str, Any]], cursor: dict[str, Any]) -> None:
    _unique((watch["id"] for watch in watches), ("access", "watches"))
    for index, watch in enumerate(watches):
        location = ("access", "watches", index)
        _ordered(
            watch["min_window_seconds"],
            watch["lookback_seconds"],
            (*location, "min_window_seconds"),
        )
        _ordered(
            cursor["overlap_seconds"], watch["lookback_seconds"], (*location, "lookback_seconds")
        )


def _rights(config: dict[str, Any]) -> None:
    rights = config["rights"]
    raw = config["raw"]
    if "retention_days" in rights:
        _ordered(raw["retention_days"], rights["retention_days"], ("raw", "retention_days"))
    adapter = config["access"]["method"] == "adapter_api"
    policy = rights.get("export_policy", "owner_private" if adapter else None)
    if policy is not None and raw["redistribution"] not in _RAW_REDISTRIBUTION[policy]:
        raise CrawlerConfigError(
            ("raw", "redistribution"),
            "ownerPrivate"
            if adapter and policy in {"owner_private", "forbidden"}
            else "exportPolicy",
            "keep raw redistribution within reviewed export rights",
        )
    if (
        adapter
        and policy in {"restricted", "permitted"}
        and "owner_export_approval_reference" not in rights
    ):
        raise CrawlerConfigError(
            ("rights", "owner_export_approval_reference"),
            "ownerPrivate",
            "record owner approval before changing the private export policy",
        )


def _data_rules(config: dict[str, Any]) -> None:
    quality = config["quality"]
    locations = (("quality", "expected_volume"), ("monitoring", "expected_records"))
    for block, key in locations:
        bounds = config[block][key]
        _ordered(bounds["min"], bounds["max"], (block, key, "max"))
    _unique((item["field"] for item in quality["ranges"]), ("quality", "ranges"))
    for index, item in enumerate(quality["ranges"]):
        _ordered(item["min"], item["max"], ("quality", "ranges", index, "max"))
    _unique(
        (tuple(sorted(rule["condition"].items())) for rule in config["errors"]),
        ("errors",),
    )
    _unique(
        (item["field_id"] for item in config.get("exchange", {}).get("field_ownership", [])),
        ("exchange", "field_ownership"),
    )


def validate_semantics(config: dict[str, Any]) -> None:
    """Validate relationships between individual schema-valid entries."""
    domain = _identity(config)
    if not valid_cron(config["schedule"]["cron"]):
        raise CrawlerConfigError(
            ("schedule", "cron"), "cron", "use a valid five-field numeric UTC expression"
        )
    cursor = config["cursor"]
    if cursor["strategy"] == "window":
        _ordered(cursor["overlap_seconds"], cursor["window_seconds"], ("cursor", "overlap_seconds"))
    _access(config, domain)
    _data_rules(config)
    _rights(config)
