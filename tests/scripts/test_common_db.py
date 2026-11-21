"""Database helpers in scripts/shared/common.sh, run against a stubbed docker command."""

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "scripts" / "shared" / "common.sh"
COMPOSE_FILE = ROOT / "deploy" / "compose.yaml"
PASSWORD_HEX = re.compile(r"^[0-9a-f]{64}$")

# Records each call as "<uid>:<gid>|<password file>|<arguments>" and fakes the outcomes.
DOCKER_STUB = r"""
docker() {
  printf '%s|%s|%s\n' "${KN_UID:-}:${KN_GID:-}" "${KN_POSTGRES_PASSWORD_FILE:-}" "$*" \
    >>"$KN_TEST_CALLS"
  case " $* " in
    *" compose version "*) return "${KN_TEST_COMPOSE_STATUS:-0}" ;;
    *" up "*) return "${KN_TEST_UP_STATUS:-0}" ;;
    *" logs "*) echo "LOG TAIL" ;;
  esac
  return 0
}
"""


def _run(tmp_path: Path, script: str, **env: str) -> subprocess.CompletedProcess[str]:
    calls = tmp_path / "calls.log"
    calls.touch()
    environment = {
        "PATH": os.environ["PATH"],
        "DATA_DIR": str(tmp_path / "data"),
        "KN_TEST_CALLS": str(calls),
        **env,
    }
    return subprocess.run(
        ["bash", "-c", f'source "{COMMON}"\n{DOCKER_STUB}\n{script}'],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls.log").read_text().splitlines()


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_password_is_created_private_and_random_at_the_default_location(tmp_path: Path) -> None:
    result = _run(tmp_path, "kn_db_ensure_password")

    assert result.returncode == 0, result.stderr
    secret = tmp_path / "data" / "secrets" / "postgres-password"
    assert PASSWORD_HEX.match(secret.read_text())
    assert _mode(secret) == 0o600
    assert _mode(secret.parent) == 0o700
    assert secret.read_text() not in result.stdout + result.stderr

    other = _run(tmp_path, "kn_db_ensure_password", DATA_DIR=str(tmp_path / "other"))
    assert other.returncode == 0, other.stderr
    assert (tmp_path / "other" / "secrets" / "postgres-password").read_text() != secret.read_text()


def test_existing_password_is_kept(tmp_path: Path) -> None:
    secret = tmp_path / "data" / "secrets" / "postgres-password"
    secret.parent.mkdir(parents=True)
    secret.write_text("chosen-by-owner")

    result = _run(tmp_path, "kn_db_ensure_password")

    assert result.returncode == 0, result.stderr
    assert secret.read_text() == "chosen-by-owner"


@pytest.mark.parametrize("empty", [False, True])
def test_missing_configured_or_empty_password_file_is_refused(tmp_path: Path, empty: bool) -> None:
    configured = tmp_path / "configured" / "password"
    if empty:
        configured.parent.mkdir()
        configured.touch()

    result = _run(tmp_path, "kn_db_ensure_password", KN_POSTGRES_PASSWORD_FILE=str(configured))

    assert result.returncode == 1
    assert "missing or empty" in result.stderr
    assert configured.exists() is empty


def test_relative_password_file_resolves_from_the_project_root(tmp_path: Path) -> None:
    result = _run(tmp_path, "kn_db_password_file", KN_POSTGRES_PASSWORD_FILE="local/password")

    assert result.stdout.strip() == str(ROOT / "local" / "password")


def test_compose_refuses_to_run_as_root(tmp_path: Path) -> None:
    root_id = 'id() { if [ "$1" = -u ]; then echo 0; else command id "$@"; fi; }\n'

    result = _run(tmp_path, root_id + "kn_compose ps")

    assert result.returncode == 1
    assert "not root" in result.stderr
    assert _calls(tmp_path) == []


def test_compose_requires_the_compose_plugin(tmp_path: Path) -> None:
    result = _run(tmp_path, "kn_compose ps", KN_TEST_COMPOSE_STATUS="1")

    assert result.returncode == 1
    assert "Compose v2" in result.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="the helpers refuse to run as root")
def test_db_up_prepares_a_private_volume_then_waits_and_bootstraps(tmp_path: Path) -> None:
    result = _run(tmp_path, "kn_db_up")

    assert result.returncode == 0, result.stderr
    assert _mode(tmp_path / "data" / "postgres") == 0o700
    calls = [call for call in _calls(tmp_path) if "compose version" not in call]
    assert len(calls) == 2
    identity, password_file, up = calls[0].split("|")
    assert identity == f"{os.getuid()}:{os.getgid()}"
    assert password_file == str(tmp_path / "data" / "secrets" / "postgres-password")
    assert up == f"compose --file {COMPOSE_FILE} up --detach --wait --wait-timeout 180 postgres"
    assert " exec -T postgres psql " in calls[1]
    assert calls[1].endswith("--file=/docker-entrypoint-initdb.d/10-kn-bootstrap.sql")


@pytest.mark.skipif(os.geteuid() == 0, reason="the helpers refuse to run as root")
def test_db_up_shows_the_log_and_skips_bootstrap_when_unhealthy(tmp_path: Path) -> None:
    result = _run(tmp_path, "kn_db_up", KN_TEST_UP_STATUS="1")

    assert result.returncode == 1
    assert "LOG TAIL" in result.stdout + result.stderr
    assert "make db-reset" in result.stderr
    assert not any(" exec " in call for call in _calls(tmp_path))


@pytest.mark.parametrize("data_dir", ["", "/", "relative/data"])
def test_reset_refuses_an_unsafe_data_dir(tmp_path: Path, data_dir: str) -> None:
    result = _run(tmp_path, "kn_db_reset", DATA_DIR=data_dir)

    assert result.returncode == 1
    assert "DATA_DIR must be an absolute path" in result.stderr
    assert _calls(tmp_path) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="the helpers refuse to run as root")
def test_reset_replaces_only_the_database_volume(tmp_path: Path) -> None:
    data = tmp_path / "data"
    (data / "postgres" / "18").mkdir(parents=True)
    (data / "postgres" / "18" / "PG_VERSION").write_text("18")
    (data / "raw").mkdir()
    (data / "raw" / "keep.warc").write_text("archive")
    secret = data / "secrets" / "postgres-password"
    secret.parent.mkdir()
    secret.write_text("kept")

    result = _run(tmp_path, "kn_db_reset")

    assert result.returncode == 0, result.stderr
    assert list((data / "postgres").iterdir()) == []
    assert (data / "raw" / "keep.warc").read_text() == "archive"
    assert secret.read_text() == "kept"
    commands = [call.split("|")[2] for call in _calls(tmp_path) if "compose version" not in call]
    assert commands[0] == f"compose --file {COMPOSE_FILE} down"
    assert " up " in f" {commands[1]} "
