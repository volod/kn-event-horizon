"""Run or replay a single archived snapshot through the registered loader."""

from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from pydantic import TypeAdapter
from sqlalchemy.engine import Connection, RowMapping

from kn.archive import Archive
from kn.archive.model import ArchiveError, BatchKey, Metadata, Segment
from kn.db.connection import engine_from_env
from kn.engine.adapter import Adapter, load_adapter
from kn.engine.attempts import Attempt, finish, register, source_lock
from kn.engine.captures import SNAPSHOT_BATCH, archived_snapshot
from kn.engine.checkpoints import INITIAL_REVISION, Advance, advance_checkpoint, latest_checkpoint
from kn.engine.loader import load_records
from kn.engine.outcomes import Metrics, RunFailure, Status
from kn.engine.profile import SnapshotProfile, snapshot_profile
from kn.engine.state import ATTEMPTS, BATCHES, state_table
from kn.identity.journal import Journal
from kn.sources.catalogue import source_enabled
from kn.sources.config.schema import CrawlerConfigError

_RUN_ID = TypeAdapter(Segment)


def source_operation(
    path: Path, data_dir: Path, *, archive_run_id: str | None = None
) -> dict[str, object]:
    profile = snapshot_profile(path)
    if archive_run_id is not None:
        _RUN_ID.validate_python(archive_run_id)
    engine = engine_from_env()
    try:
        with engine.connect() as connection, source_lock(connection, profile.stream):
            with connection.begin():
                if not source_enabled(connection, profile.stream.source_id):
                    raise CrawlerConfigError(
                        ("identity", "source_id"),
                        "catalogueState",
                        "use a source enabled in the deployed catalogue",
                    )
                adapter = load_adapter(profile.entry_point)
                archive = Archive.configured()
                attempt = register(connection, profile, adapter.code_digest, archive_run_id)
                checkpoint = latest_checkpoint(connection, profile.stream)
            key = _archive_key(profile, archive_run_id or attempt.run_id)
            return _run(
                connection, Journal(data_dir), archive, profile, adapter, attempt, key, checkpoint
            )
    finally:
        engine.dispose()


def _archive_key(profile: SnapshotProfile, run_id: str) -> BatchKey:
    source = profile.stream.source_id
    return BatchKey(
        domain=source.partition(":")[0], source_id=source, run_id=run_id, batch_id=SNAPSHOT_BATCH
    )


def _run(
    connection: Connection,
    journal: Journal,
    archive: Archive,
    profile: SnapshotProfile,
    adapter: Adapter,
    attempt: Attempt,
    key: BatchKey,
    checkpoint: RowMapping | None,
) -> dict[str, object]:
    metrics = Metrics()
    revision = checkpoint["revision"] if checkpoint is not None else INITIAL_REVISION
    try:
        capture, payload = archived_snapshot(
            archive, profile, key, adapter.code_digest, metrics, fetch=attempt.mode == "fetch"
        )
        with connection.begin():
            skip = _skip_status(connection, archive, attempt, key, capture, checkpoint)
            if skip is not None:
                return finish(connection, attempt, metrics, skip, revision)
            identity, records = adapter.records_and_claims(profile, capture, payload)
            metrics.record_count = len(records)
            metrics.claim_count = load_records(connection, journal, identity, records)
            loaded_at = datetime.now(UTC)
            _register_batch(connection, attempt, key, loaded_at)
            advance = Advance(
                attempt.run_id, key.batch_id, "snapshot_hash", capture.payload_sha256, loaded_at
            )
            revision = advance_checkpoint(
                connection, attempt.stream, advance, expected_revision=revision
            )
            return finish(connection, attempt, metrics, "success", revision)
    except RunFailure as error:
        with connection.begin():
            return finish(connection, attempt, metrics, error.status, revision, error.code)


def _skip_status(
    connection: Connection,
    archive: Archive,
    attempt: Attempt,
    key: BatchKey,
    capture: Metadata,
    checkpoint: RowMapping | None,
) -> Status | None:
    table = state_table(BATCHES)
    applied = sa.select(table.c.run_id).filter_by(
        **attempt.stream.columns(), archive_run_id=key.run_id, archive_batch_id=key.batch_id
    )
    if connection.scalar(applied) is not None:
        return "skipped"
    if checkpoint is None:
        return None
    if checkpoint["cursor_strategy"] != "snapshot_hash":
        raise RunFailure("integrity_lost", "blocked")
    same_payload = checkpoint["cursor_token"] == capture.payload_sha256
    if not same_payload and attempt.mode == "fetch":
        return None
    previous = _checkpoint_batch(connection, attempt, checkpoint)
    if same_payload and (previous["config_sha256"], previous["code_sha256"]) == (
        capture.config_sha256,
        capture.code_sha256,
    ):
        return "not_modified"
    if attempt.mode == "replay" and capture.fetched_at < _archive_time(archive, key, previous):
        return "skipped"
    return None


def _checkpoint_batch(
    connection: Connection, attempt: Attempt, checkpoint: RowMapping
) -> RowMapping:
    batch = state_table(BATCHES)
    attempts = state_table(ATTEMPTS)
    attempt_key = (*attempt.stream.columns(), "run_id", "attempt")
    joined = batch.join(
        attempts, sa.and_(*(batch.c[name] == attempts.c[name] for name in attempt_key))
    )
    query = sa.select(batch, attempts.c.config_sha256, attempts.c.code_sha256).select_from(joined)
    key = {
        **attempt.stream.columns(),
        "run_id": checkpoint["run_id"],
        "batch_id": checkpoint["batch_id"],
    }
    return (
        connection.execute(query.where(*(batch.c[name] == value for name, value in key.items())))
        .mappings()
        .one()
    )


def _archive_time(archive: Archive, key: BatchKey, previous: RowMapping) -> datetime:
    prior = BatchKey(
        domain=key.domain,
        source_id=key.source_id,
        run_id=previous["archive_run_id"],
        batch_id=previous["archive_batch_id"],
    )
    try:
        return archive.batch(prior).last_capture_at
    except (ArchiveError, OSError):
        raise RunFailure("integrity_lost") from None


def _register_batch(
    connection: Connection, attempt: Attempt, key: BatchKey, loaded_at: datetime
) -> None:
    connection.execute(
        state_table(BATCHES)
        .insert()
        .values(
            **attempt.key(),
            batch_id=key.batch_id,
            archive_run_id=key.run_id,
            archive_batch_id=key.batch_id,
            loaded_at=loaded_at,
        )
    )
