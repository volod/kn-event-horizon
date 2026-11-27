"""List candidates with stable English and machine output."""

import json
import logging

import pytest

from kn import cli
from kn.i18n import Translator
from kn.sources.seeds import reviewed_catalogue


def test_source_list_preserves_source_text(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    row = reviewed_catalogue()[0]
    source = {
        "source_id": row["source_id"],
        "label": row["label"],
        "priority": row["priority"],
        "cadence": row["cadence"],
        "lifecycle_state": row["lifecycle_state"],
        "access_verification": row["access_verification"],
    }
    result = {"sources": [source]}
    monkeypatch.setattr(cli, "source_list_operation", lambda: result)
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["source", "list"]) == 0
    heading, line = caplog.records[-1].message.splitlines()
    translator = Translator()
    assert heading == translator.text("cli.source_heading")
    assert row["label"] in line
    assert translator.text("cli.source_candidate") in line
    assert translator.text("cli.source_unverified") in line
    assert cli.main(["source", "list", "--json"]) == 0
    assert json.loads(caplog.records[-1].message) == result


def test_empty_catalogue_and_missing_execution_argument(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "source_list_operation", lambda: {"sources": []})
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["source", "list"]) == 0
    assert caplog.records[-1].message == Translator().text("cli.source_empty")
    with pytest.raises(SystemExit) as error:
        cli.main(["--json", "source", "run"])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": {"code": "E_ARGUMENTS"}}


def test_source_status_rejects_invalid_config_before_database(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KN_DATABASE_URL", raising=False)
    assert (
        cli.main(
            ["--json", "source", "status", "tests/sources/fixtures/config/invalid-labels.yaml"]
        )
        == 1
    )
    error = json.loads(caplog.records[-1].message)["error"]
    assert (error["code"], error["path"], error["rule"]) == (
        "E_SOURCE_CONFIG",
        "$/identity/labels/uk",
        "required",
    )
