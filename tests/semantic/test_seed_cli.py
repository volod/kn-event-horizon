"""The vocabulary entrypoint follows the English and machine-readable CLI contract."""

import json
import logging
from pathlib import Path

import pytest

from kn import cli
from kn.i18n import Translator
from kn.semantic.seeds import reviewed_snapshot


@pytest.mark.parametrize("machine", [False, True])
def test_seed_import_cli(machine: bool, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="kn.operator")
    arguments = [
        "vocabulary",
        "import-proposals",
        "--check",
        "--data-dir",
        str(tmp_path),
    ]
    assert cli.main([*arguments, *(["--json"] if machine else [])]) == 0
    reports = list((tmp_path / "seed-import").glob("*/reconciliation.json"))
    assert len(reports) == 1
    if machine:
        result = json.loads(caplog.records[-1].message)
        assert result["rows"] == 1173 and result["status"] == "reconciled"
        assert sum(result["counts"].values()) == result["rows"]
    else:
        assert caplog.records[-1].message == Translator().text(
            "cli.seed_ok", rows=1173, report=str(reports[0])
        )


def test_seed_import_failure_uses_input_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(cli, "discover_project_root", lambda: tmp_path)
    assert cli.main(["--json", "vocabulary", "import-proposals"]) == 1
    assert json.loads(caplog.records[-1].message) == {"error": {"code": "E_INPUT"}}


def test_reviewed_resources_load_outside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert len(reviewed_snapshot()["terms"]) == 825
