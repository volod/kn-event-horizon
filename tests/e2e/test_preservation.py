"""Existing ingestion and archive paths preserve source-only multilingual evidence."""

import csv
import json
from pathlib import Path

import sqlalchemy as sa

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata
from kn.domains.space.satcom.archive import archive
from kn.domains.space.satcom.importer import import_package
from kn.domains.space.satcom.package import CSV_DIRECTORY, read_package
from tests.e2e.support import FIXTURES, write_json


def test_untranslated_messages_survive_archive_import_and_replay(
    source_package: Path, tmp_path: Path, e2e_artifacts: Path
) -> None:
    fixtures = json.loads((FIXTURES / "source-text.json").read_text("ascii"))
    originals = [record["original"] for record in fixtures if not record["translations"]]
    payload = json.dumps(originals, ensure_ascii=True).encode("ascii")
    (source_package / "original-messages.json").write_bytes(payload)
    source_file = source_package / CSV_DIRECTORY / "sources.csv"
    with source_file.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers, rows = reader.fieldnames, list(reader)
    assert headers is not None
    for row, original in zip(rows, originals, strict=False):
        row.update(
            language=original["language"], title=original["text"], notes=original["provenance"]
        )
    with source_file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    contract = load_contract()
    package = read_package(source_package, contract)
    destination = archive(package, tmp_path / "archive")
    restored = read_package(destination / "package", contract)
    assert (destination / "package" / "original-messages.json").read_bytes() == payload
    assert restored.files == package.files
    assert restored.manifest() == package.manifest()
    engine = sa.create_engine("sqlite://")
    model = metadata(contract, "")
    try:
        with engine.begin() as connection:
            model.create_all(connection)
            assert import_package(connection, package, contract, "")
            assert not import_package(connection, restored, contract, "")
            stored = connection.execute(sa.select(model.tables["sources"])).mappings().all()
            actual = {row["source_id"]: row for row in stored}
            for row in package.rows["sources"]:
                assert actual[row["source_id"]]["language"] == row["language"]
                assert actual[row["source_id"]]["title"] == row["title"]
                assert actual[row["source_id"]]["notes"] == row["notes"]
            for row, original in zip(rows, originals, strict=False):
                assert actual[row["source_id"]]["title"] == original["text"]
                assert actual[row["source_id"]]["language"] == original["language"]
                assert actual[row["source_id"]]["notes"] == original["provenance"]
            raw = model.tables["satcom_rows"]
            cells = connection.scalars(
                sa.select(raw.c.cells_json)
                .where(raw.c.table_name == "sources")
                .order_by(raw.c.row_number)
            ).all()
            assert [json.loads(cell) for cell in cells] == package.raw_rows["sources"]
    finally:
        engine.dispose()
    write_json(
        e2e_artifacts / "source-preservation.json",
        {
            "manifest": package.manifest(),
            "originals": originals,
            "replay_status": "already_imported",
        },
    )
