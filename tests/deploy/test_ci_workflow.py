"""GitHub Actions runs only the lightweight gate; local-only tests stay on the development host."""

import shlex
from typing import Any

import yaml

from tests.conftest import LOCAL_SELECTION, UNIT_SELECTION
from tests.deploy.make_dry_run import ROOT, pytest_commands

WORKFLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
GITHUB_TARGET = "ci-github"


def _jobs() -> dict[str, Any]:
    jobs = WORKFLOW["jobs"]
    assert isinstance(jobs, dict) and jobs
    return jobs


def _run_commands() -> list[str]:
    return [step["run"] for job in _jobs().values() for step in job["steps"] if "run" in step]


def _pytest_selections(target: str) -> list[str]:
    """The -m expression of every pytest command that make would run for the target."""
    return [
        options[options.index("-m") + 1] if "-m" in options else ""
        for options in pytest_commands(target)
    ]


def test_no_github_job_starts_a_service_or_a_job_container() -> None:
    for name, job in _jobs().items():
        assert "services" not in job, name
        assert "container" not in job, name


def test_github_jobs_run_only_the_locked_install_and_the_github_gate() -> None:
    for command in _run_commands():
        words = shlex.split(command)
        assert words[:2] in (["uv", "sync"], ["make", GITHUB_TARGET]), command


def test_the_github_gate_runs_only_the_lightweight_unit_tests() -> None:
    assert _pytest_selections(GITHUB_TARGET) == [UNIT_SELECTION]


def test_the_local_gate_adds_the_local_only_tests() -> None:
    assert _pytest_selections("ci-local") == [UNIT_SELECTION, LOCAL_SELECTION]
