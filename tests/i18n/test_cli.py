"""Bilingual operator goldens, locale precedence, and stable machine output."""

import json
import logging
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError

from kn import cli
from kn.i18n import Translator
from kn.metadata import ProjectInfo

GOLDENS = Path(__file__).with_name("goldens.json")


@pytest.fixture(autouse=True)
def fixed_terminal_width(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "80")


def test_ukrainian_help_is_selected_before_the_help_action(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["--locale", "uk", "--help"])
    assert error.value.code == 0
    output = capsys.readouterr().out
    assert Translator("uk").text("cli.info_help") in output
    assert "show this help" not in output


def test_nested_help_has_one_usage_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["--locale", "uk", "space", "satcom", "--help"])
    assert error.value.code == 0
    output = capsys.readouterr().out
    assert output.count(Translator("uk").text("cli.usage")) == 1


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_info_and_help_goldens(
    locale: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = json.loads(GOLDENS.read_text(encoding="ascii"))[locale]
    monkeypatch.setattr(cli, "project_info", lambda: ProjectInfo("kn-event-horizon", "kn", "1.2.3"))
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["--locale", locale, "info"]) == 0
    assert caplog.records[-1].message == expected["info"]
    for arguments, key in [(["--help"], "help"), (["space", "satcom", "--help"], "nested_help")]:
        with pytest.raises(SystemExit) as error:
            cli.main(["--locale", locale, *arguments])
        assert error.value.code == 0
        assert capsys.readouterr().out == expected[key]


def test_locale_precedence_and_no_state_between_invocations(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    monkeypatch.setenv("KN_LOCALE", "uk")
    assert cli.main(["info"]) == 0
    assert caplog.records[-1].message.startswith("\u041f\u0440\u043e\u0454\u043a\u0442:")
    assert cli.main(["info", "--locale=en"]) == 0
    assert caplog.records[-1].message.startswith("Project:")
    monkeypatch.delenv("KN_LOCALE")
    assert cli.main(["info"]) == 0
    assert caplog.records[-1].message.startswith("Project:")


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_json_identity_and_errors_are_stable(
    locale: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["--locale", locale, "--json", "info"]) == 0
    assert set(json.loads(caplog.records[-1].message)) == {"distribution", "version", "package"}

    def fail(action: str) -> dict[str, object]:
        raise SQLAlchemyError("private-password")

    monkeypatch.setattr(cli, "database_operation", fail)
    assert cli.main(["--locale", locale, "--json", "db", "verify"]) == 1
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_DATABASE"}}
    assert "private-password" not in caplog.text
    assert cli.main(["--locale", locale, "db", "verify"]) == 1
    assert caplog.records[-1].message == Translator(locale).text("cli.database_error")


def test_invalid_locale_does_not_silently_default_to_english(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert cli.main(["--locale", "ru", "info"]) == 2
    assert "E_LOCALE" in caplog.text


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_argument_errors_are_localized_and_machine_errors_are_json(
    locale: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["--locale", locale, "unknown"])
    assert error.value.code == 2
    assert Translator(locale).text("cli.arguments_error", prog="kn") in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        cli.main(["--locale", locale, "--json", "unknown"])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": {"code": "E_ARGUMENTS"}}


@pytest.mark.parametrize("locale", ["bad", "ua", "", "../../other", "en_US"])
def test_malformed_and_unknown_locale_values_fail_cleanly(
    locale: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert cli.main(["--locale", locale, "info"]) == 2
    assert "E_LOCALE" in caplog.text
