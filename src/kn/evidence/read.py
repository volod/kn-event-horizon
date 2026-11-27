"""Reconstruct immutable claim models from registered storage rows."""

import json
from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.model import Claim, Evidence
from kn.evidence.records import Time

VALUE_FIELDS = (
    ("text", "value_text", "text"),
    ("number", "value_number", "number"),
    ("boolean", "value_boolean", "boolean"),
    ("date", "value_date", "date"),
    ("concept", "value_concept", "concept"),
    ("object", "value_kn_id", "kn_id"),
    ("missing", "missing_reason", "reason"),
)


def claim(row: Mapping[str, Any], evidence: Evidence) -> Claim:
    kind, column, member = next(item for item in VALUE_FIELDS if row[item[1]] is not None)
    value = {"kind": kind, member: row[column]}
    if kind == "text":
        value["language"] = row["value_language"]
    if kind == "number":
        value.update(normalized_unit=row["normalized_unit"], conversion_rule=row["conversion_rule"])
    data = {name: row[name] for name in Claim.model_fields if name in row}
    data.update(
        conditions=json.loads(row["conditions_json"]),
        evidence=evidence,
        value=value,
    )
    for name in ("event", "published", "valid_from", "valid_to"):
        column = name if name.startswith("valid") else name + "_at"
        data[name] = (
            Time(at=row[column], precision=row[name + "_precision"])
            if row[column] is not None
            else None
        )
    return Claim.model_validate(data)


def claims(connection: Connection, tables: Mapping[str, sa.Table]) -> list[Claim]:
    records = {
        row["evidence_id"]: Evidence.model_validate(
            {name: row[name] for name in Evidence.model_fields}
        )
        for row in connection.execute(sa.select(tables["evidence_records"])).mappings()
    }
    return [
        claim(dict(row), records[row["evidence_id"]])
        for row in connection.execute(sa.select(tables["claims"])).mappings()
    ]
