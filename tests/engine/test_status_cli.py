"""Read source status from both real runs and the full registered outcome vocabulary."""

import json
import logging
from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest
import sqlalchemy as sa

from kn.cli import main
from kn.engine.checkpoints import StreamKey
from kn.engine.state import ATTEMPTS, ERRORS, ingestion_contract, state_table
from kn.sources import status
from kn.sources.catalogue import catalogue_table
from kn.sources.status import MonitoringPolicy, read_source_status
from tests.engine.conftest import SOURCE, ProfileFile, Site
from tests.engine.test_snapshot import invoke
from tests.integration.ingestion_fixtures import LOADED, STARTED, attempt_row, error_row

STREAM = StreamKey(SOURCE, "default", "live")
POLICY = MonitoringPolicy(freshness_seconds=60, failure_threshold=2)
NOW = LOADED + timedelta(seconds=60)
GOLDEN_TEXT = (
    "Source space:fixture-snapshot | Scope default | Namespace live | Catalogue paused | State partial\n"
    "Last attempt 2026-06-01T12:05:00+00:00 | Last success 2026-06-01T12:00:00+00:00"
    " | Last fetch confirmation 2026-06-01T12:00:00+00:00\n"
    "Stale yes (threshold 60 s) | Failing yes | Consecutive failures 2 | Last error schema_drift\n"
    "Records 2 | Claims 1 | Rejects 1 | Quarantined 1 | Bytes 0 | Requests 2/5\n"
    "Checkpoint revision 0 | Cursor lag (s) unknown"
)
GOLDEN_JSON = (
    '{"source_status": {"bytes_received": 0, "checkpoint_revision": 0, "claim_count": 1, '
    '"consecutive_failures": 2, "cursor_lag_seconds": null, "cursor_namespace": "live", '
    '"failing": true, "freshness_threshold_seconds": 60, '
    '"last_attempt_at": "2026-06-01T12:05:00+00:00", '
    '"last_attempt_finished_at": "2026-06-01T12:05:00+00:00", "last_attempt_mode": "fetch", '
    '"last_attempt_number": 1, "last_attempt_run_id": "latest", '
    '"last_confirmed_at": "2026-06-01T12:00:00+00:00", "last_error_code": "schema_drift", '
    '"last_success_at": "2026-06-01T12:00:00+00:00", "lifecycle_state": "paused", '
    '"quarantine_count": 1, "record_count": 2, "reject_count": 1, "request_budget": 5, '
    '"requests_used": 2, "scope": "default", "source_id": "space:fixture-snapshot", '
    '"stale": true, "state": "partial"}}'
)


class FixedClock(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = UTC) -> datetime:
        return NOW.astimezone(tz)


def logged_status(
    profile: ProfileFile, caplog: pytest.LogCaptureFixture, *options: str, exit_code: int = 0
) -> str:
    caplog.set_level(logging.INFO, logger="kn.operator")
    assert main(["source", "status", str(profile.path), *options]) == exit_code
    return caplog.records[-1].message


def test_cli_reads_actual_snapshot_results_without_fetching(
    engine: sa.Engine,
    site: Site,
    profile: ProfileFile,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(status, "engine_from_env", lambda: engine)

    def read(*options: str) -> dict:
        return json.loads(logged_status(profile, caplog, "--json", *options))["source_status"]

    empty = read()
    assert empty["state"] == "never_run" and empty["stale"]
    assert empty["last_attempt_at"] is empty["record_count"] is empty["last_error_code"] is None
    assert empty["checkpoint_revision"] == site.requests == 0
    assert profile.config["schedule"] == {"cron": "0 */2 * * *", "timezone": "UTC"}
    assert empty["freshness_threshold_seconds"] == 2 * 7200
    applied = invoke(profile, caplog)
    first = read()
    assert first["state"] == "success" and not first["stale"]
    for name in (
        "record_count",
        "claim_count",
        "reject_count",
        "quarantine_count",
        "bytes_received",
        "requests_used",
        "request_budget",
        "checkpoint_revision",
    ):
        assert first[name] == applied[name]
    assert first["cursor_lag_seconds"] is None
    assert (
        first["last_success_at"] == first["last_confirmed_at"] == first["last_attempt_finished_at"]
    )
    invoke(profile, caplog)
    unchanged = read()
    assert unchanged["state"] == "not_modified" and not unchanged["stale"]
    assert unchanged["last_success_at"] == first["last_success_at"]
    assert unchanged["last_confirmed_at"] == unchanged["last_attempt_finished_at"]
    invoke(profile, caplog, "--archive-run-id", applied["run_id"])
    profile.path.with_name("suite.xml").unlink()
    replay = read()
    assert replay["state"] == "skipped" and replay["last_attempt_mode"] == "replay"
    assert replay["last_confirmed_at"] == unchanged["last_confirmed_at"]
    assert replay["request_budget"] == replay["requests_used"] == 0
    assert site.requests == 2


def test_selecting_a_stream_checks_the_deployed_catalogue(
    engine: sa.Engine,
    profile: ProfileFile,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(status, "engine_from_env", lambda: engine)
    other = json.loads(logged_status(profile, caplog, "--json", "--scope", "other"))
    assert (other["source_status"]["state"], other["source_status"]["scope"]) == (
        "never_run",
        "other",
    )
    backfill = json.loads(logged_status(profile, caplog, "--json", "--backfill"))
    assert (
        backfill["source_status"]["cursor_namespace"]
        == (profile.config["cursor"]["backfill_namespace"])
    )
    profile.config["identity"]["source_id"] = "space:unlisted-fixture"
    profile.save()
    missing = json.loads(logged_status(profile, caplog, "--json", exit_code=1))["error"]
    assert (missing["code"], missing["rule"]) == ("E_SOURCE_CONFIG", "catalogueReference")


def test_status_goldens_and_thresholds(
    engine: sa.Engine,
    profile: ProfileFile,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    profile.config["schedule"]["freshness_seconds"] = 60
    profile.config["monitoring"]["alert_thresholds"]["consecutive_failures"] = 2
    profile.save()
    table = catalogue_table()
    attempts = state_table(ATTEMPTS)
    with engine.begin() as connection:
        connection.execute(
            table.update().filter_by(source_id=SOURCE).values(lifecycle_state="paused")
        )
        for run_id, outcome, time in (
            ("first", "success", STARTED),
            ("failure", "failed", STARTED + timedelta(seconds=1)),
            ("latest", "partial", LOADED),
        ):
            connection.execute(
                attempts.insert().values(
                    **attempt_row(
                        STREAM,
                        run_id=run_id,
                        status=outcome,
                        started_at=time,
                        finished_at=time,
                        record_count=2,
                        claim_count=1,
                        reject_count=1,
                        quarantine_count=1,
                        bytes_received=0,
                        requests_used=2,
                        request_budget=5,
                    )
                )
            )
        for number, error in enumerate(("payload_invalid", "schema_drift"), 1):
            connection.execute(
                state_table(ERRORS)
                .insert()
                .values(
                    **error_row(
                        **STREAM.columns(),
                        run_id="latest",
                        error_no=number,
                        observed_at=LOADED,
                        error_code=error,
                    )
                )
            )
    monkeypatch.setattr(status, "engine_from_env", lambda: engine)
    monkeypatch.setattr(status, "datetime", FixedClock)
    assert logged_status(profile, caplog) == GOLDEN_TEXT
    assert logged_status(profile, caplog, "--json") == GOLDEN_JSON

    with engine.begin() as connection:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        connection.exec_driver_sql("SET LOCAL ROLE kn_system_reader")
        connection.exec_driver_sql("SET LOCAL TIME ZONE 'Asia/Kolkata'")
        offset = timezone(timedelta(hours=-5))
        cutoff = (STARTED + timedelta(seconds=60)).astimezone(offset)
        assert not read_source_status(connection, STREAM, POLICY, now=cutoff)["stale"]
        assert read_source_status(
            connection, STREAM, POLICY, now=cutoff + timedelta(microseconds=1)
        )["stale"]
        assert (
            read_source_status(connection, STREAM, POLICY, now=STARTED)["last_error_code"]
            == "schema_drift"
        )


def test_all_registered_states_and_error_codes_render(
    engine: sa.Engine,
    profile: ProfileFile,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(status, "engine_from_env", lambda: engine)
    contract = ingestion_contract()
    states = next(field.enum for field in contract.table(ATTEMPTS).fields if field.name == "status")
    codes = next(
        field.enum for field in contract.table(ERRORS).fields if field.name == "error_code"
    )
    for index, code in enumerate(codes):
        state = (*states, None)[index % (len(states) + 1)]
        time = STARTED + timedelta(minutes=index)
        run_id = f"run-{index}"
        with engine.begin() as connection:
            connection.execute(
                state_table(ATTEMPTS)
                .insert()
                .values(
                    **attempt_row(
                        STREAM,
                        run_id=run_id,
                        started_at=time,
                        status=state,
                        finished_at=time if state else None,
                    )
                )
            )
            connection.execute(
                state_table(ERRORS)
                .insert()
                .values(
                    **error_row(
                        **STREAM.columns(), run_id=run_id, observed_at=time, error_code=code
                    )
                )
            )
        text = logged_status(profile, caplog)
        assert f"| State {state or 'unfinished'}\n" in text
        assert f"| Last error {code}\n" in text
        result = json.loads(logged_status(profile, caplog, "--json"))["source_status"]
        assert result["state"] == (state or "unfinished") and result["last_error_code"] == code
