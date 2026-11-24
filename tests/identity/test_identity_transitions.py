"""Lifecycle operations over deterministic records and review evidence."""

from pathlib import Path

import pytest

from kn.identity.events import event
from kn.identity.journal import Journal
from kn.identity.model import Identifier, Merge
from kn.identity.state import replay
from tests.identity.fixtures import NOW, A, B, C, D, E, history


def test_authoritative_merge_retains_both_observations_without_duplicate_ownership() -> None:
    prefix = history()[:8]
    recorded = prefix[6].payload
    assert isinstance(recorded, Identifier)
    proof = recorded.model_copy(update={"kn_id": B})
    merged = event(
        Merge(kn_id=B, survivor=A, authoritative=proof),
        previous=prefix[-1],
        occurred_at=NOW,
        actor="engine:fixture",
        reason="Exact authoritative identity",
        evidence="archive:observation",
    )
    restored = replay((*prefix, merged))
    assert restored.resolve(B) == (A,)
    assert restored.owned(A)[prefix[6].event_id].event.payload == recorded
    assert merged.payload.authoritative == proof


@pytest.mark.parametrize(
    "change",
    [
        {"kn_id": C},
        {"authority": "weak"},
        {"issuer": "other"},
        {"namespace": "other"},
        {"value": "other"},
        {"valid_from": NOW.replace(year=2027)},
    ],
)
def test_authoritative_merge_refuses_mismatched_or_inactive_proof(change: dict) -> None:
    prefix = history()[:8]
    recorded = prefix[6].payload
    assert isinstance(recorded, Identifier)
    proof = recorded.model_copy(update={"kn_id": B, **change})
    with pytest.raises(ValueError, match="authoritative"):
        replay(
            (
                *prefix,
                event(
                    Merge(kn_id=B, survivor=A, authoritative=proof),
                    previous=prefix[-1],
                    occurred_at=NOW,
                    actor="engine:fixture",
                    reason="Exact authoritative identity",
                    evidence="archive:observation",
                ),
            )
        )


def test_resolve_uses_flat_redirects_and_history_follows_successors(tmp_path: Path) -> None:
    from kn.identity.queries import inspect

    journal = Journal(tmp_path)
    for item in history()[:17]:
        journal.append(item)
    assert inspect(journal, "resolve", A)["successors"] == [D, E]
    result = inspect(journal, "history", A)
    assert [row["payload"]["kind"] for row in result["events"]][-3:] == [
        "merged",
        "merged",
        "split",
    ]
