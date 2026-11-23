"""Shared semantic fixture and native database values for combined round trips."""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from kn.contracts.model import Contract
from kn.semantic import Snapshot


def text_fixture() -> Snapshot:
    snapshot = json.loads((Path(__file__).parents[1] / "semantic/fixtures/model.json").read_text())
    next(row for row in snapshot["terms"] if row["id"] == "space.demo.001")["definition"] = None
    reviewed_label = next(
        row
        for row in snapshot["labels"]
        if row["term_id"] == "space.demo.001" and row["locale"] == "uk"
    )
    reviewed_label["review_reference"] = "fixture:reviewed-translation"
    return snapshot


def native_rows(contract: Contract, snapshot: Snapshot) -> Snapshot:
    return {
        name: [
            {
                field.name: _native_value(field.logical_type, row.get(field.name))
                for field in contract.table(name).fields
            }
            for row in rows
        ]
        for name, rows in snapshot.items()
    }


def _native_value(logical_type: str, value: Any) -> Any:
    decoder = {
        "number": Decimal,
        "timestamp": datetime.fromisoformat,
        "date": date.fromisoformat,
    }.get(logical_type)
    return decoder(value) if value is not None and decoder else value
