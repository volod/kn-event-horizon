"""Execute the normal run and replay commands against WARC and PostgreSQL."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
import sqlalchemy as sa

from kn.cli import main
from kn.engine import runner
from kn.engine.state import ATTEMPTS, BATCHES, CHECKPOINTS, ERRORS, state_table
from kn.evidence.store import evidence_tables
from kn.evidence.text import display
from kn.identity.events import Event
from kn.identity.journal import LockedJournal
from kn.identity.model import Match
from kn.sources.catalogue import catalogue_table
from tests.engine.conftest import SOURCE, ProfileFile, Site, build_database


def invoke(profile: ProfileFile, caplog: pytest.LogCaptureFixture, *replay: str, exit_code=0):
    caplog.set_level(logging.INFO, logger="kn.operator")
    action = "replay" if replay else "run"
    assert main(["--json", "source", action, str(profile.path), *replay]) == exit_code
    return json.loads(caplog.records[-1].message)


def rows(engine: sa.Engine, table: sa.Table, *order: str) -> list[dict]:
    with engine.connect() as connection:
        query = sa.select(table).order_by(*(table.c[name] for name in order))
        return [dict(row) for row in connection.execute(query).mappings()]


def test_admission_issues_no_requests(
    engine: sa.Engine, site: Site, profile: ProfileFile, caplog: pytest.LogCaptureFixture
) -> None:
    with engine.begin() as connection:
        connection.execute(
            catalogue_table()
            .update()
            .where(catalogue_table().c.source_id == SOURCE)
            .values(lifecycle_state="candidate")
        )
    assert invoke(profile, caplog, exit_code=1)["error"]["rule"] == "catalogueState"
    with engine.begin() as connection:
        connection.execute(
            catalogue_table()
            .update()
            .where(catalogue_table().c.source_id == SOURCE)
            .values(lifecycle_state="enabled")
        )
    del profile.config["rights"]["permission"]
    profile.save()
    invalid = invoke(profile, caplog, exit_code=1)["error"]
    assert (invalid["path"], invalid["rule"]) == ("$/rights/permission", "required")
    assert site.requests == 0
    assert rows(engine, state_table(ATTEMPTS)) == []


def test_snapshot_is_idempotent_and_offline_replay_restores_claims(
    engine: sa.Engine,
    site: Site,
    profile: ProfileFile,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = invoke(profile, caplog)
    assert (first["status"], first["record_count"], first["claim_count"]) == ("success", 3, 3)
    assert (first["checkpoint_revision"], first["requests_used"]) == (1, 1)
    captures = runner.Archive.configured().verify()
    assert captures == {"batches": 1, "captures": 1, "tombstones": 0, "status": "verified"}
    tables = evidence_tables()
    claims = rows(engine, tables["claims"], "claim_key")
    evidence = rows(engine, tables["evidence_records"], "evidence_id")
    assert len(claims) == len(evidence) == 3
    assert rows(engine, tables["text_translations"]) == []
    assert_original_text(claims, evidence)
    same = invoke(profile, caplog)
    assert (same["status"], same["checkpoint_revision"], same["claim_count"]) == (
        "not_modified",
        1,
        0,
    )
    assert rows(engine, tables["claims"], "claim_key") == claims
    assert len(rows(engine, state_table(BATCHES))) == 1
    with engine.connect() as connection:
        events = connection.exec_driver_sql(
            "SELECT count(*) FROM identity.lifecycle_events"
        ).scalar_one()
        assert events == 15

    site_requests = site.requests
    monkeypatch.setattr("kn.engine.captures.HTTPSConnection", forbid_network)
    archive_args = ("--archive-run-id", first["run_id"])
    assert invoke(profile, caplog, *archive_args)["status"] == "skipped"
    build_database(engine, tmp_path)
    replayed = invoke(profile, caplog, *archive_args)
    assert (replayed["status"], replayed["requests_used"], replayed["bytes_received"]) == (
        "success",
        0,
        0,
    )
    assert rows(engine, tables["claims"], "claim_key") == claims
    assert rows(engine, tables["evidence_records"], "evidence_id") == evidence
    assert site.requests == site_requests == 2


def forbid_network(*args: object, **kwargs: object) -> None:
    pytest.fail("replay must not construct a network connection")


def assert_original_text(claims: list[dict], evidence: list[dict]) -> None:
    expected = {
        "ru": "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a",
        "zh": "\u6570\u636e\u6e90",
        "und": "\u2605",
    }
    assert {row["value_language"]: row["value_text"] for row in claims} == expected
    assert len({row["kn_id"] for row in claims}) == 3
    for claim in claims:
        expected_text = expected[claim["value_language"]]
        assert claim["original_value"] == expected_text
        linked = next(row for row in evidence if row["evidence_id"] == claim["evidence_id"])
        assert linked["archive_record_id"].startswith("urn:uuid:")
        assert linked["origin_uri"].endswith("/snapshot")
        assert linked["locator"].startswith("/records/")
        for locale in ("en", "uk"):
            selected = display(claim, (), locale)
            assert selected.is_original and selected.fallback
            assert (selected.variant.text, selected.variant.language) == (
                expected_text,
                claim["value_language"],
            )
            assert selected.variant.provenance.endswith(claim["claim_key"])


@pytest.mark.parametrize("interrupt", ["before_capture", "during_identity", "before_commit"])
def test_resume_reuses_the_run_and_its_committed_checkpoint(
    engine: sa.Engine,
    site: Site,
    profile: ProfileFile,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: str,
) -> None:
    first = invoke(profile, caplog)
    site.body = site.body.replace(b"zh-01", b"zh-02")
    with monkeypatch.context() as patch:
        if interrupt == "during_identity":
            patch.setattr(LockedJournal, "append_batch", interrupt_mint(LockedJournal.append_batch))
        else:
            function = "archived_snapshot" if interrupt == "before_capture" else "finish"
            patch.setattr(runner, function, interrupt_run)
        with pytest.raises(KeyboardInterrupt):
            invoke(profile, caplog)
    attempts = rows(engine, state_table(ATTEMPTS), "started_at")
    pending = attempts[-1]
    assert pending["status"] is None and pending["attempt"] == 1
    assert pending["run_id"] != first["run_id"]
    assert len(rows(engine, state_table(CHECKPOINTS))) == 1
    assert len(rows(engine, state_table(BATCHES))) == 1
    assert len(rows(engine, evidence_tables()["claims"])) == 3

    count = site.requests
    other = invoke(profile, caplog, "--archive-run-id", first["run_id"], exit_code=1)
    assert other["error"]["rule"] == "interruptedRun"
    profile.config["monitoring"]["freshness_sla_seconds"] += 1
    profile.save()
    assert invoke(profile, caplog, exit_code=1)["error"]["rule"] == "interruptedVersion"
    profile.config["monitoring"]["freshness_sla_seconds"] -= 1
    profile.save()
    assert site.requests == count
    resumed = invoke(profile, caplog)
    assert resumed["status"] == "success"
    assert resumed["run_id"] == pending["run_id"] and resumed["attempt"] == 2
    assert resumed["checkpoint_revision"] == 2 and resumed["claim_count"] == 1
    expected_requests = int(interrupt == "before_capture")
    assert site.requests == count + expected_requests == 2
    assert resumed["requests_used"] == expected_requests
    batches = rows(engine, state_table(BATCHES), "loaded_at")
    assert len(batches) == 2 and batches[-1]["archive_run_id"] == resumed["run_id"]
    assert len(rows(engine, evidence_tables()["claims"])) == 4


def interrupt_mint(append):
    def interrupted(locked: LockedJournal, values: tuple[Event, ...]) -> None:
        if values and isinstance(match := values[0].payload, Match) and match.decision == "mint":
            append(locked, values[:1])
            raise KeyboardInterrupt
        append(locked, values)

    return interrupted


def interrupt_run(*args: object, **kwargs: object) -> None:
    raise KeyboardInterrupt


@pytest.mark.parametrize(
    ("body", "code"),
    [(b"{", "payload_invalid"), (b'{"records":[{"unknown":true}]}', "schema_drift")],
)
def test_bad_response_is_archived_without_advancing(
    engine: sa.Engine,
    site: Site,
    profile: ProfileFile,
    caplog: pytest.LogCaptureFixture,
    body: bytes,
    code: str,
) -> None:
    site.body = body
    result = invoke(profile, caplog, exit_code=1)
    assert (result["status"], result["error_code"], result["checkpoint_revision"]) == (
        "failed",
        code,
        0,
    )
    assert rows(engine, state_table(CHECKPOINTS)) == []
    assert rows(engine, state_table(BATCHES)) == []
    assert rows(engine, evidence_tables()["claims"]) == []
    assert rows(engine, state_table(ERRORS))[0]["error_code"] == code
    assert runner.Archive.configured().verify()["captures"] == 1


def test_concurrent_runs_share_one_checkpoint(
    engine: sa.Engine, site: Site, profile: ProfileFile, tmp_path: Path
) -> None:
    start = Barrier(2)

    def run() -> dict[str, object]:
        start.wait(timeout=5)
        return runner.source_operation(profile.path, tmp_path)

    with ThreadPoolExecutor(max_workers=2) as workers:
        reports = list(workers.map(lambda _: run(), range(2)))
    assert {report["status"] for report in reports} == {"success", "not_modified"}
    assert {report["checkpoint_revision"] for report in reports} == {1}
    assert len(rows(engine, state_table(BATCHES))) == 1
    assert len(rows(engine, evidence_tables()["claims"])) == 3
    assert site.requests == 2
