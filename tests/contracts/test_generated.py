"""The committed generated/ output is current, and --check uses the compile default directory."""

from pathlib import Path

import pytest

from kn import cli
from kn.contracts import load_contract
from kn.contracts.compiler import compile_contract, compile_registry
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.registry import registered_contracts
from tests.contracts.test_compiler import compiler_document, write_document

ROOT = Path(__file__).resolve().parents[2]
SATCOM_OUTPUT = Path("generated") / "contracts" / "kn.space.satcom"


def test_committed_generated_output_matches_a_fresh_compile() -> None:
    compile_registry(registered_contracts(), ROOT / "generated" / "contracts", check=True)


def test_check_without_output_checks_the_default_compile_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["contract", "compile"]) == 0
    assert (tmp_path / SATCOM_OUTPUT / "manifest.json").is_file()
    assert cli.main(["contract", "compile", "--check"]) == 0
    (tmp_path / SATCOM_OUTPUT / "postgresql" / "schema.sql").write_text("drift")
    assert cli.main(["contract", "compile", "--check"]) == 1


@pytest.mark.parametrize("contract_id", ["../escape", "a/b", ".hidden", ""])
def test_the_default_directory_needs_a_plain_contract_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contract_id: str
) -> None:
    data = compiler_document()
    data["id"] = contract_id or " "
    data["schema"][0]["customProperties"] = []
    contract = load_contract(write_document(tmp_path, data))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ContractError, match="--output"):
        compile_contract(contract)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["contract.json"]


def test_generated_sql_has_no_trailing_whitespace_and_keeps_multiline_text(
    tmp_path: Path,
) -> None:
    data = compiler_document()
    data["schema"][0]["customProperties"] = []
    ddl = artifacts(load_contract(write_document(tmp_path, data)))["postgresql/schema.sql"]
    assert all(line == line.rstrip() for line in ddl.splitlines())
    # A line break inside a comment literal is escaped, so no literal spans lines.
    assert "U&'Owner''s coverage\\000awith a second line.'" in ddl
