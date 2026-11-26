"""Committed CLI rebuilds after database loss and concurrent SQL-backed minting."""

import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.exc import DBAPIError

from kn import cli, operations
from kn.db.rebuild import rebuild
from kn.identity import store
from kn.identity.journal import Journal
from tests.identity.fixtures import KEY, NOW, A, history
from tests.identity.test_journal import mint
from tests.integration.harness import IntegrationDatabase
from tests.integration.identity_fixtures import seed_identity_fixture
from tests.integration.test_model_baseline import _snapshot


def test_cli_after_database_drop_preserves_complete_identity_projection(
    integration_database: IntegrationDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = f"kn_identity_drop_{secrets.token_hex(8)}"
    journal = Journal(tmp_path)
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    snapshots = []
    with integration_database.connect(autocommit=True) as admin:
        for locale in (None, "en", "uk"):
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            engine = sa.create_engine(
                "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
            )
            try:
                if locale is None:
                    with engine.begin() as connection:
                        rebuild(connection, data_dir=tmp_path)
                    events = history()
                    # Append the unlink and its replacement in one batch to exercise the
                    # immediate active-link index. Every other event uses a separate write.
                    for batch in (
                        *(events[i : i + 1] for i in range(12)),
                        events[12:14],
                        *(events[i : i + 1] for i in range(14, len(events))),
                    ):
                        with engine.begin() as connection:
                            store.apply(
                                connection,
                                journal,
                                lambda locked, batch=batch: locked.append_batch(batch),
                            )
                else:
                    monkeypatch.setattr(operations, "engine_from_env", lambda engine=engine: engine)
                    assert cli.main(["--locale", locale, "--json", "db", "rebuild"]) == 0
                with engine.connect() as connection:
                    snapshots.append(_snapshot(connection, [store.contract()]))
            finally:
                engine.dispose()
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    assert snapshots[0] == snapshots[1] == snapshots[2]
    assert len(journal.read()) == 20


def test_concurrent_sql_writers_mint_once_and_reject_unsupported_isolation(
    integration_database: IntegrationDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = f"kn_identity_concurrency_{secrets.token_hex(8)}"
    journal = Journal(tmp_path)
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    engine = sa.create_engine(
        "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
    )
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with engine.begin() as connection:
                rebuild(connection, data_dir=tmp_path)

            def submit(_: int) -> str:
                with engine.begin() as connection:
                    return store.apply(
                        connection,
                        journal,
                        lambda locked: locked.mint(
                            KEY,
                            "core.organization",
                            occurred_at=NOW,
                            actor="engine:test",
                            reason="Concurrent first sight",
                            evidence="archive:test",
                        ),
                    )

            with ThreadPoolExecutor(max_workers=3) as pool:
                ids = list(pool.map(submit, range(6)))
            assert len(set(ids)) == len(journal.read()) == 1
            with engine.connect() as connection:
                assert connection.scalar(sa.text("SELECT kn_id FROM identity.objects")) == ids[0]
            with (
                engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection,
                connection.begin(),
                pytest.raises(ValueError, match="READ COMMITTED"),
            ):
                store.replay(connection, journal)
            with engine.connect() as connection, pytest.raises(ValueError, match="caller-owned"):
                store.replay(connection, journal)
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_caught_sql_failure_restores_projection_and_pending_mint_replays(
    rebuild_connection: sa.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = rebuild_connection
    journal = Journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    real_project = store._project

    def fail(conn, locked, count):
        real_project(conn, locked, count)
        conn.exec_driver_sql("SELECT 1 / 0")

    monkeypatch.setattr(store, "_project", fail)
    with pytest.raises(DBAPIError, match="division by zero"):
        store.apply(
            connection,
            journal,
            lambda locked: locked.append(seed_identity_fixture(tmp_path / "fixture").read()[0]),
        )
    assert connection.scalar(sa.text("SELECT count(*) FROM identity.objects")) == 0
    assert len(journal.read()) == 1
    monkeypatch.setattr(store, "_project", real_project)
    store.replay(connection, journal)
    assert connection.scalar(sa.text("SELECT kn_id FROM identity.objects")) == A
    assert mint(journal) == A
