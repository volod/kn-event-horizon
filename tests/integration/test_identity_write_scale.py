"""Measure the normal PostgreSQL submit path after a bulk journal replay."""

from pathlib import Path
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy.engine import Connection

from kn.contracts.model import canonical
from kn.db.rebuild import rebuild
from kn.identity.events import Event
from kn.identity.journal import Journal
from kn.identity.matching.ingest import submit
from kn.identity.matching.observe import Key, Observation, Reading
from kn.identity.model import SourceKey
from tests.identity.fixtures import NOW
from tests.identity.test_matching import profile
from tests.identity.test_replay_scale import _next, _payloads

SIZES = (5_000, 50_000)
SAMPLES = 5
MAX_RATIO = 2


@pytest.mark.heavy
def test_postgresql_submit_cost_stays_flat(rebuild_connection: Connection, tmp_path: Path) -> None:
    connection = rebuild_connection
    config = profile()
    journal = Journal(tmp_path)
    rebuild(connection, data_dir=tmp_path)
    journal.path.parent.mkdir(exist_ok=True)
    timings = []
    for size in SIZES:
        # Each point starts with precisely the requested number of objects. Preload using
        # the normal rebuild path so the baseline can be run without 50,000 quadratic writes.
        previous: Event | None = None
        connection.exec_driver_sql("DROP SCHEMA identity CASCADE")
        with journal.path.open("w", encoding="ascii") as stream:
            for number in range(1, size + 1):
                for payload in _payloads(number):
                    previous = _next(previous, payload)
                    stream.write(canonical(previous.model_dump(mode="json")) + "\n")
        rebuild(connection, data_dir=journal.data_dir)
        samples = []
        cold = 0.0
        for sample in range(SAMPLES + 1):
            number = size + sample + 1
            incoming = Observation(
                record=SourceKey(source="fixture:submit", key=str(number)),
                version="1",
                observed_at=NOW,
                authoritative=(Key(namespace="lei", issuer="fixture:lei", value=f"{number:020d}"),),
                attributes=(Reading(field_id="organization.name", value=f"Fixture {number}"),),
            )
            start = perf_counter()
            receipt = submit(
                connection,
                journal,
                config,
                incoming,
                actor="engine:fixture",
                evidence="archive:fixture",
            )
            elapsed = perf_counter() - start
            assert receipt.match.decision == "mint"
            if sample:
                samples.append(elapsed)
            else:
                cold = elapsed
        timings.append(median(samples))
        print(
            f"{size} objects: cold {cold:.6f}s, warm median {timings[-1]:.6f}s, samples {samples}",
            flush=True,
        )
    ratio = timings[1] / timings[0]
    print(f"50,000/5,000 submit ratio: {ratio:.3f}", flush=True)
    assert ratio <= MAX_RATIO
