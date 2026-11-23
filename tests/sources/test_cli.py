"""List candidates in both interface locales with stable machine output."""

import json
import logging

import pytest

from kn import cli
from kn.i18n import Translator
from kn.sources.seeds import reviewed_catalogue


@pytest.mark.parametrize("locale", ["en", "uk"])
def test_source_list_localizes_interface_and_preserves_source_text(
    locale: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
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
    assert cli.main(["source", "list", "--locale", locale]) == 0
    heading, line = caplog.records[-1].message.splitlines()
    translator = Translator(locale)
    assert heading == translator.text("cli.source_heading")
    assert row["label"] in line
    assert translator.text("cli.source_candidate") in line
    assert translator.text("cli.source_unverified") in line
    assert cli.main(["source", "list", "--locale", locale, "--json"]) == 0
    assert json.loads(caplog.records[-1].message) == result


def test_empty_catalogue_and_unavailable_execution(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "source_list_operation", lambda: {"sources": []})
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert cli.main(["source", "list"]) == 0
    assert caplog.records[-1].message == Translator().text("cli.source_empty")
    with pytest.raises(SystemExit) as error:
        cli.main(["--json", "source", "run", "space:row-4"])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": {"code": "E_ARGUMENTS"}}
