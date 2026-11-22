"""Passing the available subset cannot clear unimplemented release operator paths."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.e2e.support import ROOT, TIMEOUT_SECONDS


@pytest.mark.parametrize("write_artifacts", [False, True])
def test_release_gate_rejects_a_passing_subset(tmp_path: Path, write_artifacts: bool) -> None:
    arguments = [
        sys.executable,
        "-m",
        "pytest",
        "tests/e2e/test_data.py",
        "tests/i18n/test_core.py",
        "-k",
        "missing_data_translation or original_in_requested_language",
        "-p",
        "no:cacheprovider",
        "--require-bilingual-release",
    ]
    if write_artifacts:
        arguments.extend(["--e2e-artifacts", str(tmp_path)])
    result = subprocess.run(
        arguments, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "2 passed" in result.stdout
    if write_artifacts:
        report = json.loads((tmp_path / "manifest.json").read_text("ascii"))
        assert report["test_exit_code"] == 0
        assert (
            report["selected_tests"]
            == report["passed_tests"]
            == [
                "tests/e2e/test_data.py::test_missing_data_translation_does_not_change_interface_language",
                "tests/i18n/test_core.py::test_original_in_requested_language_precedes_english_translation",
            ]
        )
        assert report["release_ready"] is False
        assert {"review_queue", "dashboards_filters_and_map", "export_readme"} <= set(
            report["release_blockers"]
        )
