"""Shared decisions refuse spoofing and preserve exact human provenance."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from kn.review.model import Decision, Request, Stamp, Target
from kn.review.protocol import Reviewer, decide, project

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)


def target(**changes) -> Target:
    return Target.model_validate(
        {
            "contract_id": "kn.fixture",
            "dataset": "labels",
            "key": [
                {"field_id": "label.id", "kind": "string", "value": "001"},
                {"field_id": "label.locale", "kind": "string", "value": "uk"},
            ],
            "version": "a" * 64,
            "scope": "field",
            "field_id": "label.text",
            "purpose": "factual",
            **changes,
        }
    )


def request(**changes) -> Request:
    return Request.model_validate(
        {
            "request_id": "review-1",
            "target": target(),
            "outcome": "accept",
            "performed_at": "2026-01-02T14:00:00+02:00",
            "reason": "Checked source",
            "evidence": "review:fixture",
            **changes,
        }
    )


def reviewer() -> Reviewer:
    return Reviewer("person:alice", "human", True, frozenset({"factual"}))


def event(**changes) -> Decision:
    return decide(request(**changes), reviewer(), NOW)


def test_acceptance_is_utc_and_replay_is_identical() -> None:
    decision = event()
    assert decision.performed_at == NOW
    assert Decision.model_validate_json(decision.model_dump_json()) == decision
    result = project([decision], decision.target)
    assert result.state == "accepted"
    assert result.stamp.human_verified_at == NOW
    assert result.stamp.human_verified_by == "person:alice"
    assert project([decision, decision], decision.target) == result
    assert project([decision], target(scope="record", field_id=None)).stamp == Stamp()
    assert project([decision], target(version="b" * 64)).stamp == Stamp()


@pytest.mark.parametrize(
    "kind,authenticated,purposes",
    [
        ("agent", True, {"factual"}),
        ("import", True, {"factual"}),
        ("human", False, {"factual"}),
        ("human", True, {"integrity"}),
    ],
)
def test_only_authorized_authenticated_humans_decide(kind, authenticated, purposes) -> None:
    with pytest.raises(ValueError, match="human"):
        decide(request(), Reviewer("person:alice", kind, authenticated, frozenset(purposes)), NOW)


@pytest.mark.parametrize(
    "time", ["2026-01-02", "2026-01-02T12:00:00", "bad", "2026-01-03T00:00:00Z", 1767355200]
)
def test_invalid_naive_date_only_and_future_times_fail(time) -> None:
    with pytest.raises(ValueError):
        decide(request(performed_at=time), reviewer(), NOW)


def test_partial_stamp_and_payload_actor_are_refused() -> None:
    with pytest.raises(ValidationError):
        Stamp(human_verified_at=NOW)
    with pytest.raises(ValidationError):
        request(reviewer="person:alice")
    with pytest.raises(ValidationError):
        request(verified=True)


def test_conflicts_require_explicit_supersession_and_revoke_retains_history() -> None:
    accepted = event()
    rejected = event(request_id="review-2", outcome="reject")
    assert project([rejected, accepted], accepted.target).state == "conflict"
    assert project([accepted, rejected], accepted.target).stamp == Stamp()
    resolved = event(
        request_id="resolve",
        outcome="supersede",
        predecessors=[rejected.decision_id, accepted.decision_id],
    )
    assert project([resolved, accepted, rejected], accepted.target).state == "accepted"
    revoked = event(request_id="revoke", outcome="revoke", predecessors=[resolved.decision_id])
    result = project([revoked, rejected, resolved, accepted], accepted.target)
    assert result.state == "revoked" and result.stamp == Stamp()
    assert len(result.heads) == 1


def test_log_is_idempotent_and_refuses_corruption(tmp_path: Path) -> None:
    from kn.review.journal import Journal

    log = Journal(tmp_path)
    assert log.append(event())
    assert not log.append(event())
    assert log.read() == (event(),)
    with log.path.open("ab") as stream:
        stream.write(b'{"torn":')
    with pytest.raises(ValueError, match="journal"):
        log.read()


def test_conflict_cannot_be_resolved_by_ordinary_acceptance() -> None:
    accepted = event()
    rejected = event(request_id="other", outcome="reject")
    with pytest.raises(ValueError, match="supersed"):
        event(request_id="implicit", predecessors=[accepted.decision_id, rejected.decision_id])


def test_durable_event_requires_explicit_schema_version() -> None:
    data = event().model_dump(mode="json")
    del data["schema_version"]
    with pytest.raises(ValueError):
        Decision.model_validate(data)


def test_journal_refuses_bad_references_and_changed_request_ids(tmp_path: Path) -> None:
    from kn.review.journal import Journal

    journal = Journal(tmp_path)
    first = event()
    journal.append(first)
    with pytest.raises(ValueError, match="reused"):
        journal.append(event(reason="Changed content"))
    with pytest.raises(ValueError, match="predecessor"):
        journal.append(event(request_id="missing", outcome="revoke", predecessors=["b" * 64]))
    with pytest.raises(ValueError, match="exact target"):
        journal.append(
            decide(
                request(
                    request_id="different-purpose",
                    outcome="supersede",
                    target=target(purpose="integrity"),
                    predecessors=[first.decision_id],
                ),
                Reviewer("person:alice", "human", True, frozenset({"integrity"})),
                NOW,
            )
        )
    assert journal.read() == (first,)


def test_journal_refuses_symlink_paths(tmp_path: Path) -> None:
    from kn.review.journal import Journal

    (tmp_path / "decisions").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        Journal(tmp_path).append(event())
