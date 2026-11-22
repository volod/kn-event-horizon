"""Render DDL from the same SQLAlchemy metadata that Alembic consumes."""

import re

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect

from kn.contracts.model import Contract
from kn.contracts.sqlalchemy import metadata


def postgresql_ddl(contract: Contract) -> str:
    """Separate foreign keys from table creation to support cycles in stable order."""
    tables = sorted(metadata(contract).tables.values(), key=lambda table: table.name)
    postgres = dialect()
    statements: list[str] = []

    def emit(statement: sa.schema.DDLElement) -> None:
        statements.append(_ascii_sql(str(statement.compile(dialect=postgres)).strip()) + ";")

    for table in tables:
        emit(sa.schema.CreateTable(table, include_foreign_key_constraints=[]))
    for table in tables:
        for constraint in sorted(table.foreign_key_constraints, key=lambda item: str(item.name)):
            emit(sa.schema.AddConstraint(constraint))
        for index in sorted(table.indexes, key=lambda item: str(item.name)):
            emit(sa.schema.CreateIndex(index))
        if table.comment:
            emit(sa.schema.SetTableComment(table))
        for column in table.columns:
            if column.comment:
                emit(sa.schema.SetColumnComment(column))
    return "\n\n".join(statements) + "\n"


def _ascii_sql(statement: str) -> str:
    """PostgreSQL Unicode escape literals preserve text in an ASCII SQL artifact."""

    def literal(match: re.Match[str]) -> str:
        value = match.group()
        if value.isascii():
            return value
        escaped = "".join(
            char
            if ord(char) < 128
            else (f"\\{ord(char):04x}" if ord(char) <= 0xFFFF else f"\\+{ord(char):06x}")
            for char in value.replace("\\", "\\\\")
        )
        return "U&" + escaped

    return re.sub(r"'(?:''|[^'])*'", literal, statement)
