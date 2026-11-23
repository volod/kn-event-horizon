"""The reviewed deployment set: loading, validation, compilation, and refusal before access."""

import json
import logging
import shutil
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kn import cli, operations
from kn.contracts import load_contract
from kn.contracts import registry as module
from kn.contracts.compiler import compile_registry
from kn.contracts.diagnostics import ContractError
from kn.contracts.registry import MARKER_CONTRACT, registered_contracts, validate_registry
from kn.contracts.schemas import RESOURCES
from tests.contracts.test_compiler import compiler_document, write_document

FIXTURES = Path(__file__).with_name("fixtures") / "registry"


def fixture_contracts() -> tuple:
    return (
        *registered_contracts(),
        load_contract(FIXTURES / "space-observations.json"),
        load_contract(FIXTURES / "semantic-terms.json"),
    )


def registry_copy(tmp_path: Path, entries: list[dict]) -> Path:
    """A registry beside copies of the bundled governance and SATCOM contracts."""
    for name in ("system", "satcom"):
        shutil.copytree(RESOURCES / name, tmp_path / name)
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"contracts": entries}))
    return path


def test_the_registry_deploys_governance_first_then_domain_contracts() -> None:
    contracts = registered_contracts()
    assert [(item.contract_id, item.schema) for item in contracts] == [
        (MARKER_CONTRACT, "system"),
        ("kn.system.source_catalogue", "system"),
        ("kn.space.satcom", "space"),
        ("kn.core.semantic", "semantic"),
        ("kn.core.human_verification", "evidence"),
        ("kn.core.identity", "identity"),
    ]
    validate_registry(fixture_contracts())


@pytest.mark.parametrize(
    "entry",
    [
        {"path": "/etc/passwd"},
        {"path": "../outside.json"},
        {"path": "absent.json"},
        {"path": "satcom/1.0.0.json", "extra": True},
        {"file": "satcom/1.0.0.json"},
    ],
)
def test_registered_files_stay_beside_the_registry(tmp_path: Path, entry: dict) -> None:
    (tmp_path.parent / "outside.json").write_text("{}")
    path = registry_copy(tmp_path, [{"path": "system/1.0.0.json"}, entry])
    with pytest.raises(ContractError, match="registry"):
        registered_contracts(path)


def test_a_contract_outside_the_platform_schemas_is_refused(tmp_path: Path) -> None:
    data = compiler_document()
    data["customProperties"] = [{"property": "kn.storageSchema", "value": "public"}]
    with pytest.raises(ContractError) as error:
        load_contract(write_document(tmp_path, data))
    assert error.value.rule == "storageSchema"
    assert error.value.path == "$/customProperties/0/value"


def test_database_commands_refuse_an_invalid_registry_before_connecting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    data = json.loads((FIXTURES / "semantic-terms.json").read_text())
    data["customProperties"][0]["value"] = "public"
    path = registry_copy(tmp_path, [{"path": "system/1.0.0.json"}, {"path": "public.json"}])
    (tmp_path / "public.json").write_text(json.dumps(data))
    engine = MagicMock(side_effect=AssertionError("database accessed"))
    monkeypatch.setattr(module, "REGISTRY", path)
    monkeypatch.setattr(operations, "engine_from_env", engine)
    for action in ("upgrade", "verify"):
        assert cli.main(["--json", "db", action]) == 1
        assert json.loads(caplog.records[-1].message)["error"]["rule"] == "storageSchema"
    engine.assert_not_called()


def _rename_table(contract, name: str):  # type: ignore[no-untyped-def]
    table = replace(contract.tables[0], name=name)
    return replace(contract, tables=(table, *contract.tables[1:]))


@pytest.mark.parametrize("collision", ["contract", "field", "table", "index", "marker"])
def test_one_deployment_has_unique_contracts_fields_and_names(collision: str) -> None:
    system, catalogue, satcom, core_semantic, evidence, identity, space, semantic = (
        fixture_contracts()
    )
    if collision == "contract":
        space = replace(space, contract_id=satcom.contract_id)
    elif collision == "field":
        table = space.tables[0]
        fields = (replace(table.fields[0], field_id=satcom.tables[0].fields[0].field_id),)
        space = replace(space, tables=(replace(table, fields=(*fields, *table.fields[1:])),))
    elif collision == "table":
        space = _rename_table(space, "countries")
    elif collision == "index":
        # The fixture's index name, used as a SATCOM table name in the same schema.
        space = _rename_table(space, "pk_countries")
    contracts = [system, catalogue, satcom, core_semantic, evidence, identity, space, semantic]
    if collision == "marker":
        contracts = [satcom, system, core_semantic, evidence, identity, space, semantic]
    with pytest.raises(ContractError, match="registry"):
        validate_registry(contracts)


def test_each_registered_contract_compiles_into_its_own_directory(tmp_path: Path) -> None:
    contracts = fixture_contracts()
    compile_registry(contracts, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        item.contract_id for item in contracts
    )
    compile_registry(contracts, tmp_path, check=True)
    (tmp_path / "kn.space.retired").mkdir()
    with pytest.raises(ContractError, match="drift"):
        compile_registry(contracts, tmp_path, check=True)
    (tmp_path / "kn.space.retired").rmdir()
    shutil.rmtree(tmp_path / "kn.semantic.fixture_terms")
    with pytest.raises(ContractError, match="drift"):
        compile_registry(contracts, tmp_path, check=True)


def test_commands_without_a_source_report_every_registered_contract(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    assert cli.main(["--json", "contract", "lint"]) == 0
    result = json.loads(caplog.records[-1].message)
    assert [item["contract_id"] for item in result["contracts"]] == [
        item.contract_id for item in registered_contracts()
    ]
    assert cli.main(["--json", "contract", "compile", "--references", "refs.json"]) == 1
    assert json.loads(caplog.records[-1].message)["error"]["rule"] == "references"
