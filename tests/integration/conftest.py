"""Fixtures shared by the database integration tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from tests.integration.harness import IntegrationDatabase
from tests.integration.review_support import review_database  # noqa: F401


@pytest.fixture
def rebuild_connection(
    integration_database: IntegrationDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Connection]:
    """A development-mode transaction that is always rolled back, so rebuilds leave no trace."""
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            yield connection
            transaction.rollback()
    finally:
        engine.dispose()
