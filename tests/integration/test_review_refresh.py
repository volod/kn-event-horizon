"""Declared policies refresh canonical history from applied decisions, including revocation."""

from datetime import timedelta
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import Contract, Field, Table, canonical
from kn.db.rebuild import rebuild
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
from kn.review.queue_replay import reattach
from kn.review.queue_store import submit
from tests.evidence.selection_fixtures import MASS, PART, POLICY, T0, policy, stated
from tests.integration.test_review_queue import ACTOR, prepare, request

PROJECTED = ("canonical_facts", "selection_outcomes", "review_items", "review_decisions")


def _identity(connection: Connection, data_dir: Path) -> Journal:
    identity = Journal(data_dir)
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
    return identity


def _contract() -> Contract:
    return Contract(
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


def _submit(connection, data_dir, resolver, review):
    return submit(
        connection,
        data_dir,
        "fixture",
        resolver,
        review,
        lambda: ACTOR,
        lambda: review.performed_at,
    )


def _current(connection, tables):
    facts = tables["canonical_facts"]
    query = sa.select(facts).where(facts.c.knowledge_to.is_(None))
    return connection.execute(query).mappings().one()


def test_acceptance_and_revocation_refresh_the_declared_policy(rebuild_connection, tmp_path):
    connection = rebuild_connection
    resolver, tables = prepare(connection, tmp_path)
    identity = _identity(connection, tmp_path)
    claims = [stated("fixture:first", "1250"), stated("fixture:second", "1300")]
    record(connection, claims)
    write(connection, history(Subject.of(claims[0]), claims, policy(), Context()))
    fixture = _contract()
    item = next(iter(items(connection, resolver, identity).values()))
    first = _submit(connection, tmp_path, resolver, request(item, claims[0].key))
    refresh(connection, identity, [fixture])
    current = _current(connection, tables)
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
    _submit(connection, tmp_path, resolver, revoked)
    refresh(connection, identity, [fixture])
    current = _current(connection, tables)
    assert current["claim_key"] is None and current["verification_state"] == "disputed"
    facts = tables["canonical_facts"]
    assert connection.scalar(sa.select(sa.func.count()).select_from(facts)) == 3
    refresh(connection, identity, [fixture])
    assert connection.scalar(sa.select(sa.func.count()).select_from(facts)) == 3


def _projected(connection, tables) -> dict[str, list[tuple[object, ...]]]:
    """Every projected row except the time KN first wrote it."""
    result = {}
    for name in PROJECTED:
        table = tables[name]
        columns = [column for column in table.c if column.name != "recorded_at"]
        if name == "review_decisions":
            columns = list(table.c)
        rows = connection.execute(sa.select(*columns)).all()
        result[name] = sorted(tuple(row) for row in rows)
    return result


def test_review_decisions_reproduce_canonical_facts_after_two_rebuilds(
    rebuild_connection, tmp_path
):
    connection = rebuild_connection
    resolver, tables = prepare(connection, tmp_path)
    identity = _identity(connection, tmp_path)
    claims = [stated("fixture:first", "1250"), stated("fixture:second", "1300")]
    subject = Subject.of(claims[0])
    baseline = history(subject, claims, policy(), Context())
    record(connection, claims)
    write(connection, baseline)
    fixture = _contract()
    item = next(iter(items(connection, resolver, identity).values()))
    _submit(connection, tmp_path, resolver, request(item, claims[0].key))
    refresh(connection, identity, [fixture])
    before = _projected(connection, tables)
    assert _current(connection, tables)["verification_state"] == "verified"
    for _ in range(2):
        from tests.integration.test_evidence import _check_references

        _check_references(connection, tables)
        rebuild(connection, data_dir=tmp_path)
        record(connection, claims)
        write(connection, baseline)
        assert [entry["state"] for entry in reattach(connection, tmp_path, resolver)] == ["applied"]
        refresh(connection, Journal(tmp_path), [fixture])
        assert _projected(connection, tables) == before
