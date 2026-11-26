"""Corrections and retractions across condition sets, and replay only when a subject can change."""

from datetime import datetime, timedelta
from typing import Any

import pytest

from kn.evidence import projection
from kn.evidence.model import Claim
from kn.evidence.projection import history, subjects, successors
from kn.evidence.ranking import Context, Reviews, ReviewSnapshot
from kn.evidence.selection import Subject
from kn.review.model import digest
from tests.evidence.selection_fixtures import CONTEXT, MAKER, MAKER_TWO, RANKS, T0, policy, stated

STEP = timedelta(hours=1)
COLD = {"temperature_c": 25}
HOT = {"temperature_c": 85}


def _next(previous: Claim, at: datetime, **changes: Any) -> Claim:
    """The record's next version states the field again with the given changes."""
    data = previous.model_dump()
    data.update(
        {
            "source_version_id": digest([previous.source_version_id, "next"]),
            "change_kind": "changed",
            "supersedes": previous.key,
            "recorded_at": at,
            **changes,
        }
    )
    data["evidence"] = {**data["evidence"], "fetch_id": "fetch-next", "recorded_at": at}
    return Claim.model_validate(data)


def _facts(claims: list[Claim]) -> dict[str, Any]:
    grouped, unattributed = subjects(claims, lambda kn_id: (kn_id,))
    assert unattributed == []
    retired = successors(claims)
    return {
        subject.conditions_json: history(subject, values, policy(), CONTEXT, retired)
        for subject, values in grouped.items()
    }


def test_a_correction_to_another_condition_set_retires_the_old_value() -> None:
    first = stated(MAKER, "1300", conditions=COLD)
    corrected = _next(first, T0 + STEP, conditions=HOT)
    facts = _facts([first, corrected])
    (cold,) = facts['{"temperature_c":25}']
    assert cold.fact.claim_key == first.key and cold.fact.knowledge_to == corrected.recorded_at
    (hot,) = facts['{"temperature_c":85}']
    assert hot.fact.claim_key == corrected.key and hot.fact.knowledge_to is None


def test_an_emptied_field_under_another_condition_set_still_needs_review() -> None:
    first = stated(MAKER, "1300", conditions=COLD)
    empty = _next(
        first,
        T0 + STEP,
        conditions={},
        change_kind="emptied",
        value={"kind": "missing", "reason": "source_empty"},
        original_value="",
    )
    facts = _facts([first, empty])
    assert list(facts) == ['{"temperature_c":25}']
    held = facts['{"temperature_c":25}'][-1]
    assert held.fact.claim_key == first.key and held.fact.knowledge_to is None
    assert [item.kind for item in held.selection.items] == ["empty_claim"]


def test_decisions_about_other_claims_replay_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = [stated(MAKER, "1250", at=T0), stated(MAKER_TWO, "1300", at=T0 + STEP)]
    other = Reviews(
        snapshots=tuple(
            ReviewSnapshot(
                at=T0 + (index + 2) * STEP,
                selected={f"{index:064x}": T0},
                rejected={},
                decisions={},
            )
            for index in range(20)
        )
    )
    evaluated: list[datetime] = []
    select = projection.select

    def counted(*args: Any, **kwargs: Any) -> Any:
        evaluated.append(args[4])
        return select(*args, **kwargs)

    monkeypatch.setattr(projection, "select", counted)
    subject = Subject.of(claims[0])
    unrelated = history(subject, claims, policy(), Context(ranks=RANKS, reviews=other))
    assert evaluated == [claim.recorded_at for claim in claims]
    assert unrelated == history(subject, claims, policy(), CONTEXT)
