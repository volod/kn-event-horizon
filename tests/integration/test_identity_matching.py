"""Normal matching entry point through PostgreSQL and rebuild."""

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.sqlalchemy import metadata
from kn.db.rebuild import rebuild
from kn.identity import store
from kn.identity.journal import Journal
from kn.identity.matching.ingest import submit
from kn.identity.matching.observe import Observation
from kn.identity.matching.scoring import verify_match
from kn.identity.model import Candidate
from tests.identity.test_matching import calibrated, observation, profile
from tests.integration.test_model_baseline import _snapshot


def test_matching_projects_receipts_and_recovers_after_database_rollback(
    rebuild_connection: Connection, tmp_path: Path
) -> None:
    connection = rebuild_connection
    journal = Journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    config = calibrated(profile())
    attrs = {
        "organization.name": "Fixture Systems Ltd",
        "organization.domain": "https://sales.example.com/path",
        "organization.country": "GB",
    }
    first = observation(attrs)
    with pytest.raises(RuntimeError, match="interrupted"), connection.begin_nested():
        original = submit(connection, journal, config, first, actor="engine:fixture", evidence="a")
        raise RuntimeError("interrupted")
    tables = metadata(store.contract()).tables
    matches = tables["identity.matches"]
    assert connection.scalar(sa.select(sa.func.count()).select_from(matches)) == 0

    def ingest(incoming: Observation):
        return submit(connection, journal, config, incoming, actor="engine:fixture", evidence="a")

    assert ingest(first) == original
    scored = ingest(observation(attrs, source="fixture:second"))
    assert scored.kn_id == original.kn_id
    assert scored.match.trace.route == "scored_match"
    review = ingest(
        observation({"organization.name": "Fixture Systems Inc"}, source="fixture:third")
    )
    assert review.kn_id is None
    assert review.match.decision == "review"

    stored = (
        connection.execute(sa.select(matches).where(matches.c.match_id == scored.match_id))
        .mappings()
        .one()
    )
    candidate = Candidate.model_validate(json.loads(stored["candidates_json"])[0])
    assert candidate == scored.match.candidates[0]
    verify_match(config, journal.state().matches[scored.match_id])
    before = _snapshot(connection, [store.contract()])
    connection.exec_driver_sql("DROP SCHEMA identity CASCADE")
    rebuild(connection, data_dir=tmp_path)
    assert _snapshot(connection, [store.contract()]) == before
