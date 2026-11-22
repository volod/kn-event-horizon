"""A small reference-closed mixture selected from the real owner-provided package."""

import csv
import json
from pathlib import Path

import pytest

from kn.domains.space.satcom.package import CSV_DIRECTORY

FIXTURE = Path(__file__).with_name("real_sample.json")


@pytest.fixture
def source_package(tmp_path: Path) -> Path:
    source = tmp_path / "input"
    directory = source / CSV_DIRECTORY
    directory.mkdir(parents=True)
    fixture = json.loads(FIXTURE.read_text())
    for name, table in fixture["tables"].items():
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=table["headers"])
            writer.writeheader()
            writer.writerows(table["rows"])
    (source / "source-note.txt").write_text(
        "Real SATCOM mixture; assertions are not independently verified.\n"
    )
    return source
