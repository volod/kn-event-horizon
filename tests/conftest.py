"""Shared pytest configuration: the local-only markers and the database fixtures.

GitHub Actions runs only the lightweight unit tests, UNIT_SELECTION, through make ci-github. Tests
that need a service endpoint carry the integration marker, and tests that need large memory or a
long run time carry the heavy marker; both run only locally, through make ci-local.

Tests under tests/integration/, and tests that use the integration_database fixture directly or
through another fixture, are marked integration. `make test-integration` selects them, and they
skip with a reason when no database is configured.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.integration.harness import (
    NOT_CONFIGURED,
    Connection,
    HarnessError,
    IntegrationDatabase,
    ScratchSchemas,
)

INTEGRATION_MARKER = "integration"
HEAVY_MARKER = "heavy"
# The -m expressions of the Makefile; tests/deploy/test_ci_workflow.py checks that they agree.
UNIT_SELECTION = f"not {INTEGRATION_MARKER} and not {HEAVY_MARKER}"
LOCAL_SELECTION = f"{INTEGRATION_MARKER} or {HEAVY_MARKER}"
INTEGRATION_FIXTURE = "integration_database"
INTEGRATION_DIRECTORY = Path(__file__).resolve().parent / "integration"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        f"{INTEGRATION_MARKER}: needs the integration database; runs only locally "
        "(make test-integration, make ci-local)",
    )
    config.addinivalue_line(
        "markers",
        f"{HEAVY_MARKER}: needs large memory or a long run time; runs only locally (make ci-local)",
    )


# Runs before the mark plugin deselects by -m, so that -m sees the added markers.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        in_directory = item.path.is_relative_to(INTEGRATION_DIRECTORY)
        if in_directory or INTEGRATION_FIXTURE in getattr(item, "fixturenames", ()):
            item.add_marker(INTEGRATION_MARKER)


@pytest.fixture(scope="session")
def integration_database() -> IntegrationDatabase:
    """The configured database, checked once per session. Skips when none is configured."""
    try:
        database = IntegrationDatabase.from_environment(os.environ)
        if database is None:
            pytest.skip(NOT_CONFIGURED)
        database.check()
    except HarnessError as error:
        pytest.fail(str(error), pytrace=False)
    return database


@pytest.fixture(scope="session")
def scratch_schemas(integration_database: IntegrationDatabase) -> Iterator[ScratchSchemas]:
    """Scratch schemas private to this session. They are dropped when the session ends."""
    scratch = ScratchSchemas.create(integration_database)
    try:
        yield scratch
    finally:
        scratch.close()


@pytest.fixture
def db_connection(integration_database: IntegrationDatabase) -> Iterator[Connection]:
    """A new connection per test. Work that the test does not commit is rolled back."""
    connection = integration_database.connect()
    try:
        yield connection
    finally:
        connection.close()


from tests.domains.space.satcom.fixtures import source_package  # noqa: E402, F401
