"""Representative review fixtures for the combined model checkpoint."""

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Decision, Request, Stamp, Target
from kn.review.projection import ReadRights, read
from kn.review.protocol import Reviewer
from kn.review.targets import ContractResolver, Dataset, Row

INSTANT = datetime(2026, 1, 2, 12, tzinfo=UTC)
REVIEWER = Reviewer("person:fixture-reviewer", "human", True, frozenset({"factual", "integrity"}))
OPEN = ReadRights(lambda *_: True, lambda _: True)
SEMANTIC = "kn.core.semantic"
SATCOM = "kn.space.satcom"
TERMINAL = "TRM-OW-GOSHAWK-U8"


def first(connection: Connection, dataset: Dataset, **where: object) -> Row:
    table = dataset.table
    query = sa.select(table).filter_by(**where).order_by(*table.primary_key.columns).limit(1)
    return dict(connection.execute(query).mappings().one())


def approve(
    connection: Connection, journal: Journal, resolver: ContractResolver, target: Target
) -> Decision:
    request = Request(
        request_id=f"baseline-{target.target_id}",
        target=target,
        outcome="accept",
        performed_at=INSTANT,
        reason="Fixture content checked",
        evidence="review:fixture",
    )
    return store.submit(connection, journal, resolver, request, lambda: REVIEWER, lambda: INSTANT)


def seed_reviews(
    connection: Connection, resolver: ContractResolver, data_dir: Path
) -> tuple[Decision, ...]:
    journal = Journal(data_dir)
    labels = resolver.dataset(SEMANTIC, "namespace_labels")
    mappings = resolver.dataset(SEMANTIC, "concept_mappings")
    terminals = resolver.dataset(SATCOM, "terminal_models")
    targets = (
        labels.target(
            first(connection, labels, locale="en"), "factual", "semantic.namespace_labels.label"
        ),
        mappings.target(first(connection, mappings), "factual"),
        terminals.target(
            first(connection, terminals, terminal_id=TERMINAL),
            "factual",
            "space.satcom.terminal_models.mass_antenna_kg",
        ),
    )
    decisions = tuple(approve(connection, journal, resolver, target) for target in targets)
    audit = resolver.dataset(store.DECISION_CONTRACT, "human_verification_decisions")
    audited = first(connection, audit, decision_id=decisions[-1].decision_id)
    bilingual = labels.target(
        first(connection, labels, namespace_id="space.demo", locale="en"),
        "factual",
        "semantic.namespace_labels.label",
    )
    return (
        *decisions,
        approve(connection, journal, resolver, audit.target(audited, "integrity")),
        approve(connection, journal, resolver, bilingual),
    )


def assert_stamps(
    connection: Connection, resolver: ContractResolver, decisions: Iterable[Decision]
) -> None:
    for decision in decisions:
        target = decision.target
        dataset = resolver.dataset(target.contract_id, target.dataset)
        result = read(connection, dataset, target.key, target.purpose, rights=OPEN)
        assert result is not None
        expected = Stamp(
            human_verified_at=INSTANT,
            human_verified_by=REVIEWER.principal,
            human_verification_decision_id=decision.decision_id,
        )
        assert result.record == (expected if target.field_id is None else Stamp())
        assert set(result.fields) == set(dataset.fields)
        assert result.fields == {
            field: expected if field == target.field_id else Stamp() for field in result.fields
        }


def assert_label_isolation(
    connection: Connection, resolver: ContractResolver, decision: Decision
) -> None:
    target = decision.target
    dataset = resolver.dataset(target.contract_id, target.dataset)
    original = dataset.fetch(connection, target.key)
    assert original is not None
    ukrainian = first(connection, dataset, namespace_id=original["namespace_id"], locale="uk")
    result = read(connection, dataset, dataset.key(ukrainian), "factual", rights=OPEN)
    assert result is not None and all(stamp == Stamp() for stamp in result.fields.values())
    connection.execute(
        dataset.table.update()
        .where(
            dataset.table.c.namespace_id == original["namespace_id"],
            dataset.table.c.locale == "en",
        )
        .values(label="Edited fixture label")
    )
    result = read(connection, dataset, target.key, "factual", rights=OPEN)
    assert result is not None and all(stamp == Stamp() for stamp in result.fields.values())
    assert store.projection(connection, target).stamp.human_verification_decision_id == (
        decision.decision_id
    )


def assert_audit_rights(
    connection: Connection, resolver: ContractResolver, reviewed: Decision
) -> None:
    dataset = resolver.dataset(store.DECISION_CONTRACT, "human_verification_decisions")
    row = first(connection, dataset, decision_id=reviewed.decision_id)
    rights = ReadRights(OPEN.data, lambda event: event.decision_id != reviewed.decision_id)
    assert read(connection, dataset, dataset.key(row), "integrity", rights=rights) is None
