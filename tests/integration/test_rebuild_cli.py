"""Run the normal rebuild command through committed transactions in a temporary database."""

import json
import secrets
from pathlib import Path

import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import Engine

from kn import cli, operations
from kn.contracts.registry import registered_contracts
from kn.db.governance import verify
from kn.review.journal import Journal
from kn.review.targets import ContractResolver
from tests.integration.harness import IntegrationDatabase
from tests.integration.review_fixtures import SATCOM, TERMINAL, approve, assert_stamps, first
from tests.integration.test_rebuild import catalog


def test_cli_rebuild_commits_repeatably_and_released_guard_preserves_data(
    integration_database: IntegrationDatabase,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    source_package: Path,
    tmp_path: Path,
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
            monkeypatch.setenv("DATA_DIR", str(tmp_path))
            assert cli.main(["--json", "db", "rebuild"]) == 0
            with engine.connect() as connection:
                first = catalog(connection)
                verify(connection)
            _assert_satcom_review_replay(engine, source_package, tmp_path, caplog)
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


def _assert_satcom_review_replay(
    engine: Engine, source_package: Path, data_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO", logger="kn.operator")
    command = ["--json", "space", "satcom", "import", str(source_package)]
    assert cli.main(command) == 0
    resolver = ContractResolver.registered(registered_contracts())
    dataset = resolver.dataset(SATCOM, "terminal_models")
    with engine.begin() as connection:
        row = first(connection, dataset, terminal_id=TERMINAL)
        target = dataset.target(row, "factual", "space.satcom.terminal_models.mass_antenna_kg")
        decision = approve(connection, Journal(data_dir), resolver, target)

    expected = {"target_id": target.target_id, "contract_id": SATCOM, "dataset": target.dataset}
    assert cli.main(["--json", "db", "rebuild"]) == 0
    assert _replay_report(caplog) == [{**expected, "state": "pending"}]
    for status in ("imported", "already_imported"):
        assert cli.main(command) == 0
        assert json.loads(caplog.records[-1].message)["status"] == status
        assert _replay_report(caplog) == [{**expected, "state": "applied"}]
        with engine.connect() as connection:
            assert_stamps(connection, resolver, (decision,))


def _replay_report(caplog: pytest.LogCaptureFixture) -> list[dict[str, str]]:
    path = Path(json.loads(caplog.records[-1].message)["verification_replay"])
    return json.loads(path.read_text(encoding="ascii"))
