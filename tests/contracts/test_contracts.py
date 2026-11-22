"""Contract compatibility, generated artifacts, and independent Avro validation."""

import io
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import fastavro
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from jsonschema import ValidationError, validate
from sqlalchemy.dialects import postgresql

from kn.contracts import Field, load_contract
from kn.contracts.compiler import compile_contract
from kn.contracts.evolution import additions, evolve
from kn.contracts.exports import artifacts, avro, elasticsearch, json_schema
from kn.contracts.loader import SATCOM
from kn.contracts.registry import marker_table
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import record_installed


def test_contract_compilation_is_deterministic_and_matches_reviewed_digests(tmp_path: Path) -> None:
    contract = load_contract()
    assert contract.version == "1.0.0"
    assert len(contract.tables) == 31
    assert artifacts(contract) == artifacts(load_contract())
    compile_contract(contract, check=True)
    compile_contract(contract, tmp_path)
    for name, content in artifacts(contract).items():
        assert (tmp_path / name).read_text() == content


@pytest.mark.parametrize(
    "mutation", ["unknown_extension", "missing_type", "bad_type", "bad_fk", "duplicate"]
)
def test_invalid_contracts_are_refused(tmp_path: Path, mutation: str) -> None:
    data = json.loads(SATCOM.read_text())
    field = data["schema"][4]["properties"][1]
    if mutation == "unknown_extension":
        field["customProperties"].append({"property": "kn.typo", "value": "ignored"})
    elif mutation == "missing_type":
        del field["logicalType"]
    elif mutation == "bad_type":
        field["logicalType"] = "object"
    elif mutation == "bad_fk":
        field["customProperties"].append(
            {
                "property": "kn.foreignKey",
                "value": {"table": "absent", "fields": ["id"], "targetFields": ["id"]},
            }
        )
    elif mutation == "duplicate":
        data["schema"].append(data["schema"][0])
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data))
    with pytest.raises((ValueError, ValidationError, KeyError)):
        load_contract(path)


def test_postgresql_model_preserves_keys_exact_types_and_deferred_snapshot_references() -> None:
    model = metadata(load_contract())
    table = model.tables["space.evidence_claims"]
    assert [c.name for c in table.primary_key] == ["import_id", "claim_id"]
    assert isinstance(table.c.value_num.type, sa.Numeric)
    assert table.c.value_num.type.precision == 38
    assert table.c.value_num.type.scale == 18
    assert isinstance(table.c.fact_date.type, sa.Text)
    foreign = next(fk for fk in table.foreign_key_constraints if "source_id" in fk.column_keys)
    assert foreign.column_keys == ["import_id", "source_id"]
    assert foreign.deferrable and foreign.initially == "DEFERRED"
    # Every cyclic table and check compiles through SQLAlchemy's PostgreSQL dialect.
    for item in model.tables.values():
        assert str(sa.schema.CreateTable(item).compile(dialect=postgresql.dialect()))


def test_strict_mapping_and_avro_round_trip_preserve_decimal_date_and_null() -> None:
    contract = load_contract()
    table = contract.table("evidence_claims")
    mapping = elasticsearch(contract, table)
    assert mapping["dynamic"] == "strict"
    assert mapping["properties"]["value_num"]["type"] == "keyword"
    assert mapping["properties"]["fact_date"]["type"] == "keyword"
    schema = fastavro.parse_schema(avro(contract, table))
    values = {field.name: None for field in table.fields}
    values.update({field.name: "source" for field in table.fields if field.required})
    values.update(
        is_canonical=False,
        value_num=Decimal("0.704"),
        access_date=date(2026, 11, 22),
        fact_date="2026-11",
        qualifier="exact",
        verification_status="quote_verified",
        information_character="manufacturer_operator_statement",
    )
    buffer = io.BytesIO()
    fastavro.schemaless_writer(buffer, schema, values)
    buffer.seek(0)
    assert fastavro.schemaless_reader(buffer, schema) == values
    wire = {
        name: str(value) if isinstance(value, (Decimal, date)) else value
        for name, value in values.items()
    }
    validate(wire, json_schema(table))
    with pytest.raises(ValidationError):
        validate({**wire, "unknown": "must fail"}, json_schema(table))
    for other in contract.tables:
        fastavro.parse_schema(avro(contract, other))


def _contracts() -> tuple:
    old = load_contract()
    table = old.table("countries")
    new_table = replace(
        table,
        fields=(
            *table.fields,
            Field("new_note", "space.countries.new_note", "string", False, False),
        ),
    )
    new = replace(
        old,
        version="1.1.0",
        tables=tuple(new_table if t.name == table.name else t for t in old.tables),
    )
    return old, new


def test_additive_release_evolution_preserves_records() -> None:
    old, new = _contracts()
    # SQLite is enough to prove additive operations preserve existing rows; PostgreSQL has its own gate.
    old = replace(old, schema="")
    new = replace(new, schema="")
    engine = sa.create_engine("sqlite://")
    model = metadata(old)
    model.create_all(engine)
    with engine.begin() as connection:
        marker_table("").create(connection)
        record_installed(connection, [old], marker_schema="")
        connection.execute(
            model.tables["countries"].insert(),
            {
                "import_id": "snapshot",
                "country_iso2": "UA",
                "name_uk": "\u0423\u043a\u0440\u0430\u0457\u043d\u0430",
                "name_en": "Ukraine",
                "region": "\u0404\u0432\u0440\u043e\u043f\u0430",
            },
        )
        evolve(Operations(MigrationContext.configure(connection)), old, new, marker_schema="")
        table = metadata(new).tables["countries"]
        row = connection.execute(sa.select(table)).mappings().one()
        assert row["country_iso2"] == "UA" and row["new_note"] is None
    engine.dispose()


@pytest.mark.parametrize("change", ["same_version", "drop_table", "rename", "required", "type"])
def test_breaking_evolution_is_rejected_before_ddl(change: str) -> None:
    old, new = _contracts()
    if change == "same_version":
        new = replace(new, version=old.version)
    elif change == "drop_table":
        new = replace(new, tables=new.tables[1:])
    else:
        table = new.table("countries")
        fields = list(table.fields)
        if change == "rename":
            fields[1] = replace(fields[1], name="renamed")
        elif change == "required":
            fields[-1] = replace(fields[-1], required=True)
        elif change == "type":
            fields[1] = replace(fields[1], logical_type="integer")
        updated = replace(table, fields=tuple(fields))
        new = replace(new, tables=tuple(updated if t.name == table.name else t for t in new.tables))
    with pytest.raises(ValueError):
        additions(old, new)
