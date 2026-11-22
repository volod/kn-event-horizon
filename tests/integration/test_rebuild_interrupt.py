"""A rebuild that is killed midway leaves the previous committed schemas in use."""

import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from kn import cli, operations
from kn.db.governance import verify
from tests.integration.harness import IntegrationDatabase
from tests.integration.test_rebuild import catalog

ROOT = Path(__file__).resolve().parents[2]
PROBE = "kn_rebuild_interrupt_probe"
WAIT_SECONDS = 60
POLL_SECONDS = 0.1
# The rebuild child sleeps in a reviewed seed loader, after every schema has been dropped and
# recreated in its transaction. The server notices the killed client within 100 ms.
CHILD = f"""
import os, sys
import sqlalchemy as sa
from kn import cli, operations
from kn.db import seeds
from tests.integration.harness import IntegrationDatabase

database = IntegrationDatabase.from_environment(os.environ)
options = "-c client_connection_check_interval=100"
engine = sa.create_engine(
    "postgresql+psycopg://", creator=lambda: database.connect(dbname=sys.argv[1], options=options)
)
seeds.REVIEWED_SEED_LOADERS = (
    ("space", lambda connection: connection.exec_driver_sql("SELECT pg_sleep({WAIT_SECONDS}) AS {PROBE}")),
)
operations.engine_from_env = lambda: engine
raise SystemExit(cli.main(["--json", "db", "rebuild"]))
"""


def _sleeping_backend(engine: Engine) -> int:
    deadline = time.monotonic() + WAIT_SECONDS
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            pid = connection.scalar(
                sa.text(
                    "SELECT pid FROM pg_stat_activity WHERE datname = current_database() "
                    "AND state = 'active' AND query LIKE :probe AND pid <> pg_backend_pid()"
                ),
                {"probe": f"%AS {PROBE}%"},
            )
            if pid is not None:
                return int(pid)
            connection.rollback()
            time.sleep(POLL_SECONDS)
    raise AssertionError("the rebuild never reached its seed loader")


def _wait_for_exit(engine: Engine, pid: int) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    with engine.connect() as connection:
        while connection.scalar(
            sa.text("SELECT count(*) FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid}
        ):
            assert time.monotonic() < deadline, "the killed rebuild kept its server session"
            connection.rollback()
            time.sleep(POLL_SECONDS)


def test_a_killed_rebuild_leaves_the_previous_schemas_in_use(
    integration_database: IntegrationDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = f"kn_rebuild_kill_{secrets.token_hex(8)}"
    engine = sa.create_engine(
        "postgresql+psycopg://", creator=lambda: integration_database.connect(dbname=name)
    )
    with integration_database.connect(autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            monkeypatch.setattr(operations, "engine_from_env", lambda: engine)
            monkeypatch.setenv("KN_ENVIRONMENT", "development")
            assert cli.main(["--json", "db", "rebuild"]) == 0
            with engine.begin() as connection:
                # A row that the next rebuild would drop with its table.
                connection.exec_driver_sql(
                    "INSERT INTO space.satcom_imports VALUES ('kept', '1.0.0', 'kept', 'kept')"
                )
                before = catalog(connection)
            child = subprocess.Popen([sys.executable, "-c", CHILD, name], cwd=ROOT)
            try:
                pid = _sleeping_backend(engine)
                with engine.connect() as observer:
                    assert catalog(observer) == before
                    observer.exec_driver_sql("SET lock_timeout = '200ms'")
                    # Readers wait for the rebuild instead of seeing a partial schema.
                    with pytest.raises(OperationalError, match="lock timeout"):
                        observer.exec_driver_sql("SELECT * FROM space.satcom_imports")
                os.kill(child.pid, signal.SIGKILL)
                child.wait(timeout=WAIT_SECONDS)
                _wait_for_exit(engine, pid)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
            with engine.connect() as connection:
                assert catalog(connection) == before
                kept = "SELECT count(*) FROM space.satcom_imports WHERE import_id = 'kept'"
                assert connection.scalar(sa.text(kept)) == 1
                verify(connection)
            assert cli.main(["--json", "db", "rebuild"]) == 0
            with engine.connect() as connection:
                assert connection.scalar(sa.text(kept)) == 0
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
