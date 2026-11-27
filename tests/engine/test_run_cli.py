"""Admission for source execution precedes archive or database setup."""

import json
from pathlib import Path

import pytest

from kn.cli import main

CANDIDATE = Path(__file__).parents[1] / "sources/fixtures/config/http.yaml"


@pytest.mark.parametrize("action", ["run", "replay"])
def test_candidate_profile_is_not_executable(action: str, caplog: pytest.LogCaptureFixture) -> None:
    arguments = ["--json", "source", action, str(CANDIDATE)]
    if action == "replay":
        arguments.extend(["--archive-run-id", "fixture-run"])
    assert main(arguments) == 1
    error = json.loads(caplog.records[-1].message)["error"]
    assert (error["code"], error["path"], error["rule"]) == (
        "E_SOURCE_CONFIG",
        "$/approval/state",
        "enabledState",
    )
