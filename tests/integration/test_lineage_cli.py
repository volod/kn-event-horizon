"""`kn lineage` against PostgreSQL returns the goldens of the in-memory lineage view."""

import json
import logging
import secrets
from pathlib import Path

import pytest
import sqlalchemy as sa
from psycopg import sql

from kn import cli, operations
from kn.db.rebuild import rebuild
from kn.evidence.lineage import SqlEvidenceRows
from kn.evidence.store import evidence_tables, record
from tests.e2e.test_lineage_cli import GOLDENS, rendered
from tests.identity.lineage_fixtures import CASES, build
from tests.integration.harness import IntegrationDatabase


def test_the_cli_reads_identity_and_evidence(
    integration_database: IntegrationDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data_dir = tmp_path / "data"
    fixture = build(data_dir)
    expected = json.loads(GOLDENS.read_text("ascii"))
    machine = rendered(tmp_path / "memory")
    name = f"kn_lineage_{secrets.token_hex(8)}"
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    engine = sa.create_engine(
        "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
    )
    monkeypatch.setattr(operations, "engine_from_env", lambda: engine)
    modes: list[str] = []

    class Recorded(SqlEvidenceRows):
        def __init__(self, connection: sa.Connection) -> None:
            modes.append(connection.exec_driver_sql("SHOW transaction_read_only").scalar_one())
            super().__init__(connection)

    monkeypatch.setattr(operations, "SqlEvidenceRows", Recorded)
    caplog.set_level(logging.INFO, logger="kn.operator")
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with engine.begin() as connection:
                rebuild(connection, data_dir=data_dir)
                assert record(connection, fixture.records) > 0
            with engine.connect() as connection:
                claims = evidence_tables()["claims"]
                before = connection.scalar(sa.select(sa.func.count()).select_from(claims))
            for case_name, case in CASES.items():
                assert cli.main([*case.arguments]) == 0
                assert caplog.records[-1].message == expected[case_name], case_name
                assert cli.main(["--json", *case.arguments]) == 0
                result = json.loads(caplog.records[-1].message)
                assert result == json.loads(json.dumps(machine[case_name]["json"]))
            with engine.connect() as connection:
                assert connection.scalar(sa.select(sa.func.count()).select_from(claims)) == before
            assert modes and set(modes) == {"on"}
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
