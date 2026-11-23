"""The semantic contract stores exact values and enforces keys, enums and deferred FKs."""

from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from kn.contracts.sqlalchemy import metadata
from kn.semantic import validate_model
from kn.semantic.structure import semantic_contract
from tests.integration.harness import IntegrationDatabase, ScratchSchemas
from tests.integration.semantic_fixtures import native_rows, text_fixture
from tests.semantic.conftest import REFERENCES


def test_semantic_round_trip_and_database_constraints(
    integration_database: IntegrationDatabase, scratch_schemas: ScratchSchemas
) -> None:
    schema = scratch_schemas.schema("semantic")
    contract = semantic_contract()
    model = metadata(contract, schema)
    snapshot = text_fixture()
    validate_model(snapshot, REFERENCES)
    native = native_rows(contract, snapshot)
    engine = sa.create_engine("postgresql+psycopg://", creator=integration_database.connect)
    try:
        with engine.connect() as connection, connection.begin():
            model.create_all(connection)
            # Reverse table order proves that deferred references permit unordered input.
            for definition in reversed(contract.tables):
                table = model.tables[f"{schema}.{definition.name}"]
                connection.execute(table.insert(), native[definition.name])
            connection.exec_driver_sql("SET CONSTRAINTS ALL IMMEDIATE")
            criteria = model.tables[f"{schema}.rubric_criteria"]
            assert connection.scalar(sa.select(criteria.c.weight)) == Decimal("1.25")
            terms = model.tables[f"{schema}.terms"]
            assert (
                connection.scalar(
                    sa.select(terms.c.definition).where(terms.c.id == "space.demo.001")
                )
                is None
            )
            term_labels = model.tables[f"{schema}.labels"]
            assert (
                connection.scalar(
                    sa.select(term_labels.c.review_reference).where(
                        term_labels.c.locale == "uk", term_labels.c.term_id == "space.demo.001"
                    )
                )
                == "fixture:reviewed-translation"
            )
            assert (
                connection.scalar(sa.select(terms.c.code).where(terms.c.id == "space.demo.001"))
                == "001"
            )
            labels = model.tables[f"{schema}.namespace_labels"]
            assert (
                connection.scalar(sa.select(labels.c.label).where(labels.c.locale == "uk"))
                == "\u041f\u0440\u0438\u043a\u043b\u0430\u0434"
            )
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(terms.insert().values(**snapshot["terms"][0]))
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    terms.update().where(terms.c.id == "space.demo.001").values(status="unknown")
                )
            concepts = model.tables[f"{schema}.concepts"]
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    concepts.update()
                    .where(concepts.c.id == "space.demo.001")
                    .values(parent_id="space.demo.unknown")
                )
    finally:
        engine.dispose()
