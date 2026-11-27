"""Register logical run attempts and store their outcomes."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

import sqlalchemy as sa
from sqlalchemy.engine import Connection, RowMapping

from kn.contracts.model import canonical
from kn.engine.checkpoints import StreamKey
from kn.engine.outcomes import ErrorCode, Metrics, Status
from kn.engine.profile import SnapshotProfile
from kn.engine.state import ATTEMPTS, ERRORS, state_table
from kn.sources.config.schema import CrawlerConfigError

type Mode = Literal["fetch", "replay"]


@dataclass(frozen=True, slots=True)
class Attempt:
    stream: StreamKey
    run_id: str
    number: int
    mode: Mode
    started_at: datetime
    request_budget: int

    def key(self) -> dict[str, str | int]:
        return {**self.stream.columns(), "run_id": self.run_id, "attempt": self.number}


@contextmanager
def source_lock(connection: Connection, stream: StreamKey) -> Iterator[None]:
    """Hold one session lock across registration, acquisition, and the load commit."""
    key = canonical(("kn.ingestion", stream.source_id, stream.scope))
    identifier = int.from_bytes(sha256(key.encode("ascii")).digest()[:8], signed=True)
    try:
        with connection.begin():
            connection.execute(sa.select(sa.func.pg_advisory_lock(identifier)))
        yield
    finally:
        # If the session has died, PostgreSQL has already released its lock.
        if not connection.invalidated:
            with connection.begin():
                connection.execute(sa.select(sa.func.pg_advisory_unlock(identifier)))


def register(
    connection: Connection, profile: SnapshotProfile, code_digest: str, archive_run_id: str | None
) -> Attempt:
    table = state_table(ATTEMPTS)
    mode: Mode = "fetch" if archive_run_id is None else "replay"
    selected = (
        _replay_run_id(profile.stream, archive_run_id) if archive_run_id is not None else None
    )
    previous = _pending_attempt(connection, profile.stream)
    if previous is not None:
        if previous["mode"] != mode or (selected is not None and previous["run_id"] != selected):
            raise CrawlerConfigError(
                ("identity", "source_id"), "interruptedRun", "resume the interrupted run first"
            )
        if (previous["config_sha256"], previous["code_sha256"]) != (
            profile.config_digest,
            code_digest,
        ):
            raise CrawlerConfigError(
                ("approval",), "interruptedVersion", "restore the interrupted profile and code"
            )
        run_id, number = previous["run_id"], previous["attempt"] + 1
    elif selected is None:
        run_id, number = str(uuid4()), 1
    else:
        query = sa.select(sa.func.max(table.c.attempt)).filter_by(
            **profile.stream.columns(), run_id=selected
        )
        run_id, number = selected, (connection.scalar(query) or 0) + 1
    budget = profile.request_budget if mode == "fetch" else 0
    attempt = Attempt(profile.stream, run_id, number, mode, datetime.now(UTC), budget)
    connection.execute(
        table.insert().values(
            **attempt.key(),
            mode=mode,
            started_at=attempt.started_at,
            config_sha256=profile.config_digest,
            code_sha256=code_digest,
            request_budget=budget,
        )
    )
    return attempt


def _replay_run_id(stream: StreamKey, archive_run_id: str) -> str:
    key = canonical(
        ("kn.replay", stream.source_id, stream.scope, stream.cursor_namespace, archive_run_id)
    )
    return str(uuid5(NAMESPACE_URL, key))


def _pending_attempt(connection: Connection, stream: StreamKey) -> RowMapping | None:
    table = state_table(ATTEMPTS)
    order = sa.func.row_number().over(partition_by=table.c.run_id, order_by=table.c.attempt.desc())
    attempts = (
        sa.select(table, order.label("run_position")).filter_by(**stream.columns()).subquery()
    )
    query = sa.select(attempts).where(attempts.c.run_position == 1, attempts.c.status.is_(None))
    return connection.execute(query).mappings().one_or_none()


def finish(
    connection: Connection,
    attempt: Attempt,
    metrics: Metrics,
    status: Status,
    revision: int,
    error: ErrorCode | None = None,
) -> dict[str, object]:
    finished_at = max(datetime.now(UTC), attempt.started_at)
    fields = {
        "record_count": metrics.record_count,
        "claim_count": metrics.claim_count,
        "reject_count": 0,
        "quarantine_count": 0,
        "bytes_received": metrics.bytes_received,
        "requests_used": metrics.requests_used,
    }
    table = state_table(ATTEMPTS)
    connection.execute(
        table.update()
        .where(*(table.c[k] == v for k, v in attempt.key().items()))
        .values(**fields, status=status, finished_at=finished_at)
    )
    if error is not None:
        connection.execute(
            state_table(ERRORS)
            .insert()
            .values(**attempt.key(), error_no=1, observed_at=finished_at, error_code=error)
        )
    return {
        **attempt.key(),
        **fields,
        "mode": attempt.mode,
        "request_budget": attempt.request_budget,
        "status": status,
        "error_code": error,
        "checkpoint_revision": revision,
    }
