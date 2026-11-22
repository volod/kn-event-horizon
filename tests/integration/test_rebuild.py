"""All-schema rebuild acceptance, with every destructive probe rolled back."""

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

from kn.contracts import load_contract
from kn.db import seeds
from kn.db.governance import verify
from kn.db.platform import SCHEMAS
from kn.db.rebuild import rebuild
from kn.db.statements import SetRole
from tests.integration.harness import IntegrationDatabase, ScratchSchemas


@pytest.fixture
def rebuild_connection(
    integration_database: IntegrationDatabase, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Connection]:
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            yield connection
            transaction.rollback()
    finally:
        engine.dispose()


def catalog(connection: Connection) -> list[tuple[object, ...]]:
    return list(
        connection.execute(
            sa.text(
                "SELECT n.nspname, c.relname, c.relkind, pg_get_userbyid(c.relowner), "
                "a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull "
                "FROM pg_namespace n LEFT JOIN pg_class c ON c.relnamespace=n.oid "
                "LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 "
                "AND NOT a.attisdropped WHERE n.nspname = ANY(:schemas) "
                "ORDER BY n.nspname, c.relname, a.attnum"
            ),
            {"schemas": list(SCHEMAS)},
        ).all()
    )


def test_rebuild_from_empty_is_identical_and_loads_seeds_as_loader(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = rebuild_connection
    # Start from no KN schema, while retaining the extension and separate databases.
    connection.exec_driver_sql("DROP SCHEMA " + ", ".join(SCHEMAS) + " CASCADE")
    seen: list[str] = []

    def seed(conn: Connection) -> None:
        seen.append(str(conn.scalar(sa.text("SELECT current_user"))))
        conn.exec_driver_sql(
            "INSERT INTO space.satcom_contract "
            "SELECT 'reviewed-seed', version, digest, managed_tables_json "
            "FROM space.satcom_contract LIMIT 1"
        )

    monkeypatch.setattr(seeds, "REVIEWED_SEED_LOADERS", (("space", seed),))
    rebuild(connection)
    first = catalog(connection)
    verify(connection)
    assert set(sa.inspect(connection).get_table_names(schema="space")) == {
        table.name for table in load_contract().tables
    }
    assert set(SCHEMAS) <= set(sa.inspect(connection).get_schema_names())
    rebuild(connection)
    assert catalog(connection) == first
    assert seen == ["kn_space_loader", "kn_space_loader"]
    assert connection.scalar(sa.text("SELECT count(*) FROM space.satcom_contract")) == 2
    for statement in (
        "CREATE TABLE space.forbidden (id integer)",
        "ALTER TABLE space.countries ADD COLUMN forbidden integer",
        "DROP TABLE space.countries",
        "CREATE TABLE public.forbidden (id integer)",
    ):
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(SetRole("kn_space_loader"))
            connection.exec_driver_sql(statement)


def test_seed_failure_restores_all_schemas_even_if_caller_catches_it(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = rebuild_connection
    connection.exec_driver_sql("CREATE TABLE semantic.rebuild_sentinel (id integer)")
    connection.exec_driver_sql("INSERT INTO semantic.rebuild_sentinel VALUES (7)")
    before = catalog(connection)

    def fail(conn: Connection) -> None:
        conn.exec_driver_sql("UPDATE space.satcom_contract SET version = 'bad'")
        raise ValueError("seed failed")

    monkeypatch.setattr(seeds, "REVIEWED_SEED_LOADERS", (("space", fail),))
    with pytest.raises(ValueError, match="seed failed"):
        rebuild(connection)
    assert catalog(connection) == before
    assert connection.scalar(sa.text("SELECT id FROM semantic.rebuild_sentinel")) == 7
    assert connection.scalar(sa.text("SELECT current_user = session_user"))


def test_rebuild_refuses_external_dependents_without_removing_them(
    rebuild_connection: Connection, scratch_schemas: ScratchSchemas
) -> None:
    connection = rebuild_connection
    schema = scratch_schemas.schema("rebuild_vendor")
    connection.exec_driver_sql("CREATE TABLE semantic.rebuild_sentinel (id integer PRIMARY KEY)")
    connection.exec_driver_sql(
        f"CREATE TABLE {schema}.vendor (id integer REFERENCES semantic.rebuild_sentinel)"
    )
    before = catalog(connection)
    with pytest.raises(DBAPIError):
        rebuild(connection)
    assert catalog(connection) == before
    assert sa.inspect(connection).has_table("vendor", schema=schema)


def test_rebuild_removes_obsolete_tables_in_every_kn_schema(
    rebuild_connection: Connection, scratch_schemas: ScratchSchemas
) -> None:
    connection = rebuild_connection
    schema = scratch_schemas.schema("rebuild_unrelated")
    connection.exec_driver_sql(f"CREATE TABLE {schema}.vendor (id integer)")
    connection.exec_driver_sql(f"INSERT INTO {schema}.vendor VALUES (7)")
    for name in SCHEMAS:
        connection.exec_driver_sql(f"CREATE TABLE {name}.obsolete_rebuild (id integer)")
    rebuild(connection)
    for name in SCHEMAS:
        assert not sa.inspect(connection).has_table("obsolete_rebuild", schema=name)
    assert connection.scalar(sa.text(f"SELECT id FROM {schema}.vendor")) == 7


@pytest.mark.parametrize(
    "damage",
    [
        "ALTER TABLE space.countries DROP CONSTRAINT {check}",
        "ALTER TABLE space.aliases_crosswalk RENAME CONSTRAINT pk_aliases_crosswalk TO wrong_key",
        "COMMENT ON COLUMN space.countries.country_iso2 IS NULL",
        "ALTER TABLE space.aliases_crosswalk RENAME CONSTRAINT {reference} TO wrong_reference",
    ],
)
def test_damaged_baseline_object_rolls_back_before_returning(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    from kn.contracts.sqlalchemy import metadata
    from kn.db import rebuild as module

    model = metadata(load_contract())
    check = next(
        str(item.name)
        for item in model.tables["space.countries"].constraints
        if isinstance(item, sa.CheckConstraint)
    )
    reference = min(
        str(item.name) for item in model.tables["space.aliases_crosswalk"].foreign_key_constraints
    )
    real_upgrade = module.upgrade

    def damaged(connection: Connection) -> None:
        # Simulate an object that differs from the compiled contract after the baseline.
        real_upgrade(connection)
        connection.exec_driver_sql(damage.format(check=check, reference=reference))

    monkeypatch.setattr(module, "upgrade", damaged)
    before = catalog(rebuild_connection)
    with pytest.raises(ValueError, match=r"constraint|primary key|comment|foreign key|structure"):
        rebuild(rebuild_connection)
    assert catalog(rebuild_connection) == before


def test_database_seed_error_preserves_original_error_and_schemas(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = catalog(rebuild_connection)

    def fail(conn: Connection) -> None:
        conn.exec_driver_sql("SELECT 1 / 0")

    monkeypatch.setattr(seeds, "REVIEWED_SEED_LOADERS", (("space", fail),))
    with pytest.raises(DBAPIError, match="division by zero"):
        rebuild(rebuild_connection)
    assert catalog(rebuild_connection) == before
    assert rebuild_connection.scalar(sa.text("SELECT current_user = session_user"))


def test_noncontracted_view_refuses_without_partial_drop(rebuild_connection: Connection) -> None:
    before = catalog(rebuild_connection)
    rebuild_connection.exec_driver_sql("CREATE VIEW analytics.uncompiled AS SELECT 1 AS id")
    with pytest.raises(DBAPIError):
        rebuild(rebuild_connection)
    assert "uncompiled" in sa.inspect(rebuild_connection).get_view_names(schema="analytics")
    rebuild_connection.exec_driver_sql("DROP VIEW analytics.uncompiled")
    assert catalog(rebuild_connection) == before


def test_rebuild_creates_schemas_through_alembic_without_sql_text(
    rebuild_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Schema objects come from SQLAlchemy constructs in the Alembic baseline, as in upgrade."""
    statements: list[str] = []
    original = Connection.exec_driver_sql

    def record(self: Connection, statement: str, *args: object, **kwargs: object) -> object:
        statements.append(statement)
        return original(self, statement, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Connection, "exec_driver_sql", record)
    rebuild(rebuild_connection)
    assert not [statement for statement in statements if "CREATE TABLE" in statement.upper()]
    assert sa.inspect(rebuild_connection).has_table("satcom_contract", schema="space")
