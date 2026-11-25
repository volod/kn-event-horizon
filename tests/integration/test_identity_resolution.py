"""Lifecycle and matching handoff through PostgreSQL: merge, split, review boundary, rebuild."""

from datetime import timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.rebuild import rebuild
from kn.identity import store
from kn.identity.events import Event
from kn.identity.journal import Journal, LockedJournal
from kn.identity.matching.ingest import Receipt, submit
from kn.identity.matching.observe import Key, Observation, Reading
from kn.identity.matching.resolve import resolve
from kn.identity.model import Assignment, Merge, SourceKey, Split
from kn.identity.profiles import Profile
from kn.review.journal import Journal as ReviewJournal
from tests.identity.fixtures import NOW
from tests.identity.test_matching import calibrated, profile
from tests.integration.test_identity_lifecycle import _decision_ids, _submit
from tests.integration.test_model_baseline import _snapshot

LEI = "00000000000000000042"


def _org(source: str, minutes: int, *, version: str = "1", lei: str = "", **fields: str):
    return Observation(
        record=SourceKey(source=source, key="00042"),
        version=version,
        observed_at=NOW + timedelta(minutes=minutes),
        attributes=tuple(
            Reading(field_id=f"organization.{key}", value=value) for key, value in fields.items()
        ),
        authoritative=(Key(namespace="lei", issuer="fixture:lei", value=lei),) if lei else (),
    )


def _ingest(connection: Connection, journal: Journal, config: Profile, incoming: Observation):
    return submit(connection, journal, config, incoming, actor="engine:fixture", evidence="a")


def _merge_then_split(connection: Connection, journal: Journal, config: Profile) -> list[Receipt]:
    receipts = [
        _ingest(
            connection,
            journal,
            config,
            _org(
                f"src:{name}",
                index,
                lei=LEI if name == "alpha" else "",
                name=f"Fixture {name.title()} Ltd",
                domain=f"fixture-{name}.com",
            ),
        )
        for index, name in enumerate(("alpha", "beta", "gamma", "delta"))
    ]
    alpha, beta, gamma, delta = (str(item.kn_id) for item in receipts)
    _submit(connection, journal, Merge(kn_id=alpha, survivor=beta), "audit-merge")
    assignments = tuple(
        Assignment(item_id=key, successor=gamma if holding.event.payload.kn_id == alpha else delta)
        for key, holding in journal.state().owned(beta).items()
    )
    split = Split(kn_id=beta, successors=(gamma, delta), assignments=assignments)
    _submit(connection, journal, split, "audit-split")
    return receipts


def test_merge_split_and_name_only_match_reproduce_across_rebuilds(
    rebuild_connection: Connection, tmp_path: Path
) -> None:
    connection, journal, config = rebuild_connection, Journal(tmp_path), profile()
    rebuild(connection, data_dir=tmp_path)
    receipts = _merge_then_split(connection, journal, config)
    alpha, beta, gamma, delta = (str(item.kn_id) for item in receipts)
    assert journal.state().resolve(alpha) == journal.state().resolve(beta)
    assert set(journal.state().resolve(alpha)) == {gamma, delta}

    name_only = _org("src:name-only", 9, name="Fixture Alpha Limited")
    review = _ingest(connection, journal, config, name_only)
    assert (review.match.decision, review.kn_id) == ("review", None)
    assert [item.kn_id for item in review.match.candidates] == [gamma]
    assert _ingest(connection, journal, config, name_only) == review
    assert resolve(journal.state(), calibrated(config), name_only).decision == "review"
    redelivered = _ingest(connection, journal, config, _org("src:alpha", 10, version="2"))
    by_key = _ingest(connection, journal, config, _org("src:lei", 11, lei=LEI))
    assert (redelivered.match.trace.route, redelivered.kn_id) == ("existing_link", gamma)
    assert (by_key.match.trace.route, by_key.kn_id) == ("authoritative_key", gamma)

    tables = metadata(store.contract()).tables
    links, matches = tables["identity.links"], tables["identity.matches"]
    record_id = name_only.record.record_id
    assert connection.scalar(sa.select(sa.func.count()).where(links.c.record_id == record_id)) == 0
    row = connection.execute(sa.select(matches).where(matches.c.record_id == record_id)).one()
    assert (row.decision, row.selected) == ("review", None)

    before, decisions = _snapshot(connection, [store.contract()]), _decision_ids(connection)
    assert len(decisions) == 2
    for drop in (False, False, True):
        if drop:
            connection.exec_driver_sql("DROP SCHEMA identity CASCADE")
        rebuild(connection, data_dir=tmp_path)
        assert _snapshot(connection, [store.contract()]) == before
        assert _decision_ids(connection) == decisions
    assert set(journal.state().resolve(alpha)) == {gamma, delta}


def test_lifecycle_refuses_before_review_while_a_match_batch_is_pending(
    rebuild_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection, journal, config = rebuild_connection, Journal(tmp_path), profile()
    rebuild(connection, data_dir=tmp_path)
    alpha, beta = (
        str(_ingest(connection, journal, config, _org(f"src:{name}", 0, domain=name)).kn_id)
        for name in ("fixture-alpha.com", "fixture-beta.com")
    )
    pending = _org("src:pending", 1, domain="fixture-gamma.com")
    original = LockedJournal.append_batch

    def interrupted(locked: LockedJournal, values: tuple[Event, ...]) -> None:
        original(locked, values[:1])
        raise OSError("fixture interruption")

    with monkeypatch.context() as patch:
        patch.setattr(LockedJournal, "append_batch", interrupted)
        with pytest.raises(OSError, match="fixture interruption"):
            _ingest(connection, journal, config, pending)
    with pytest.raises(ValueError, match="retry the pending identity match"):
        _submit(connection, journal, Merge(kn_id=alpha, survivor=beta), "while-pending")
    assert ReviewJournal(tmp_path).read() == ()
    assert _ingest(connection, journal, config, pending).kn_id is not None
    _submit(connection, journal, Merge(kn_id=alpha, survivor=beta), "while-pending")
    assert journal.state().resolve(alpha) == (beta,)
