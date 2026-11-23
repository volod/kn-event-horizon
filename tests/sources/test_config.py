"""Validate every source shape and exercise the offline validation entry point."""

import json
from pathlib import Path
from typing import Any

import pytest

from kn.contracts.document import read_document
from kn.sources.config import load_crawler_config
from kn.sources.config.schema import CrawlerConfigError, retry_class_for, validate_schema

CONFIGS = Path(__file__).parent / "fixtures" / "config"
NETWORK_KEYS = (
    "allowed_hosts",
    "redirect_policy",
    "request_budget",
    "rate_limit",
    "conditional_requests",
    "content_types",
)


@pytest.fixture
def config() -> dict[str, Any]:
    return read_document(CONFIGS / "http.yaml")


def write_config(root: Path, config: dict[str, Any]) -> Path:
    path = root / "crawler.json"
    path.write_text(json.dumps(config), encoding="ascii")
    return path


@pytest.mark.parametrize("name", ["http", "curated", "package", "watch", "adapter"])
def test_reviewable_shapes(name: str) -> None:
    config = load_crawler_config(CONFIGS / f"{name}.yaml")
    assert config["approval"]["state"] == "candidate"


@pytest.mark.parametrize("method", ["http_csv", "http_xml", "feed", "bulk_file", "html_permitted"])
def test_other_network_methods(method: str, config: dict[str, Any], tmp_path: Path) -> None:
    config["access"]["method"] = method
    del config["access"]["pagination"]
    assert load_crawler_config(write_config(tmp_path, config))["access"]["method"] == method


def test_drive_package_and_binary_limits(config: dict[str, Any], tmp_path: Path) -> None:
    package = read_document(CONFIGS / "package.yaml")
    access = package["access"]
    access.update({key: config["access"][key] for key in NETWORK_KEYS})
    access["allowed_hosts"] = ["www.googleapis.com"]
    access["content_types"] = ["application/zip"]
    access["package"]["drive"] = {"service_account_key_file_env": "FIXTURE_DRIVE_KEY_FILE"}
    path = write_config(tmp_path, package)
    assert load_crawler_config(path)["access"]["package"]["drive"]
    access["allowed_hosts"].append("extra.example.test")
    with pytest.raises(CrawlerConfigError, match=r"\$/access/allowed_hosts"):
        load_crawler_config(write_config(tmp_path, package))


@pytest.mark.parametrize(
    ("name", "location", "replacement", "diagnostic"),
    [
        ("http", ("identity", "source_id"), "row-4", "/identity/source_id"),
        ("http", ("identity", "source_id"), "space:row-4\n", "/identity/source_id"),
        ("http", ("identity", "labels", "uk"), "", "/identity/labels/uk"),
        ("http", ("schedule", "timezone"), "Europe/Kyiv", "/schedule/timezone"),
        ("http", ("schedule", "cron"), "60 */2 * * *", "/schedule/cron"),
        ("http", ("schedule", "cron"), "5-2 * * * *", "/schedule/cron"),
        ("http", ("schedule", "cron"), "*/0 * * * *", "/schedule/cron"),
        ("http", ("schedule", "cron"), "* * * *", "/schedule/cron"),
        ("http", ("cursor", "backfill_namespace"), "live", "/cursor/backfill_namespace"),
        ("http", ("cursor", "field"), None, "/cursor/field"),
        ("http", ("raw", "format"), "zip", "/raw/format"),
        ("http", ("parse", "entry_point"), "kn.domains.gdelt.fixture:parse", "/parse/entry_point"),
        ("http", ("parse", "schema_fingerprint"), "wrong", "/parse/schema_fingerprint"),
        ("http", ("mapping", "record_key"), [], "/mapping/record_key"),
        ("http", ("mapping", "record_key"), ["id", "id"], "/mapping/record_key"),
        ("http", ("mapping", "codes", 0, "code"), 1, "/mapping/codes/0/code"),
        ("http", ("quality", "ranges", 0, "max"), -1, "/quality/ranges/0/max"),
        (
            "http",
            ("monitoring", "expected_records", "min"),
            1001,
            "/monitoring/expected_records/max",
        ),
        ("http", ("access", "allowed_hosts"), ["elsewhere.example.test"], "/access/endpoints/0"),
        ("http", ("access", "endpoints"), ["https://api.example.test:/a"], "/access/endpoints/0"),
        ("http", ("access", "endpoints"), ["http://api.example.test/a"], "/access/endpoints/0"),
        (
            "http",
            ("access", "endpoints"),
            ["https://user@api.example.test/a"],
            "/access/endpoints/0",
        ),
        (
            "http",
            ("access", "endpoints"),
            ["https://api.example.test/?%61ccess_token=x"],
            "/access/endpoints/0",
        ),
        ("http", ("access", "redirect_policy"), "any", "/access/redirect_policy"),
        ("http", ("errors", 0, "condition", "status"), 600, "/errors/0/condition/status"),
        ("http", ("errors", 0, "code"), "unreviewed", "/errors/0/code"),
        (
            "curated",
            ("access", "curated", "directory"),
            "domains/space/curation-other",
            "/access/curated/directory",
        ),
        (
            "package",
            ("access", "package", "expected_files", 0, "headers"),
            None,
            "/access/package/expected_files/0/headers",
        ),
        (
            "package",
            ("access", "package", "limits", "max_files"),
            1,
            "/access/package/limits/max_files",
        ),
        (
            "package",
            ("access", "package", "default_directory"),
            "../escape",
            "/access/package/default_directory",
        ),
        (
            "watch",
            ("access", "watches", 0, "min_window_seconds"),
            86401,
            "/access/watches/0/min_window_seconds",
        ),
        ("adapter", ("access", "adapter", "name"), "unreviewed", "/access/adapter/name"),
        ("adapter", ("access", "adapter", "resources"), ["users"], "/access/adapter/resources/0"),
        (
            "adapter",
            ("access", "pagination", "page_size_parameter"),
            "size",
            "/access/pagination/page_size_parameter",
        ),
        ("adapter", ("exchange", "direction"), "bidirectional", "/exchange/export_profile"),
        (
            "adapter",
            ("rights", "export_policy"),
            "permitted",
            "/rights/owner_export_approval_reference",
        ),
        ("adapter", ("raw", "redistribution"), "permitted", "/raw/redistribution"),
    ],
)
def test_invalid_shapes_report_exact_paths(
    tmp_path: Path,
    name: str,
    location: tuple[str | int, ...],
    replacement: object,
    diagnostic: str,
) -> None:
    config = read_document(CONFIGS / f"{name}.yaml")
    parent = config
    for part in location[:-1]:
        parent = parent[part]
    if replacement is None:
        del parent[location[-1]]
    else:
        parent[location[-1]] = replacement
    with pytest.raises(CrawlerConfigError) as caught:
        load_crawler_config(write_config(tmp_path, config))
    assert caught.value.path == f"${diagnostic}"


@pytest.mark.parametrize(
    ("code", "retry_class"),
    [
        ("transient_network", "transient"),
        ("rate_limited", "rate_limit"),
        ("auth_failed", "permanent"),
        ("permission_denied", "permanent"),
        ("not_modified", "none"),
        ("payload_invalid", "permanent"),
        ("schema_drift", "permanent"),
        ("integrity_lost", "permanent"),
        ("budget_exhausted", "permanent"),
    ],
)
def test_standard_retry_mapping(config: dict[str, Any], code: str, retry_class: str) -> None:
    rule = {
        "condition": {"kind": "signal", "name": "test"},
        "code": code,
        "retry_class": retry_class,
    }
    config["errors"] = [rule]
    assert retry_class_for(code) == retry_class
    validate_schema(config)
    rule["retry_class"] = "permanent" if retry_class == "transient" else "transient"
    with pytest.raises(CrawlerConfigError, match=r"\$/errors/0/retry_class: const"):
        validate_schema(config)


def test_unknown_standard_code_has_no_retry_class() -> None:
    with pytest.raises(ValueError, match="unknown standard source error code"):
        retry_class_for("unreviewed")


@pytest.mark.parametrize(
    ("status", "code", "retry_class"),
    [
        (304, "not_modified", "none"),
        (401, "auth_failed", "permanent"),
        (403, "permission_denied", "permanent"),
        (429, "rate_limited", "rate_limit"),
    ],
)
def test_standard_http_status_meaning(
    config: dict[str, Any], status: int, code: str, retry_class: str
) -> None:
    rule = {
        "condition": {"kind": "http_status", "status": status},
        "code": code,
        "retry_class": retry_class,
    }
    config["errors"] = [rule]
    validate_schema(config)
    rule.update(code="transient_network", retry_class="transient")
    with pytest.raises(CrawlerConfigError, match=r"\$/errors/0/code: const"):
        validate_schema(config)


def test_conflicting_error_condition(config: dict[str, Any], tmp_path: Path) -> None:
    config["errors"].append(
        {**config["errors"][1], "code": "budget_exhausted", "retry_class": "permanent"}
    )
    with pytest.raises(CrawlerConfigError, match=r"\$/errors/2: duplicateKey"):
        load_crawler_config(write_config(tmp_path, config))


def test_allowlist_disallows_ip_literals(config: dict[str, Any], tmp_path: Path) -> None:
    config["access"]["allowed_hosts"] = ["127.0.0.1"]
    config["access"]["endpoints"] = ["https://127.0.0.1/fixture"]
    with pytest.raises(CrawlerConfigError, match=r"\$/access/allowed_hosts/0"):
        load_crawler_config(write_config(tmp_path, config))


def test_id_range_cursor(config: dict[str, Any], tmp_path: Path) -> None:
    config["cursor"] = {"strategy": "id_range", "field": "seq", "backfill_namespace": "history"}
    assert load_crawler_config(write_config(tmp_path, config))["cursor"]["field"] == "seq"


def test_counterpart_export_shape(tmp_path: Path) -> None:
    config = read_document(CONFIGS / "adapter.yaml")
    config["exchange"] = {
        "direction": "bidirectional",
        "field_ownership": [{"field_id": "description", "owner": "counterpart"}],
        "export_profile": "fixture-export",
        "write_approval_reference": "fixture-write-review",
    }
    updated = load_crawler_config(write_config(tmp_path, config))
    assert updated["exchange"]["direction"] == "bidirectional"
