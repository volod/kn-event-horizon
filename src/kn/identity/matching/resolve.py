"""Pure, deterministic resolution over an identity registry snapshot."""

from collections.abc import Mapping
from dataclasses import dataclass

from kn.contracts.model import canonical
from kn.identity.matching.comparators import AGREEING_OUTCOMES
from kn.identity.matching.observe import Observation
from kn.identity.matching.registry import (
    anchor,
    authoritative_targets,
    current_attributes,
    source_links,
)
from kn.identity.matching.scoring import Value, blocks, prepare, score, shortcut
from kn.identity.model import Candidate, Match, MatchDecision, MatchRoute, MatchTrace
from kn.identity.profiles import Profile
from kn.identity.state import State


@dataclass(frozen=True)
class Decision:
    route: MatchRoute
    decision: MatchDecision
    candidates: tuple[Candidate, ...] = ()
    selected: str | None = None


def _rank(candidates: list[Candidate]) -> tuple[Candidate, ...]:
    return tuple(sorted(candidates, key=lambda item: (-item.score, item.kn_id)))


def _exact(state: State, incoming: Observation, active: set[str]) -> Decision | None:
    authority, occupied = authoritative_targets(
        state, incoming.authoritative, active, incoming.observed_at
    )
    hits = {
        kn_id: shortcut(kn_id, "authoritative_key", tuple(canonical(key.parts) for key in keys))
        for kn_id, keys in authority.items()
    }
    links = source_links(state, incoming.record)
    linked = next((item.kn_id for item in links if item.ended_event is None), None)
    anchored = anchor(state, incoming.record)
    existing = linked or (anchored if not links and anchored in active else None)
    source_key = (canonical(incoming.record.model_dump(mode="json")),)
    if existing in active and existing is not None:
        hits.setdefault(existing, shortcut(existing, "existing_link", source_key))
    if occupied or len(hits) > 1 or (linked is not None and linked not in active):
        return Decision("conflict", "review", _rank(list(hits.values())))
    if hits:
        (candidate,) = hits.values()
        route: MatchRoute = "authoritative_key" if candidate.kn_id in authority else "existing_link"
        return Decision(route, "link", (candidate,), candidate.kn_id)
    if anchored is not None:
        # Anchors are never reused; an ended or terminal anchor needs a lifecycle decision.
        return Decision("conflict", "review")
    return None


def _can_link(profile: Profile, ranked: tuple[Candidate, ...]) -> bool:
    best = ranked[0]
    if not profile.calibrated or best.probability < profile.link_threshold:
        return False
    if len(ranked) > 1:
        runner_up = ranked[1]
        if best.probability <= runner_up.probability:
            return False
        if best.probability - runner_up.probability < profile.minimum_margin:
            return False
    discriminators = {item.field_id for item in profile.attributes if item.discriminating}
    return any(
        item.field_id in discriminators and item.outcome in AGREEING_OUTCOMES
        for item in best.features
    )


def _scored(state: State, profile: Profile, incoming: Observation, active: set[str]) -> Decision:
    left = prepare(profile, {item.field_id: item.value for item in incoming.attributes})
    aliases = active.intersection(incoming.aliases)
    right = {
        kn_id: prepare(profile, raw)
        for kn_id, raw in current_attributes(state, active, incoming.observed_at).items()
    }
    blocked = _rank(
        [
            score(profile, kn_id, left, values)
            for kn_id, values in right.items()
            if blocks(profile, left, values)
        ]
    )
    if blocked and _can_link(profile, blocked):
        return Decision("scored_match", "link", blocked, blocked[0].kn_id)
    if aliases:
        known = {item.kn_id for item in blocked}
        return Decision(
            "alias", "review", _with_aliases(profile, left, right, blocked, aliases - known)
        )
    if blocked and blocked[0].probability >= profile.review_threshold:
        return Decision("scored_match", "review", blocked)
    return Decision("no_match", "mint", blocked)


def _with_aliases(
    profile: Profile,
    left: Mapping[str, Value],
    right: Mapping[str, dict[str, Value]],
    blocked: tuple[Candidate, ...],
    aliases: set[str],
) -> tuple[Candidate, ...]:
    return _rank([*blocked, *(score(profile, key, left, right.get(key, {})) for key in aliases)])


def resolve(state: State, profile: Profile, incoming: Observation) -> Match:
    """Resolve at the observation instant. Candidate selection never changes registry state."""
    active = {
        key
        for key, item in state.objects.items()
        if item.state == "active" and item.entity_class == profile.entity_class
    }
    result = _exact(state, incoming, active) or _scored(state, profile, incoming, active)
    profile_digest = profile.digest
    return Match(
        record=incoming.record,
        profile_digest=profile_digest,
        profile_version=profile.version,
        decision=result.decision,
        selected=result.selected,
        candidates=result.candidates,
        trace=MatchTrace(
            route=result.route,
            request_digest=incoming.fingerprint(profile_digest),
            source_version=incoming.version,
            prior=profile.prior,
        ),
    )
