"""Exercise the real CLI, its golden outputs, and machine contract in both locales."""

import hashlib
import json
from pathlib import Path

import pytest

from kn.contracts import load_contract
from kn.domains.space.satcom.package import read_package
from kn.i18n import Translator
from kn.metadata import project_info
from tests.e2e.support import FIXTURES, LOCALES, run_cli, write_json


@pytest.mark.parametrize("locale", LOCALES)
def test_cli_golden_paths(locale: str, e2e_artifacts: Path) -> None:
    goldens = json.loads((FIXTURES / "cli.json").read_text("ascii"))[locale]
    for case in goldens:
        actual = run_cli(case["arguments"], KN_LOCALE=locale)
        write_json(e2e_artifacts / locale / "cli" / f"{case['id']}.json", actual)
        normalized = {
            key: value.replace(project_info().version, "<version>")
            if isinstance(value, str)
            else value
            for key, value in actual.items()
        }
        assert normalized == case["expected"], case["id"]


@pytest.mark.parametrize("locale", LOCALES)
def test_real_package_validation_and_compilation(
    locale: str, source_package: Path, tmp_path: Path, e2e_artifacts: Path
) -> None:
    package = read_package(source_package, load_contract())
    arguments = ["space", "satcom", "validate", str(source_package)]
    human = run_cli(arguments, KN_LOCALE=locale)
    write_json(e2e_artifacts / locale / "cli" / "satcom-validate.json", human)
    assert human == {
        "exit_code": 0,
        "stdout": "",
        "stderr": Translator(locale).text(
            "cli.validated",
            import_id=package.import_id,
            tables=Translator(locale).plural("cli.tables", len(package.rows)),
        )
        + "\n",
    }
    machine = run_cli([*arguments, "--json"], KN_LOCALE=locale)
    write_json(e2e_artifacts / locale / "cli" / "satcom-manifest.json", machine)
    assert machine["exit_code"] == 0 and machine["stdout"] == ""
    assert json.loads(machine["stderr"]) == package.manifest()
    destination = tmp_path / locale / "compiled"
    compiled = run_cli(["contract", "compile", "--output", str(destination)], KN_LOCALE=locale)
    write_json(e2e_artifacts / locale / "cli" / "contract-compile.json", compiled)
    assert compiled["exit_code"] == 0
    satcom = destination / load_contract().contract_id
    manifest = json.loads((satcom / "manifest.json").read_text("ascii"))
    assert manifest["contract_digest"] == load_contract().digest
    assert manifest["artifacts"]
    for name, digest in manifest["artifacts"].items():
        assert hashlib.sha256((satcom / name).read_bytes()).hexdigest() == digest
    write_json(e2e_artifacts / locale / "compiled-manifest.json", manifest)


def test_locale_selection_does_not_change_machine_results(e2e_artifacts: Path) -> None:
    results = [run_cli(["info", "--json"], KN_LOCALE=locale) for locale in LOCALES]
    assert results[0] == results[1]
    assert set(json.loads(results[0]["stderr"])) == {"distribution", "package", "version"}
    write_json(e2e_artifacts / "machine-parity.json", results[0])
    assert run_cli(["info", "--locale", "en"], KN_LOCALE="uk") == run_cli(["info"])
    assert run_cli(["info", "--locale=uk"], KN_LOCALE="en") == run_cli(["info"], KN_LOCALE="uk")


@pytest.mark.parametrize(
    ("arguments", "environment", "expected"),
    [
        (["--locale"], "uk", "uk"),
        (["--locale", "uk", "info", "--locale"], "en", "uk"),
        (["--locale", "en", "info", "--locale"], "uk", "en"),
        (["--locale", "bad", "info", "--locale"], "uk", "en"),
        (["--locale"], "bad", "en"),
    ],
)
def test_malformed_locale_option_keeps_the_selected_interface(
    arguments: list[str], environment: str, expected: str
) -> None:
    result = run_cli(arguments, KN_LOCALE=environment)
    assert result["exit_code"] == 2
    assert result["stderr"] == Translator(expected).text("cli.arguments_error", prog="kn") + "\n"
    assert str(result["stdout"]).startswith(Translator(expected).text("cli.usage"))


def test_malformed_locale_json_is_machine_readable() -> None:
    result = run_cli(["--locale", "--json"], KN_LOCALE="uk")
    assert result == {
        "exit_code": 2,
        "stdout": "",
        "stderr": '{"error": {"code": "E_ARGUMENTS"}}\n',
    }
