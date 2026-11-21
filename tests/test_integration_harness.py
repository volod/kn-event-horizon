"""The integration harness without a database: configuration, selection, skips, and failures."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import UNIT_SELECTION
from tests.integration.harness import (
    DATABASE_URL_VARIABLE,
    PASSWORD_FILE_VARIABLE,
    HarnessError,
    IntegrationDatabase,
)

ROOT = Path(__file__).resolve().parents[1]
SECRET = "s3cret-sentinel"
NO_DATABASE_REASON = f"no integration database configured: {DATABASE_URL_VARIABLE} is not set"
NO_TESTS_RAN = 5


def _missing_socket(tmp_path: Path) -> str:
    """A server address that fails at once without the network: a socket directory with no socket."""
    return f"host={tmp_path} port=5432 dbname=kn user=postgres"


def _pytest(*arguments: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *arguments],
        env={"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1", **env},
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("value", [None, "", "   "])
def test_no_database_is_configured_without_a_url(value: str | None) -> None:
    environ = {} if value is None else {DATABASE_URL_VARIABLE: value}

    assert IntegrationDatabase.from_environment(environ) is None


def test_the_password_file_resolves_from_the_project_root_without_its_newline(
    tmp_path: Path,
) -> None:
    secret = tmp_path / "password"
    secret.write_text(f"{SECRET}\n")
    relative = os.path.relpath(secret, ROOT)

    for path in (str(secret), relative):
        database = IntegrationDatabase.from_environment(
            {
                DATABASE_URL_VARIABLE: "postgresql://postgres@127.0.0.1/kn",
                PASSWORD_FILE_VARIABLE: path,
            }
        )
        assert database == IntegrationDatabase("postgresql://postgres@127.0.0.1/kn", SECRET)


@pytest.mark.parametrize("content", [None, "", "\n"])
def test_a_missing_or_empty_password_file_is_refused(tmp_path: Path, content: str | None) -> None:
    secret = tmp_path / "password"
    if content is not None:
        secret.write_text(content)
    environ = {DATABASE_URL_VARIABLE: "dbname=kn", PASSWORD_FILE_VARIABLE: str(secret)}

    with pytest.raises(HarnessError, match="missing or empty") as error:
        IntegrationDatabase.from_environment(environ)

    assert str(secret) in str(error.value)
    assert "make db-up" in str(error.value)


def test_an_invalid_url_is_refused_without_quoting_it() -> None:
    with pytest.raises(HarnessError, match="not a libpq connection string") as error:
        IntegrationDatabase.from_environment({DATABASE_URL_VARIABLE: f"host=x {SECRET}"})

    assert SECRET not in str(error.value)


def test_the_description_names_the_server_without_the_password() -> None:
    database = IntegrationDatabase(f"postgresql://kn:{SECRET}@127.0.0.1:15432/kn", SECRET)

    assert database.describe() == "kn@127.0.0.1:15432/kn"


def test_an_unreachable_database_fails_with_a_hint_and_no_password(tmp_path: Path) -> None:
    database = IntegrationDatabase(_missing_socket(tmp_path), SECRET)

    with pytest.raises(HarnessError, match="cannot connect to the integration database") as error:
        database.check()

    assert "make db-up" in str(error.value)
    assert SECRET not in str(error.value)


def test_unit_runs_deselect_the_integration_tests() -> None:
    result = _pytest("tests/integration", "-m", UNIT_SELECTION)

    assert result.returncode == NO_TESTS_RAN, result.stdout + result.stderr
    assert " deselected" in result.stdout
    assert " passed" not in result.stdout


def test_integration_tests_skip_with_a_reason_without_a_database() -> None:
    result = _pytest("tests/integration")

    assert result.returncode == 0, result.stdout + result.stderr
    assert " skipped" in result.stdout
    assert " passed" not in result.stdout
    assert NO_DATABASE_REASON in result.stdout


def test_integration_tests_fail_when_the_configured_database_is_unreachable(
    tmp_path: Path,
) -> None:
    secret = tmp_path / "password"
    secret.write_text(SECRET)

    result = _pytest(
        "tests/integration",
        **{DATABASE_URL_VARIABLE: _missing_socket(tmp_path), PASSWORD_FILE_VARIABLE: str(secret)},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert " error" in result.stdout
    assert "cannot connect to the integration database" in result.stdout
    assert "make db-up" in result.stdout
    assert SECRET not in result.stdout + result.stderr


def test_a_test_elsewhere_that_uses_the_database_is_an_integration_test(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    module = tmp_path / "test_elsewhere.py"
    module.write_text("def test_uses_the_database(db_connection):\n    pass\n")

    result = _pytest(
        "-p", "tests.conftest", "-c", str(tmp_path / "pytest.ini"), "--rootdir", str(tmp_path),
        "-m", UNIT_SELECTION, str(module),
    )  # fmt: skip

    assert result.returncode == NO_TESTS_RAN, result.stdout + result.stderr
    assert "1 deselected" in result.stdout


def test_unit_runs_deselect_a_heavy_test(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    module = tmp_path / "test_heavy.py"
    module.write_text(
        "import pytest\n\n\n@pytest.mark.heavy\ndef test_large_rebuild():\n    pass\n\n\n"
        "def test_light():\n    pass\n"
    )

    result = _pytest(
        "-p", "tests.conftest", "-c", str(tmp_path / "pytest.ini"), "--rootdir", str(tmp_path),
        "--strict-markers", "-m", UNIT_SELECTION, str(module),
    )  # fmt: skip

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed, 1 deselected" in result.stdout
