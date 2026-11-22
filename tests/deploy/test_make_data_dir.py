"""Make resolves DATA_DIR as the shell helpers do and keeps a path with a space in one piece."""

import shutil
from pathlib import Path

import pytest

from tests.deploy.make_dry_run import ROOT, pytest_commands

# The files that make needs to resolve DATA_DIR in a copy of the project.
PROJECT_FILES = ("Makefile", "scripts/shared/common.sh")
CACHE_OPTION = "cache_dir="


def _project(tmp_path: Path, dot_env: str | None = None) -> Path:
    project = tmp_path / "project"
    for name in PROJECT_FILES:
        copy = project / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, copy)
    if dot_env is not None:
        (project / ".env").write_text(dot_env, encoding="utf-8")
    return project


def _pytest_caches(target: str, project: Path, **env: str) -> list[str]:
    unset = () if "DATA_DIR" in env else ("DATA_DIR",)
    return [
        option.removeprefix(CACHE_OPTION)
        for options in pytest_commands(target, project, unset, **env)
        for option in options
        if option.startswith(CACHE_OPTION)
    ]


@pytest.mark.parametrize("target", ["test", "test-integration"])
def test_a_data_dir_with_a_space_is_one_pytest_cache_path(tmp_path: Path, target: str) -> None:
    data_dir = tmp_path / "audit data"

    caches = _pytest_caches(target, _project(tmp_path), DATA_DIR=str(data_dir))

    assert caches == [f"{data_dir}/cache/pytest"]


@pytest.mark.parametrize(
    ("dot_env", "expected"),
    [(None, ".data"), ("DATA_DIR=from-dot-env\n", "from-dot-env")],
    ids=["default", "dot-env"],
)
def test_make_reads_data_dir_from_dot_env_like_the_shell_helpers(
    tmp_path: Path, dot_env: str | None, expected: str
) -> None:
    project = _project(tmp_path, dot_env)

    assert _pytest_caches("test", project) == [f"{project}/{expected}/cache/pytest"]
