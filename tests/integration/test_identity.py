"""PostgreSQL identity replay and guarded rebuild acceptance."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import canonical
from kn.contracts.sqlalchemy import metadata
from kn.db.rebuild import rebuild
from kn.identity import store
from kn.identity.journal import Journal
from kn.identity.model import Link, Merge, Mint, SourceKey
from tests.identity.fixtures import KEY, A, B, D, F, history
from tests.identity.test_state import append
from tests.integration.identity_fixtures import seed_identity_fixture as seed_journal
from tests.integration.test_model_baseline import _snapshot


def test_identity_replay_twice_and_database_drop_preserve_all_rows(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    connection = rebuild_connection
    journal = seed_journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    state = store.replay(connection, journal)
    first = _snapshot(connection, [store.contract()])
    assert state.resolve(A) == (D, F)
    assert all(first.values())
    assert any(row["native_key"] == "00042" for row in first["identity.source_records"])
    store.replay(connection, journal)
    assert _snapshot(connection, [store.contract()]) == first
    connection.exec_driver_sql("DROP SCHEMA identity CASCADE")
    rebuild(connection, data_dir=tmp_path)
    assert _snapshot(connection, [store.contract()]) == first
    # The durable log never changes during SQL replay or rebuild.
    assert journal.read() == history()


def test_durable_append_survives_sql_rollback_and_retry(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    connection = rebuild_connection
    journal = Journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    value = history()[0]
    with pytest.raises(RuntimeError), connection.begin_nested():
        assert store.apply(connection, journal, lambda locked: locked.append(value))
        raise RuntimeError("interrupted SQL")
    assert connection.scalar(sa.text("SELECT count(*) FROM identity.objects")) == 0
    assert journal.read() == (value,)
    store.replay(connection, journal)
    assert connection.scalar(sa.text("SELECT kn_id FROM identity.objects")) == A
    assert not store.apply(connection, journal, lambda locked: locked.append(value))


def test_invalid_transitions_refuse_before_durable_write_or_sql_change(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    connection = rebuild_connection
    journal = Journal(tmp_path)
    for item in history()[:5]:
        journal.append(item)
    rebuild(connection, data_dir=tmp_path)
    before = _snapshot(connection, [store.contract()])
    invalid = append(
        journal.read(),
        Mint(
            kn_id=A,
            entity_class="core.organization",
            anchor=SourceKey(source="fixture:new", key="x"),
        ),
    )[-1]
    with pytest.raises(ValueError, match="reused"):
        store.apply(connection, journal, lambda locked: locked.append(invalid))
    assert _snapshot(connection, [store.contract()]) == before
    assert len(journal.read()) == 5
    # Fixture history includes merged and retired objects; both are invalid merge/link targets.
    for item in history()[5:]:
        journal.append(item)
    store.replay(connection, journal)
    for payload in (Merge(kn_id=D, survivor=B), Link(record=KEY, kn_id=A, method="minted")):
        value = append(journal.read(), payload)[-1]
        with pytest.raises(ValueError, match="active object"):
            store.apply(connection, journal, lambda locked, value=value: locked.append(value))
    assert journal.read() == history()


def test_malformed_log_rolls_back_rebuild_even_when_caught(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    connection = rebuild_connection
    journal = seed_journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    before = _snapshot(connection, [store.contract()])
    journal.path.write_bytes(journal.path.read_bytes()[:-1])
    with pytest.raises(ValueError, match="incomplete"):
        rebuild(connection, data_dir=tmp_path)
    assert _snapshot(connection, [store.contract()]) == before


def test_sql_history_ahead_of_log_refuses_without_erasing_evidence(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    connection = rebuild_connection
    journal = seed_journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    table = metadata(store.contract()).tables["identity.lifecycle_events"]
    connection.execute(table.update().where(table.c.sequence == 1).values(event_json=canonical({})))
    before = _snapshot(connection, [store.contract()])
    with pytest.raises(ValueError, match="not a prefix"):
        store.replay(connection, journal)
    assert _snapshot(connection, [store.contract()]) == before


def test_database_index_refuses_a_second_active_link_and_allows_history(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    from sqlalchemy.exc import IntegrityError

    journal = Journal(tmp_path)
    for item in history()[:6]:
        journal.append(item)
    rebuild(rebuild_connection, data_dir=tmp_path)
    table = metadata(store.contract()).tables["identity.links"]
    link = dict(rebuild_connection.execute(sa.select(table)).mappings().one())
    # The event FK is deferred; the unique active-record index must refuse immediately.
    with (
        pytest.raises(IntegrityError, match="identity_active_link_idx"),
        rebuild_connection.begin_nested(),
    ):
        rebuild_connection.execute(table.insert().values(**{**link, "link_id": "b" * 64}))
    with rebuild_connection.begin_nested() as probe:
        rebuild_connection.execute(
            table.insert().values(
                **{
                    **link,
                    "link_id": "b" * 64,
                    "ended_event": history()[0].event_id,
                }
            )
        )
        assert rebuild_connection.scalar(sa.select(sa.func.count()).select_from(table)) == 2
        probe.rollback()


def test_missing_partial_predicate_is_detected_by_compiled_verification(
    rebuild_connection: Connection,
    tmp_path: Path,
) -> None:
    from kn.db.verification import verify_compiled_catalog

    rebuild(rebuild_connection, data_dir=tmp_path)
    rebuild_connection.exec_driver_sql("DROP INDEX identity.identity_active_link_idx")
    rebuild_connection.exec_driver_sql(
        "CREATE UNIQUE INDEX identity_active_link_idx ON identity.links (record_id)"
    )
    with pytest.raises(ValueError, match="index predicate mismatch"):
        verify_compiled_catalog(rebuild_connection)
