"""Runtime privilege and structural checks generated from policy and contract models."""

import secrets

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

from kn.contracts import Contract, load_contract
from kn.contracts.sqlalchemy import Geometry, metadata
from kn.db.catalog import PG_ATTRIBUTE
from kn.db.platform import ROLE_KINDS, SCHEMAS, role_name
from kn.db.statements import ResetRole, SetRole


def verify_structure(connection: Connection, contract: Contract | None = None) -> None:
    """Compare the deployed contract, or a supplied one, with the database through Alembic."""
    contract = contract or load_contract()
    managed = {table.name for table in contract.tables}

    def include_name(name: str | None, kind: str, parents: dict[str, str | None]) -> bool:
        if kind == "schema":
            return name == contract.schema
        if kind == "table":
            return name in managed and parents.get("schema_name") == contract.schema
        return (
            parents.get("schema_name") == contract.schema and parents.get("table_name") in managed
        )

    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_name": include_name,
            "version_table_schema": "system",
            "compare_type": True,
        },
    )
    model = metadata(contract)
    if compare_metadata(context, model) or _geometry_drift(connection, model):
        raise ValueError("database structure differs from the contract; rebuild or migrate")


def _geometry_drift(connection: Connection, model: sa.MetaData) -> bool:
    """Alembic reflects PostGIS columns as an unknown type, so compare their typmods here."""
    quote = connection.dialect.identifier_preparer.format_table
    for table in model.tables.values():
        for column in table.columns:
            if isinstance(column.type, Geometry):
                attribute = PG_ATTRIBUTE.c
                actual = connection.scalar(
                    sa.select(sa.func.format_type(attribute.atttypid, attribute.atttypmod)).where(
                        attribute.attrelid == sa.func.to_regclass(quote(table)),
                        attribute.attname == column.name,
                        sa.not_(attribute.attisdropped),
                    )
                )
                if actual != column.type.get_col_spec():
                    return True
    return False


def verify_privileges(connection: Connection) -> None:
    """Probe default grants inside a savepoint and always remove every probe."""
    savepoint = connection.begin_nested()
    try:
        for schema in SCHEMAS:
            _schema_privileges(connection, schema)
            _table_privileges(connection, schema)
    finally:
        savepoint.rollback()


def _expect(actual: object, expected: object, context: str) -> None:
    if actual != expected:
        raise ValueError(f"privilege mismatch: {context}")


def _schema_privileges(connection: Connection, schema: str) -> None:
    for kind in ROLE_KINDS:
        role = role_name(schema, kind)
        for other in SCHEMAS:
            for privilege in ("USAGE", "CREATE"):
                allowed = other == schema and (privilege == "USAGE" or kind == "owner")
                value = connection.scalar(
                    sa.select(sa.func.has_schema_privilege(role, other, privilege))
                )
                _expect(value, allowed, f"{role} {privilege} {other}")
        for privilege, allowed in (("CONNECT", True), ("TEMPORARY", False)):
            value = connection.scalar(
                sa.select(
                    sa.func.has_database_privilege(role, sa.func.current_database(), privilege)
                )
            )
            _expect(value, allowed, f"{role} {privilege} database")
        value = connection.scalar(sa.select(sa.func.has_schema_privilege(role, "public", "CREATE")))
        _expect(value, False, f"{role} CREATE public")


def _table_privileges(connection: Connection, schema: str) -> None:
    name = f"kn_role_probe_{secrets.token_hex(4)}"
    connection.execute(SetRole(role_name(schema, "owner")))
    table = sa.Table(
        name,
        sa.MetaData(schema=schema),
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
    )
    table.create(connection)
    connection.execute(ResetRole())
    for kind in ROLE_KINDS:
        role = role_name(schema, kind)
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            allowed = (
                kind == "owner"
                or privilege == "SELECT"
                or (kind == "loader" and privilege != "TRUNCATE")
            )
            value = connection.scalar(
                sa.select(sa.func.has_table_privilege(role, f"{schema}.{name}", privilege))
            )
            _expect(value, allowed, f"{role} {privilege} table")
        for privilege in ("USAGE", "SELECT"):
            value = connection.scalar(
                sa.select(
                    sa.func.has_sequence_privilege(role, f"{schema}.{name}_id_seq", privilege)
                )
            )
            _expect(value, kind != "reader", f"{role} {privilege} sequence")


def verify_compiled_catalog(connection: Connection, contract: Contract | None = None) -> None:
    """Check compiled keys, checks and comments that Alembic does not fully compare."""
    contract = contract or load_contract()
    model = metadata(contract)
    inspector = sa.inspect(connection)
    expected_tables = {table.name for table in contract.tables}
    if set(inspector.get_table_names(schema=contract.schema)) != expected_tables:
        raise ValueError("rebuilt tables differ from the compiled contract")
    for table in model.tables.values():
        _verify_compiled_table(inspector, table)


def _verify_compiled_table(inspector: Inspector, table: sa.Table) -> None:
    primary = inspector.get_pk_constraint(table.name, schema=table.schema)
    if (primary["name"], primary["constrained_columns"]) != (
        table.primary_key.name,
        [column.name for column in table.primary_key.columns],
    ):
        raise ValueError(f"compiled primary key mismatch: {table.fullname}")
    checks = inspector.get_check_constraints(table.name, schema=table.schema)
    expected = {
        str(item.name) for item in table.constraints if isinstance(item, sa.CheckConstraint)
    }
    if {item["name"] for item in checks} != expected:
        raise ValueError(f"compiled check constraint mismatch: {table.fullname}")
    references = inspector.get_foreign_keys(table.name, schema=table.schema)
    if {item["name"] for item in references} != {
        str(item.name) for item in table.foreign_key_constraints
    }:
        raise ValueError(f"compiled foreign key mismatch: {table.fullname}")
    comment = inspector.get_table_comment(table.name, schema=table.schema)["text"]
    columns = inspector.get_columns(table.name, schema=table.schema)
    if comment != table.comment or any(
        column.get("comment") != table.c[column["name"]].comment for column in columns
    ):
        raise ValueError(f"compiled comment mismatch: {table.fullname}")
