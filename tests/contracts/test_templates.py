"""Generated native models and physical templates handle edge cases without coercion."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from kn import cli
from kn.contracts import load_contract
from kn.contracts.compiler import compile_contract
from kn.contracts.diagnostics import ContractError
from kn.contracts.exports import artifacts
from tests.contracts.test_compiler import compiler_document, write_document


def test_native_models_preserve_exact_types_and_reject_lossy_values() -> None:
    namespace: dict = {}
    contract = load_contract()
    exec(compile(artifacts(contract)["pydantic/models.py"], "models.py", "exec"), namespace)
    model = namespace["EvidenceClaims"]
    values = {
        field.name: "example"
        for field in contract.table("evidence_claims").fields
        if field.required
    }
    values.update(
        qualifier="exact",
        verification_status="quote_verified",
        information_character="manufacturer_operator_statement",
    )
    values.update(
        is_canonical=False,
        value_num=Decimal("0.704"),
        access_date=date(2026, 11, 22),
        fact_date="2026-11",
    )
    record = model(**values)
    assert record.value_num == Decimal("0.704")
    assert json.loads(record.model_dump_json())["value_num"] == "0.704"
    for invalid in [float("nan"), 0.704, Decimal("1e40"), Decimal("0.0000000000000000001")]:
        with pytest.raises(ValidationError):
            model(**{**values, "value_num": invalid})
    with pytest.raises(ValidationError):
        model(**{**values, "fact_date": "November"})


def test_models_handle_python_reserved_names_dates_and_timestamp(tmp_path: Path) -> None:
    data = compiler_document()
    table = data["schema"][0]
    table["customProperties"] = []
    table["properties"] = table["properties"][:1]
    for name, logical in [
        ("class", "string"),
        ("date", "date"),
        ("str", "string"),
        ("model_dump", "timestamp"),
    ]:
        table["properties"].append(
            {
                "name": name,
                "logicalType": logical,
                "required": True,
                "customProperties": [{"property": "kn.fieldId", "value": f"example.{name}"}],
            }
        )
    contract = load_contract(write_document(tmp_path, data))
    namespace: dict = {}
    exec(compile(artifacts(contract)["pydantic/models.py"], "models.py", "exec"), namespace)
    model = namespace["Select"]
    values = {
        "id": 0,
        "class": "value",
        "date": date(2026, 1, 1),
        "str": "text",
        "model_dump": datetime(2026, 1, 1, tzinfo=UTC),
    }
    assert model(**values).model_dump(by_alias=True) == values
    with pytest.raises(ValidationError):
        model(**{**values, "model_dump": datetime(2026, 1, 1)})
    assert "TIMESTAMP WITH TIME ZONE" in artifacts(contract)["postgresql/schema.sql"]


@pytest.mark.parametrize(
    "mutation", ["unknown_column", "duplicate_index", "bad_unique", "partition_key"]
)
def test_invalid_physical_intent_is_refused(tmp_path: Path, mutation: str) -> None:
    data = compiler_document()
    table = data["schema"][0]
    table["customProperties"] = table["customProperties"][1:]
    index = table["customProperties"][0]["value"][0]
    if mutation == "unknown_column":
        index["fields"] = ["missing"]
    elif mutation == "duplicate_index":
        table["customProperties"][0]["value"].append({**index, "fields": ["id"]})
    elif mutation == "bad_unique":
        index["unique"] = True
    else:
        table["customProperties"].append(
            {"property": "kn.partition", "value": {"strategy": "hash", "fields": ["coverage"]}}
        )
    with pytest.raises(ContractError):
        load_contract(write_document(tmp_path, data))


def test_default_directory_and_custom_check_require_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["contract", "compile"]) == 0
    assert (tmp_path / "generated/manifest.json").is_file()
    data = compiler_document()
    data["schema"][0]["customProperties"] = []
    contract = load_contract(write_document(tmp_path, data))
    with pytest.raises(ContractError, match="--output"):
        compile_contract(contract, check=True)


def test_canonical_outputs_ignore_object_key_order_and_bind_reference_payload(
    tmp_path: Path,
) -> None:
    data = compiler_document()
    data["schema"][0]["customProperties"] = []
    first = load_contract(write_document(tmp_path, data))
    path = tmp_path / "reordered.yaml"
    import yaml

    path.write_text(yaml.safe_dump(data, sort_keys=True))
    second = load_contract(path)
    assert first.digest == second.digest and artifacts(first) == artifacts(second)


def test_reference_definitions_participate_in_digest(tmp_path: Path) -> None:
    from tests.contracts.test_compiler import reference_catalog

    path = write_document(tmp_path, compiler_document())
    refs = reference_catalog(tmp_path)
    first = load_contract(path, references=refs)
    refs.write_text('{"entityClass":{"space.satellite":{"revision":2}}}')
    second = load_contract(path, references=refs)
    assert first.digest != second.digest
    assert artifacts(first) != artifacts(second)


def test_previous_manifest_cannot_delete_unmanaged_files(tmp_path: Path) -> None:
    output = tmp_path / "generated"
    contract = load_contract()
    compile_contract(contract, output)
    protected = tmp_path / "protected.txt"
    protected.write_text("keep")
    (output / "manifest.json").write_text('{"artifacts":{"../protected.txt":"planted"}}')
    with pytest.raises(ContractError, match="managed"):
        compile_contract(contract, output)
    assert protected.read_text() == "keep"


@pytest.mark.parametrize("change", ["index", "references", "spatial"])
def test_additive_evolution_refuses_unimplemented_new_metadata(change: str) -> None:
    from dataclasses import replace

    from kn.contracts import Field
    from kn.contracts.evolution import additions

    previous = load_contract()
    current = replace(previous, version="1.1.0")
    table = current.tables[0]
    if change == "index":
        table = replace(table, extensions_json='{"index":[]}')
    elif change == "references":
        current = replace(current, references_json='{"entityClass":{}}')
    else:
        table = replace(
            table,
            fields=(
                *table.fields,
                Field(
                    "area",
                    "example.area",
                    "string",
                    False,
                    False,
                    extensions_json='{"spatialProfile":{}}',
                ),
            ),
        )
    current = replace(current, tables=(table, *current.tables[1:]))
    with pytest.raises(ValueError, match="reviewed"):
        additions(previous, current)
