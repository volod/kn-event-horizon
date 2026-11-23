"""Network-free governance generation and refusal diagnostics; live behavior has integration gates."""

from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from kn.db import governance, platform, verification


def connection() -> MagicMock:
    result = MagicMock()
    result.dialect = postgresql.dialect()
    return result


def test_python_platform_generates_safe_policy_and_owns_default_grants() -> None:
    conn = connection()
    conn.scalar.side_effect = ["kn", *([False] * 30)]
    platform.apply_platform(conn)
    statements = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert "pg_advisory_xact_lock" in statements[0]
    assert statements.count("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public") == 1
    assert "REVOKE ALL ON DATABASE kn FROM PUBLIC" in statements
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in statements
    assert "ALTER EXTENSION postgis UPDATE" in statements
    assert sum(statement.startswith("CREATE ROLE ") for statement in statements) == 30
    assert sum(statement.startswith("CREATE SCHEMA ") for statement in statements) == 10
    assert not any("PASSWORD" in statement for statement in statements)
    assert (
        "ALTER DEFAULT PRIVILEGES FOR ROLE kn_space_owner IN SCHEMA space GRANT SELECT ON TABLES TO kn_space_reader"
        in statements
    )
    assert (
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA space TO kn_space_loader"
        in statements
    )


def test_upgrade_is_alembic_upgrade_head_in_the_caller_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    command = MagicMock()
    monkeypatch.setattr(governance.command, "upgrade", command)
    governance.upgrade(conn)
    config, target = command.call_args.args
    assert config.attributes["connection"] is conn and target == "head"
    conn.commit.assert_not_called()


def test_every_alembic_run_converges_the_platform_around_its_revisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    events: list[str] = []
    monkeypatch.setattr(governance, "apply_platform", lambda _: events.append("platform"))
    conn.execute.side_effect = lambda statement: events.append(str(statement))
    governance.governed_migrations(conn, lambda: events.append("revisions"))
    assert events == [
        "platform",
        "SET LOCAL ROLE kn_system_owner",
        "revisions",
        "RESET ROLE",
        "platform",
    ]


def test_verification_refuses_wrong_revision_unsafe_roles_and_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    context = MagicMock()
    monkeypatch.setattr("alembic.migration.MigrationContext.configure", lambda *a, **k: context)
    context.get_current_revision.return_value = "old"
    with pytest.raises(ValueError, match="revision"):
        governance.verify(conn)
    context.get_current_revision.return_value = "0001_baseline"
    conn.scalar.return_value = "intruder"
    with pytest.raises(ValueError, match="owner"):
        governance.verify(conn)
    conn.scalar.side_effect = [f"kn_{schema}_owner" for schema in platform.SCHEMAS]
    conn.execute.return_value.one_or_none.return_value = (True, False, False, False, False, False)
    with pytest.raises(ValueError, match="unsafe"):
        governance.verify(conn)


def test_contract_verification_refuses_missing_marker_and_digest_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kn.contracts.model import canonical
    from kn.contracts.registry import registered_contracts

    conn = connection()
    inspector = MagicMock()
    monkeypatch.setattr(sa, "inspect", lambda _: inspector)
    inspector.has_table.return_value = False
    with pytest.raises(ValueError, match="baseline"):
        governance.verify_contracts(conn)
    inspector.has_table.return_value = True
    contracts = registered_contracts()
    rows = [
        {
            "contract_id": item.contract_id,
            "version": item.version,
            "digest": item.digest,
            "storage_schema": item.schema,
            "managed_tables_json": canonical([table.name for table in item.tables]),
        }
        for item in contracts
    ]
    for installed in (
        [],
        rows[:1],
        *[
            [rows[0], {**rows[1], field: value}, *rows[2:]]
            for field, value in (
                ("digest", "old"),
                ("storage_schema", "identity"),
                ("managed_tables_json", "[]"),
            )
        ],
    ):
        conn.execute.return_value.mappings.return_value = installed
        with pytest.raises(ValueError, match="digest drift"):
            governance.verify_contracts(conn)
    conn.execute.return_value.mappings.return_value = rows
    structure, tables = MagicMock(), MagicMock()
    monkeypatch.setattr(governance, "verify_structure", structure)
    monkeypatch.setattr(governance, "verify_registered_tables", tables)
    governance.verify_contracts(conn)
    structure.assert_called_once_with(conn, contracts)
    tables.assert_called_once_with(conn, contracts)


def test_structural_drift_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    context = MagicMock()
    monkeypatch.setattr(verification.MigrationContext, "configure", lambda *a, **k: context)
    diff = MagicMock(return_value=[("remove_table", "evidence_claims")])
    monkeypatch.setattr(verification, "compare_metadata", diff)
    with pytest.raises(ValueError, match="structure"):
        verification.verify_structure(connection())
    diff.return_value = []
    verification.verify_structure(connection())


def test_privilege_refusal_always_rolls_back_probe_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = connection()
    conn.scalar.return_value = False
    with pytest.raises(ValueError, match="privilege mismatch"):
        verification.verify_privileges(conn)
    conn.begin_nested.return_value.rollback.assert_called_once()
    monkeypatch.setattr(verification, "_schema_privileges", lambda *a: None)
    conn.begin_nested.reset_mock()
    # Deliberately incomplete privileges also fail at the table probe.
    with pytest.raises(ValueError, match="privilege mismatch"):
        verification.verify_privileges(conn)
    conn.begin_nested.return_value.rollback.assert_called_once()
