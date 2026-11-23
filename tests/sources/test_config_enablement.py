"""Exercise local eligibility evidence and public source validation output."""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
import yaml

from kn import cli
from kn.contracts.document import read_document
from kn.i18n import Translator
from kn.sources.config import load_crawler_config
from kn.sources.config.schema import CrawlerConfigError

CONFIG = Path(__file__).parent / "fixtures" / "config" / "http.yaml"
PASSING_REPORT = (
    '<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0">'
    '<testcase name="test_source_fixture"/></testsuite></testsuites>'
)


@pytest.fixture
def enabled(tmp_path: Path) -> dict[str, Any]:
    config = read_document(CONFIG)
    config["rights"] = {
        "terms_uri": "https://api.example.test/terms",
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-11-23T00:00:00Z",
        "licence": "fixture-only",
        "permission": "granted",
        "export_policy": "forbidden",
        "retention_days": 30,
    }
    config["approval"] = {
        "state": "enabled",
        "approver": "fixture-approver",
        "reference": "fixture-enable-1",
    }
    config["verification"] = {"fixtures": ["fixtures/payload.json"], "test_report": "run/suite.xml"}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures/payload.json").write_text("[]\n", encoding="ascii")
    (tmp_path / "run").mkdir()
    (tmp_path / "run/suite.xml").write_text(PASSING_REPORT, encoding="ascii")
    return config


def _write(root: Path, config: dict[str, Any]) -> Path:
    path = root / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="ascii")
    return path


@pytest.mark.parametrize(
    ("block", "key"),
    [
        ("rights", "terms_uri"),
        ("rights", "reviewer"),
        ("rights", "reviewed_at"),
        ("rights", "licence"),
        ("rights", "export_policy"),
        ("rights", "retention_days"),
        ("approval", "approver"),
        ("approval", "reference"),
        ("verification", "fixtures"),
        ("verification", "test_report"),
    ],
)
def test_enablement_requires_every_review_and_evidence_field(
    enabled: dict[str, Any], tmp_path: Path, block: str, key: str
) -> None:
    del enabled[block][key]
    with pytest.raises(CrawlerConfigError, match=rf"\$/{block}/{key}: required"):
        load_crawler_config(_write(tmp_path, enabled))


@pytest.mark.parametrize(
    ("block", "key", "value", "rule"),
    [
        ("rights", "permission", "pending", "const"),
        ("rights", "permission", "denied", "const"),
        ("rights", "reviewed_at", "2026-02-31T00:00:00Z", "format"),
        ("rights", "reviewed_at", "2026-11-23T00:00:00", "format"),
        ("rights", "reviewed_at", "2026-11-23T00:00:00+05:99", "format"),
        ("rights", "retention_days", 15, "range"),
        ("approval", "reference", "", "pattern"),
        ("identity", "source_id", "space:unknown", "catalogueReference"),
        ("verification", "test_report", "missing.xml", "evidenceFile"),
        ("verification", "fixtures", ["missing.json"], "evidenceFile"),
        ("verification", "fixtures", ["../outside.json"], "pattern"),
    ],
)
def test_enabled_config_validates_review_and_artifacts(
    enabled: dict[str, Any], tmp_path: Path, block: str, key: str, value: object, rule: str
) -> None:
    enabled[block][key] = value
    path = _write(tmp_path, enabled)
    with pytest.raises(CrawlerConfigError) as exc:
        load_crawler_config(path)
    location = ("raw", "retention_days") if key == "retention_days" else (block, key)
    suffix = "/0" if key == "fixtures" else ""
    assert (exc.value.path, exc.value.rule) == ("$/" + "/".join(location) + suffix, rule)


@pytest.mark.parametrize(
    "content",
    [
        '<testsuite tests="0"/>',
        '<testsuite tests="2"><testcase name="source"/></testsuite>',
        '<testsuite failures="1"><testcase name="source"/></testsuite>',
        '<testsuite><testcase name="source"><failure/></testcase></testsuite>',
        '<testsuite><testcase name="source"><error/></testcase></testsuite>',
        '<testsuite><testcase name="source"><skipped/></testcase></testsuite>',
        "<testsuites><testcase/></testsuites>",
        "<testsuite><testcase/></testsuite>",
        '<!DOCTYPE testsuite><testsuite><testcase name="source"/></testsuite>',
        "<testsuite",
    ],
)
def test_incomplete_and_failed_reports_refuse_enablement(
    enabled: dict[str, Any], tmp_path: Path, content: str
) -> None:
    (tmp_path / "run/suite.xml").write_text(content, encoding="ascii")
    with pytest.raises(CrawlerConfigError, match=r"\$/verification/test_report: testReport"):
        load_crawler_config(_write(tmp_path, enabled))


def test_missing_evidence_block_is_required(enabled: dict[str, Any], tmp_path: Path) -> None:
    del enabled["verification"]
    with pytest.raises(CrawlerConfigError, match=r"\$/verification: required"):
        load_crawler_config(_write(tmp_path, enabled))


def test_utf16_report_cannot_bypass_the_doctype_check(
    enabled: dict[str, Any], tmp_path: Path
) -> None:
    report = '<!DOCTYPE testsuite><testsuite><testcase name="source"/></testsuite>'
    (tmp_path / "run/suite.xml").write_bytes(report.encode("utf-16-le"))
    with pytest.raises(CrawlerConfigError, match=r"\$/verification/test_report: testReport"):
        load_crawler_config(_write(tmp_path, enabled))


def test_empty_evidence_file_refuses_enablement(enabled: dict[str, Any], tmp_path: Path) -> None:
    (tmp_path / "fixtures/payload.json").write_bytes(b"")
    with pytest.raises(CrawlerConfigError, match=r"\$/verification/fixtures/0: evidenceFile"):
        load_crawler_config(_write(tmp_path, enabled))


def test_fixture_symlinks_cannot_escape_evidence_root(
    enabled: dict[str, Any], tmp_path: Path
) -> None:
    working = tmp_path / "config"
    working.mkdir()
    for folder in ("run", "fixtures"):
        (tmp_path / folder).rename(working / folder)
    outside = tmp_path / "outside.json"
    (working / "fixtures/payload.json").rename(outside)
    (working / "fixtures/payload.json").symlink_to(outside)
    with pytest.raises(CrawlerConfigError, match=r"\$/verification/fixtures/0: evidenceFile"):
        load_crawler_config(_write(working, enabled))


def test_evidence_paths_are_checkout_relative(
    enabled: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("AGENTS.md", "pyproject.toml"):
        (tmp_path / name).touch()
    directory = tmp_path / "domains/space/sources"
    directory.mkdir(parents=True)
    monkeypatch.chdir(directory)
    assert load_crawler_config(_write(directory, enabled))["approval"]["state"] == "enabled"


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_cli_validates_and_localizes(
    enabled: dict[str, Any], tmp_path: Path, caplog: pytest.LogCaptureFixture, locale: str
) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    path = str(_write(tmp_path, enabled))
    expected = {"source_id": "space:row-4", "state": "enabled", "status": "valid"}
    assert cli.main(["source", "validate", path, "--locale", locale]) == 0
    translator = Translator(locale)
    assert caplog.records[-1].message == translator.text(
        "cli.source_config_ok", source_id="space:row-4", state=translator.text("cli.source_enabled")
    )
    assert cli.main(["--json", "--locale", locale, "source", "validate", path]) == 0
    assert json.loads(caplog.records[-1].message) == expected

    del enabled["approval"]["reference"]
    path = str(_write(tmp_path, enabled))
    assert cli.main(["--locale", locale, "source", "validate", path]) == 1
    assert caplog.records[-1].message == Translator(locale).text(
        "cli.source_config_diagnostic",
        path="$/approval/reference",
        rule="required",
        hint="include the required property",
    )


@pytest.mark.parametrize(
    ("body", "path", "rule"),
    [
        ("access: [", "$", "syntax"),
        ("version: 1\nversion: 2\n", "$", "duplicate"),
        ("identity: &id {}\nparse: *id\n", "$", "alias"),
        ("secret-like-field: value\n", "$", "additionalProperties"),
        (
            "version: 1\nidentity: {example-secret-value: '\\x00'}",
            "$/identity",
            "additionalProperties",
        ),
        ('version: 1\nidentity: {example-secret-value: "\\0"}', "$", "character"),
    ],
)
def test_cli_redacts_input_and_returns_stable_diagnostic(
    body: str, path: str, rule: str, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(body, encoding="ascii")
    for locale in ("en", "uk"):
        assert cli.main(["--json", "--locale", locale, "source", "validate", str(config_path)]) == 1
        message = caplog.records[-1].message
        assert "secret" not in message
        error = json.loads(message)["error"]
        assert (error["code"], error["path"], error["rule"]) == ("E_SOURCE_CONFIG", path, rule)
