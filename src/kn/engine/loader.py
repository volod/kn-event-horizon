"""The sole ingestion writer for mapped domain data."""

from sqlalchemy.engine import Connection

from kn.engine.outcomes import RunFailure
from kn.evidence.model import Claim
from kn.identity import store
from kn.identity.journal import Journal, LockedJournal
from kn.identity.matching.ingest import record, submit
from kn.identity.matching.observe import Observation
from kn.identity.matching.resolve import resolve
from kn.identity.model import Match
from kn.identity.profiles import Profile
from kn.identity.tracking.delivery import Delivery
from kn.identity.tracking.writer import track

ACTOR = "engine:ingestion"


def load_records(
    connection: Connection,
    journal: Journal,
    profile: Profile,
    deliveries: tuple[Delivery, ...],
) -> int:
    observations = tuple(
        Observation(
            record=delivery.record, version=delivery.version_text, observed_at=delivery.fetched_at
        )
        for delivery in deliveries
    )
    store.apply(
        connection, journal, lambda locked: _prepare(locked, profile, observations, deliveries)
    )
    return sum(
        _load_record(connection, journal, profile, incoming, delivery)
        for incoming, delivery in zip(observations, deliveries, strict=True)
    )


def _prepare(
    locked: LockedJournal,
    profile: Profile,
    observations: tuple[Observation, ...],
    deliveries: tuple[Delivery, ...],
) -> None:
    state = locked.state
    by_request = {item.fingerprint(profile.digest): item for item in observations}
    pending = state.pending_match()
    for request, incoming in by_request.items():
        saved = state.requests.get(request)
        match = saved.payload if saved is not None else resolve(state, profile, incoming)
        if not isinstance(match, Match) or match.decision == "review":
            raise RunFailure("integrity_lost", "blocked")
    if pending is not None:
        match = pending.payload
        assert isinstance(match, Match) and match.trace is not None
        retry = by_request.get(match.trace.request_digest)
        if retry is None:
            raise RunFailure("integrity_lost", "blocked")
        delivery = next(item for item in deliveries if item.record == retry.record)
        record(locked, profile, retry, actor=ACTOR, evidence=delivery.archive_record_id)


def _load_record(
    connection: Connection,
    journal: Journal,
    profile: Profile,
    incoming: Observation,
    delivery: Delivery,
) -> int:
    submit(connection, journal, profile, incoming, actor=ACTOR, evidence=delivery.archive_record_id)
    receipt = track(connection, journal, delivery, actor=ACTOR, clock=lambda: delivery.fetched_at)
    return sum(isinstance(row, Claim) for row in receipt.rows)
