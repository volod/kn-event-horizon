"""Queue content binding, explicit revocation and deterministic selection inputs."""

from datetime import timedelta
from itertools import permutations
from pathlib import Path

import pytest

from kn.evidence.model import Claim
from kn.evidence.read import claim as read_claim
from kn.review.journal import Journal
from kn.review.model import Choice, Request
from kn.review.protocol import decide
from kn.review.queue_model import domain_name
from kn.review.selection import accepted_reviews, dispute_rates
from tests.evidence.fixtures import one_of_each
from tests.review.test_protocol import NOW, reviewer, target


def decision(outcome="accept", parents=(), at=NOW, **choice):
    return decide(
        Request(
            request_id=f"{outcome}-{at.isoformat()}",
            target=target(),
            outcome=outcome,
            performed_at=at,
            reason="Checked fixture",
            evidence="review:fixture",
            predecessors=parents,
            queue=Choice(
                item_id="a" * 64,
                kind="fact_conflict",
                candidates=("b" * 64, "c" * 64),
                selected=choice.get("selected", "b" * 64),
            ),
        ),
        reviewer(),
        at,
    )


def test_applied_reviews_preserve_history_and_revocation_for_every_replay_order():
    accepted = decision()
    revoked = decision("revoke", (accepted.decision_id,), NOW + timedelta(hours=1))
    for events in permutations((accepted, revoked)):
        result = accepted_reviews(events)
        assert result.selected == {}
        assert result.at(NOW).selected == {"b" * 64: NOW}
        assert result.at(revoked.recorded_at).selected == {}
        assert result.times() == {NOW, revoked.recorded_at}


def test_independent_decisions_conflict_instead_of_last_writer_winning():
    first = decision()
    second = decision("reject", at=NOW + timedelta(minutes=1))
    assert accepted_reviews([second, first]).selected == {}
    assert accepted_reviews([second, first]).rejected == {}
    resolved = decision(
        "supersede", (first.decision_id, second.decision_id), NOW + timedelta(hours=1)
    )
    assert accepted_reviews([resolved, first, second]).selected == {"b" * 64: resolved.recorded_at}


def test_source_dispute_rates_count_claims_once_and_clear_on_revocation():
    rejected = decision("reject")
    assert dispute_rates([rejected, rejected], {"b" * 64: "fixture:source"}) == [
        {"source_id": "fixture:source", "reviewed": 1, "disputed": 1, "dispute_rate": 1.0}
    ]
    revoked = decision("revoke", (rejected.decision_id,), NOW + timedelta(hours=1))
    assert dispute_rates([rejected, revoked], {"b" * 64: "fixture:source"}) == []


def test_domain_journal_retains_old_wire_events_and_refuses_path_escape(tmp_path: Path):
    event = decision()
    journal = Journal(tmp_path, "fixture")
    assert journal.append(event) and not journal.append(event)
    assert journal.read() == (event,)
    assert journal.path.parent == tmp_path / "decisions" / "fixture"
    for value in ("../escape", "/tmp", "", "a/b", "."):
        with pytest.raises(ValueError):
            domain_name(value)


def test_claim_storage_round_trip_keeps_exact_reviewed_versions():
    for value in one_of_each():
        if isinstance(value, Claim):
            restored = read_claim(value.row(), value.evidence)
            assert restored == value and restored.key == value.key


def test_domain_journal_syncs_the_decisions_directory_entry(tmp_path, monkeypatch):
    from kn.review import journal as module

    synced = []
    monkeypatch.setattr(module, "_sync_directory", synced.append)
    Journal(tmp_path, "fixture").append(decision())
    assert tmp_path in synced
