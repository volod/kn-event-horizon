"""PostgreSQL enforces the evidence contract; writes are idempotent and as-of views stable."""

import random
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.db.statements import SetConstraints
from kn.evidence.asof import claims_as_of, facts_as_of, relations_as_of
from kn.evidence.records import Record
from kn.evidence.relations import RelationAssertion
from kn.evidence.store import evidence_tables, record
from tests.evidence.fixtures import (
    OPERATOR,
    SPACECRAFT,
    T0,
    changed_mass,
    claim,
    evidence,
    fact,
    name_claim,
    one_of_each,
    undisclosed_claim,
)
from tests.integration.harness import IntegrationDatabase, ScratchSchemas

Tables = dict[str, sa.Table]


@pytest.fixture
def evidence_db(
    integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> Iterator[tuple[sa.Engine, Tables]]:
    tables = evidence_tables(scratch_schemas.schema("evidence_model"))
    model = next(iter(tables.values())).metadata
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    with engine.begin() as connection:
        model.create_all(connection)
    try:
        yield engine, tables
    finally:
        with engine.begin() as connection:
            model.drop_all(connection)
        engine.dispose()


def _check_references(connection: Connection, tables: Tables) -> None:
    names = tuple(
        sorted(str(key.name) for table in tables.values() for key in table.foreign_key_constraints)
    )
    schema = str(next(iter(tables.values())).schema)
    connection.execute(SetConstraints(schema, names, deferred=False))


def _rows(connection: Connection, table: sa.Table) -> list[dict[str, Any]]:
    query = sa.select(table).order_by(*table.primary_key.columns)
    return [dict(row) for row in connection.execute(query).mappings()]


@pytest.mark.parametrize(
    ("change", "constraint"),
    [
        ({"origin_uri": None}, "not-null"),
        ({"fetched_at": None}, "not-null"),
        ({"value_number": None}, "ck_claims_value_or_reason_presence"),
        ({"missing_reason": "not_found"}, "ck_claims_value_or_reason_presence"),
        ({"value_text": "x", "value_language": "en"}, "ck_claims_value_or_reason_presence"),
        ({"normalized_unit": None}, "ck_claims_unit_conversion_presence"),
        ({"valid_from_precision": None}, "ck_claims_valid_from_time_presence"),
        ({"evidence_class": "rumour"}, "ck_claims_evidence_class_enum"),
        ({"value_number": None, "value_date": "26-01"}, "ck_claims_value_date_precision"),
    ],
)
def test_the_database_rejects_claims_without_provenance_or_value_or_reason(
    evidence_db: tuple[sa.Engine, Tables], change: dict[str, Any], constraint: str
) -> None:
    engine, tables = evidence_db
    source = claim()
    with engine.connect() as connection, connection.begin():
        record(connection, [source.evidence], tables)
        with pytest.raises(sa.exc.IntegrityError) as error:
            connection.execute(tables["claims"].insert().values(**{**source.row(), **change}))
    if constraint != "not-null":
        assert constraint in str(error.value)


def test_every_reference_resolves_and_reinserting_a_key_is_a_no_op(
    evidence_db: tuple[sa.Engine, Tables],
) -> None:
    engine, tables = evidence_db
    rows = one_of_each()
    with engine.connect() as connection, connection.begin():
        added = record(connection, rows, tables)
        _check_references(connection, tables)
        before = {name: _rows(connection, table) for name, table in tables.items()}
        assert all(before.values())
        assert added == sum(len(items) for items in before.values())
        assert record(connection, rows, tables) == 0
        later = T0 + timedelta(days=90)
        rerun = claim(recorded_at=later, evidence=evidence(recorded_at=later))
        assert record(connection, [rerun], tables) == 0
        assert {name: _rows(connection, table) for name, table in tables.items()} == before
        claims, sources = tables["claims"], tables["evidence_records"]
        lookup = (
            sa.select(sources)
            .join_from(claims, sources, claims.c.evidence_id == sources.c.evidence_id)
            .where(claims.c.claim_key == rows[0].key)
        )
        found = connection.execute(lookup).mappings().one()
        expected = claim().evidence
        assert (found["locator_kind"], found["locator"]) == ("json_pointer", "/mass")
        assert (found["origin_uri"], found["fetched_at"]) == (expected.origin_uri, T0)
        assert (found["code_digest"], found["contract_digest"]) == (
            expected.code_digest,
            expected.contract_digest,
        )


def test_a_key_stored_with_other_content_fails_the_whole_batch(
    evidence_db: tuple[sa.Engine, Tables],
) -> None:
    engine, tables = evidence_db
    source = claim()
    with engine.connect() as connection, connection.begin():
        record(connection, [source], tables)
        connection.execute(
            tables["claims"]
            .update()
            .where(tables["claims"].c.claim_key == source.key)
            .values(original_value="tampered")
        )
        with pytest.raises(ValueError, match="different content"):
            record(connection, [name_claim(), source], tables)
        assert len(_rows(connection, tables["claims"])) == 1


def _history() -> list[Record]:
    first = claim()
    second = changed_mass(first)
    other = claim(
        source_id="space:other",
        record_id="e" * 64,
        evidence=evidence(source_id="space:other", origin_uri="https://example.net/s.csv"),
        valid_from=None,
    )
    first_fact = fact(first, knowledge_to=second.recorded_at)
    second_fact = fact(second, outcome="replaced", deciding_criterion="data_time")
    return [first, second, other, name_claim(), undisclosed_claim(), first_fact, second_fact]


VIEW_TIMES = [
    (T0 - timedelta(days=1), None),
    (T0 + timedelta(days=1), None),
    (T0 + timedelta(days=31), None),
    (None, None),
    (None, datetime(2025, 6, 1, tzinfo=UTC)),
    (T0 + timedelta(days=1), datetime(2025, 6, 1, tzinfo=UTC)),
    (None, datetime(2026, 3, 1, tzinfo=UTC)),
]


def _views(connection: Connection, tables: Tables) -> list[list[tuple[str, ...]]]:
    result = []
    for known, valid in VIEW_TIMES:
        claims = connection.execute(claims_as_of(tables["claims"], known, valid)).mappings()
        facts = connection.execute(facts_as_of(tables["canonical_facts"], known, valid)).mappings()
        result.append([row["claim_key"] for row in claims])
        result.append([row["fact_version_id"] for row in facts])
    return result


def _permuted_views(engine: sa.Engine, tables: Tables, rows: Sequence[Record]) -> list:
    with engine.connect() as connection, connection.begin() as transaction:
        record(connection, rows, tables)
        _check_references(connection, tables)
        views = _views(connection, tables)
        transaction.rollback()
    return views


def test_as_of_views_are_deterministic_and_half_open(evidence_db: tuple[sa.Engine, Tables]) -> None:
    engine, tables = evidence_db
    rows = _history()
    first, second, other, name, undisclosed, first_fact, second_fact = rows
    expected = _permuted_views(engine, tables, rows)
    for seed in range(3):
        shuffled = list(rows)
        random.Random(seed).shuffle(shuffled)
        assert _permuted_views(engine, tables, shuffled) == expected
    early = sorted([first, other, name, undisclosed], key=lambda item: (item.field_id, item.key))
    current = sorted([second, other, name, undisclosed], key=lambda item: (item.field_id, item.key))
    keys = [[item.key for item in group] for group in (early, current)]
    assert expected[0:2] == [[], []]
    assert expected[2:4] == [keys[0], [first_fact.key]]
    assert expected[4:6] == [keys[1], [second_fact.key]]
    assert expected[6:8] == [keys[1], [second_fact.key]]
    # Mid-2025 is before the second version's validity; its unknown-validity peers remain.
    assert expected[8] == [item.key for item in current if item is not second]
    assert expected[9] == []
    assert expected[10] == keys[0] and expected[11] == [first_fact.key]
    assert expected[12] == keys[1] and expected[13] == [second_fact.key]


def test_one_current_fact_version_and_no_active_duplicate_relation(
    evidence_db: tuple[sa.Engine, Tables],
) -> None:
    engine, tables = evidence_db
    first = claim()
    duplicate = fact(changed_mass(first), outcome="replaced", deciding_criterion="data_time")
    with engine.connect() as connection, connection.begin():
        record(connection, [first, changed_mass(first), fact(first)], tables)
        with pytest.raises(sa.exc.IntegrityError, match="facts_current_idx"):
            record(connection, [duplicate], tables)
    relation = RelationAssertion(
        subject_kn_id=OPERATOR,
        relation_type="space.operates",
        object_kn_id=SPACECRAFT,
        opened_by=first.key,
        opened_at=T0 + timedelta(days=1),
    )
    second_claim = name_claim()
    again = relation.model_copy(update={"opened_by": second_claim.key})
    with engine.connect() as connection, connection.begin():
        record(connection, [first, second_claim, relation], tables)
        with pytest.raises(sa.exc.IntegrityError, match="relations_active_idx"):
            record(connection, [again], tables)
        closing = T0 + timedelta(days=2)
        connection.execute(
            tables["relation_assertions"]
            .update()
            .where(tables["relation_assertions"].c.assertion_id == relation.key)
            .values(closed_at=closing, close_reason="retracted")
        )
        record(connection, [again.model_copy(update={"opened_at": closing})], tables)
        view = relations_as_of(tables["relation_assertions"], T0 + timedelta(days=1, hours=1))
        assert [row["assertion_id"] for row in connection.execute(view).mappings()] == [
            relation.key
        ]
        current = connection.execute(relations_as_of(tables["relation_assertions"])).mappings()
        assert [row["assertion_id"] for row in current] == [again.key]
        assert relation.relation_key == again.relation_key and relation.key != again.key
