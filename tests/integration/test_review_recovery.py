"""Queue write-ahead recovery and exact record/field verification scope."""

import pytest
import sqlalchemy as sa

from kn.evidence.projection import history as fact_history
from kn.evidence.projection import write
from kn.evidence.selection import Subject
from kn.evidence.store import record
from kn.identity.journal import Journal as IdentityJournal
from kn.review import store
from kn.review.facts import applied
from kn.review.journal import Journal
from kn.review.model import Request
from kn.review.queue import items
from kn.review.queue_replay import reattach
from kn.review.queue_store import submit
from kn.review.selection import accepted_reviews
from tests.evidence.selection_fixtures import CONTEXT, MAKER, MAKER_TWO, T0, policy, stated
from tests.integration.test_review_queue import ACTOR, prepare, request


def test_rolled_back_fact_decision_reattaches_from_the_log(
    rebuild_connection, tmp_path, monkeypatch
):
    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    claims = [stated(MAKER, "1250"), stated(MAKER_TWO, "1300")]
    record(connection, claims)
    write(connection, fact_history(Subject.of(claims[0]), claims, policy(), CONTEXT))
    item = next(iter(items(connection, resolver, IdentityJournal(tmp_path)).values()))
    review = request(item, claims[0].key)
    original = store._insert

    def fail(*_):
        raise ValueError("injected SQL failure")

    with monkeypatch.context() as patch:
        patch.setattr(store, "_insert", fail)
        with pytest.raises(ValueError, match="injected"), connection.begin_nested():
            submit(
                connection,
                tmp_path,
                "fixture",
                resolver,
                review,
                lambda: ACTOR,
                lambda: review.performed_at,
            )
    (event,) = Journal(tmp_path, "fixture").read()
    assert event.decision_id not in {row.decision_id for row in applied(connection)}
    assert reattach(connection, tmp_path, resolver) == [
        {"decision_id": event.decision_id, "state": "applied"}
    ]
    assert accepted_reviews(applied(connection)).selected == {claims[0].key: event.recorded_at}
    assert reattach(connection, tmp_path, resolver) == [
        {"decision_id": event.decision_id, "state": "applied"}
    ]
    assert store._insert is original


def test_record_field_target_preparation_and_rejection_clear_only_that_stamp(
    rebuild_connection, tmp_path
):
    import json

    from kn.review.verification import inspect

    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    dataset = resolver.dataset("kn.core.semantic", "namespace_labels")
    row = dict(
        connection.execute(
            sa.select(dataset.table).order_by(*dataset.table.primary_key.columns).limit(1)
        )
        .mappings()
        .one()
    )
    field = "semantic.namespace_labels.label"
    query = {
        "contract_id": "kn.core.semantic",
        "dataset": "namespace_labels",
        "key": [part.model_dump(mode="json") for part in dataset.key(row)],
        "purpose": "factual",
        "field_id": field,
    }
    prepared = inspect(connection, resolver, json.dumps(query))
    from kn.review.model import Target

    target = Target.model_validate(prepared["target"])
    first = Request(
        request_id="field-check",
        target=target,
        outcome="accept",
        performed_at=T0,
        reason="Compared fixture label",
        evidence="review:fixture",
    )
    event = submit(connection, tmp_path, "fixture", resolver, first, lambda: ACTOR, lambda: T0)
    assert store.projection(connection, target).stamp.human_verified_at == T0
    record_target = dataset.target(row, "factual")
    assert store.projection(connection, record_target).stamp.human_verified_at is None
    second = Request(
        request_id="field-reject",
        target=target,
        outcome="reject",
        performed_at=T0,
        reason="Fixture rejected",
        evidence="review:fixture",
        predecessors=(event.decision_id,),
    )
    submit(connection, tmp_path, "fixture", resolver, second, lambda: ACTOR, lambda: T0)
    assert store.projection(connection, target).stamp.human_verified_at is None
    assert len(Journal(tmp_path, "fixture").read()) == 2
    changed_domain = "different"
    with pytest.raises(ValueError, match="another domain"):
        submit(connection, tmp_path, changed_domain, resolver, first, lambda: ACTOR, lambda: T0)


def test_two_rebuilds_reattach_the_original_queue_decision(rebuild_connection, tmp_path):
    from kn.db.rebuild import rebuild

    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    claims = [stated(MAKER, "1250"), stated(MAKER_TWO, "1300")]
    subject = Subject.of(claims[0])
    baseline = fact_history(subject, claims, policy(), CONTEXT)
    record(connection, claims)
    write(connection, baseline)
    item = next(iter(items(connection, resolver, IdentityJournal(tmp_path)).values()))
    review = request(item, claims[0].key)
    original = submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        review,
        lambda: ACTOR,
        lambda: review.performed_at,
    )
    for _ in range(2):
        from kn.evidence.store import evidence_tables
        from tests.integration.test_evidence import _check_references

        _check_references(connection, evidence_tables())
        rebuild(connection, data_dir=tmp_path)
        assert reattach(connection, tmp_path, resolver) == [
            {"decision_id": original.decision_id, "state": "orphan"}
        ]
        record(connection, claims)
        write(connection, baseline)
        assert reattach(connection, tmp_path, resolver) == [
            {"decision_id": original.decision_id, "state": "applied"}
        ]
        (event,) = applied(connection)
        assert event == original
        assert accepted_reviews((event,)).selected == {claims[0].key: original.recorded_at}


def test_caught_replay_failure_rolls_back_the_entire_sql_batch(
    rebuild_connection, tmp_path, monkeypatch
):
    from kn.evidence.store import evidence_tables
    from kn.review import queue_replay

    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    claims = [stated(MAKER, "1250"), stated(MAKER_TWO, "1300")]
    record(connection, claims)
    write(connection, fact_history(Subject.of(claims[0]), claims, policy(), CONTEXT))
    item = next(iter(items(connection, resolver, IdentityJournal(tmp_path)).values()))
    first = request(item, claims[0].key)
    accepted = submit(
        connection, tmp_path, "fixture", resolver, first, lambda: ACTOR, lambda: first.performed_at
    )
    second = request(
        item, claims[0].key, name="reject", outcome="reject", predecessors=(accepted.decision_id,)
    )
    submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        second,
        lambda: ACTOR,
        lambda: second.performed_at,
    )
    table = evidence_tables()["review_decisions"]
    connection.execute(table.delete())
    connection.execute(store.decision_table().delete())
    apply_event = queue_replay.apply_fact_event
    calls = []

    def fail_on_second(*args):
        calls.append(True)
        if len(calls) == 2:
            raise ValueError("injected replay failure")
        return apply_event(*args)

    monkeypatch.setattr(queue_replay, "apply_fact_event", fail_on_second)
    with pytest.raises(ValueError, match="injected replay failure"):
        reattach(connection, tmp_path, resolver)
    assert connection.scalar(sa.select(sa.func.count()).select_from(table)) == 0
