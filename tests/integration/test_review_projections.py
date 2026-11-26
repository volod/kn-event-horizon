"""Current review reads protect target scope and private decision details."""

from pathlib import Path

import sqlalchemy as sa

from kn.review import store
from kn.review.journal import Journal
from kn.review.model import Stamp
from kn.review.projection import ReadRights, read
from kn.review.targets import ContractResolver
from tests.integration.review_fixtures import OPEN
from tests.integration.review_support import LABEL, submit


def test_read_checks_row_field_reviewer_and_evidence_rights(
    review_database, tmp_path: Path
) -> None:
    engine, resolver, _, target = review_database
    dataset = resolver.dataset(target.contract_id, target.dataset)
    journal = Journal(tmp_path)
    with engine.begin() as connection:
        decision = submit(connection, journal, resolver, target)
        visible = read(connection, dataset, target.key, "factual", rights=OPEN)
        assert visible is not None
        assert visible.record == Stamp()
        assert visible.fields[LABEL].human_verification_decision_id == decision.decision_id
        for allowed in (
            lambda event: event.reviewer != decision.reviewer,
            lambda event: event.evidence != decision.evidence,
        ):
            result = read(
                connection, dataset, target.key, "factual", rights=ReadRights(OPEN.data, allowed)
            )
            assert result is not None and result.fields[LABEL] == result.record == Stamp()
        denied = ReadRights(lambda _, _row, field: field != LABEL, OPEN.decision)
        result = read(connection, dataset, target.key, "factual", rights=denied)
        assert result is not None and result.values == {"term_id": "001"}
        assert result.fields == {}
        denied = ReadRights(lambda _, _row, field: field is not None, OPEN.decision)
        assert read(connection, dataset, target.key, "factual", rights=denied) is None


def test_missing_target_stays_pending_and_replay_preserves_original_event(
    review_database, tmp_path: Path
) -> None:
    engine, resolver, table, target = review_database
    journal = Journal(tmp_path)
    with engine.connect() as connection:
        with connection.begin() as transaction:
            decision = submit(connection, journal, resolver, target)
            transaction.rollback()
        with connection.begin():
            connection.execute(table.delete())
            assert [entry.state for entry in store.replay(connection, journal, resolver)] == [
                "pending"
            ]
            assert [
                entry.state for entry in store.replay(connection, journal, resolver, complete=True)
            ] == ["orphan"]
            assert store.projection(connection, target).stamp == Stamp()
            connection.execute(table.insert().values(term_id="001", label="Edited"))
            assert [entry.state for entry in store.replay(connection, journal, resolver)] == [
                "stale"
            ]
            assert store.projection(connection, target).stamp == Stamp()
            connection.execute(sa.update(table).values(label="Original"))
            for _ in range(2):
                assert [entry.state for entry in store.replay(connection, journal, resolver)] == [
                    "applied"
                ]
            assert store.history(connection, (target.target_id,)) == {target.target_id: [decision]}
    assert journal.read() == (decision,)


def test_replay_reports_an_unregistered_dataset(review_database, tmp_path: Path) -> None:
    engine, resolver, _, target = review_database
    journal = Journal(tmp_path)
    with engine.begin() as connection:
        submit(connection, journal, resolver, target)
        assert [
            entry.state
            for entry in store.replay(connection, journal, ContractResolver((), ()), complete=True)
        ] == ["incompatible"]
