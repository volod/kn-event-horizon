"""Validate complete source packages before archiving or touching a database."""

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from kn.contracts.loader import canonical
from kn.contracts.model import Contract, Field, Table
from kn.domains.space.satcom.validation import Row, row

CSV_DIRECTORY = "reference_tables_enriched"


@dataclass(frozen=True)
class Package:
    import_id: str
    files: dict[str, bytes]
    rows: dict[str, list[Row]]
    raw_rows: dict[str, list[dict[str, str]]]

    def manifest(self) -> dict[str, object]:
        return {
            "import_id": self.import_id,
            "tables": {name: len(rows) for name, rows in self.rows.items()},
            "files": file_manifest(self.files),
        }


def file_manifest(files: dict[str, bytes]) -> list[dict[str, str | int]]:
    return [
        {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
        for name, data in sorted(files.items())
    ]


def read_package(path: Path, contract: Contract) -> Package:
    """Use contracted CSVs as the relational input; preserve every other package file as bytes."""
    files = _read_files(path)
    import_id = hashlib.sha256(canonical(file_manifest(files)).encode()).hexdigest()
    raw_rows: dict[str, list[dict[str, str]]] = {}
    rows: dict[str, list[Row]] = {}
    expected = {f"{CSV_DIRECTORY}/{table.name}.csv" for table in contract.tables if table.csv}
    actual = {name for name in files if name.startswith(f"{CSV_DIRECTORY}/")}
    if actual != expected:
        raise ValueError(
            f"CSV files differ from contract: missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )
    for table in contract.tables:
        if not table.csv:
            continue
        raw_rows[table.name], rows[table.name] = _read_table(table, files, import_id)
    package = Package(import_id, files, rows, raw_rows)
    _references(package, contract)
    return package


def _read_files(path: Path) -> dict[str, bytes]:
    if not path.is_dir() or path.is_symlink():
        raise ValueError("package must be an existing directory, not a symlink")
    files = {}
    for file in sorted(path.rglob("*")):
        if file.is_symlink():
            raise ValueError("package symlinks are refused")
        if file.is_file():
            files[file.relative_to(path).as_posix()] = file.read_bytes()
    return files


def _read_table(
    table: Table, files: dict[str, bytes], import_id: str
) -> tuple[list[dict[str, str]], list[Row]]:
    data = files[f"{CSV_DIRECTORY}/{table.name}.csv"].decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(data, newline=""), strict=True)
    headers = [field.name for field in table.fields if field.name != "import_id"]
    if reader.fieldnames != headers:
        raise ValueError(f"{table.name}: CSV headers differ from contract")
    raw_rows = []
    rows = []
    for line, raw in enumerate(reader, start=2):
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError(f"{table.name}:{line}: CSV row width differs from header")
        raw_rows.append(raw)
        rows.append(row(table, raw, import_id, line))
    return raw_rows, rows


def _references(package: Package, contract: Contract) -> None:
    keys = {table.name: _table_keys(package, table) for table in contract.tables if table.csv}
    for table in contract.tables:
        if table.csv:
            for field in table.fields:
                _reference(package, table, field, keys)


def _table_keys(package: Package, table: Table) -> set[tuple[object, ...]]:
    values = [tuple(item[name] for name in table.primary_key) for item in package.rows[table.name]]
    if len(set(values)) != len(values):
        raise ValueError(f"{table.name}: duplicate primary key")
    return set(values)


def _reference(
    package: Package, table: Table, field: Field, keys: dict[str, set[tuple[object, ...]]]
) -> None:
    ref = field.reference
    if ref is None or ref.table not in keys:
        return
    for line, item in enumerate(package.rows[table.name], start=2):
        values = tuple(item[name] for name in ref.fields)
        if all(value is not None for value in values) and values not in keys[ref.table]:
            raise ValueError(
                f"{table.name}:{line}:{field.name}: unresolved {ref.table}.{ref.target_fields}"
            )
