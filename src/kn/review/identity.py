"""Validated identity effects of an accepted queue choice, recoverable after interruption."""

from kn.identity.events import Event, event
from kn.identity.journal import LockedJournal
from kn.identity.matching.ingest import observations
from kn.identity.matching.observe import Observation
from kn.identity.matching.registry import holder
from kn.identity.model import Attribute, Identifier, Link, Payload, Unlink
from kn.identity.profiles import Profile
from kn.identity.state import State, replay
from kn.review.model import Decision
from kn.review.targets import TargetUnavailable

REVIEW_REF = "queue-review:"


def effects(locked: LockedJournal, decision: Decision) -> tuple[Event, ...]:
    choice = decision.queue
    if (
        choice is None
        or not choice.kind.startswith("identity_")
        or decision.outcome not in {"accept", "supersede"}
    ):
        return ()
    if choice.selected is None:
        raise ValueError("accepting an identity item requires a candidate")
    match_id = str(decision.target.key[0].value)
    incoming, profile = _context(locked.state, match_id)
    ref = REVIEW_REF + decision.decision_id
    prior = next((entry for entry in locked.state.events if entry.decision_ref == ref), None)
    state = replay(locked.state.events[: prior.sequence - 1]) if prior else locked.state
    latest = next(
        key for key in reversed(state.matches) if state.matches[key].record == incoming.record
    )
    if latest != match_id:
        raise TargetUnavailable("stale", "stale identity choice; review the latest observation")
    state.active(choice.selected)
    payloads = _payloads(state, profile, incoming, choice.selected)
    planned = _events(state, payloads, decision)
    if prior:
        prefix = tuple(locked.state.events[prior.sequence - 1 : prior.sequence - 1 + len(planned)])
        if prefix != planned[: len(prefix)]:
            raise ValueError("identity history diverged from review effects")
        return planned[len(prefix) :]
    return planned


def _context(state: State, match_id: str) -> tuple[Observation, Profile]:
    match = state.matches.get(match_id)
    if match is None:
        raise TargetUnavailable("missing", "identity match disappeared")
    if not match.review_observation or not match.review_profile:
        raise ValueError(
            "legacy match lacks observations; resolve a fresh delivery before accepting"
        )
    incoming = Observation.model_validate_json(match.review_observation)
    profile = Profile.model_validate_json(match.review_profile)
    if profile.digest != match.profile_digest or incoming.record != match.record:
        raise ValueError("identity observation does not match its recorded profile")
    return incoming, profile


def _payloads(
    state: State, profile: Profile, incoming: Observation, selected: str
) -> list[Payload]:
    _require_authority(state, incoming, selected)
    payloads: list[Payload] = []
    linked = False
    for holding in state.links(incoming.record):
        if holding.ended_event is None:
            if holding.kn_id == selected:
                linked = True
            else:
                payloads.append(Unlink(record=incoming.record, kn_id=holding.kn_id))
    if not linked:
        payloads.append(Link(record=incoming.record, kn_id=selected, method="review_decision"))
    payloads.extend(observations(state, profile, incoming, selected, before=None))
    return payloads


def _require_authority(state: State, incoming: Observation, selected: str) -> None:
    for key in incoming.authoritative:
        current, reserved = holder(state, key, incoming.observed_at)
        if reserved:
            raise ValueError("authoritative key has a reserved validity interval")
        if current is not None:
            owner, identifier = current
            if (
                owner != selected
                or identifier.issuer != key.issuer
                or identifier.authority != "authoritative"
            ):
                raise ValueError(
                    "authoritative key conflicts with the selected identity; resolve ownership first"
                )


def _events(state: State, payloads: list[Payload], decision: Decision) -> tuple[Event, ...]:
    previous = state.events[-1] if state.events else None
    planned = []
    for payload in payloads:
        previous = event(
            payload,
            previous=previous,
            occurred_at=decision.performed_at,
            actor=decision.reviewer,
            reason=decision.reason,
            evidence=decision.evidence,
            decision_ref=REVIEW_REF + decision.decision_id,
        )
        planned.append(previous)
    # Validate the whole batch before the decision becomes durable.
    probe = replay(state.events)
    for value in planned:
        probe.apply(value)
    return tuple(planned)


def validate_reference(value: Event, decision: Decision) -> None:
    choice = decision.queue
    payload = value.payload
    if (
        choice is None
        or not choice.kind.startswith("identity_")
        or decision.outcome not in {"accept", "supersede"}
        or not isinstance(payload, (Link, Unlink, Identifier, Attribute))
        or (not isinstance(payload, Unlink) and payload.kn_id != choice.selected)
        or value.actor != decision.reviewer
        or value.reason != decision.reason
        or value.evidence != decision.evidence
        or value.occurred_at != decision.performed_at
    ):
        raise ValueError("identity effect differs from its durable queue decision")
