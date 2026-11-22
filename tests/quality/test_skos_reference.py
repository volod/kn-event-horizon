"""The Jena reference check exports every scheme and fails on any RIOT error or warning."""

import json
import subprocess
from pathlib import Path

import pytest

from kn.quality import skos_reference
from kn.quality.prerequisites import MARKER, load_manifest
from tests.quality.test_prerequisites import ROOT


def fake_jena(data_dir: Path) -> None:
    tool = load_manifest(ROOT)["downloaded_tools"]["apache_jena"]
    target = data_dir / tool["install_dir"]
    (target / "bin").mkdir(parents=True)
    (target / tool["executable"]).write_text("#!/bin/sh\n")
    (target / MARKER).write_text(tool["sha512"] + "\n")


def run_with(returncode: int, stderr: str) -> skos_reference.Run:
    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        assert command[0].endswith("bin/riot") and command[1] == "--validate"
        assert Path(command[2]).read_bytes().isascii()
        return subprocess.CompletedProcess(command, returncode, "", stderr)

    return run


def test_every_scheme_is_validated_and_summarized(tmp_path: Path) -> None:
    fake_jena(tmp_path)
    summary, failed = skos_reference.check(ROOT, tmp_path, run_with(0, ""))
    document = json.loads(summary.read_text())
    assert failed == [] and len(document["schemes"]) == 16
    assert document["tool"] == "Apache Jena RIOT 6.3.0"
    assert summary.parent.parent == tmp_path / "skos-reference"


@pytest.mark.parametrize(("returncode", "stderr"), [(1, "ERROR riot :: bad IRI"), (0, "WARN x")])
def test_an_error_or_a_warning_fails_the_check(
    tmp_path: Path, returncode: int, stderr: str
) -> None:
    fake_jena(tmp_path)
    _, failed = skos_reference.check(ROOT, tmp_path, run_with(returncode, stderr))
    assert len(failed) == 16 and failed[0]["messages"] == stderr


def test_a_missing_jena_names_the_bootstrap(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="make bootstrap"):
        skos_reference.check(ROOT, tmp_path, run_with(0, ""))
    assert skos_reference.main(["--root", str(ROOT), "--data-dir", str(tmp_path)]) == 1
