"""A durable but unapplied identity choice never replaces a newer source observation."""

import pytest

from kn.identity.journal import Journal
from kn.identity.matching.ingest import submit as ingest
from kn.review import store
from kn.review.journal import Journal as Decisions
from kn.review.queue import items
from kn.review.queue_replay import reattach
from kn.review.queue_store import submit
from tests.identity.test_matching import observation, profile
from tests.integration.test_review_queue import ACTOR, prepare, request


def test_pending_old_identity_choice_is_reported_stale(rebuild_connection, tmp_path, monkeypatch):
    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    identity, config = Journal(tmp_path), profile()
    known = ingest(
        connection,
        identity,
        config,
        observation({"organization.name": "Fixture"}, source="fixture:known"),
        actor="engine",
        evidence="archive:fixture",
    )
    incoming = observation({"organization.name": "Fixture"}, source="fixture:new")
    pending = ingest(
        connection, identity, config, incoming, actor="engine", evidence="archive:fixture"
    )
    item = next(
        item
        for item in items(connection, resolver, identity).values()
        if item.details.get("match_id") == pending.match_id
    )
    review = request(item, known.kn_id)

    def fail(*_):
        raise ValueError("injected SQL failure")

    with monkeypatch.context() as patch:
        patch.setattr(store, "_insert", fail)
        with pytest.raises(ValueError, match="injected"):
            submit(
                connection,
                tmp_path,
                "fixture",
                resolver,
                review,
                lambda: ACTOR,
                lambda: review.performed_at,
            )
    (event,) = Decisions(tmp_path, "fixture").read()
    ingest(
        connection,
        identity,
        config,
        incoming.model_copy(update={"version": "2"}),
        actor="engine",
        evidence="archive:fixture",
    )
    assert reattach(connection, tmp_path, resolver) == [
        {"decision_id": event.decision_id, "state": "stale"}
    ]
    assert identity.state().links(incoming.record) == []
