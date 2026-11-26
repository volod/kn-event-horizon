"""Reviewed identity links preserve authoritative ownership and interruption recovery."""

from types import SimpleNamespace

import pytest

from kn.contracts.model import canonical
from kn.identity.events import event
from kn.identity.matching.resolve import resolve
from kn.identity.model import Match
from kn.review.identity import effects
from kn.review.model import Request
from kn.review.protocol import Reviewer, decide
from kn.review.queue import identity_item
from tests.identity.fixtures import NOW, A, B
from tests.identity.test_matching import observation, profile, registry


def test_accepting_a_candidate_cannot_ignore_an_authoritative_key_owned_elsewhere():
    config = profile()
    state = registry(
        config,
        [
            {"attributes": {"organization.name": "First"}},
            {"attributes": {"organization.name": "Second"}, "lei": "00000000000000000042"},
        ],
    )
    incoming = observation({}, lei="00000000000000000042", aliases=(A,))
    match = Match(
        record=incoming.record,
        profile_digest=config.digest,
        profile_version=config.version,
        candidates=resolve(state, config, incoming).candidates,
        decision="review",
        review_observation=canonical(incoming.model_dump(mode="json")),
        review_profile=canonical(config.model_dump(mode="json")),
    )
    entry = event(
        match,
        previous=state.events[-1],
        occurred_at=NOW,
        actor="engine",
        reason="fixture",
        evidence="archive:fixture",
    )
    state.apply(entry)
    # The explicit reviewed choice includes both competing candidates.
    item = identity_item(entry)
    choice = item.choice(B)
    review = decide(
        Request(
            request_id="fixture",
            target=item.target,
            queue=choice,
            outcome="accept",
            performed_at=NOW,
            reason="Compared identity",
            evidence="review:fixture",
        ),
        Reviewer("person:fixture", "human", True, frozenset({"workflow"})),
        NOW,
    )
    assert effects(SimpleNamespace(state=state), review)
    # Extend the reviewed candidate set to exercise an operator choosing the conflicting object.
    from kn.review.model import Choice

    conflicting = decide(
        Request(
            request_id="conflict",
            target=item.target,
            queue=Choice(item_id=item.item_id, kind=item.kind, candidates=(A, B), selected=A),
            outcome="accept",
            performed_at=NOW,
            reason="Compared identity",
            evidence="review:fixture",
        ),
        Reviewer("person:fixture", "human", True, frozenset({"workflow"})),
        NOW,
    )
    with pytest.raises(ValueError, match="authoritative"):
        effects(SimpleNamespace(state=state), conflicting)


def test_pending_identity_choice_cannot_replace_a_newer_observation():
    config = profile()
    state = registry(config, [{"attributes": {"organization.name": "Fixture"}}])
    first = observation({}, aliases=(A,))
    match = resolve(state, config, first).model_copy(
        update={
            "review_observation": canonical(first.model_dump(mode="json")),
            "review_profile": canonical(config.model_dump(mode="json")),
        }
    )
    original = event(
        match,
        previous=state.events[-1],
        occurred_at=NOW,
        actor="engine",
        reason="fixture",
        evidence="archive:fixture",
    )
    state.apply(original)
    item = identity_item(original)
    decision = decide(
        Request(
            request_id="pending",
            target=item.target,
            queue=item.choice(A),
            outcome="accept",
            performed_at=NOW,
            reason="Compared identity",
            evidence="review:fixture",
        ),
        Reviewer("person:fixture", "human", True, frozenset({"workflow"})),
        NOW,
    )
    latest = resolve(state, config, observation({}, version="2", aliases=(A,)))
    state.apply(
        event(
            latest,
            previous=state.events[-1],
            occurred_at=NOW,
            actor="engine",
            reason="newer observation",
            evidence="archive:fixture",
        )
    )
    with pytest.raises(ValueError, match="stale"):
        effects(SimpleNamespace(state=state), decision)
