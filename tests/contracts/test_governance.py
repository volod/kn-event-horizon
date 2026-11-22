"""Development safety gates need no service endpoint."""

import pytest

from kn.db.rebuild import rebuild


def test_rebuild_refuses_released_environment_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KN_ENVIRONMENT", "released")
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
