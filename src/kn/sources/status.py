"""Project the registered run, error and checkpoint records into source health."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection
from sqlalchemy.sql.selectable import Subquery

from kn.db.connection import engine_from_env
from kn.engine.checkpoints import (
    DEFAULT_SCOPE,
    INITIAL_REVISION,
    LIVE_NAMESPACE,
    StreamKey,
    latest_checkpoint_query,
)
from kn.engine.state import ATTEMPTS, ERRORS, state_table
from kn.sources.catalogue import catalogue_table
from kn.sources.config import load_status_config
from kn.sources.config.schema import CrawlerConfigError

_CONFIRMED = ("success", "not_modified")
_UNHEALTHY = ("partial", "blocked", "failed")
_ATTEMPT_FIELDS = {
    "run_id": "last_attempt_run_id",
    "attempt": "last_attempt_number",
    "mode": "last_attempt_mode",
    "started_at": "last_attempt_at",
    "finished_at": "last_attempt_finished_at",
    "status": "last_attempt_status",
}
_METRICS = (
    "record_count",
    "claim_count",
    "reject_count",
    "quarantine_count",
    "bytes_received",
    "requests_used",
    "request_budget",
)
_TIMESTAMPS = (
    "last_attempt_at",
    "last_attempt_finished_at",
    "last_success_at",
    "last_confirmed_at",
)


@dataclass(frozen=True, slots=True)
class MonitoringPolicy:
    freshness_seconds: int
    failure_threshold: int | None = None


def source_status_operation(
    path: Path, *, scope: str = DEFAULT_SCOPE, backfill: bool = False
) -> dict[str, object]:
    config = load_status_config(path)
    monitoring = config["monitoring"]
    policy = MonitoringPolicy(
        config["schedule"].get("freshness_seconds", monitoring["freshness_sla_seconds"]),
        monitoring["alert_thresholds"].get("consecutive_failures"),
    )
    namespace = config["cursor"]["backfill_namespace"] if backfill else LIVE_NAMESPACE
    stream = StreamKey(config["identity"]["source_id"], scope, namespace)
    engine = engine_from_env()
    try:
        with engine.connect() as connection:
            return {"source_status": read_source_status(connection, stream, policy)}
    finally:
        engine.dispose()


def read_source_status(
    connection: Connection,
    stream: StreamKey,
    policy: MonitoringPolicy,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return one CLI and operations mart row from a single database snapshot.

    The optional clock controls ages. History is always the connection's current snapshot.
    """
    stored = connection.execute(_status_query(stream)).mappings().one_or_none()
    if stored is None:
        raise CrawlerConfigError(
            ("identity", "source_id"), "catalogueReference", "use an ID in the deployed catalogue"
        )
    observed = _utc(datetime.now(UTC) if now is None else now)
    confirmation_age = _age_seconds(observed, stored["last_confirmed_at"])
    watermark_lag = _age_seconds(observed, stored["watermark_at"])
    failure_count = stored["consecutive_failures"]
    result = dict(stored)
    lag = result.pop("reported_cursor_lag_seconds")
    result.pop("watermark_at")
    run_status = result.pop("last_attempt_status")
    result.update(
        **stream.columns(),
        state=run_status or ("never_run" if stored["last_attempt_at"] is None else "unfinished"),
        stale=confirmation_age is None or confirmation_age > policy.freshness_seconds,
        freshness_threshold_seconds=policy.freshness_seconds,
        failing=policy.failure_threshold is not None and failure_count >= policy.failure_threshold,
        cursor_lag_seconds=lag if watermark_lag is None else int(watermark_lag),
        checkpoint_revision=stored["checkpoint_revision"] or INITIAL_REVISION,
    )
    for key in _TIMESTAMPS:
        value = stored[key]
        result[key] = _utc(value).isoformat() if value is not None else None
    return result


def _status_query(stream: StreamKey) -> sa.Select[tuple[object, ...]]:
    catalogue = catalogue_table()
    attempts = state_table(ATTEMPTS)
    history = sa.select(attempts).filter_by(**stream.columns()).subquery()
    last = _latest_attempt(history)
    summary = _attempt_summary(history)
    checkpoint = latest_checkpoint_query(stream).subquery()
    errors = state_table(ERRORS)
    error = (
        sa.select(errors.c.error_code)
        .filter_by(**stream.columns())
        .order_by(
            errors.c.observed_at.desc(),
            errors.c.run_id.desc(),
            errors.c.attempt.desc(),
            errors.c.error_no.desc(),
        )
        .limit(1)
        .scalar_subquery()
    )
    return (
        sa.select(
            catalogue.c.lifecycle_state,
            *(last.c[name].label(label) for name, label in _ATTEMPT_FIELDS.items()),
            *(last.c[name] for name in _METRICS),
            last.c.cursor_lag_seconds.label("reported_cursor_lag_seconds"),
            checkpoint.c.watermark_at,
            checkpoint.c.revision.label("checkpoint_revision"),
            error.label("last_error_code"),
            *summary.c,
        )
        .select_from(
            catalogue.outerjoin(last, sa.true())
            .outerjoin(checkpoint, sa.true())
            .join(summary, sa.true())
        )
        .where(catalogue.c.source_id == stream.source_id)
    )


def _latest_attempt(history: Subquery) -> Subquery:
    # A higher retry number supersedes its earlier attempts even if their clocks disagree.
    latest_per_run = sa.select(
        history,
        sa.func.row_number()
        .over(partition_by=history.c.run_id, order_by=history.c.attempt.desc())
        .label("run_position"),
    ).subquery()
    return (
        sa.select(latest_per_run)
        .where(latest_per_run.c.run_position == 1)
        .order_by(latest_per_run.c.started_at.desc(), latest_per_run.c.run_id.desc())
        .limit(1)
        .subquery()
    )


def _attempt_summary(history: Subquery) -> Subquery:
    fetch_results = (
        sa.select(
            history.c.status,
            history.c.finished_at,
            sa.func.row_number()
            .over(
                order_by=(
                    history.c.started_at.desc(),
                    history.c.run_id.desc(),
                    history.c.attempt.desc(),
                )
            )
            .label("position"),
        )
        .where(history.c.mode == "fetch", history.c.status.in_(_CONFIRMED + _UNHEALTHY))
        .subquery()
    )
    confirmed = fetch_results.c.status.in_(_CONFIRMED)
    last_success = (
        sa.select(sa.func.max(history.c.finished_at))
        .where(history.c.status == "success")
        .scalar_subquery()
    )
    return sa.select(
        last_success.label("last_success_at"),
        sa.func.max(fetch_results.c.finished_at).filter(confirmed).label("last_confirmed_at"),
        sa.func.coalesce(
            sa.func.min(fetch_results.c.position).filter(confirmed) - 1, sa.func.count()
        ).label("consecutive_failures"),
    ).subquery()


def _utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("source status timestamps require an explicit UTC offset")
    return value.astimezone(UTC)


def _age_seconds(now: datetime, then: datetime | None) -> float | None:
    return None if then is None else max(0.0, (now - _utc(then)).total_seconds())
