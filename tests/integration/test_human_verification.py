"""Human decisions apply atomically, replay exactly and expose concurrent conflicts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Request, Stamp, Target
from kn.review.targets import content_version
from tests.integration.review_support import (
    ID,
    LABEL,
    submit,
)
from tests.review.test_protocol import NOW, reviewer


def test_transaction_rollback_and_exact_idempotent_replay(review_database, tmp_path: Path) -> None:
    engine, resolver, _, target = review_database
    log = Journal(tmp_path)
    with engine.connect() as connection:
        with connection.begin() as transaction:
            decision = submit(connection, log, resolver, target)
            assert store.projection(connection, target).state == "accepted"
            transaction.rollback()
        with connection.begin():
            assert store.projection(connection, target).stamp == Stamp()
            assert (
                store.replay_target(connection, log, resolver, target).stamp.human_verified_at
                == NOW
            )
            assert submit(connection, log, resolver, target) == decision
            later = Request.model_validate(
                {
                    key: value
                    for key, value in decision.model_dump().items()
                    if key in Request.model_fields
                }
            )
            retried = store.submit(
                connection, log, resolver, later, reviewer, lambda: NOW + timedelta(days=1)
            )
            assert retried == decision
        assert log.read() == (decision,)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_dataset",
        "unknown_field",
        "incomplete_key",
        "wrong_key_type",
        "unknown_record",
        "stale",
    ],
)
def test_bad_targets_never_append(review_database, tmp_path: Path, mutation: str) -> None:
    engine, resolver, _, target = review_database
    data = target.model_dump()
    if mutation == "unknown_dataset":
        data["dataset"] = "unknown"
    elif mutation == "unknown_field":
        data["field_id"] = "unknown"
    elif mutation == "incomplete_key":
        data["key"][0]["field_id"] = "unknown"
    elif mutation == "wrong_key_type":
        data["key"][0].update(kind="integer", value=1)
    elif mutation == "unknown_record":
        data["key"][0]["value"] = "missing"
    else:
        data["version"] = "b" * 64
    log = Journal(tmp_path)
    with engine.begin() as connection, pytest.raises(ValueError):
        submit(connection, log, resolver, Target.model_validate(data))
    assert not log.path.exists()


def test_changed_content_does_not_inherit_approval_and_row_scope_is_independent(
    review_database,
    tmp_path: Path,
) -> None:
    engine, resolver, row_table, target = review_database
    log = Journal(tmp_path)
    with engine.begin() as connection:
        submit(connection, log, resolver, target)
        record = target.model_dump()
        record.update(
            scope="record", field_id=None, version=content_version({ID: "001", LABEL: "Original"})
        )
        assert store.projection(connection, Target.model_validate(record)).stamp == Stamp()
        connection.execute(row_table.update().values(label="Edited"))
        with pytest.raises(ValueError, match="stale"):
            store.replay_target(connection, log, resolver, target)
        edited = Target.model_validate(
            {**target.model_dump(), "version": content_version({LABEL: "Edited"})}
        )
        assert store.projection(connection, edited).stamp == Stamp()
        assert store.projection(connection, target).state == "accepted"  # historical version


def test_concurrent_decisions_remain_conflicted_until_explicit_resolution(
    review_database,
    tmp_path: Path,
) -> None:
    engine, resolver, _, target = review_database
    log = Journal(tmp_path)

    def worker(outcome):
        request = Request(
            request_id=outcome,
            target=target,
            outcome=outcome,
            performed_at=NOW,
            reason="Checked",
            evidence="review:fixture",
        )
        with engine.begin() as connection:
            return store.submit(connection, log, resolver, request, reviewer, lambda: NOW)

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted, rejected = list(pool.map(worker, ["accept", "reject"]))
    with engine.begin() as connection:
        conflict = store.projection(connection, target)
        assert conflict.state == "conflict" and conflict.stamp == Stamp()
        request = Request(
            request_id="resolve",
            target=target,
            outcome="supersede",
            predecessors=(accepted.decision_id, rejected.decision_id),
            performed_at=NOW,
            reason="Compared evidence",
            evidence="review:resolution",
        )
        resolved = store.submit(connection, log, resolver, request, reviewer, lambda: NOW)
        assert (
            store.projection(connection, target).stamp.human_verification_decision_id
            == resolved.decision_id
        )
        request = Request(
            request_id="revoke",
            target=target,
            outcome="revoke",
            predecessors=(resolved.decision_id,),
            performed_at=NOW,
            reason="Withdrawn",
            evidence="review:withdrawal",
        )
        store.submit(connection, log, resolver, request, reviewer, lambda: NOW)
        assert store.projection(connection, target).state == "revoked"
        assert (
            connection.scalar(sa.select(sa.func.count()).select_from(store.decision_table())) == 4
        )
    assert len(log.read()) == 4


def test_concurrent_retries_append_once(review_database, tmp_path: Path) -> None:
    engine, resolver, _, target = review_database
    log = Journal(tmp_path)

    def worker(_):
        with engine.begin() as connection:
            return submit(connection, log, resolver, target)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(worker, range(2)))
    assert first == second and log.read() == (first,)


def test_failed_application_retains_journal_but_rolls_back_partial_sql(
    review_database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, resolver, _, target = review_database
    log = Journal(tmp_path)
    apply = store._apply

    def fail_after_insert(connection, events, target):
        apply(connection, events, target)
        raise ValueError("planted projection failure")

    with engine.begin() as connection:
        with monkeypatch.context() as patch:
            patch.setattr(store, "_apply", fail_after_insert)
            with pytest.raises(ValueError, match="planted"):
                submit(connection, log, resolver, target)
        assert store.projection(connection, target).stamp == Stamp()
        assert len(log.read()) == 1
        assert store.replay_target(connection, log, resolver, target).state == "accepted"


def test_reused_request_and_automated_actor_never_publish_new_decisions(
    review_database,
    tmp_path: Path,
) -> None:
    from kn.review.protocol import Reviewer

    engine, resolver, _, target = review_database
    log = Journal(tmp_path)
    with engine.begin() as connection:
        first = submit(connection, log, resolver, target)
        request = Request(
            request_id="spoof",
            target=target,
            outcome="accept",
            performed_at=NOW,
            reason="Source verified text",
            evidence="source:verified",
        )
        actor = Reviewer("agent:import", "import", True, frozenset({"factual"}))
        with pytest.raises(ValueError, match="human"):
            store.submit(connection, log, resolver, request, lambda: actor, lambda: NOW)
        reused = Request.model_validate({**request.model_dump(), "request_id": "first"})
        with pytest.raises(ValueError, match="reused"):
            store.submit(connection, log, resolver, reused, reviewer, lambda: NOW)
        assert log.read() == (first,)
        assert (
            store.projection(connection, target).stamp.human_verification_decision_id
            == first.decision_id
        )
