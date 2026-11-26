"""Discriminating attribute changes on an existing source link require human review."""

from kn.identity.matching.comparators import DISAGREE
from kn.identity.matching.observe import Observation
from kn.identity.matching.registry import current_attributes
from kn.identity.matching.scoring import prepare, score
from kn.identity.model import Match
from kn.identity.profiles import Profile
from kn.identity.state import State


def guard(state: State, profile: Profile, incoming: Observation, match: Match) -> Match:
    if match.selected is None or match.trace is None or match.trace.route != "existing_link":
        return match
    fields = {attribute.field_id for attribute in profile.attributes if attribute.discriminating}
    new = prepare(profile, {reading.field_id: reading.value for reading in incoming.attributes})
    views = current_attributes(state, {match.selected}, incoming.observed_at).get(
        match.selected, ()
    )
    for raw in views:
        old = prepare(profile, raw)
        if any(
            feature.field_id in fields and feature.outcome == DISAGREE
            for feature in score(profile, match.selected, new, old).features
        ):
            return match.model_copy(
                update={
                    "decision": "review",
                    "selected": None,
                    "trace": match.trace.model_copy(update={"route": "conflict"}),
                }
            )
    return match
