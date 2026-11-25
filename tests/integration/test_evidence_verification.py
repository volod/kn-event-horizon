"""Stored claims are human verification targets; a changed version inherits nothing."""

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
import sqlalchemy as sa

from kn.contracts.sqlalchemy import metadata
from kn.evidence.store import evidence_contract, record
from kn.evidence.verification import target
from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Request, Stamp
from kn.review.targets import ContractResolver, declared_coverage
from tests.evidence.fixtures import changed_mass, claim
from tests.integration.harness import IntegrationDatabase, ScratchSchemas
from tests.review.test_protocol import NOW, reviewer


@pytest.fixture
def verification_db(
    integration_database: IntegrationDatabase,
    scratch_schemas: ScratchSchemas,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[sa.Engine, dict[str, sa.Table], ContractResolver]]:
    contract = replace(evidence_contract(), schema=scratch_schemas.schema("evidence_claims"))
    model = metadata(contract)
    decisions = store.decision_table().to_metadata(
        sa.MetaData(), schema=scratch_schemas.schema("evidence_decisions")
    )
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    with engine.begin() as connection:
        model.create_all(connection)
        decisions.create(connection)
    monkeypatch.setattr(store, "decision_table", lambda: decisions)
    resolver = ContractResolver([contract], declared_coverage(contract))
    tables = {table.name: table for table in model.tables.values()}
    try:
        yield engine, tables, resolver
    finally:
        with engine.begin() as connection:
            decisions.drop(connection)
            model.drop_all(connection)
        engine.dispose()


def test_a_changed_claim_and_an_imported_label_carry_no_human_stamp(
    verification_db: tuple[sa.Engine, dict[str, sa.Table], ContractResolver], tmp_path: Path
) -> None:
    engine, tables, resolver = verification_db
    original = claim()
    changed = changed_mass(original)
    imported = claim(source_verification_label="verified", field_id="space.spacecraft.dry_mass")
    journal = Journal(tmp_path)
    with engine.connect() as connection, connection.begin():
        record(connection, [original, changed, imported], tables)
        request = Request(
            request_id="mass-review",
            target=target(original),
            outcome="accept",
            performed_at=NOW,
            reason="Checked against the datasheet",
            evidence="review:fixture",
        )
        decision = store.submit(connection, journal, resolver, request, reviewer, lambda: NOW)
        accepted = store.projection(connection, target(original))
        assert accepted.stamp.human_verification_decision_id == decision.decision_id
        assert accepted.stamp.human_verified_at == NOW
        for unreviewed in (changed, imported):
            resolver.resolve(connection, target(unreviewed))
            assert store.projection(connection, target(unreviewed)).stamp == Stamp()


def test_a_target_that_does_not_match_the_stored_claim_is_stale(
    verification_db: tuple[sa.Engine, dict[str, sa.Table], ContractResolver],
) -> None:
    engine, tables, resolver = verification_db
    original = claim()
    with engine.connect() as connection, connection.begin():
        record(connection, [original], tables)
        connection.execute(
            tables["claims"]
            .update()
            .where(tables["claims"].c.claim_key == original.key)
            .values(source_verification_label="verified")
        )
        with pytest.raises(ValueError, match="stale"):
            resolver.resolve(connection, target(original))
