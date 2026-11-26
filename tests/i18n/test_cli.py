"""English operator goldens and stable machine output."""

import json
import logging
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError

from kn import cli
from kn.i18n import Translator
from kn.metadata import ProjectInfo
from tests.e2e.support import normalize_usage

GOLDENS = Path(__file__).with_name("goldens.json")


def test_info_and_help_goldens(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = json.loads(GOLDENS.read_text(encoding="ascii"))
    monkeypatch.setenv("KN_LOCALE", "uk")
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setattr(cli, "project_info", lambda: ProjectInfo("kn-event-horizon", "kn", "1.2.3"))
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["info"]) == 0
    assert caplog.records[-1].message == expected["info"]
    for arguments, key in [(["--help"], "help"), (["space", "satcom", "--help"], "nested_help")]:
        with pytest.raises(SystemExit) as error:
            cli.main(arguments)
        assert error.value.code == 0
        assert normalize_usage(capsys.readouterr().out) == normalize_usage(expected[key])


def test_json_identity_and_errors_are_stable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["--json", "info"]) == 0
    assert set(json.loads(caplog.records[-1].message)) == {"distribution", "version", "package"}

    def fail(action: str) -> dict[str, object]:
        raise SQLAlchemyError("private-password")

    monkeypatch.setattr(cli, "database_operation", fail)
    assert cli.main(["--json", "db", "verify"]) == 1
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_DATABASE"}}
    assert "private-password" not in caplog.text
    assert cli.main(["db", "verify"]) == 1
    assert caplog.records[-1].message == Translator().text("cli.database_error")


def test_argument_errors_use_english_or_json(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["unknown"])
    assert error.value.code == 2
    assert capsys.readouterr().err == Translator().text("cli.arguments_error", prog="kn") + "\n"
    with pytest.raises(SystemExit) as error:
        cli.main(["unknown", "--json"])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": {"code": "E_ARGUMENTS"}}
