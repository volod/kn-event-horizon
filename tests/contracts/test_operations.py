"""Normal CLI paths and secret-safe failures with local database projections."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from jsonschema import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from kn import cli, operations
from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata


def test_contract_and_space_commands_use_the_real_profile(
    source_package: Path, tmp_path: Path
) -> None:
    assert cli.main(["contract", "lint"]) == 0
    assert cli.main(["contract", "compile", "--check"]) == 0
    assert cli.main(["contract", "compile", "--output", str(tmp_path / "schemas")]) == 0
    assert cli.main(["space", "satcom", "validate", str(source_package)]) == 0
    # The default generated/ output is exercised in an isolated working directory.


def test_import_command_archives_and_is_idempotent(
    source_package: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = sa.create_engine("sqlite://")
    contract = load_contract()
    metadata(contract, "").create_all(engine)
    monkeypatch.setattr(operations, "engine_from_env", lambda: engine)
    monkeypatch.setattr(operations, "verify_contracts", lambda *a: None)
    real_import = operations.import_package
    monkeypatch.setattr(operations, "import_package", lambda c, p, m: real_import(c, p, m, ""))
    # Keep the in-memory database alive across command invocations.
    monkeypatch.setattr(engine, "dispose", lambda: None)
    arguments = [
        "space",
        "satcom",
        "import",
        str(source_package),
        "--data-dir",
        str(tmp_path / "data"),
    ]
    assert cli.main(arguments) == 0
    assert cli.main(arguments) == 0
    assert len(list((tmp_path / "data" / "satcom-import").glob("*/manifest.json"))) == 1


def test_database_commands_dispatch_and_dispose_even_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MagicMock()
    monkeypatch.setattr(operations, "engine_from_env", lambda: engine)
    upgrade, rebuild, verify = MagicMock(), MagicMock(), MagicMock(return_value="verified")
    monkeypatch.setattr(operations, "upgrade", upgrade)
    monkeypatch.setattr(operations, "rebuild", rebuild)
    monkeypatch.setattr(operations, "verify", verify)
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    for action in ("upgrade", "rebuild", "verify"):
        assert cli.main(["db", action]) == 0
    assert upgrade.call_count == rebuild.call_count == 1
    assert verify.call_count == engine.dispose.call_count == 3
    verify.side_effect = SQLAlchemyError("private-password")
    assert cli.main(["db", "verify"]) == 1
    assert engine.dispose.call_count == 4


@pytest.mark.parametrize(
    "error",
    [SQLAlchemyError("private-password"), ValidationError("bad contract"), ValueError("bad input")],
)
def test_command_failures_are_actionable_and_secret_safe(
    error: Exception, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(*args: object) -> None:
        raise error

    monkeypatch.setattr(cli, "database_operation", fail)
    assert cli.main(["db", "verify"]) == 1
    assert "private-password" not in caplog.text
