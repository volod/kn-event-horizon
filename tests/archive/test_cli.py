import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kn.archive import Archive
from kn.archive.model import ArchiveError
from tests.archive.fixtures import LIMITS, batch, capture, committed_path


def _checkout(root: Path) -> Path:
    for marker in ("pyproject.toml", "AGENTS.md"):
        (root / marker).touch()
    nested = root / "nested"
    nested.mkdir()
    return nested


def _raw(cwd: Path, environment: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    executable = Path(sys.executable).with_name("kn")
    return subprocess.run(
        [str(executable), "--json", "raw", *args],
        env=environment,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_root_required_even_with_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = _checkout(tmp_path)
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("KN_RAW_ARCHIVE_DIR", raising=False)
    monkeypatch.delenv("KN_RAW_INDEX_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "runtime"))
    with pytest.raises(ArchiveError, match="archive_root_required"):
        Archive.configured()
    result = _raw(cwd, dict(os.environ), "verify")
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"] == {
        "code": "E_RAW_ARCHIVE",
        "reason": "archive_root_required",
        "variable": "KN_RAW_ARCHIVE_DIR",
    }
    assert not (tmp_path / "runtime").exists()


def test_dotenv_relative_root_and_cli_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cwd = _checkout(tmp_path)
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("KN_RAW_ARCHIVE_DIR", raising=False)
    monkeypatch.delenv("KN_RAW_INDEX_DIR", raising=False)
    (tmp_path / ".env").write_text("KN_RAW_ARCHIVE_DIR='data/raw archive'\n", encoding="ascii")
    archive = Archive.configured()
    assert archive.root == tmp_path / "data/raw archive"
    assert Archive(Path("data/raw archive")).root == archive.root
    entry = archive.commit(batch(), [capture(backend="blob")], limits=LIMITS).captures[0]
    result = _raw(cwd, dict(os.environ), "verify")
    assert result.returncode == 0
    assert json.loads(result.stderr) == {
        "batches": 1,
        "captures": 1,
        "status": "verified",
        "tombstones": 0,
    }
    committed_path(archive.root, batch(), entry.payload_path).write_bytes(b"truncated")
    corrupted = _raw(cwd, dict(os.environ), "verify")
    assert corrupted.returncode == 1
    assert json.loads(corrupted.stderr)["error"]["reason"] == "payload_digest"
    configured = _raw(cwd, dict(os.environ) | {"KN_RAW_ARCHIVE_DIR": "missing"}, "verify")
    assert configured.returncode == 1
    assert json.loads(configured.stderr)["error"]["reason"] == "archive_root_unavailable"


def test_reindex_requires_explicit_index_and_resolves_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cwd = _checkout(tmp_path)
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("KN_RAW_ARCHIVE_DIR", raising=False)
    monkeypatch.delenv("KN_RAW_INDEX_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "runtime"))
    dotenv = tmp_path / ".env"
    dotenv.write_text("KN_RAW_ARCHIVE_DIR='data/archive'\n", encoding="ascii")
    archive = Archive.configured()
    archive.commit(batch(), [capture(backend="blob")], limits=LIMITS)
    result = _raw(cwd, dict(os.environ), "reindex")
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"] == {
        "code": "E_RAW_ARCHIVE",
        "reason": "index_root_required",
        "variable": "KN_RAW_INDEX_DIR",
    }
    assert not (tmp_path / "runtime").exists()

    dotenv.write_text(
        "KN_RAW_ARCHIVE_DIR='data/archive'\nKN_RAW_INDEX_DIR='data/raw index'\n",
        encoding="ascii",
    )
    result = _raw(cwd, dict(os.environ), "reindex", "--source", "space:example")
    assert result.returncode == 0
    assert json.loads(result.stderr) == {
        "status": "reindexed",
        "schema_version": 1,
        "partitions": 1,
        "covered_captures": 1,
        "published_retained": 1,
    }
    destination = tmp_path / "data/raw index"
    assert (destination / "CURRENT").is_file()
    assert len(list(destination.rglob("*.parquet"))) == 1
    assert Archive.configured().index_root == destination


@pytest.mark.parametrize(
    ("options", "index", "reason"),
    [
        (["--source", "gdelt:example", "--domain", "space"], "index", "index_scope"),
        (["--since", "2026-01-02"], "index", "index_scope"),
        ([], "archive/inside", "index_root_overlap"),
    ],
)
def test_reindex_rejects_invalid_scope_and_roots(
    tmp_path: Path, options: list[str], index: str, reason: str
) -> None:
    cwd = _checkout(tmp_path)
    env = dict(os.environ) | {"KN_RAW_ARCHIVE_DIR": "archive", "KN_RAW_INDEX_DIR": index}
    result = _raw(cwd, env, "reindex", *options)
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"]["reason"] == reason
    assert not (tmp_path / index).exists()
