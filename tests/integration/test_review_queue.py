"""Review decisions apply once, reattach, report orphans, and preserve human scope."""

from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import Connection

from kn.contracts.registry import registered_contracts
from kn.db.rebuild import rebuild
from kn.evidence.projection import history as fact_history
from kn.evidence.projection import write
from kn.evidence.ranking import Context
from kn.evidence.selection import Subject
from kn.evidence.store import evidence_tables, record
from kn.identity.journal import Journal as IdentityJournal
from kn.identity.matching.ingest import submit as ingest
from kn.identity.model import Attribute, Identifier, Link
from kn.review.facts import applied
from kn.review.journal import Journal
from kn.review.model import Request
from kn.review.protocol import Reviewer
from kn.review.queue import items
from kn.review.queue_replay import reattach
from kn.review.queue_store import submit
from kn.review.selection import accepted_reviews
from kn.review.targets import ContractResolver
from tests.evidence.selection_fixtures import CONTEXT, MAKER, MAKER_TWO, T0, policy, stated
from tests.identity.test_matching import observation, profile

ACTOR = Reviewer("person:reviewer", "human", True, frozenset({"workflow", "factual"}))


def request(
    item,
    selected,
    *,
    name="fixture-decision",
    outcome="accept",
    predecessors=(),
    at=T0 + timedelta(hours=1),
):
    return Request(
        request_id=name,
        target=item.target,
        queue=item.choice(selected),
        outcome=outcome,
        performed_at=at,
        reason="Compared fixture evidence",
        evidence="review:fixture",
        predecessors=predecessors,
    )


def prepare(connection, tmp_path):
    rebuild(connection, data_dir=tmp_path)
    return ContractResolver.registered(registered_contracts()), evidence_tables()


def test_fact_queue_idempotency_rejection_revocation_and_orphans(
    rebuild_connection: Connection, tmp_path: Path
):
    connection = rebuild_connection
    resolver, tables = prepare(connection, tmp_path)
    claims = [stated(MAKER, "1250"), stated(MAKER_TWO, "1300")]
    record(connection, claims)
    subject = Subject.of(claims[0])
    write(connection, fact_history(subject, claims, policy(), CONTEXT))
    item = next(iter(items(connection, resolver, IdentityJournal(tmp_path)).values()))
    review = request(item, claims[0].key)
    first = submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        review,
        lambda: ACTOR,
        lambda: review.performed_at,
    )
    assert (
        submit(
            connection,
            tmp_path,
            "fixture",
            resolver,
            review,
            lambda: ACTOR,
            lambda: T0 + timedelta(days=1),
        )
        == first
    )
    assert len(Journal(tmp_path, "fixture").read()) == 1
    reviews = accepted_reviews(applied(connection))
    assert reviews.selected == {claims[0].key: first.recorded_at}
    selected = fact_history(
        subject, claims, policy(), Context(ranks=CONTEXT.ranks, reviews=reviews)
    )
    assert selected[-1].fact.claim_key == claims[0].key
    write(connection, selected)
    reject = request(
        item,
        claims[0].key,
        name="reject",
        outcome="reject",
        predecessors=(first.decision_id,),
        at=T0 + timedelta(hours=2),
    )
    rejected = submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        reject,
        lambda: ACTOR,
        lambda: reject.performed_at,
    )
    assert accepted_reviews(applied(connection)).rejected == {claims[0].key: rejected.recorded_at}
    revoke = request(
        item,
        claims[0].key,
        name="revoke",
        outcome="revoke",
        predecessors=(rejected.decision_id,),
        at=T0 + timedelta(hours=3),
    )
    submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        revoke,
        lambda: ACTOR,
        lambda: revoke.performed_at,
    )
    assert accepted_reviews(applied(connection)).selected == {}
    assert accepted_reviews(applied(connection)).rejected == {}
    assert all(row["state"] == "applied" for row in reattach(connection, tmp_path, resolver))
    connection.execute(tables["selection_outcomes"].delete())
    connection.execute(tables["canonical_facts"].delete())
    connection.execute(tables["claims"].delete())
    assert {row["state"] for row in reattach(connection, tmp_path, resolver)} == {"orphan"}


def test_accepted_identity_match_records_link_keys_attributes_and_replays(
    rebuild_connection: Connection, tmp_path: Path
):
    connection = rebuild_connection
    resolver, _ = prepare(connection, tmp_path)
    identity = IdentityJournal(tmp_path)
    config = profile()
    first = ingest(
        connection,
        identity,
        config,
        observation(
            {"organization.name": "Fixture Company", "organization.domain": "fixture.example"},
            source="fixture:known",
        ),
        actor="engine",
        evidence="archive:fixture",
    )
    incoming = observation(
        {"organization.name": "Fixture Company"}, source="fixture:new", lei="00000000000000000042"
    )
    pending = ingest(
        connection, identity, config, incoming, actor="engine", evidence="archive:fixture"
    )
    assert pending.match.decision == "review"
    item = next(
        item
        for item in items(connection, resolver, identity).values()
        if item.details.get("match_id") == pending.match_id
    )
    review = request(item, first.kn_id)
    accepted = submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        review,
        lambda: ACTOR,
        lambda: review.performed_at,
    )
    state = identity.state()
    assert any(
        h.kn_id == first.kn_id and h.ended_event is None for h in state.links(incoming.record)
    )
    payloads = [
        e.payload for e in state.events if e.decision_ref == "queue-review:" + accepted.decision_id
    ]
    assert any(isinstance(p, Link) and p.method == "review_decision" for p in payloads)
    assert any(
        isinstance(p, Identifier) and p.value == incoming.authoritative[0].value for p in payloads
    )
    assert any(isinstance(p, Attribute) and p.record == incoming.record for p in payloads)
    before = identity.read()
    assert (
        submit(
            connection,
            tmp_path,
            "fixture",
            resolver,
            review,
            lambda: ACTOR,
            lambda: review.performed_at,
        )
        == accepted
    )
    assert identity.read() == before
    from kn.identity import store as identity_store

    identity_store.replay(connection, identity)
    assert accepted.decision_id in {e.decision_id for e in applied(connection)}
