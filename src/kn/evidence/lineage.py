"""Read-only, rights-filtered evidence behind an object's lineage.

Rights belong to evidence records. A claim or confirmation whose evidence the audience may not see
is withheld, and so is every fact, outcome, review item and decision that would reveal it. Each
withheld row is counted, never shown. A row whose evidence is missing is shown only to an audience
that permits every rights statement, and it is reported as a gap in the chain.
"""

import json
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.ranking import Audience
from kn.evidence.store import evidence_tables
from kn.review.model import utc

JSON_SUFFIX = "_json"
type Row = Mapping[str, Any]
type View = dict[str, object]
# Evidence tables and the key that orders their rows.
TABLE_KEYS = {
    "claims": "claim_key",
    "claim_confirmations": "confirmation_id",
    "evidence_records": "evidence_id",
    "canonical_facts": "fact_version_id",
    "selection_outcomes": "outcome_id",
    "review_items": "item_id",
    "review_decisions": "decision_id",
}


class EvidenceRows(Protocol):
    def rows(self, table: str, column: str, values: Collection[str], **equal: object) -> list[Row]:
        """Rows whose `column` is one of `values` and that equal every `equal` column."""
        ...


class SqlEvidenceRows:
    """Evidence rows read from PostgreSQL; the caller owns a read-only transaction."""

    def __init__(self, connection: Connection, tables: Mapping[str, sa.Table] | None = None):
        self.connection = connection
        self.tables = tables or evidence_tables()

    def rows(self, table: str, column: str, values: Collection[str], **equal: object) -> list[Row]:
        if not values:
            return []
        source = self.tables[table]
        clauses: list[sa.ColumnElement[bool]] = [source.c[column].in_(sorted(values))]
        clauses.extend(
            source.c[name].is_(None) if value is None else source.c[name] == value
            for name, value in equal.items()
        )
        query = sa.select(source).where(*clauses).order_by(source.c[TABLE_KEYS[table]])
        return [dict(row) for row in self.connection.execute(query).mappings()]


def jsonable(row: Row) -> dict[str, Any]:
    """Exact decimals as plain strings, UTC instants, and JSON columns parsed under their names."""
    result: dict[str, Any] = {}
    for name, value in row.items():
        if isinstance(value, Decimal):
            value = format(value.normalize(), "f")
        elif isinstance(value, datetime):
            value = instant(value)
        elif name.endswith(JSON_SUFFIX) and isinstance(value, str):
            name, value = name.removesuffix(JSON_SUFFIX), json.loads(value)
        result[name] = value
    return result


def instant(value: datetime) -> str:
    """The UTC form identity events use, such as `2026-01-01T00:00:00Z`."""
    return utc(value).isoformat().replace("+00:00", "Z")


def gap(kind: str, reference: str) -> dict[str, str]:
    return {"kind": kind, "reference": reference}


@dataclass
class EvidenceView:
    """Visible evidence rows in a stable order, withheld counts and broken references."""

    sections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    withheld: Counter[str] = field(default_factory=Counter)
    gaps: list[dict[str, str]] = field(default_factory=list)

    def keep(self, section: str, rows: Iterable[Row], visible: Callable[[Row], bool]) -> list[Row]:
        kept = []
        for row in rows:
            if visible(row):
                kept.append(row)
            else:
                self.withheld[section] += 1
        self.sections[section] = [jsonable(row) for row in kept]
        return kept


def evidence_view(
    rows: EvidenceRows,
    kn_ids: Collection[str],
    terminals: Sequence[str],
    *,
    field_id: str | None,
    audience: Audience,
    belongs: Callable[[Row], bool],
) -> EvidenceView:
    """Claims about the objects, their evidence, the current facts and their explanations."""
    view = EvidenceView()
    fields = {} if field_id is None else {"field_id": field_id}
    claims = [row for row in rows.rows("claims", "kn_id", kn_ids, **fields) if belongs(row)]
    claims.sort(key=lambda row: (row["field_id"], row["recorded_at"], row["claim_key"]))
    keys = {row["claim_key"] for row in claims}
    confirmations = rows.rows("claim_confirmations", "claim_key", keys)
    wanted = {row["evidence_id"] for row in (*claims, *confirmations)}
    records = {
        row["evidence_id"]: row for row in rows.rows("evidence_records", "evidence_id", wanted)
    }

    def permitted(row: Row) -> bool:
        found = records.get(row["evidence_id"])
        return audience.rights is None if found is None else audience.permits(found["rights"])

    shown = view.keep("claims", claims, permitted)
    visible = {row["claim_key"] for row in shown}
    kept = view.keep(
        "confirmations",
        confirmations,
        lambda row: row["claim_key"] in visible and permitted(row),
    )
    _evidence(view, records, [*shown, *kept], audience)

    def allowed(key: str | None) -> bool:
        """A claim the view does not hold has unknown rights; only an open audience sees it."""
        return key is None or key in visible or (key not in keys and audience.rights is None)

    facts = rows.rows(
        "canonical_facts", "kn_id", kn_ids, audience=audience.name, knowledge_to=None, **fields
    )
    _facts(view, rows, facts, allowed, keys, terminals)
    return view


def _evidence(
    view: EvidenceView, records: Mapping[str, Row], cited: Sequence[Row], audience: Audience
) -> None:
    shown: list[dict[str, Any]] = []
    for key in sorted({row["evidence_id"] for row in cited}):
        found = records.get(key)
        if found is None:
            view.gaps.append(gap("evidence_missing", key))
            continue
        item = jsonable(found)
        if item["excerpt_rights"] is not None and not audience.permits(item["excerpt_rights"]):
            item.update(excerpt=None, excerpt_rights=None)
            view.withheld["excerpts"] += 1
        shown.append(item)
    view.sections["evidence"] = shown


def _facts(
    view: EvidenceView,
    rows: EvidenceRows,
    facts: Sequence[Row],
    allowed: Callable[[str | None], bool],
    known: Collection[str],
    terminals: Sequence[str],
) -> None:
    shown = view.keep("facts", facts, lambda row: allowed(row["claim_key"]))
    for row in shown:
        if row["claim_key"] is not None and row["claim_key"] not in known:
            view.gaps.append(gap("fact_claim_missing", row["fact_version_id"]))
        if row["kn_id"] not in terminals:
            view.gaps.append(gap("fact_subject_superseded", row["fact_version_id"]))
    versions = {row["fact_version_id"] for row in shown}
    outcomes = rows.rows("selection_outcomes", "fact_version_id", versions)
    view.keep("outcomes", outcomes, lambda row: allowed(row["claim_key"]))
    named = {row["review_item_id"] for row in shown} - {None}
    items = view.keep(
        "review_items",
        rows.rows("review_items", "item_id", named),
        lambda row: all(allowed(key) for key in json.loads(row["candidates_json"])),
    )
    decisions = rows.rows("review_decisions", "item_id", {row["item_id"] for row in items})
    view.keep("review_decisions", decisions, lambda row: allowed(row["selected_claim_key"]))
