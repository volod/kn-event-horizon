"""Run the normal rebuild command through committed transactions in a temporary database."""

import secrets

import pytest
import sqlalchemy as sa
from psycopg import sql

from kn import cli, operations
from kn.db.governance import verify
from tests.integration.harness import IntegrationDatabase
from tests.integration.test_rebuild import catalog


def test_cli_rebuild_commits_repeatably_and_released_guard_preserves_data(
    integration_database: IntegrationDatabase,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    name = f"kn_rebuild_test_{secrets.token_hex(8)}"
    engine = sa.create_engine(
        "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
    )
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            monkeypatch.setattr(operations, "engine_from_env", lambda: engine)
            monkeypatch.setenv("KN_ENVIRONMENT", "development")
            assert cli.main(["--json", "db", "rebuild"]) == 0
            with engine.connect() as connection:
                first = catalog(connection)
                verify(connection)
            assert cli.main(["--json", "db", "rebuild"]) == 0
            with engine.begin() as connection:
                assert catalog(connection) == first
                connection.exec_driver_sql("CREATE TABLE semantic.keep_on_release (id integer)")
                connection.exec_driver_sql("INSERT INTO semantic.keep_on_release VALUES (7)")
            monkeypatch.setenv("KN_ENVIRONMENT", "released")
            assert cli.main(["--json", "db", "rebuild"]) == 1
            with engine.connect() as connection:
                assert connection.scalar(sa.text("SELECT id FROM semantic.keep_on_release")) == 7
            assert '"code": "E_INPUT"' in caplog.text
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
