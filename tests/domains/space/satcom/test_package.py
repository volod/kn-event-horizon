"""Real source mixtures plus malformed rows and lossless snapshot behavior."""

import csv
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa

from kn.contracts import Field, load_contract
from kn.contracts.sqlalchemy import metadata
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import CSV_DIRECTORY, read_package
from kn.domains.space.satcom.validation import cell


def mutate(source: Path, table: str, field: str, value: str, duplicate: bool = False) -> None:
    path = source / CSV_DIRECTORY / f"{table}.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        rows = list(reader)
    rows[0][field] = value
    if duplicate:
        rows.append(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_real_mixture_preserves_raw_cells_and_typed_values(source_package: Path) -> None:
    contract = load_contract()
    package = read_package(source_package, contract)
    assert len(package.rows) == 28
    assert package.import_id == read_package(source_package, contract).import_id
    raw = package.raw_rows["evidence_claims"][0]
    typed = package.rows["evidence_claims"][0]
    assert typed["raw_value"] == raw["raw_value"]
    assert typed["value_num"] == Decimal(raw["value_num"])
    assert typed["value_text"] is None
    assert typed["access_date"] == date(2026, 11, 22)
    assert typed["is_canonical"] is True
    assert {row["is_canonical"] for row in package.rows["evidence_claims"]} == {True, False}
    assert any(row["null_reason"] for row in package.rows["parameter_gaps"])


@pytest.mark.parametrize(
    ("table", "field", "value", "reason"),
    [
        ("sources", "url", "", "required"),
        ("evidence_claims", "value_num", "NaN", "decimal"),
        ("evidence_claims", "source_id", "SRC-MISSING", "unresolved"),
        ("evidence_claims", "is_canonical", "yes", "true or false"),
        ("evidence_claims", "qualifier", "made_up", "enum"),
        ("evidence_claims", "fact_date", "2026-02-30", "day"),
        ("deployment_observations", "count", "1.2", "integer"),
    ],
)
def test_bad_real_mixtures_fail_before_import(
    source_package: Path, table: str, field: str, value: str, reason: str
) -> None:
    mutate(source_package, table, field, value)
    with pytest.raises(ValueError, match=reason):
        read_package(source_package, load_contract())


def test_duplicate_composite_key_is_rejected(source_package: Path) -> None:
    raw = read_package(source_package, load_contract()).raw_rows["program_organizations"][0]
    mutate(source_package, "program_organizations", "role", raw["role"], duplicate=True)
    with pytest.raises(ValueError, match="duplicate primary key"):
        read_package(source_package, load_contract())


def test_missing_extra_columns_and_files_are_rejected(source_package: Path) -> None:
    path = source_package / CSV_DIRECTORY / "countries.csv"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"country_iso2", b"unknown", 1))
    with pytest.raises(ValueError, match="headers"):
        read_package(source_package, load_contract())
    path.unlink()
    with pytest.raises(ValueError, match="missing"):
        read_package(source_package, load_contract())


def test_archive_retains_every_file_and_refuses_tampering(
    source_package: Path, tmp_path: Path
) -> None:
    package = read_package(source_package, load_contract())
    target = archive(package, tmp_path / "data")
    assert archive(package, tmp_path / "data") == target
    for name, value in package.files.items():
        assert (target / "package" / name).read_bytes() == value
    (target / "package" / "source-note.txt").write_text("tampered")
    with pytest.raises(ValueError, match="bytes differ"):
        archive(package, tmp_path / "data")
    assert not list(target.parent.glob(".staging-*"))


def test_two_snapshots_coexist_and_repeated_import_is_idempotent(source_package: Path) -> None:
    contract = load_contract()
    first = read_package(source_package, contract)
    engine = sa.create_engine("sqlite://")
    model = metadata(contract, "")
    model.create_all(engine)
    with engine.begin() as connection:
        assert import_package(connection, first, contract, "")
        assert not import_package(connection, first, contract, "")
        mutate(source_package, "sources", "notes", "second snapshot")
        second = read_package(source_package, contract)
        assert first.import_id != second.import_id
        assert import_package(connection, second, contract, "")
        raw_rows = connection.execute(sa.select(model.tables["satcom_rows"])).mappings().all()
        assert len(raw_rows) == sum(map(len, first.rows.values())) * 2
        for raw in raw_rows:
            source = first if raw["import_id"] == first.import_id else second
            assert (
                json.loads(raw["cells_json"])
                == source.raw_rows[raw["table_name"]][raw["row_number"] - 2]
            )
        with pytest.raises(ValueError, match="different contract"):
            import_package(connection, first, replace(contract, digest="changed"), "")
    engine.dispose()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("", None), ("0", Decimal("0")), ("0.000000000000000001", Decimal("1e-18"))],
)
def test_decimal_blank_zero_and_precision_are_distinct(
    value: str, expected: Decimal | None
) -> None:
    field = Field("value", "test.value", "number", False, False)
    assert cell(field, value) == expected


@pytest.mark.parametrize(
    "value", ["1e9", "Infinity", "0.0000000000000000001", "100000000000000000000"]
)
def test_unrepresentable_decimals_are_refused(value: str) -> None:
    with pytest.raises(ValueError):
        cell(Field("value", "test.value", "number", False, False), value)


@pytest.mark.parametrize("value", ["2026", "2026-11", "2026-11-22"])
def test_partial_dates_keep_their_precision(value: str) -> None:
    assert (
        cell(Field("when", "test.when", "string", False, False, partial_date=True), value) == value
    )
