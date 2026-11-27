"""Check the status projection's stream boundaries, checkpoints and chronology."""

from datetime import timedelta

import sqlalchemy as sa

from kn.engine.checkpoints import Advance, StreamKey, advance_checkpoint
from kn.engine.state import ATTEMPTS, BATCHES, state_table
from kn.sources.status import MonitoringPolicy, read_source_status
from tests.engine.conftest import SOURCE
from tests.integration.ingestion_fixtures import LOADED, STARTED, attempt_row, batch_row

STREAM = StreamKey(SOURCE, "default", "live")
POLICY = MonitoringPolicy(freshness_seconds=60, failure_threshold=2)
NOW = LOADED + timedelta(seconds=60)


def test_checkpoint_lag_and_run_history_keep_streams_independent(engine: sa.Engine) -> None:
    backfill = StreamKey(SOURCE, STREAM.scope, "repair")
    other_scope = StreamKey(SOURCE, "other", STREAM.cursor_namespace)
    attempts = state_table(ATTEMPTS)
    with engine.begin() as connection:
        connection.execute(
            attempts.insert().values(
                **attempt_row(
                    STREAM,
                    started_at=STARTED,
                    status="failed",
                    finished_at=STARTED,
                    cursor_lag_seconds=157,
                )
            )
        )
        assert read_source_status(connection, STREAM, POLICY, now=NOW)["cursor_lag_seconds"] == 157
        for stream in (STREAM, backfill, other_scope):
            connection.execute(
                attempts.insert().values(
                    **attempt_row(
                        stream,
                        run_id="second",
                        started_at=LOADED,
                        status="success",
                        finished_at=LOADED,
                        mode="replay" if stream == STREAM else "fetch",
                    )
                )
            )
            connection.execute(
                state_table(BATCHES).insert().values(**batch_row(stream, run_id="second"))
            )
            advance_checkpoint(
                connection,
                stream,
                Advance("second", "page-1", "window", NOW if stream == STREAM else STARTED, LOADED),
                expected_revision=0,
            )
        live = read_source_status(connection, STREAM, POLICY, now=LOADED)
        assert live["cursor_lag_seconds"] == 0 and live["checkpoint_revision"] == 1
        assert live["stale"] and live["last_success_at"] == LOADED.isoformat()
        assert live["consecutive_failures"] == 1 and not live["failing"]
        assert live["last_confirmed_at"] is None
        for stream in (backfill, other_scope):
            isolated = read_source_status(connection, stream, POLICY, now=NOW)
            assert not isolated["stale"] and isolated["cursor_lag_seconds"] == 360
            assert isolated["consecutive_failures"] == 0

        connection.execute(
            state_table(BATCHES)
            .insert()
            .values(**batch_row(STREAM, "page-2", run_id="second", archive_batch_id="page-2"))
        )
        advance_checkpoint(
            connection,
            STREAM,
            Advance("second", "page-2", "window", NOW + timedelta(seconds=10), STARTED),
            expected_revision=1,
        )
        current = read_source_status(connection, STREAM, POLICY, now=NOW + timedelta(seconds=15))
        assert current["checkpoint_revision"] == 2 and current["cursor_lag_seconds"] == 5


def test_retry_with_clock_skew_and_unchanged_fetch_reset_health(engine: sa.Engine) -> None:
    attempts = state_table(ATTEMPTS)
    with engine.begin() as connection:
        for row in (
            attempt_row(STREAM, run_id="failed", status="blocked", finished_at=STARTED),
            attempt_row(STREAM, started_at=NOW),
            attempt_row(STREAM, attempt=2, started_at=LOADED),
        ):
            connection.execute(attempts.insert().values(**row))
        interrupted = read_source_status(connection, STREAM, POLICY, now=NOW)
        assert interrupted["state"] == "unfinished" and interrupted["last_attempt_number"] == 2
        assert interrupted["consecutive_failures"] == 1 and interrupted["stale"]
        connection.execute(
            attempts.update()
            .filter_by(**STREAM.columns(), run_id="run-1", attempt=2)
            .values(status="not_modified", finished_at=LOADED)
        )
        healthy = read_source_status(connection, STREAM, POLICY, now=NOW)
        assert healthy["state"] == "not_modified" and healthy["consecutive_failures"] == 0
        assert not healthy["stale"] and healthy["last_success_at"] is None
