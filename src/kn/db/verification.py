"""Runtime privilege and structural checks generated from policy and contract models."""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

from kn.contracts import Contract
from kn.contracts.registry import registered_contracts
from kn.contracts.sqlalchemy import Geometry, deployment_metadata
from kn.db.catalog import PG_ATTRIBUTE, PG_CLASS, PG_NAMESPACE, TABLE_KINDS
from kn.db.platform import MIGRATION_SCHEMA, ROLE_KINDS, SCHEMAS, VERSION_TABLE, role_name
from kn.db.statements import ResetRole, SetRole
from kn.identity.checkpoint import CHECKPOINT


def verify_structure(connection: Connection, contracts: Sequence[Contract] | None = None) -> None:
    """Compare the registered contracts, or supplied ones, with the database through Alembic."""
    contracts = contracts or registered_contracts()
    managed = {(contract.schema, table.name) for contract in contracts for table in contract.tables}
    schemas = {schema for schema, _ in managed}

    def include_name(name: str | None, kind: str, parents: dict[str, str | None]) -> bool:
        if kind == "schema":
            return name in schemas
        if kind == "table":
            return (parents.get("schema_name"), name) in managed
        return (parents.get("schema_name"), parents.get("table_name")) in managed

    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_name": include_name,
            "version_table_schema": MIGRATION_SCHEMA,
            "compare_type": True,
        },
    )
    model = deployment_metadata(contracts)
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


def verify_registered_tables(connection: Connection, contracts: Sequence[Contract]) -> None:
    """Every table in a KN schema belongs to a registered contract; partitions count with their
    parent. The migration marker and identity projection checkpoint are internal tables."""
    for schema in SCHEMAS:
        actual: set[str] = set(
            connection.scalars(
                sa.select(PG_CLASS.c.relname)
                .join(PG_NAMESPACE, PG_NAMESPACE.c.oid == PG_CLASS.c.relnamespace)
                .where(
                    PG_NAMESPACE.c.nspname == schema,
                    PG_CLASS.c.relkind.in_(TABLE_KINDS),
                    sa.not_(PG_CLASS.c.relispartition),
                )
            )
        )
        expected = {
            table.name
            for contract in contracts
            if contract.schema == schema
            for table in contract.tables
        }
        if schema == MIGRATION_SCHEMA:
            expected.add(VERSION_TABLE)
        if schema == CHECKPOINT.schema and any(
            contract.contract_id == "kn.core.identity" for contract in contracts
        ):
            expected.add(CHECKPOINT.name)
        if actual != expected:
            raise ValueError(f"tables in schema {schema} differ from the registered contracts")


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


def verify_compiled_catalog(
    connection: Connection, contracts: Sequence[Contract] | None = None
) -> None:
    """Check compiled keys, checks and comments that Alembic does not fully compare."""
    contracts = contracts or registered_contracts()
    inspector = sa.inspect(connection)
    for table in deployment_metadata(contracts).tables.values():
        if not inspector.has_table(table.name, schema=table.schema):
            raise ValueError(f"compiled table missing: {table.fullname}")
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
    _verify_index_predicates(inspector, table)
    comment = inspector.get_table_comment(table.name, schema=table.schema)["text"]
    columns = inspector.get_columns(table.name, schema=table.schema)
    if comment != table.comment or any(
        column.get("comment") != table.c[column["name"]].comment for column in columns
    ):
        raise ValueError(f"compiled comment mismatch: {table.fullname}")


def _verify_index_predicates(inspector: Inspector, table: sa.Table) -> None:
    actual = {
        item["name"]: item.get("dialect_options", {}).get("postgresql_where")
        for item in inspector.get_indexes(table.name, schema=table.schema)
    }
    for index in table.indexes:
        predicate = index.dialect_options["postgresql"].get("where")
        expected = (
            ""
            if predicate is None
            else str(
                predicate.compile(
                    dialect=inspector.bind.dialect,
                    compile_kwargs={"literal_binds": True, "include_table": False},
                )
            )
        )
        if str(actual.get(str(index.name)) or "").strip("() ") != expected:
            raise ValueError(f"compiled index predicate mismatch: {table.fullname}")
