"""Durable resolver entry point for source adapters."""

from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.engine import Connection

from kn.contracts.model import canonical
from kn.identity import store
from kn.identity.events import Event, event
from kn.identity.journal import Journal, LockedJournal, new_id
from kn.identity.matching.observe import Observation
from kn.identity.matching.registry import identifiers, source_links
from kn.identity.matching.resolve import resolve
from kn.identity.matching.scoring import prepare
from kn.identity.model import MATCH_LINK_METHODS, Attribute, Identifier, Link, Match, Mint, Payload
from kn.identity.profiles import Profile
from kn.identity.state import PENDING_MATCH, State


@dataclass(frozen=True)
class Receipt:
    match_id: str
    match: Match
    kn_id: str | None


@dataclass(frozen=True)
class Followups:
    mint: Mint | None = None
    bind: bool = False
    observations: tuple[Identifier | Attribute, ...] = ()

    @property
    def count(self) -> int:
        return int(self.mint is not None) + int(self.bind) + len(self.observations)


def submit(
    connection: Connection,
    journal: Journal,
    profile: Profile,
    incoming: Observation,
    *,
    actor: str,
    evidence: str,
) -> Receipt:
    """Resolve and project one source observation in a caller-owned transaction."""
    return store.apply(
        connection,
        journal,
        lambda locked: record(locked, profile, incoming, actor=actor, evidence=evidence),
    )


def record(
    locked: LockedJournal,
    profile: Profile,
    incoming: Observation,
    *,
    actor: str,
    evidence: str,
) -> Receipt:
    """Record a decision and any binding under the existing identity writer lock."""
    entry = locked.state.requests.get(incoming.fingerprint(profile.digest))
    if entry is not None and isinstance(saved := entry.payload, Match):
        return _resume(locked, entry, saved, profile, incoming)
    if locked.state.pending_match() is not None:
        raise ValueError(PENDING_MATCH)
    match = resolve(locked.state, profile, incoming)
    trace = match.trace
    assert trace is not None
    minted = new_id(incoming.observed_at) if match.decision == "mint" else None
    target = match.selected or minted
    planned = _plan(locked.state, profile, incoming, target, minted)
    trace = trace.model_copy(update={"minted_id": minted, "followup_count": planned.count})
    match = match.model_copy(
        update={
            "trace": trace,
            "review_observation": canonical(incoming.model_dump(mode="json"))
            if match.decision == "review"
            else None,
            "review_profile": canonical(profile.model_dump(mode="json"))
            if match.decision == "review"
            else None,
        }
    )
    entry = event(
        match,
        previous=locked.head,
        occurred_at=incoming.observed_at,
        actor=actor,
        reason=f"Identity resolution: {trace.route}",
        evidence=evidence,
    )
    locked.append_batch((entry, *_effect_events(entry, match, planned)))
    return Receipt(entry.event_id, match, target)


def _resume(
    locked: LockedJournal, entry: Event, match: Match, profile: Profile, incoming: Observation
) -> Receipt:
    trace = match.trace
    assert trace is not None
    target = match.selected or trace.minted_id
    planned = _plan(locked.state, profile, incoming, target, trace.minted_id, before=entry.sequence)
    if trace.followup_count != planned.count:
        raise ValueError("identity match followups cannot be reproduced")
    effects = _effect_events(entry, match, planned)
    prefix = tuple(locked.state.events[entry.sequence : entry.sequence + len(effects)])
    if prefix != effects[: len(prefix)]:
        raise ValueError("identity history diverged from the pending match; inspect the journal")
    locked.append_batch(effects[len(prefix) :])
    return Receipt(entry.event_id, match, target)


def _effect_events(entry: Event, match: Match, planned: Followups) -> tuple[Event, ...]:
    predecessor = entry
    events: list[Event] = []
    for payload in _effects(entry.event_id, match, planned):
        predecessor = event(
            payload,
            previous=predecessor,
            occurred_at=entry.occurred_at,
            actor=entry.actor,
            reason=entry.reason,
            evidence=entry.evidence,
        )
        events.append(predecessor)
    return tuple(events)


def _effects(match_id: str, match: Match, planned: Followups) -> Iterator[Payload]:
    trace = match.trace
    assert trace is not None
    if planned.mint is not None:
        yield planned.mint
    if planned.bind:
        target = match.selected or trace.minted_id
        assert target is not None
        selected = next((item for item in match.candidates if item.kn_id == match.selected), None)
        yield Link(
            record=match.record,
            kn_id=target,
            method=MATCH_LINK_METHODS[trace.route],
            score=selected.score if selected is not None else None,
            probability=selected.probability if selected is not None else None,
            profile_digest=match.profile_digest,
            profile_version=match.profile_version,
            match_id=match_id,
        )
    yield from planned.observations


def _plan(
    state: State,
    profile: Profile,
    incoming: Observation,
    target: str | None,
    minted: str | None,
    *,
    before: int | None = None,
) -> Followups:
    if target is None:
        return Followups()
    mint = (
        Mint(kn_id=minted, entity_class=profile.entity_class, anchor=incoming.record)
        if minted is not None
        else None
    )
    active_link = any(
        item.ended_event is None if before is None else item.was_active(before)
        for item in source_links(state, incoming.record)
    )
    observed = observations(state, profile, incoming, target, before=before)
    return Followups(mint, not active_link, tuple(observed))


def observations(
    state: State, profile: Profile, incoming: Observation, target: str, *, before: int | None
) -> Iterator[Identifier | Attribute]:
    for key in sorted(incoming.authoritative, key=lambda item: item.parts):
        registered = any(
            item.valid_to is None or incoming.observed_at < item.valid_to
            for _, item in identifiers(state, key, before=before)
        )
        if not registered:
            yield Identifier(
                kn_id=target,
                namespace=key.namespace,
                issuer=key.issuer,
                value=key.value,
                authority="authoritative",
                valid_from=incoming.observed_at,
            )
    fields = {item.field_id: item.normalizer for item in profile.attributes}
    for field_id, value in prepare(
        profile, {item.field_id: item.value for item in incoming.attributes}
    ).items():
        yield Attribute(
            kn_id=target,
            field_id=field_id,
            original=value.original,
            normalized=value.normalized,
            normalizer=fields[field_id],
            profile_digest=profile.digest,
            record=incoming.record,
        )
