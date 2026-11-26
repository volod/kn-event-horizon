"""Exercise the real CLI, its English goldens, and machine contract."""

import hashlib
import json
from pathlib import Path

import pytest

from kn.contracts import load_contract
from kn.domains.space.satcom.package import read_package
from kn.i18n import Translator
from kn.metadata import project_info
from tests.e2e.support import FIXTURES, normalize_usage, run_cli, write_json


def _golden_output(
    result: dict[str, object], *, version: str, usage_prefix: str
) -> dict[str, object]:
    normalized = {
        key: value.replace(version, "<version>") if isinstance(value, str) else value
        for key, value in result.items()
    }
    stdout = normalized["stdout"]
    if isinstance(stdout, str):
        normalized["stdout"] = normalize_usage(stdout, usage_prefix)
    return normalized


@pytest.mark.parametrize("separator", [" ", "\n                   "])
def test_cli_golden_normalization_preserves_help_body_and_stderr(separator: str) -> None:
    result: dict[str, object] = {
        "stdout": f"usage: kn identity {{show,resolve}}{separator}...\n\n"
        "commands:\n  show    show current holdings\n          and object state\n",
        "stderr": "diagnostic from 0.1.0\n  details\n",
        "exit_code": 0,
    }
    assert _golden_output(result, version="0.1.0", usage_prefix="usage: ") == {
        "stdout": "usage: kn identity {show,resolve} ...\n\n"
        "commands:\n  show    show current holdings\n          and object state\n",
        "stderr": "diagnostic from <version>\n  details\n",
        "exit_code": 0,
    }


def test_usage_only_golden_accepts_argparse_continuation_wrapping() -> None:
    expected: dict[str, object] = {
        "stdout": "usage: kn identity {show,resolve} ...\n",
        "stderr": "E_ARGUMENTS: invalid arguments\n",
        "exit_code": 2,
    }
    wrapped = {**expected, "stdout": "usage: kn identity {show,resolve}\n                 ...\n"}
    assert _golden_output(wrapped, version="0.1.0", usage_prefix="usage: ") == expected


def test_cli_golden_paths(e2e_artifacts: Path) -> None:
    goldens = json.loads((FIXTURES / "cli.json").read_text("ascii"))
    version = project_info().version
    usage_prefix = Translator().text("cli.usage")
    for case in goldens:
        actual = run_cli(case["arguments"])
        write_json(e2e_artifacts / "cli" / f"{case['id']}.json", actual)
        assert _golden_output(actual, version=version, usage_prefix=usage_prefix) == _golden_output(
            case["expected"], version=version, usage_prefix=usage_prefix
        ), case["id"]


def test_real_package_validation_and_compilation(
    source_package: Path, tmp_path: Path, e2e_artifacts: Path
) -> None:
    package = read_package(source_package, load_contract())
    arguments = ["space", "satcom", "validate", str(source_package)]
    human = run_cli(arguments)
    write_json(e2e_artifacts / "cli" / "satcom-validate.json", human)
    assert human == {
        "exit_code": 0,
        "stdout": "",
        "stderr": Translator().text(
            "cli.validated",
            import_id=package.import_id,
            tables=Translator().plural("cli.tables", len(package.rows)),
        )
        + "\n",
    }
    machine = run_cli([*arguments, "--json"])
    write_json(e2e_artifacts / "cli" / "satcom-manifest.json", machine)
    assert machine["exit_code"] == 0 and machine["stdout"] == ""
    assert json.loads(machine["stderr"]) == package.manifest()
    destination = tmp_path / "compiled"
    compiled = run_cli(["contract", "compile", "--output", str(destination)])
    write_json(e2e_artifacts / "cli" / "contract-compile.json", compiled)
    assert compiled["exit_code"] == 0
    satcom = destination / load_contract().contract_id
    manifest = json.loads((satcom / "manifest.json").read_text("ascii"))
    assert manifest["contract_digest"] == load_contract().digest
    assert manifest["artifacts"]
    for name, digest in manifest["artifacts"].items():
        assert hashlib.sha256((satcom / name).read_bytes()).hexdigest() == digest
    write_json(e2e_artifacts / "compiled-manifest.json", manifest)


def test_json_option_works_on_both_sides_of_the_command(e2e_artifacts: Path) -> None:
    result = run_cli(["info", "--json"])
    assert result == run_cli(["--json", "info"])
    assert set(json.loads(result["stderr"])) == {"distribution", "package", "version"}
    write_json(e2e_artifacts / "machine-info.json", result)


@pytest.mark.parametrize("arguments", [["--locale", "uk", "info"], ["info", "--locale=uk"]])
def test_removed_interface_locale_option_is_an_argument_error(arguments: list[str]) -> None:
    assert run_cli([*arguments, "--json"]) == {
        "exit_code": 2,
        "stdout": "",
        "stderr": '{"error": {"code": "E_ARGUMENTS"}}\n',
    }
