"""Typed platform statements quote names and accept only known keywords."""

from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

from kn.db.statements import PUBLIC, AlterRole, CreateRole, Privileges, SetRole


def sql(statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]


def test_names_are_quoted_by_the_dialect_not_by_string_assembly() -> None:
    assert sql(CreateRole("kn_space_owner")) == "CREATE ROLE kn_space_owner"
    assert sql(CreateRole('odd"name')) == 'CREATE ROLE "odd""name"'
    assert sql(SetRole("Mixed")) == 'SET LOCAL ROLE "Mixed"'
    grant = Privileges("GRANT", ("CONNECT",), "DATABASE", "kn test", (PUBLIC, "kn_a"))
    assert sql(grant) == 'GRANT CONNECT ON DATABASE "kn test" TO PUBLIC, kn_a'


def test_default_privileges_name_their_owner_and_schema() -> None:
    statement = Privileges(
        "GRANT", ("SELECT",), "TABLES", None, ("kn_space_reader",), defaults=("o", "space")
    )
    assert sql(statement) == (
        "ALTER DEFAULT PRIVILEGES FOR ROLE o IN SCHEMA space GRANT SELECT ON TABLES TO "
        "kn_space_reader"
    )


@pytest.mark.parametrize(
    "build",
    [
        lambda: Privileges("GRANT", ("SELECT; DROP",), "SCHEMA", "s", ("r",)),
        lambda: Privileges("GRANT", ("SELECT",), "SCHEMA", "s", ()),
        lambda: Privileges("GRANT", ("SELECT",), "TABLES", "s", ("r",)),
        lambda: Privileges("GRANT", ("SELECT",), "SCHEMA", None, ("r",), defaults=("o", "s")),
        lambda: AlterRole("r", ("SUPERUSER",)),
    ],
)
def test_unknown_keywords_and_inconsistent_targets_are_refused(build: object) -> None:
    with pytest.raises(ValueError):
        build()  # type: ignore[operator]


def test_production_code_sends_no_sql_strings_to_the_database() -> None:
    """Schema, migration, policy, and catalog statements are SQLAlchemy or Alembic constructs."""
    root = Path(__file__).resolve().parents[2] / "src" / "kn"
    forbidden = ("sa.text(", "sqlalchemy.text(", "sa.DDL(", "exec_driver_sql(", 'op.execute("')
    offenders = [
        f"{path.relative_to(root)}: {marker}"
        for path in sorted(root.rglob("*.py"))
        for marker in forbidden
        if marker in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
