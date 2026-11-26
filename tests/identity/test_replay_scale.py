"""Replay validation and SQL row projection grow linearly with identity history."""

import time
from datetime import timedelta

import pytest

from kn.identity.events import Event, event
from kn.identity.model import (
    Attribute,
    ChangeSet,
    FieldChange,
    FieldHash,
    Identifier,
    Link,
    Match,
    Mint,
    Payload,
    SourceKey,
    Version,
)
from kn.identity.projection import rows
from kn.identity.state import replay
from tests.identity.fixtures import DIGEST, NOW

SMALL_RECORDS = 400
GROWTH = 4
# Linear work gives a ratio near GROWTH; one linear scan per event gives about GROWTH squared.
MAX_RATIO = 2 * GROWTH
ATTEMPTS = 3


def _kn_id(number: int) -> str:
    return f"kn:019b76da-a800-7000-8000-{number:012d}"


def _payloads(number: int) -> list[Payload]:
    record = SourceKey(source="fixture:scale", key=f"{number:06d}")
    kn_id = _kn_id(number)
    version = Version(
        record=record,
        version="1",
        content_digest=DIGEST,
        field_hashes=(FieldHash(field_id="organization.name", digest=DIGEST),),
        observed_at=NOW + timedelta(seconds=number),
        fetch_id="fetch:scale",
        archive_record_id=f"archive:{number}",
        code_digest=DIGEST,
    )
    return [
        version,
        Match(
            record=record,
            profile_digest=DIGEST,
            profile_version="1.0.0",
            candidates=(),
            decision="mint",
        ),
        Mint(kn_id=kn_id, entity_class="core.organization", anchor=record),
        Link(record=record, kn_id=kn_id, method="minted"),
        Identifier(
            kn_id=kn_id,
            namespace="lei",
            value=f"{number:020d}",
            issuer="fixture:lei",
            authority="authoritative",
            valid_from=NOW,
        ),
        Attribute(
            kn_id=kn_id,
            field_id="organization.name",
            original=f"Fixture {number}",
            normalized=f"fixture {number}",
            normalizer="legal-name-v1",
            profile_digest=DIGEST,
        ),
    ]


def _history(records: int) -> tuple[Event, ...]:
    events: list[Event] = []
    for number in range(1, records + 1):
        payloads = _payloads(number)
        for payload in payloads:
            events.append(_next(events[-1] if events else None, payload))
        version_id = events[-6].event_id
        changes = (FieldChange(field_id="organization.name", change="added", current_hash=DIGEST),)
        events.append(_next(events[-1], ChangeSet(version_id=version_id, changes=changes)))
    return tuple(events)


def _next(previous: Event | None, payload: Payload) -> Event:
    return event(
        payload,
        previous=previous,
        occurred_at=NOW,
        actor="engine:fixture",
        reason="Scale fixture",
        evidence="archive:fixture",
    )


def _seconds(events: tuple[Event, ...]) -> float:
    best = float("inf")
    for _ in range(ATTEMPTS):
        start = time.perf_counter()
        rows(replay(events))
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.heavy
def test_replay_and_projection_cost_grows_linearly_with_history() -> None:
    small = _history(SMALL_RECORDS)
    large = _history(SMALL_RECORDS * GROWTH)
    assert len(rows(replay(large))["matches"]) == SMALL_RECORDS * GROWTH
    assert _seconds(large) / _seconds(small) < MAX_RATIO
