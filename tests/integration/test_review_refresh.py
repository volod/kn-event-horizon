"""Declared policies refresh canonical history from applied decisions, including revocation."""

from datetime import timedelta

import sqlalchemy as sa

from kn.contracts.model import Contract, Field, Table, canonical
from kn.evidence.projection import history, write
from kn.evidence.ranking import Context
from kn.evidence.selection import Subject
from kn.evidence.store import record
from kn.identity import store as identity_store
from kn.identity.events import event
from kn.identity.journal import Journal
from kn.identity.model import Mint, SourceKey
from kn.review.facts import refresh
from kn.review.queue import items
from kn.review.queue_store import submit
from tests.evidence.selection_fixtures import MASS, PART, POLICY, T0, policy, stated
from tests.integration.test_review_queue import ACTOR, prepare, request


def test_acceptance_and_revocation_refresh_the_declared_policy(rebuild_connection, tmp_path):
    connection = rebuild_connection
    resolver, tables = prepare(connection, tmp_path)
    identity = Journal(tmp_path)
    identity.append(
        event(
            Mint(
                kn_id=PART, entity_class="fixture.part", anchor=SourceKey(source="fixture", key="1")
            ),
            previous=None,
            occurred_at=T0,
            actor="engine:fixture",
            reason="Fixture identity",
            evidence="archive:fixture",
        )
    )
    identity_store.replay(connection, identity)
    claims = [stated("fixture:first", "1250"), stated("fixture:second", "1300")]
    record(connection, claims)
    write(connection, history(Subject.of(claims[0]), claims, policy(), Context()))
    fixture = Contract(
        contract_id="fixture.policy",
        version="1.0.0",
        digest="a" * 64,
        schema="fixture",
        source_profile="fixture",
        tables=(
            Table(
                name="part",
                csv=False,
                fields=(
                    Field(
                        name="mass",
                        field_id=MASS,
                        logical_type="number",
                        required=False,
                        primary_key=False,
                        extensions_json=canonical({"updatePolicy": POLICY}),
                    ),
                ),
            ),
        ),
    )
    item = next(iter(items(connection, resolver, identity).values()))
    accepted = request(item, claims[0].key)
    first = submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        accepted,
        lambda: ACTOR,
        lambda: accepted.performed_at,
    )
    refresh(connection, identity, [fixture])
    facts = tables["canonical_facts"]
    current = (
        connection.execute(sa.select(facts).where(facts.c.knowledge_to.is_(None))).mappings().one()
    )
    assert current["claim_key"] == claims[0].key
    assert current["verification_state"] == "verified"
    revoked = request(
        item,
        claims[0].key,
        name="revoke",
        outcome="revoke",
        predecessors=(first.decision_id,),
        at=T0 + timedelta(hours=2),
    )
    submit(
        connection,
        tmp_path,
        "fixture",
        resolver,
        revoked,
        lambda: ACTOR,
        lambda: revoked.performed_at,
    )
    refresh(connection, identity, [fixture])
    current = (
        connection.execute(sa.select(facts).where(facts.c.knowledge_to.is_(None))).mappings().one()
    )
    assert current["claim_key"] is None and current["verification_state"] == "disputed"
    assert connection.scalar(sa.select(sa.func.count()).select_from(facts)) == 3
    refresh(connection, identity, [fixture])
    assert connection.scalar(sa.select(sa.func.count()).select_from(facts)) == 3
