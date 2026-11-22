"""Network-free governance generation and refusal diagnostics; live behavior has integration gates."""

from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from kn.contracts import load_contract
from kn.contracts.loader import canonical
from kn.db import governance, platform, rebuild, verification


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
    assert 'REVOKE ALL ON DATABASE "kn" FROM PUBLIC' in statements
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


def test_upgrade_uses_one_caller_transaction_and_resets_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    apply = MagicMock()
    command = MagicMock()
    monkeypatch.setattr(governance, "apply_platform", apply)
    monkeypatch.setattr(governance.command, "upgrade", command)
    governance.upgrade(conn)
    assert apply.call_count == 2
    config, target = command.call_args.args
    assert config.attributes["connection"] is conn and target == "head"
    assert "RESET ROLE" in [str(call.args[0]) for call in conn.execute.call_args_list]
    conn.commit.assert_not_called()


def test_verification_refuses_wrong_revision_unsafe_roles_and_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    context = MagicMock()
    monkeypatch.setattr("alembic.migration.MigrationContext.configure", lambda *a, **k: context)
    context.get_current_revision.return_value = "old"
    with pytest.raises(ValueError, match="revision"):
        governance.verify(conn)
    context.get_current_revision.return_value = "0001_satcom"
    conn.scalar.return_value = "intruder"
    with pytest.raises(ValueError, match="owner"):
        governance.verify(conn)
    conn.scalar.side_effect = lambda statement, params: f"kn_{params['schema']}_owner"
    conn.execute.return_value.one_or_none.return_value = (True, False, False, False, False, False)
    with pytest.raises(ValueError, match="unsafe"):
        governance.verify(conn)


def test_contract_verification_refuses_missing_marker_and_digest_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = connection()
    inspector = MagicMock()
    monkeypatch.setattr(sa, "inspect", lambda _: inspector)
    inspector.has_table.return_value = False
    with pytest.raises(ValueError, match="baseline"):
        governance.verify_contract(conn)
    inspector.has_table.return_value = True
    conn.execute.return_value.one_or_none.return_value = ("1.0.0", "old")
    with pytest.raises(ValueError, match="digest drift"):
        governance.verify_contract(conn)
    contract = load_contract()
    conn.execute.return_value.one_or_none.return_value = (contract.version, contract.digest)
    check = MagicMock()
    monkeypatch.setattr(governance, "verify_structure", check)
    governance.verify_contract(conn)
    check.assert_called_once_with(conn)


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


def test_explicit_rebuild_filters_unmanaged_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = connection()
    monkeypatch.setenv("KN_ENVIRONMENT", "development")
    monkeypatch.setattr(rebuild, "apply_platform", lambda *a: None)
    inspector = MagicMock()
    inspector.get_table_names.return_value = [
        "satcom_contract",
        "countries",
        "removed_old",
        "unmanaged",
    ]
    monkeypatch.setattr(sa, "inspect", lambda _: inspector)
    marker = sa.Table(
        "satcom_contract",
        sa.MetaData(),
        sa.Column("managed_tables_json", sa.Text()),
        sa.Column("contract_id", sa.Text()),
    )
    original_table = sa.Table
    monkeypatch.setattr(
        rebuild.sa,
        "Table",
        lambda *a, **k: marker if a[0] == "satcom_contract" else original_table(*a, **k),
    )
    conn.scalar.return_value = canonical(["satcom_contract", "removed_old"])
    reflect = MagicMock()
    monkeypatch.setattr(sa.MetaData, "reflect", reflect)
    monkeypatch.setattr(sa.MetaData, "drop_all", lambda *a: None)
    stamp = MagicMock()
    monkeypatch.setattr(rebuild.command, "stamp", stamp)
    upgrade = MagicMock()
    monkeypatch.setattr(rebuild, "upgrade", upgrade)
    rebuild.rebuild(conn)
    assert reflect.call_args.kwargs == {
        "only": ["countries", "removed_old", "satcom_contract"],
        "resolve_fks": False,
    }
    assert stamp.call_args.args[1] == "base"
    upgrade.assert_called_once_with(conn)
