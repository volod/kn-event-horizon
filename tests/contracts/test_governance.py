"""Development safety gates need no service endpoint."""

import pytest

from kn.db.rebuild import rebuild


@pytest.mark.parametrize("environment", [None, "released", "production", "Development", ""])
def test_rebuild_refuses_released_environment_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
    environment: str | None,
) -> None:
    monkeypatch.delenv("KN_ENVIRONMENT", raising=False)
    if environment is not None:
        monkeypatch.setenv("KN_ENVIRONMENT", environment)
    with pytest.raises(ValueError, match="released data"):
        rebuild(None)


def test_bad_connection_configuration_never_contains_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kn.cli import main

    monkeypatch.setenv("KN_DATABASE_URL", "not-a-url:private-password")
    assert main(["db", "upgrade"]) == 1


def test_schema_checksum_tampering_is_refused(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    from kn.contracts import schemas
    from kn.contracts.loader import load_contract

    resource = tmp_path / "resources"
    shutil.copytree(schemas.RESOURCES, resource)
    (resource / "odcs-3.1.0.json").write_text("{}")
    monkeypatch.setattr(schemas, "RESOURCES", resource)
    with pytest.raises(ValueError, match="checksum"):
        load_contract()


def test_password_file_connection_hides_credentials(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kn.db.connection import engine_from_env

    secret = tmp_path / "password"
    secret.write_text("private-password\n")
    monkeypatch.setenv("KN_DATABASE_URL", "postgresql://postgres@127.0.0.1/kn")
    monkeypatch.setenv("KN_DATABASE_PASSWORD_FILE", str(secret))
    engine = engine_from_env()
    assert engine.hide_parameters
    assert engine.url.password == "private-password"
    assert "private-password" not in str(engine.url)
    engine.dispose()
    secret.write_text("")
    with pytest.raises(ValueError, match="non-empty"):
        engine_from_env()
    monkeypatch.delenv("KN_DATABASE_URL")
    with pytest.raises(ValueError, match="required"):
        engine_from_env()
    monkeypatch.setenv("KN_DATABASE_URL", "sqlite://")
    with pytest.raises(ValueError, match="PostgreSQL"):
        engine_from_env()


def test_rebuild_command_guard_precedes_engine_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import MagicMock

    from kn import operations
    from kn.cli import main

    monkeypatch.setenv("KN_ENVIRONMENT", "released")
    engine = MagicMock(side_effect=AssertionError("database accessed"))
    monkeypatch.setattr(operations, "engine_from_env", engine)
    assert main(["db", "rebuild"]) == 1
    engine.assert_not_called()


def test_rebuild_requires_caller_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    connection = MagicMock()
    connection.in_transaction.return_value = False
    with pytest.raises(ValueError, match="transaction"):
        rebuild(connection)
    connection.execute.assert_not_called()


def test_rebuild_refusal_names_the_guard(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from kn.cli import main
    from kn.i18n import Translator

    monkeypatch.setenv("KN_ENVIRONMENT", "released")
    assert main(["db", "rebuild"]) == 1
    assert caplog.records[-1].message == Translator().text("cli.rebuild_refused")
    assert "KN_ENVIRONMENT=development" in caplog.records[-1].message
    caplog.clear()
    assert main(["--json", "db", "rebuild"]) == 1
    assert '"code": "E_INPUT"' in caplog.records[-1].message
