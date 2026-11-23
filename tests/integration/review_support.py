"""Scratch-schema fixtures and shared submissions for PostgreSQL review tests."""

from collections.abc import Iterator
from dataclasses import replace

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata
from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Request, Target
from kn.review.targets import ContractResolver, Coverage, content_version
from tests.contracts.test_registry import FIXTURES
from tests.integration.harness import IntegrationDatabase, ScratchSchemas
from tests.review.test_protocol import NOW, reviewer

ID = "fixture.terms.fixture_terms.term_id"
LABEL = "fixture.terms.fixture_terms.label"


@pytest.fixture
def review_database(
    integration_database: IntegrationDatabase,
    scratch_schemas: ScratchSchemas,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[sa.Engine, ContractResolver, sa.Table, Target]]:
    contract = replace(
        load_contract(FIXTURES / "semantic-terms.json"),
        schema=scratch_schemas.schema("review_targets"),
    )
    model = metadata(contract)
    row_table = model.tables[f"{contract.schema}.fixture_terms"]
    decisions = store.decision_table().to_metadata(
        sa.MetaData(), schema=scratch_schemas.schema("review_decisions")
    )
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    with engine.begin() as connection:
        model.create_all(connection)
        decisions.create(connection)
        connection.execute(row_table.insert().values(term_id="001", label="Original"))
    monkeypatch.setattr(store, "decision_table", lambda: decisions)
    resolver = ContractResolver(
        [contract],
        [Coverage(contract.contract_id, "fixture_terms", (ID, LABEL), {LABEL: (LABEL,)})],
    )
    target = Target.model_validate(
        {
            "contract_id": contract.contract_id,
            "dataset": "fixture_terms",
            "key": [{"field_id": ID, "kind": "string", "value": "001"}],
            "scope": "field",
            "field_id": LABEL,
            "version": content_version({LABEL: "Original"}),
            "purpose": "factual",
        }
    )
    try:
        yield engine, resolver, row_table, target
    finally:
        with engine.begin() as connection:
            decisions.drop(connection)
            model.drop_all(connection)
        engine.dispose()


def submit(
    connection: Connection,
    journal: Journal,
    resolver: ContractResolver,
    target: Target,
    request_id: str = "first",
    **changes,
):
    request = Request(
        request_id=request_id,
        target=target,
        outcome="accept",
        performed_at=NOW,
        reason="Checked",
        evidence="review:fixture",
        **changes,
    )
    return store.submit(connection, journal, resolver, request, reviewer, lambda: NOW)
