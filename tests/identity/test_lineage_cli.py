"""The lineage command resolves its reference before it opens the evidence database."""

import json
import logging
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from kn import cli, operations
from tests.identity.lineage_fixtures import X1, build


def _run(caplog: pytest.LogCaptureFixture, *arguments: str) -> tuple[int, dict[str, object]]:
    caplog.set_level(logging.INFO, logger="kn.operator")
    code = cli.main(["--json", *arguments])
    return code, json.loads(caplog.records[-1].message)


def test_an_unknown_reference_is_refused_without_a_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    build(tmp_path)

    def unexpected() -> None:
        raise AssertionError("the database must not be opened")

    monkeypatch.setattr(operations, "engine_from_env", unexpected)
    for reference in ("kn:019b76da-a800-7000-8000-0000000000ff", "unknown:identifier"):
        code, result = _run(caplog, "lineage", reference, "--data-dir", str(tmp_path))
        assert (code, result) == (1, {"error": {"code": "E_INPUT"}})


def test_an_unavailable_database_reports_a_database_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    build(tmp_path)

    def unavailable() -> None:
        raise OperationalError("connect", {}, Exception("refused"))

    monkeypatch.setattr(operations, "engine_from_env", unavailable)
    code, result = _run(caplog, "lineage", X1, "--data-dir", str(tmp_path))
    assert (code, result) == (1, {"error": {"code": "E_DATABASE"}})
