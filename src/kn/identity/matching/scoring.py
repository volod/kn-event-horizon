"""Feature preparation, blocking, scoring, and evidence verification."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from kn.identity.matching.comparators import compare
from kn.identity.matching.likelihood import posterior, weight
from kn.identity.matching.normalizers import normalize
from kn.identity.model import Candidate, Feature, Match
from kn.identity.profiles import Attribute, Profile

SHORTCUTS = frozenset({"authoritative_key", "existing_link"})


@dataclass(frozen=True)
class Value:
    original: str
    normalized: str


def prepare(profile: Profile, raw: Mapping[str, str]) -> dict[str, Value]:
    prepared: dict[str, Value] = {}
    for item in sorted(profile.attributes, key=lambda attribute: attribute.field_id):
        if (original := raw.get(item.field_id)) is None:
            continue
        normalized = normalize(item.normalizer, original)
        if normalized is None:
            continue
        compared = original if item.comparator == "exact" else normalized
        if compare(item.comparator, compared, compared, item.tolerance) == "agree":
            prepared[item.field_id] = Value(original, normalized)
    return prepared


def blocks(profile: Profile, left: Mapping[str, Value], right: Mapping[str, Value]) -> bool:
    return any(
        all(
            key in left and key in right and left[key].normalized == right[key].normalized
            for key in block
        )
        for block in profile.blocking_keys
    )


def _feature(attribute: Attribute, left: str | None, right: str | None) -> Feature:
    outcome = compare(attribute.comparator, left, right, attribute.tolerance)
    level = next((part for part in attribute.agreements if part.outcome == outcome), None)
    return Feature(
        field_id=attribute.field_id,
        left=left,
        right=right,
        comparator=attribute.comparator,
        outcome=outcome,
        weight=weight(level.m, level.u) if level is not None else 0.0,
    )


def _side(attribute: Attribute, values: Mapping[str, Value]) -> str | None:
    value = values.get(attribute.field_id)
    if value is None:
        return None
    return value.original if attribute.comparator == "exact" else value.normalized


def score(
    profile: Profile, kn_id: str, left: Mapping[str, Value], right: Mapping[str, Value]
) -> Candidate:
    features = tuple(
        _feature(item, _side(item, left), _side(item, right))
        for item in sorted(profile.attributes, key=lambda attribute: attribute.field_id)
    )
    total = math.fsum(part.weight for part in features)
    return Candidate(
        kn_id=kn_id, features=features, score=total, probability=posterior(profile.prior, total)
    )


def shortcut(kn_id: str, method: str, values: tuple[str, ...]) -> Candidate:
    return Candidate(
        kn_id=kn_id,
        features=tuple(
            Feature(
                field_id=method,
                left=value,
                right=value,
                comparator=method,
                outcome="agree",
                weight=0,
            )
            for value in values
        ),
        score=0,
        probability=1,
    )


def verify_candidate(profile: Profile, candidate: Candidate) -> None:
    """Recreate comparator outcomes, weights, score, and probability from recorded operands."""
    if candidate.features and all(_shortcut_feature(item) for item in candidate.features):
        if (candidate.score, candidate.probability) == (0, 1):
            return
        raise ValueError("shortcut probability and score do not reproduce")
    attributes = sorted(profile.attributes, key=lambda item: item.field_id)
    if len(attributes) != len(candidate.features):
        raise ValueError("candidate does not cover the profile attributes")
    for attribute, feature in zip(attributes, candidate.features, strict=True):
        if feature != _feature(attribute, feature.left, feature.right):
            raise ValueError("recorded comparator or weight does not reproduce")
    total = math.fsum(item.weight for item in candidate.features)
    if (candidate.score, candidate.probability) != (total, posterior(profile.prior, total)):
        raise ValueError("recorded score or probability does not reproduce")


def verify_match(profile: Profile, match: Match) -> None:
    """Verify a match against the exact profile used to produce it."""
    if (match.profile_digest, match.profile_version) != (profile.digest, profile.version):
        raise ValueError("match requires the recorded profile version and digest")
    if match.trace is not None and match.trace.prior != profile.prior:
        raise ValueError("recorded prior does not match the profile")
    for candidate in match.candidates:
        verify_candidate(profile, candidate)


def _shortcut_feature(item: Feature) -> bool:
    return (
        item.field_id == item.comparator
        and item.comparator in SHORTCUTS
        and item.left is not None
        and item.left == item.right
        and item.outcome == "agree"
        and item.weight == 0
    )
