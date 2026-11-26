"""Claims and facts reuse the shared version-bound human verification protocol."""

from datetime import UTC, datetime

import pytest

from kn.evidence.records import Record
from kn.evidence.verification import target
from kn.review.model import Request, Stamp
from kn.review.protocol import Reviewer, decide, project
from tests.evidence.fixtures import changed_mass, claim, fact

NOW = datetime(2026, 4, 1, 9, tzinfo=UTC)
REVIEWER = Reviewer("person:fixture-reviewer", "human", True, frozenset({"factual"}))


def accepted(record: Record):
    request = Request(
        request_id=f"accept-{record.key[:8]}",
        target=target(record),
        outcome="accept",
        performed_at=NOW,
        reason="Checked against the datasheet",
        evidence="review:fixture",
    )
    return decide(request, REVIEWER, NOW)


def test_a_target_names_the_stable_key_and_full_content_version() -> None:
    original = claim()
    item = target(original)
    assert (item.contract_id, item.dataset, item.scope) == ("kn.core.evidence", "claims", "record")
    assert [(part.field_id, part.value) for part in item.key] == [
        ("evidence.claims.claim_key", original.key)
    ]
    assert target(claim()) == item


def test_a_changed_claim_version_inherits_no_human_verification() -> None:
    original = claim()
    decision = accepted(original)
    assert project([decision], target(original)).stamp.human_verified_by == REVIEWER.principal
    changed = changed_mass(original)
    assert target(changed).version != target(original).version
    result = project([decision], target(changed))
    assert (result.state, result.stamp) == ("unreviewed", Stamp())


def test_a_fact_selecting_a_different_claim_inherits_no_human_verification() -> None:
    original = claim()
    first = fact(original)
    decision = accepted(first)
    replaced = fact(changed_mass(original), outcome="replaced", deciding_criterion="data_time")
    assert project([decision], target(replaced)).stamp == Stamp()
    assert project([decision], target(first)).state == "accepted"


@pytest.mark.parametrize("label", ["verified", "Verified by vendor", "human_verified"])
def test_an_imported_verification_label_leaves_the_stamp_null(label: str) -> None:
    imported = claim(source_verification_label=label)
    assert imported.row()["source_verification_label"] == label
    result = project([], target(imported))
    assert (result.state, result.stamp) == ("unreviewed", Stamp())
    assert target(imported).version != target(claim()).version


def test_automation_cannot_accept_a_claim() -> None:
    agent = Reviewer("agent:importer", "agent", True, frozenset({"factual"}))
    request = Request(
        request_id="agent",
        target=target(claim()),
        outcome="accept",
        performed_at=NOW,
        reason="Imported label",
        evidence="import:fixture",
    )
    with pytest.raises(ValueError, match="human reviewer"):
        decide(request, agent, NOW)
