"""Real PostgreSQL enforcement of ingestion keys and the load transaction."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from threading import Barrier

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from kn.archive import Archive
from kn.engine.checkpoints import (
    INITIAL_REVISION,
    Advance,
    CheckpointConflict,
    StreamKey,
    advance_checkpoint,
    latest_checkpoint,
)
from kn.engine.state import ATTEMPTS, BATCHES, CHECKPOINTS, ERRORS, state_table
from kn.evidence.store import evidence_tables, record
from tests.evidence.fixtures import claim, evidence
from tests.integration.harness import IntegrationDatabase, ScratchSchemas
from tests.integration.ingestion_fixtures import (
    BATCH,
    LOADED,
    RUN,
    STARTED,
    STREAM,
    attempt_row,
    batch_row,
    error_row,
    fixture_archive,
)

SECOND = "page-2"


@pytest.fixture
def state_db(
    integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> Iterator[sa.Engine]:
    schema = scratch_schemas.schema("ingestion_state")
    model = state_table(ATTEMPTS).metadata
    engine = sa.create_engine(
        "postgresql+psycopg://",
        creator=integration_database.connect,
        execution_options={"schema_translate_map": {"system": schema}},
    )
    try:
        with engine.begin() as connection:
            model.create_all(connection)
        yield engine
    finally:
        with engine.begin() as connection:
            model.drop_all(connection)
        engine.dispose()


def advance(
    connection: sa.Connection,
    batch_id: str = BATCH,
    *,
    stream: StreamKey = STREAM,
    expected: int = INITIAL_REVISION,
    position: datetime = STARTED,
) -> int:
    return advance_checkpoint(
        connection,
        stream,
        Advance(RUN, batch_id, "window", position, LOADED),
        expected_revision=expected,
    )


@pytest.mark.parametrize(
    ("name", "row", "constraint"),
    [
        (ATTEMPTS, attempt_row(), "pk_source_run_attempts"),
        (BATCHES, batch_row(), "pk_source_loaded_batches"),
        (
            BATCHES,
            batch_row(batch_id=SECOND, archive_batch_id=BATCH),
            "source_loaded_batches_archive_idx",
        ),
        (ERRORS, error_row(), "pk_source_run_errors"),
        (ERRORS, error_row(error_no=2, error_code="unclassified"), "error_code_enum"),
        (ATTEMPTS, attempt_row(attempt=2, status="success"), "terminal_outcome_presence"),
        (ATTEMPTS, attempt_row(attempt=2, finished_at=LOADED, status="running"), "status_enum"),
    ],
)
def test_state_ddl_rejects_duplicates_and_invalid_outcomes(
    state_db: sa.Engine, name: str, row: dict, constraint: str
) -> None:
    with state_db.begin() as connection:
        connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row()))
        connection.execute(state_table(BATCHES).insert().values(**batch_row()))
        connection.execute(state_table(ERRORS).insert().values(**error_row()))
        with pytest.raises(IntegrityError, match=constraint), connection.begin_nested():
            connection.execute(state_table(name).insert().values(**row))


@pytest.mark.parametrize("target", ["missing", "other_source", "other_scope", "backfill"])
def test_checkpoint_requires_a_loaded_batch_in_the_same_stream(
    state_db: sa.Engine, target: str
) -> None:
    stream = {
        "missing": STREAM,
        "other_source": StreamKey("space:other", STREAM.scope, STREAM.cursor_namespace),
        "other_scope": StreamKey(STREAM.source_id, "other", STREAM.cursor_namespace),
        "backfill": StreamKey(STREAM.source_id, STREAM.scope, "repair"),
    }[target]
    with state_db.begin() as connection:
        connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row()))
        connection.execute(state_table(BATCHES).insert().values(**batch_row()))
    with (
        pytest.raises(IntegrityError, match="fk_source_checkpoints"),
        state_db.begin() as connection,
    ):
        advance(connection, "missing" if target == "missing" else BATCH, stream=stream)
    with state_db.begin() as connection:
        assert latest_checkpoint(connection, stream) is None


def test_failed_load_rolls_back_data_and_cursor_but_keeps_archive(
    state_db: sa.Engine, scratch_schemas: ScratchSchemas, tmp_path: Path
) -> None:
    schema = scratch_schemas.schema("ingestion_claims")
    claims = evidence_tables(schema)
    claims["claims"].metadata.create_all(state_db)
    manifest = fixture_archive(tmp_path)
    capture = manifest.captures[0]
    row = claim(evidence=evidence(fetch_id=capture.fetch_id, archive_record_id=capture.record_id))
    with state_db.begin() as connection:
        connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row()))
        connection.execute(
            state_table(BATCHES).insert().values(**batch_row(archive_batch_id="prior"))
        )
        assert advance(connection) == 1
    with (
        pytest.raises(IntegrityError, match="fk_source_loaded_batches"),
        state_db.begin() as connection,
    ):
        assert record(connection, (row,), claims) == 2
        # The claimed writing attempt does not exist; failure occurs at outer commit.
        retry_batch = batch_row(batch_id=SECOND, archive_batch_id=manifest.batch.batch_id)
        connection.execute(state_table(BATCHES).insert().values(**(retry_batch | {"attempt": 2})))
        assert advance(connection, SECOND, expected=1, position=LOADED) == 2
    with state_db.begin() as connection:
        current = latest_checkpoint(connection, STREAM)
        assert current is not None and current["revision"] == 1
        assert connection.scalar(sa.select(sa.func.count()).select_from(claims["claims"])) == 0
        connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row(attempt=2)))
        replayed = BytesIO()
        assert Archive(tmp_path).replay(capture.record_id, replayed).batch == manifest.batch
        assert replayed.getvalue() == b'{"mass": 1250}'
        assert record(connection, (row,), claims) == 2
        connection.execute(state_table(BATCHES).insert().values(**(retry_batch | {"attempt": 2})))
        assert advance(connection, SECOND, expected=1, position=LOADED) == 2
    with state_db.begin() as connection:
        current = latest_checkpoint(connection, STREAM)
        assert current is not None and current["revision"] == 2
        assert connection.scalar(sa.select(sa.func.count()).select_from(claims["claims"])) == 1


def test_append_preserves_historical_and_backfill_checkpoints(state_db: sa.Engine) -> None:
    repair = StreamKey(STREAM.source_id, STREAM.scope, "repair")
    with state_db.begin() as connection:
        for stream in (STREAM, repair):
            connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row(stream)))
            connection.execute(state_table(BATCHES).insert().values(**batch_row(stream)))
        connection.execute(state_table(BATCHES).insert().values(**batch_row(batch_id=SECOND)))
        assert advance(connection, position=STARTED.astimezone(timezone(timedelta(hours=5)))) == 1
        assert advance(connection, stream=repair, position=STARTED - timedelta(days=1)) == 1
        with pytest.raises(CheckpointConflict, match="revision changed"):
            advance(connection, SECOND)
        with pytest.raises(ValueError, match="moved backward"):
            advance(connection, SECOND, expected=1, position=STARTED - timedelta(seconds=1))
        assert advance(connection, SECOND, expected=1, position=LOADED) == 2
        with (
            pytest.raises(IntegrityError, match="source_checkpoints_batch_idx"),
            connection.begin_nested(),
        ):
            advance(connection, expected=2, position=LOADED)
    with state_db.begin() as connection:
        table = state_table(CHECKPOINTS)
        assert connection.execute(
            sa.select(table.c.revision, table.c.watermark_at)
            .filter_by(**STREAM.columns())
            .order_by(table.c.revision)
        ).all() == [(1, STARTED), (2, LOADED)]
        backfill = latest_checkpoint(connection, repair)
        assert backfill is not None and backfill["revision"] == 1


def test_competing_checkpoint_advances_cannot_overwrite_each_other(state_db: sa.Engine) -> None:
    with state_db.begin() as connection:
        connection.execute(state_table(ATTEMPTS).insert().values(**attempt_row()))
        for batch_id in (BATCH, SECOND):
            connection.execute(state_table(BATCHES).insert().values(**batch_row(batch_id=batch_id)))
    both_read = Barrier(2, timeout=10)

    def wait_before_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO") and "source_checkpoints" in statement:
            both_read.wait()

    def try_advance(batch_id: str) -> int | None:
        try:
            with state_db.begin() as connection:
                return advance(connection, batch_id)
        except CheckpointConflict:
            return None

    sa.event.listen(state_db, "before_cursor_execute", wait_before_insert)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(try_advance, (BATCH, SECOND)))
    finally:
        sa.event.remove(state_db, "before_cursor_execute", wait_before_insert)
    assert results.count(1) == results.count(None) == 1
    with state_db.begin() as connection:
        current = latest_checkpoint(connection, STREAM)
        assert current is not None and current["revision"] == 1


def test_checkpoint_requires_a_real_transaction_and_aware_time(state_db: sa.Engine) -> None:
    with state_db.connect() as connection, pytest.raises(ValueError, match="caller-owned"):
        advance(connection)
    with (
        state_db.connect().execution_options(isolation_level="AUTOCOMMIT") as connection,
        connection.begin(),
        pytest.raises(ValueError, match="caller-owned"),
    ):
        advance(connection)
    with state_db.begin() as connection:
        with pytest.raises(ValueError, match="explicit UTC offset"):
            advance(connection, position=STARTED.replace(tzinfo=None))
        with pytest.raises(ValueError, match="position does not match"):
            advance_checkpoint(
                connection,
                STREAM,
                Advance(RUN, BATCH, "snapshot_hash", "invalid", LOADED),
                expected_revision=INITIAL_REVISION,
            )
        assert latest_checkpoint(connection, STREAM) is None
