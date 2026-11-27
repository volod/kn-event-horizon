"""Atomic, explicitly disposable rebuild of all KN schemas through the Alembic baseline."""

import os
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts import Contract
from kn.db.governance import deployment, upgrade, verify
from kn.db.platform import SCHEMAS, apply_platform
from kn.db.seeds import load_reviewed_seeds
from kn.db.verification import verify_compiled_catalog
from kn.identity.checkpoint import DropCheckpointInvalidator
from kn.identity.journal import Journal
from kn.identity.lifecycle_reviews import references
from kn.identity.store import lock as identity_lock
from kn.identity.store import replay as replay_identity
from kn.quality.project_root import discover_project_root
from kn.review.journal import Journal as ReviewJournal
from kn.review.reports import ReplayReport
from kn.review.store import DECISION_CONTRACT
from kn.review.store import lock as review_lock
from kn.review.store import replay as replay_verification
from kn.review.targets import ContractResolver


class RebuildRefused(ValueError):
    """The environment is not explicitly marked as a disposable development environment."""


def require_development() -> None:
    """Check before opening a database connection and again at the destructive boundary."""
    if os.environ.get("KN_ENVIRONMENT") != "development":
        raise RebuildRefused(
            "rebuild requires KN_ENVIRONMENT=development; released data cannot be rebuilt"
        )


def rebuild_data_dir(data_dir: Path | None = None) -> Path:
    directory = data_dir or Path(os.environ.get("DATA_DIR", ".data"))
    return directory if directory.is_absolute() else discover_project_root() / directory


def rebuild(
    connection: Connection,
    contracts: Sequence[Contract] | None = None,
    *,
    data_dir: Path | None = None,
) -> ReplayReport:
    """The caller commits; a failure restores the previous schemas even when caught.

    After the drop, the database is empty, and the normal upgrade recreates every registered
    contract: the same SQLAlchemy metadata and Alembic revisions as every deployment, never SQL
    text. Tests supply a fixture deployment set.
    """
    require_development()
    if not connection.in_transaction():
        raise ValueError("rebuild requires a caller-owned transaction")
    deployed = deployment(contracts)
    directory = rebuild_data_dir(data_dir)
    # All schemas form one group: references and the Alembic marker cannot become partial.
    with connection.begin_nested():
        apply_platform(connection)
        identity_lock(connection)
        review_lock(connection)
        _drop_schemas(connection)
        upgrade(connection, deployed)
        restored_ids: frozenset[str] = frozenset()
        if any(contract.contract_id == "kn.core.identity" for contract in deployed):
            identity = replay_identity(connection, Journal(directory))
            restored_ids = frozenset(key for _, key in references(identity.reviewed))
        load_reviewed_seeds(connection)
        report = _replay_reviews(connection, deployed, directory, restored_ids)
        verify(connection, deployed)
        verify_compiled_catalog(connection, deployed)
        return report


def _replay_reviews(
    connection: Connection,
    deployed: Sequence[Contract],
    directory: Path,
    restored_ids: frozenset[str],
) -> ReplayReport:
    if not any(contract.contract_id == DECISION_CONTRACT for contract in deployed):
        return ()
    return replay_verification(
        connection,
        ReviewJournal(directory),
        ContractResolver.registered(deployed),
        restored_ids=restored_ids,
    )


def _drop_schemas(connection: Connection) -> None:
    """RESTRICT protects objects outside KN; unsupported non-table objects refuse safely."""
    old = sa.MetaData()
    for schema in SCHEMAS:
        old.reflect(connection, schema=schema, resolve_fks=False)
    old.drop_all(connection)
    connection.execute(DropCheckpointInvalidator())
    for schema in reversed(SCHEMAS):
        # Without CASCADE, PostgreSQL drops only an empty schema (RESTRICT).
        connection.execute(sa.schema.DropSchema(schema))
