"""Replay validation of stored match decisions and of the links that cite them."""

from collections.abc import Callable

from kn.identity.model import MATCH_LINK_METHODS, Link, Match, SourceKey


def check_match(payload: Match, active: Callable[[str], object]) -> None:
    """Candidates must be distinct active objects; ``active`` raises for any other ID."""
    keys = [item.kn_id for item in payload.candidates]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate match candidates")
    for key in keys:
        active(key)
    if (payload.decision == "link") != (payload.selected is not None):
        raise ValueError("only link decisions select a candidate")
    if payload.selected is not None and payload.selected not in keys:
        raise ValueError("selected match must be a candidate")
    if payload.trace is not None and (payload.decision == "mint") != (
        payload.trace.minted_id is not None
    ):
        raise ValueError("persisted mint decisions require exactly one new KN ID")
    if payload.trace is not None and (
        (payload.decision == "review" and payload.trace.followup_count != 0)
        or (payload.decision == "mint" and payload.trace.followup_count < 2)
    ):
        raise ValueError("match followup count contradicts the decision")


def check_match_link(payload: Link, match: Match, anchor: SourceKey) -> None:
    """``anchor`` is the anchoring record of the linked object."""
    if match.trace is not None and MATCH_LINK_METHODS.get(match.trace.route) != payload.method:
        raise ValueError("link method must match the recorded resolution route")
    if payload.method == "minted" and match.decision == "mint" and match.trace is not None:
        if match.trace.minted_id != payload.kn_id or anchor != payload.record:
            raise ValueError("minted link must use the recorded source anchor and KN ID")
        score, probability = None, None
    else:
        candidate = next((item for item in match.candidates if item.kn_id == match.selected), None)
        if candidate is None or candidate.kn_id != payload.kn_id:
            raise ValueError("link requires a matching stored decision")
        score, probability = candidate.score, candidate.probability
    recorded = (payload.score, payload.probability, payload.profile_digest, payload.profile_version)
    if recorded != (score, probability, match.profile_digest, match.profile_version):
        raise ValueError("link score and profile must match the stored decision")
