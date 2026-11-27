"""Read and append checkpoint revisions inside the caller's load transaction."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, RowMapping

from kn.engine.state import CHECKPOINTS, state_table

CursorStrategy = Literal["snapshot_hash", "updated_since", "id_range", "window"]
INITIAL_REVISION = 0
DEFAULT_SCOPE = "default"
LIVE_NAMESPACE = "live"
_SNAPSHOT_DIGEST = re.compile(r"[0-9a-f]{64}")


class CheckpointConflict(RuntimeError):
    """The stream advanced after the caller selected its input range."""


@dataclass(frozen=True, slots=True)
class StreamKey:
    source_id: str
    scope: str
    cursor_namespace: str

    def columns(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "scope": self.scope,
            "cursor_namespace": self.cursor_namespace,
        }


@dataclass(frozen=True, slots=True)
class Advance:
    run_id: str
    batch_id: str
    strategy: CursorStrategy
    position: str | datetime
    advanced_at: datetime


def latest_checkpoint(connection: Connection, stream: StreamKey) -> RowMapping | None:
    """Read the greatest revision visible to this transaction."""
    return connection.execute(latest_checkpoint_query(stream)).mappings().one_or_none()


def latest_checkpoint_query(stream: StreamKey) -> sa.Select[tuple[object, ...]]:
    """Select the greatest revision, including when composed into a health read."""
    table = state_table(CHECKPOINTS)
    return sa.select(table).filter_by(**stream.columns()).order_by(table.c.revision.desc()).limit(1)


def advance_checkpoint(
    connection: Connection,
    stream: StreamKey,
    advance: Advance,
    *,
    expected_revision: int,
) -> int:
    """Append a revision for a contiguous loaded prefix; caller commits or rolls back the load.

    The table's foreign key checks the batch in the same stream at transaction commit. The
    caller determines contiguous coverage from the source and includes the loaded rows and
    batch registration in the same transaction when applying new data.
    """
    if not connection.in_transaction() or getattr(
        connection.connection.driver_connection, "autocommit", False
    ):
        raise ValueError("checkpoint advance requires a caller-owned transaction")
    token, watermark = _position(advance.strategy, advance.position)
    advanced_at = _utc(advance.advanced_at)
    current = latest_checkpoint(connection, stream)
    _check_current(current, expected_revision, advance.strategy, watermark)
    table = state_table(CHECKPOINTS)
    next_revision = expected_revision + 1
    statement = (
        insert(table)
        .values(
            **stream.columns(),
            revision=next_revision,
            run_id=advance.run_id,
            batch_id=advance.batch_id,
            cursor_strategy=advance.strategy,
            cursor_token=token,
            watermark_at=watermark,
            advanced_at=advanced_at,
        )
        .on_conflict_do_nothing(constraint=table.primary_key)
        .returning(sa.literal(True))
    )
    if connection.execute(statement).scalar_one_or_none() is None:
        raise CheckpointConflict("checkpoint revision changed")
    return next_revision


def _check_current(
    current: RowMapping | None, expected: int, strategy: CursorStrategy, watermark: datetime | None
) -> None:
    if expected != (INITIAL_REVISION if current is None else current["revision"]):
        raise CheckpointConflict("checkpoint revision changed")
    if current is None:
        return
    if current["cursor_strategy"] != strategy:
        raise ValueError("checkpoint strategy changed within the stream")
    previous = current["watermark_at"]
    if watermark is not None and previous is not None and watermark < previous:
        raise ValueError("checkpoint watermark moved backward")


def _position(
    strategy: CursorStrategy, position: str | datetime
) -> tuple[str | None, datetime | None]:
    if strategy in {"updated_since", "window"} and isinstance(position, datetime):
        return None, _utc(position)
    if (
        strategy == "snapshot_hash"
        and isinstance(position, str)
        and _SNAPSHOT_DIGEST.fullmatch(position)
    ):
        return position, None
    if (
        strategy == "id_range"
        and isinstance(position, str)
        and position.strip()
        and "\x00" not in position
    ):
        return position, None
    raise ValueError("position does not match the cursor strategy")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("checkpoint timestamps require an explicit UTC offset")
    return value.astimezone(UTC)
