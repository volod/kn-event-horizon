"""Fixtures shared by the database integration tests."""

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from tests.integration.harness import IntegrationDatabase


@pytest.fixture
def rebuild_connection(
    integration_database: IntegrationDatabase, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Connection]:
    """A development-mode transaction that is always rolled back, so rebuilds leave no trace."""
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            yield connection
            transaction.rollback()
    finally:
        engine.dispose()
