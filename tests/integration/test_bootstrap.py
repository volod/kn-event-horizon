"""The role bootstrap applied to a running database, as `make db-up` applies it on every start.

The bootstrap converges the KN schemas and roles to their declared state, so applying it here
changes nothing on a database that `make db-up` started.
"""

import threading

import psycopg
import yaml

from tests.deploy.bootstrap_sql import ROOT, bootstrap_script
from tests.integration.harness import Connection, IntegrationDatabase

MANIFEST = yaml.safe_load((ROOT / "deploy" / "versions.yaml").read_text(encoding="utf-8"))
POSTGIS = MANIFEST["images"]["postgres"]["components"]["postgis"]
CONCURRENT_RUNS = 4
ROUNDS = 3
# A blocked run waits for the others; a lock wait this long means a deadlock, not a slow host.
LOCK_TIMEOUT = "30s"


def _apply(database: IntegrationDatabase, script: str, start: threading.Barrier) -> None:
    with database.connect(autocommit=True) as connection:
        connection.execute("SELECT set_config('lock_timeout', %s, false)", [LOCK_TIMEOUT])
        for _ in range(ROUNDS):
            start.wait()
            connection.execute(script)


def test_concurrent_bootstrap_runs_all_succeed(integration_database: IntegrationDatabase) -> None:
    script = bootstrap_script()
    start = threading.Barrier(CONCURRENT_RUNS)
    failures: list[psycopg.Error] = []

    def run() -> None:
        try:
            _apply(integration_database, script, start)
        except psycopg.Error as error:
            failures.append(error)
            start.abort()
        except threading.BrokenBarrierError:
            pass  # another run failed; its error is reported

    threads = [threading.Thread(target=run) for _ in range(CONCURRENT_RUNS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert [str(error).splitlines()[0] for error in failures] == []


def test_the_bootstrap_brings_postgis_to_the_version_of_the_image(
    integration_database: IntegrationDatabase, db_connection: Connection
) -> None:
    with integration_database.connect(autocommit=True) as connection:
        connection.execute(bootstrap_script())

    row = db_connection.execute(
        "SELECT installed_version, default_version FROM pg_catalog.pg_available_extensions "
        "WHERE name = 'postgis'"
    ).fetchone()

    assert row == (POSTGIS, POSTGIS)
