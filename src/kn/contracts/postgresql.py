"""Reviewable PostgreSQL metadata manifest, generated without executable SQL files."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect

from kn.contracts.model import Contract
from kn.contracts.sqlalchemy import metadata


def manifest(contract: Contract) -> dict[str, Any]:
    model = metadata(contract)
    postgres = dialect()
    tables = {}
    for table in sorted(model.tables.values(), key=lambda item: item.name):
        tables[table.name] = {
            "columns": [
                {
                    "name": column.name,
                    "type": str(column.type.compile(dialect=postgres)),
                    "nullable": column.nullable,
                    "comment": column.comment,
                }
                for column in table.columns
            ],
            "primary_key": [column.name for column in table.primary_key],
            "foreign_keys": [
                {
                    "columns": list(key.column_keys),
                    "targets": [element.target_fullname for element in key.elements],
                    "deferrable": key.deferrable,
                    "initially": key.initially,
                }
                for key in sorted(table.foreign_key_constraints, key=lambda key: str(key.name))
            ],
            "checks": [
                {
                    "name": str(check.name),
                    "expression": str(
                        check.sqltext.compile(
                            dialect=postgres, compile_kwargs={"literal_binds": True}
                        )
                    ),
                }
                for check in sorted(table.constraints, key=lambda key: str(key.name))
                if isinstance(check, sa.CheckConstraint)
            ],
        }
    return {
        "schema": contract.schema,
        "contract_version": contract.version,
        "contract_digest": contract.digest,
        "tables": tables,
    }
