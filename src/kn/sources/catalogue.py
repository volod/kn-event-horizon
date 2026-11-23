"""Persist reviewed candidates and expose the read-only catalogue listing."""

import json
from functools import cache

from sqlalchemy import Table, select
from sqlalchemy.engine import Connection

from kn.contracts import load_contract
from kn.contracts.schemas import RESOURCES
from kn.contracts.sqlalchemy import metadata
from kn.db.seed_rows import load_seed_rows
from kn.sources.seeds import reviewed_catalogue

CATALOGUE = RESOURCES / "system" / "source-catalogue" / "1.0.0.json"
TABLE_NAME = "system.source_catalogue"
LIST_FIELDS = (
    "source_id",
    "domain",
    "original_id",
    "label",
    "priority",
    "cadence",
    "access_notes_json",
    "access_verification",
    "lifecycle_state",
)


@cache
def catalogue_table() -> Table:
    return metadata(load_contract(CATALOGUE)).tables[TABLE_NAME]


def load_reviewed_catalogue(connection: Connection) -> None:
    """Load candidates as part of the caller's all-schema rebuild transaction."""
    if not connection.in_transaction():
        raise ValueError("source catalogue loading requires a caller-owned transaction")
    rows = reviewed_catalogue()
    with connection.begin_nested():
        load_seed_rows(connection, catalogue_table(), rows)


def list_sources(connection: Connection) -> list[dict[str, object]]:
    """Read only catalogue fields and preserve the original proposal language."""
    table = catalogue_table()
    columns = [table.c[name] for name in LIST_FIELDS]
    query = select(*columns).order_by(table.c.domain, table.c.proposal_row, table.c.source_id)
    sources: list[dict[str, object]] = []
    for stored in connection.execute(query).mappings():
        source = dict(stored)
        source["access_notes"] = json.loads(source.pop("access_notes_json"))
        sources.append(source)
    return sources
