"""Registry integrity and lifecycle replay, independent of SQL and filesystem order."""

import json
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from kn.identity.events import Event, event
from kn.identity.model import (
    Assignment,
    Identifier,
    Link,
    Match,
    Merge,
    Mint,
    Reclassify,
    Restore,
    SourceKey,
    Split,
    Unlink,
    Version,
)
from kn.identity.projection import rows
from kn.identity.state import replay
from kn.identity.store import contract
from kn.review.targets import declared_coverage
from tests.identity.fixtures import KEY, NOW, A, B, C, D, E, F, history

ROOT = Path(__file__).resolve().parents[2]


def append(events, payload, decision_ref="review:fixture"):
    value = event(
        payload,
        previous=events[-1] if events else None,
        occurred_at=NOW,
        actor="engine:fixture",
        reason="Test",
        evidence="archive:test",
        decision_ref=decision_ref,
    )
    return (*events, value)


def test_all_event_kinds_round_trip_and_replay_to_identical_rows() -> None:
    events = history()
    schema = json.loads((ROOT / "contracts/core/identity/event.schema.json").read_text())
    assert schema == Event.model_json_schema()
    validator = Draft202012Validator(schema)
    for item in events:
        validator.validate(item.model_dump(mode="json"))
    restored = tuple(Event.model_validate_json(item.model_dump_json()) for item in events)
    assert rows(replay(restored)) == rows(replay(events))
    state = replay(events)
    assert state.resolve(A) == state.resolve(B) == state.resolve(C) == (D, F)
    assert state.objects[E].state == "retired"
    assert state.objects[F].entity_class == "core.manufacturer"
    assert state.objects[D].state == "active"
    assert all(rows(state).values())
    assert len(declared_coverage(contract())) == len(contract().tables)
    assert all(UUID(key.removeprefix("kn:")).version == 7 for key in state.objects)


@pytest.mark.parametrize(
    "payload,match",
    [
        (
            Mint(
                kn_id=A, entity_class="core.organization", anchor=SourceKey(source="new", key="x")
            ),
            "reused",
        ),
        (Mint(kn_id=F, entity_class="core.organization", anchor=KEY), "anchoring"),
        (Link(record=KEY, kn_id=B, method="minted"), "active link"),
        (Link(record=SourceKey(source="new", key="y"), kn_id=F, method="minted"), "active object"),
        (Unlink(record=KEY, kn_id=B), "without its active link"),
        (Merge(kn_id=A, survivor=A), "distinct active"),
        (Restore(kn_id=A), "only a retired"),
        (Split(kn_id=A, successors=(D, D)), "distinct successors"),
        (Split(kn_id=A, successors=(D, E)), "exactly once"),
        (
            Split(
                kn_id=A, successors=(D, E), assignments=(Assignment(item_id="b" * 64, successor=D),)
            ),
            "exactly once",
        ),
    ],
)
def test_invalid_transition_does_not_enter_history(payload, match: str) -> None:
    events = history()[:8]
    with pytest.raises(ValueError, match=match):
        replay(append(events, payload))


@pytest.mark.parametrize("kind", ["merged", "split", "retired"])
def test_nonactive_objects_refuse_links_and_merges(kind: str) -> None:
    events = history()
    prefix = next(index + 1 for index, item in enumerate(events) if item.payload.kind == kind)
    current = events[:prefix]
    old = current[-1].payload.kn_id
    for payload in (
        Link(record=SourceKey(source="new", key="z"), kn_id=old, method="minted"),
        Merge(kn_id=D if old != D else E, survivor=old),
    ):
        with pytest.raises(ValueError, match="active object"):
            replay(append(current, payload))


def test_cross_class_merge_and_split_refuse_and_terminal_restore_refuses() -> None:
    events = history()
    for payload in (
        Merge(kn_id=D, survivor=F),
        Split(kn_id=D, successors=(F, B)),
        Restore(kn_id=A),
        Restore(kn_id=C),
        Restore(kn_id=E),
    ):
        with pytest.raises(ValueError):
            replay(append(events, payload))


def test_identifier_namespace_and_half_open_validity() -> None:
    events = history()[:7]
    identifier = events[-1].payload
    assert isinstance(identifier, Identifier)
    with pytest.raises(ValueError, match="overlaps"):
        replay(append(events, identifier.model_copy(update={"kn_id": B})))
    other_namespace = identifier.model_copy(update={"namespace": "other", "kn_id": B})
    assert len(replay(append(events, other_namespace)).holdings) == 3
    end = NOW.replace(year=2027)
    closed = identifier.model_copy(update={"valid_to": end})
    prior = append(events[:-1], closed)
    later = identifier.model_copy(update={"kn_id": B, "valid_from": end})
    assert replay(append(prior, later))
    with pytest.raises(ValidationError, match="half-open"):
        Identifier(**{**identifier.model_dump(), "valid_to": NOW})


def test_versions_keep_history_and_last_seen_without_change_detection() -> None:
    events = history()[:9]
    version = events[-1].payload
    assert isinstance(version, Version)
    older = version.model_copy(update={"version": "older", "observed_at": NOW.replace(year=2025)})
    state = replay(append(events, older))
    assert len(state.versions) == 2 and state.last_seen[KEY.record_id] == NOW
    with pytest.raises(ValueError, match="version already"):
        replay(append(events, version))


def test_match_link_context_and_complete_lifecycle_decision_references() -> None:
    events = history()[:11]
    match = events[-1].payload
    assert isinstance(match, Match)
    with pytest.raises(ValueError, match="candidate"):
        replay(append(events, match.model_copy(update={"selected": F})))
    link = history()[11].payload
    assert isinstance(link, Link)
    with pytest.raises(ValueError, match="score and profile"):
        replay(append(events, link.model_copy(update={"score": 999})))
    with pytest.raises(ValueError, match="decision reference"):
        append(events, Merge(kn_id=A, survivor=B), decision_ref=None)


def test_envelope_rejects_digest_version_predecessor_and_reordering() -> None:
    events = history()
    for update in ({"reason": "tampered"}, {"schema_version": 2}, {"sequence": True}):
        with pytest.raises(ValueError):
            Event.model_validate({**events[0].model_dump(), **update})
    with pytest.raises(ValueError, match="predecessor"):
        replay((events[1], events[0]))
    with pytest.raises(ValueError, match="canonical kn"):
        Mint(kn_id="kn:550e8400-e29b-41d4-a716-446655440000", entity_class="x", anchor=KEY)
    with pytest.raises(ValueError, match="different class"):
        replay(
            append(
                events[:5],
                Reclassify(
                    kn_id=A,
                    successor=Mint(
                        kn_id=F,
                        entity_class="core.organization",
                        anchor=SourceKey(source="x", key="y"),
                    ),
                ),
            )
        )


def test_long_redirect_chain_resolves_without_recursion() -> None:
    from kn.identity.state import Object, State

    state = State()
    keys = [f"kn:019b76da-a800-7000-8000-{number:012d}" for number in range(1100)]
    for index, key in enumerate(keys):
        state.objects[key] = Object(
            key,
            "core.organization",
            SourceKey(source="fixture:chain", key=str(index)),
            "a" * 64,
            state="merged" if index + 1 < len(keys) else "active",
            successors=(keys[index + 1],) if index + 1 < len(keys) else (),
        )
    assert state.resolve(keys[0]) == (keys[-1],)
