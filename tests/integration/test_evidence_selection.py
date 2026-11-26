"""PostgreSQL stores selected fact versions once, closes replaced ones and refuses drift."""

from datetime import timedelta

import pytest
import sqlalchemy as sa

from kn.evidence.asof import facts_as_of
from kn.evidence.model import Claim
from kn.evidence.projection import history, write
from kn.evidence.selection import Subject
from kn.evidence.store import record
from tests.evidence.selection_fixtures import (
    CONTEXT,
    DISTRIBUTOR,
    MAKER,
    T0,
    emptied,
    policy,
    stated,
)
from tests.integration.test_evidence import Tables, _check_references, _rows
from tests.integration.test_evidence import evidence_db as evidence_db

HOUR = timedelta(hours=1)


def _claims() -> list[Claim]:
    channel = stated(DISTRIBUTOR, "1300", at=T0)
    maker = stated(MAKER, "1250", at=T0 + HOUR)
    return [channel, maker, emptied(maker, T0 + 2 * HOUR)]


def test_versions_are_written_once_and_replaced_ones_are_closed(
    evidence_db: tuple[sa.Engine, Tables],
) -> None:
    engine, tables = evidence_db
    claims = _claims()
    subject = Subject.of(claims[0])
    early = history(subject, claims[:1], policy(), CONTEXT)
    full = history(subject, claims, policy(), CONTEXT)
    with engine.begin() as connection:
        record(connection, claims, tables)
        assert write(connection, early, tables) > 0
        added = write(connection, full, tables)
        assert added > 0 and write(connection, full, tables) == 0
        _check_references(connection, tables)
        facts = tables["canonical_facts"]
        current = connection.execute(facts_as_of(facts)).mappings().all()
        assert [row["fact_version_id"] for row in current] == [full[-1].fact.key]
        assert current[0]["claim_key"] == claims[1].key
        assert current[0]["review_item_id"] is not None
        earlier = connection.execute(facts_as_of(facts, T0 + HOUR / 2)).mappings().one()
        assert earlier["claim_key"] == claims[0].key
        assert earlier["knowledge_to"] == T0 + HOUR
        outcomes = _rows(connection, tables["selection_outcomes"])
        assert {row["claim_key"] for row in outcomes} == {claim.key for claim in claims}
        items = _rows(connection, tables["review_items"])
        assert [row["kind"] for row in items] == ["empty_claim"]


def test_a_stored_history_that_differs_from_the_projection_is_refused(
    evidence_db: tuple[sa.Engine, Tables],
) -> None:
    engine, tables = evidence_db
    claims = _claims()
    subject = Subject.of(claims[0])
    with engine.begin() as connection:
        record(connection, claims, tables)
        write(connection, history(subject, claims, policy(), CONTEXT), tables)
        changed = history(subject, claims, policy(emptyValueHandling="allow_clear"), CONTEXT)
        with pytest.raises(ValueError, match="differ from the projection"):
            write(connection, changed, tables)
        facts = tables["canonical_facts"]
        current = connection.execute(facts_as_of(facts)).mappings().one()
        assert current["unresolved_reason"] is None
