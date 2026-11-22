"""Full compiler artifacts, offline references, and non-mutating drift checks."""

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from kn import cli
from kn.contracts.compiler import compile_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from kn.contracts.loader import load_contract


def compiler_document() -> dict:
    return {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": "space.example",
        "version": "1.0.0",
        "status": "draft",
        "customProperties": [{"property": "kn.storageSchema", "value": "space"}],
        "schema": [
            {
                "name": "select",
                "logicalType": "object",
                "physicalType": "table",
                "description": "Owner's coverage\nwith a second line.",
                "customProperties": [
                    {"property": "kn.entityClass", "value": "space.satellite"},
                    {
                        "property": "kn.index",
                        "value": [
                            {
                                "name": "coverage_idx",
                                "fields": ["coverage"],
                                "method": "gist",
                                "unique": False,
                            }
                        ],
                    },
                ],
                "properties": [
                    {
                        "name": "id",
                        "logicalType": "integer",
                        "required": True,
                        "primaryKey": True,
                        "customProperties": [
                            {"property": "kn.fieldId", "value": "space.example.id"}
                        ],
                    },
                    {
                        "name": "coverage",
                        "logicalType": "string",
                        "description": "Area of use",
                        "customProperties": [
                            {"property": "kn.fieldId", "value": "space.example.coverage"},
                            {
                                "property": "kn.spatialProfile",
                                "value": {
                                    "geometryType": "Polygon",
                                    "srid": 4326,
                                    "precision": 6,
                                    "coverageSemantics": "declared",
                                    "validity": "required",
                                },
                            },
                        ],
                    },
                ],
            }
        ],
    }


def write_document(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data))
    return path


def reference_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "references.json"
    path.write_text(json.dumps({"entityClass": {"space.satellite": {}}}))
    return path


def test_supplied_contract_generates_all_outputs_and_checks_actual_bytes(tmp_path: Path) -> None:
    path = write_document(tmp_path, compiler_document())
    references = reference_catalog(tmp_path)
    contract = load_contract(path, references=references)
    output = tmp_path / "generated"
    compile_contract(contract, output)
    first = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    compile_contract(contract, output)
    assert first == {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    }
    compile_contract(contract, output, check=True)
    result = artifacts(contract)
    ddl = result["postgresql/schema.sql"]
    assert 'CREATE TABLE space."select"' in ddl
    assert "geometry(Polygon,4326)" in ddl and "ST_IsValid" in ddl
    assert "USING gist" in ddl and "COMMENT ON TABLE" in ddl and "Owner''s" in ddl
    namespace: dict = {}
    exec(compile(result["pydantic/models.py"], "models.py", "exec"), namespace)
    model = namespace["Select"]
    assert model(id=1).id == 1
    with pytest.raises(ValidationError):
        model(id="1")
    with pytest.raises(ValidationError):
        model(id=1, unknown="refused")
    dbt = yaml.safe_load(result["dbt/sources.yaml"])
    assert dbt["sources"][0]["tables"][0]["name"] == "select"
    assert "space.example.coverage" in result["docs/contract.md"]
    (output / "postgresql/schema.sql").write_text("drift")
    with pytest.raises(ContractError, match="drift"):
        compile_contract(contract, output, check=True)
    assert (output / "postgresql/schema.sql").read_text() == "drift"


def test_reference_failure_is_actionable_and_does_not_create_output(tmp_path: Path, caplog) -> None:
    path = write_document(tmp_path, compiler_document())
    output = tmp_path / "generated"
    assert cli.main(["contract", "compile", str(path), "--output", str(output), "--json"]) == 1
    error = json.loads(caplog.records[-1].message)["error"]
    assert error["rule"] == "reference" and "/customProperties/" in error["path"]
    assert not output.exists()


def test_cli_compiles_yaml_with_local_references(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(compiler_document()))
    refs = reference_catalog(tmp_path)
    args = [
        "contract",
        "compile",
        str(path),
        "--references",
        str(refs),
        "--output",
        str(tmp_path / "out"),
    ]
    assert cli.main(args) == 0
    assert cli.main([*args, "--check"]) == 0


@pytest.mark.parametrize("mutation", ["extra", "missing", "manifest", "symlink"])
def test_check_detects_file_set_manifest_and_symlink_drift(tmp_path: Path, mutation: str) -> None:
    contract = load_contract()
    output = tmp_path / "generated"
    compile_contract(contract, output)
    if mutation == "extra":
        (output / "stale.txt").write_text("stale")
    elif mutation == "missing":
        (output / "postgresql/metadata.json").unlink()
    elif mutation == "manifest":
        (output / "manifest.json").write_text("{}")
    else:
        path = output / "postgresql/metadata.json"
        path.unlink()
        path.symlink_to(tmp_path / "absent")
    with pytest.raises(ContractError, match=r"drift|symlink"):
        compile_contract(contract, output, check=True)


def test_recompile_removes_previously_managed_stale_artifacts(tmp_path: Path) -> None:
    from dataclasses import replace

    contract = load_contract()
    compile_contract(contract, tmp_path)
    next_contract = replace(contract, tables=contract.tables[:1])
    compile_contract(next_contract, tmp_path)
    compile_contract(next_contract, tmp_path, check=True)


def test_repeated_composite_reference_produces_one_constraint(tmp_path: Path) -> None:
    from kn.contracts.sqlalchemy import metadata

    data = compiler_document()
    table = data["schema"][0]
    table["customProperties"] = []
    fields = table["properties"]
    fields[1]["logicalType"] = "integer"
    fields[1]["required"] = fields[1]["primaryKey"] = True
    fields[1]["customProperties"] = fields[1]["customProperties"][:1]
    ref = {"table": "select", "fields": ["id", "coverage"], "targetFields": ["id", "coverage"]}
    for field in fields:
        field["customProperties"].append({"property": "kn.foreignKey", "value": ref})
    contract = load_contract(write_document(tmp_path, data))
    assert len(metadata(contract).tables["space.select"].foreign_key_constraints) == 1


def test_artifact_digests_are_identical_in_independent_processes() -> None:
    import os
    import subprocess
    import sys

    program = (
        "import json; from kn.contracts import load_contract; "
        "from kn.contracts.exports import artifact_digests; "
        "print(json.dumps(artifact_digests(load_contract()), sort_keys=True))"
    )
    results = [
        subprocess.check_output(
            [sys.executable, "-c", program],
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
            timeout=30,
        )
        for seed in (1, 42, 99)
    ]
    assert results[0] == results[1] == results[2]
