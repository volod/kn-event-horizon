"""Transactional, snapshot-scoped projections with original CSV cells alongside typed values."""

from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.loader import canonical
from kn.contracts.model import Contract
from kn.contracts.sqlalchemy import metadata
from kn.domains.space.satcom.package import Package, file_manifest

BATCH_SIZE = 500
IMPORT_LOCK_NAMESPACE = 0x4B4E494D


def import_package(
    connection: Connection, package: Package, contract: Contract, schema: str | None = None
) -> bool:
    """Return false for an existing identical snapshot. The caller commits or rolls back."""
    model = metadata(contract, schema)
    prefix = f"{model.schema}." if model.schema else ""
    imports = model.tables[f"{prefix}satcom_imports"]
    if connection.dialect.name == "postgresql":
        token = int(package.import_id[:8], 16) & 0x7FFFFFFF
        connection.execute(sa.select(sa.func.pg_advisory_xact_lock(IMPORT_LOCK_NAMESPACE, token)))
    existing = (
        connection.execute(sa.select(imports).where(imports.c.import_id == package.import_id))
        .mappings()
        .one_or_none()
    )
    if existing:
        if existing["contract_digest"] != contract.digest:
            raise ValueError(
                "snapshot already exists under a different contract; use a reviewed replay"
            )
        return False
    connection.execute(
        imports.insert(),
        {
            "import_id": package.import_id,
            "contract_version": contract.version,
            "contract_digest": contract.digest,
            "adapter_version": contract.source_profile,
        },
    )
    _insert(
        connection,
        model.tables[f"{prefix}satcom_files"],
        ({"import_id": package.import_id, **file} for file in file_manifest(package.files)),
    )
    for name, rows in package.rows.items():
        _insert(connection, model.tables[f"{prefix}{name}"], rows)
        _insert(
            connection,
            model.tables[f"{prefix}satcom_rows"],
            (
                {
                    "import_id": package.import_id,
                    "table_name": name,
                    "row_number": line,
                    "cells_json": canonical(raw),
                }
                for line, raw in enumerate(package.raw_rows[name], start=2)
            ),
        )
    return True


def _insert(connection: Connection, table: sa.Table, rows: Iterable[dict[str, Any]]) -> None:
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            connection.execute(table.insert(), batch)
            batch = []
    if batch:
        connection.execute(table.insert(), batch)
