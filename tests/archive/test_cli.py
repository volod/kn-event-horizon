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


def _verify(cwd: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    executable = Path(sys.executable).with_name("kn")
    return subprocess.run(
        [str(executable), "--json", "raw", "verify"],
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
    result = _verify(cwd, dict(os.environ))
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
    result = _verify(cwd, dict(os.environ))
    assert result.returncode == 0
    assert json.loads(result.stderr) == {
        "batches": 1,
        "captures": 1,
        "status": "verified",
        "tombstones": 0,
    }
    committed_path(archive.root, batch(), entry.payload_path).write_bytes(b"truncated")
    corrupted = _verify(cwd, dict(os.environ))
    assert corrupted.returncode == 1
    assert json.loads(corrupted.stderr)["error"]["reason"] == "payload_digest"
    configured = _verify(cwd, dict(os.environ) | {"KN_RAW_ARCHIVE_DIR": "missing"})
    assert configured.returncode == 1
    assert json.loads(configured.stderr)["error"]["reason"] == "archive_root_unavailable"
