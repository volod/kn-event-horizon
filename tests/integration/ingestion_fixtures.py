"""Deterministic run history and archive input for the registered-model rebuild."""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Connection

from kn.archive import Archive
from kn.archive.model import BatchKey, Capture, Limits, Manifest, Metadata, Retention
from kn.db.platform import role_name
from kn.db.statements import ResetRole, SetRole
from kn.engine.checkpoints import INITIAL_REVISION, Advance, StreamKey, advance_checkpoint
from kn.engine.state import ATTEMPTS, BATCHES, CHECKPOINTS, ERRORS, state_table

STREAM = StreamKey("space:fixture", "catalogue", "live")
STARTED = datetime(2026, 6, 1, 12, tzinfo=UTC)
LOADED = STARTED + timedelta(minutes=5)
CONFIG = "a" * 64
CODE = "b" * 64
RUN = "run-1"
BATCH = "page-1"


def attempt_row(stream: StreamKey = STREAM, **changes: Any) -> dict[str, Any]:
    return {
        **stream.columns(),
        "run_id": RUN,
        "attempt": 1,
        "mode": "fetch",
        "started_at": STARTED,
        "config_sha256": CONFIG,
        "code_sha256": CODE,
        **changes,
    }


def batch_row(stream: StreamKey = STREAM, batch_id: str = BATCH, **changes: Any) -> dict[str, Any]:
    return {
        **stream.columns(),
        "run_id": RUN,
        "attempt": 1,
        "batch_id": batch_id,
        "archive_run_id": RUN,
        "archive_batch_id": batch_id,
        "loaded_at": LOADED,
        **changes,
    }


def error_row(**changes: Any) -> dict[str, Any]:
    return {
        **STREAM.columns(),
        "run_id": RUN,
        "attempt": 1,
        "error_no": 1,
        "observed_at": STARTED,
        "error_code": "transient_network",
        **changes,
    }


def fixture_archive(path: Path) -> Manifest:
    archive = Archive(path)
    key = BatchKey(domain="space", source_id=STREAM.source_id, run_id=RUN, batch_id=BATCH)
    body = b'{"mass": 1250}'
    capture = Capture(
        key="data",
        origin_uri="https://example.test/ingestion",
        fetched_at=STARTED,
        body=BytesIO(body),
        config_sha256=CONFIG,
        code_sha256=CODE,
        retention=Retention(access="internal", deletion_scope="fixture"),
    )
    return archive.commit(key, (capture,), limits=Limits(len(body), len(body)))


def ingestion_rows(capture: Metadata) -> dict[str, list[dict[str, Any]]]:
    return {
        ATTEMPTS: [
            attempt_row(bytes_received=capture.payload_size, requests_used=2, request_budget=4),
            attempt_row(
                attempt=2,
                started_at=STARTED + timedelta(minutes=2),
                finished_at=LOADED,
                status="success",
                record_count=1,
                claim_count=1,
                reject_count=0,
                quarantine_count=0,
                bytes_received=0,
                requests_used=0,
                request_budget=4,
                cursor_lag_seconds=300,
            ),
            attempt_row(
                run_id="run-2",
                started_at=LOADED + timedelta(minutes=1),
                finished_at=LOADED + timedelta(minutes=1),
                status="not_modified",
                record_count=0,
                claim_count=0,
                bytes_received=0,
                requests_used=1,
                request_budget=4,
            ),
        ],
        ERRORS: [
            error_row(),
            error_row(
                error_no=2, error_code="rate_limited", observed_at=STARTED + timedelta(minutes=1)
            ),
        ],
        BATCHES: [
            batch_row(
                attempt=2,
                archive_run_id=capture.batch.run_id,
                archive_batch_id=capture.batch.batch_id,
            )
        ],
        CHECKPOINTS: [
            {
                **STREAM.columns(),
                "revision": 1,
                "run_id": RUN,
                "batch_id": BATCH,
                "cursor_strategy": "updated_since",
                "watermark_at": STARTED,
                "advanced_at": LOADED,
            }
        ],
    }


def seed_ingestion_fixture(connection: Connection, capture: Metadata) -> None:
    rows = ingestion_rows(capture)
    connection.execute(SetRole(role_name("system", "loader")))
    for name in (ATTEMPTS, ERRORS, BATCHES):
        table = state_table(name)
        # Separate inserts preserve the optional, unmeasured fields of each attempt.
        for row in rows[name]:
            connection.execute(table.insert().values(**row))
    assert (
        advance_checkpoint(
            connection,
            STREAM,
            Advance(RUN, BATCH, "updated_since", STARTED, LOADED),
            expected_revision=INITIAL_REVISION,
        )
        == 1
    )
    connection.execute(ResetRole())


def assert_ingestion_snapshot(
    snapshot: dict[str, list[dict[str, Any]]],
    capture: Metadata,
) -> None:
    for name, rows in ingestion_rows(capture).items():
        table = state_table(name)
        assert snapshot[table.fullname] == [
            {field.name: row.get(field.name) for field in table.columns} for row in rows
        ]
