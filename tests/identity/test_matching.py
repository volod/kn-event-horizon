"""Synthetic baseline for resolution decisions and replayable evidence."""

import json
import math
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kn.identity.matching.observe import Key, Observation, Reading
from kn.identity.matching.resolve import resolve
from kn.identity.matching.scoring import verify_candidate
from kn.identity.model import Attribute, Identifier, Mint, SourceKey
from kn.identity.profiles import Profile
from kn.identity.state import replay
from tests.identity.fixtures import NOW, A, B
from tests.identity.test_state import append

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "contracts/core/identity/match-profiles"
CASES = json.loads((ROOT / "tests/fixtures/identity/match-cases.json").read_text())
IDS = (A, B)


def profile(entity_class: str = "core.organization") -> Profile:
    return Profile.model_validate_json(
        (PROFILES / f"{entity_class.split('.')[1]}.json").read_bytes()
    )


def observation(
    attributes: dict[str, str],
    *,
    lei: str | None = None,
    aliases: tuple[str, ...] = (),
    source: str = "fixture:incoming",
    version: str = "1",
) -> Observation:
    return Observation(
        record=SourceKey(source=source, key="00042"),
        version=version,
        observed_at=NOW,
        attributes=tuple(Reading(field_id=key, value=value) for key, value in attributes.items()),
        authoritative=(Key(namespace="lei", issuer="fixture:lei", value=lei),) if lei else (),
        aliases=aliases,
    )


def registry(config: Profile, rows: list[dict]):
    events = ()
    for kn_id, row in zip(IDS, rows, strict=False):
        events = append(
            events,
            Mint(
                kn_id=kn_id,
                entity_class=config.entity_class,
                anchor=SourceKey(source="fixture:known", key=kn_id),
            ),
        )
        for key, raw in row["attributes"].items():
            events = append(
                events,
                Attribute(
                    kn_id=kn_id,
                    field_id=key,
                    original=raw,
                    normalized=raw,
                    normalizer="identity-v1",
                    profile_digest=config.digest,
                ),
            )
        if "lei" in row:
            events = append(
                events,
                Identifier(
                    kn_id=kn_id,
                    valid_from=NOW,
                    authority="authoritative",
                    namespace="lei",
                    issuer="fixture:lei",
                    value=row["lei"],
                ),
            )
    return replay(events)


@pytest.mark.parametrize("case", CASES, ids=[row["case"] for row in CASES])
def test_labeled_resolution(case: dict) -> None:
    config = profile(case["class"])
    if case.get("calibrated"):
        config = calibrated(config)
    state = registry(config, case["objects"])
    incoming = observation(case["incoming"], lei=case.get("lei"))
    match = resolve(state, config, incoming)
    assert match.decision == case["decision"]
    assert [entry.kn_id for entry in match.candidates] == [IDS[i] for i in case["candidates"]]
    assert match.selected == (A if match.decision == "link" else None)
    for entry in match.candidates:
        verify_candidate(config, entry)
    if case.get("calibrated"):
        best, runner_up = match.candidates
        assert config.link_threshold <= runner_up.probability < best.probability
        assert best.probability - runner_up.probability < config.minimum_margin
        assert resolve(registry(config, case["objects"][:1]), config, incoming).selected == A
    state.objects = dict(reversed(list(state.objects.items())))
    state.holdings = dict(reversed(list(state.holdings.items())))
    incoming = incoming.model_copy(update={"attributes": incoming.attributes[::-1]})
    assert resolve(state, config, incoming) == match


def test_shipped_profiles_validate_against_early_wire_schema() -> None:
    schema = json.loads((PROFILES.parent / "match-profile.schema.json").read_text())
    files = sorted(PROFILES.glob("*.json"))
    assert len(files) == 4
    for file in files:
        payload = json.loads(file.read_text())
        Draft202012Validator(schema).validate(payload)
        assert not Profile.model_validate(payload).calibrated


def test_names_cannot_reach_link_threshold() -> None:
    config = profile()
    with pytest.raises(ValueError, match="name or description"):
        Profile.model_validate({**config.model_dump(), "prior": 0.6})


def test_camel_case_name_cannot_be_declared_discriminating() -> None:
    from kn.identity.profiles import Attribute as ProfileAttribute

    legal_name = next(item for item in profile().attributes if item.field_id == "organization.name")
    with pytest.raises(ValueError, match="name or description"):
        ProfileAttribute.model_validate(
            {
                **legal_name.model_dump(),
                "field_id": "organization.legalName",
                "normalizer": "casefold-v1",
                "authority": "authoritative",
                "discriminating": True,
            }
        )


def calibrated(config: Profile) -> Profile:
    return Profile.model_validate(
        {**config.model_dump(), "calibrated": True, "calibration_ref": "fixture:held-out"}
    )


def test_scoring_auto_link_requires_calibration_and_discrimination() -> None:
    config = profile()
    attributes = {
        "organization.name": "Fixture Inc",
        "organization.domain": "fixture.example.com",
        "organization.country": "GB",
    }
    state = registry(config, [{"attributes": attributes}])
    incoming = observation(attributes)
    assert resolve(state, config, incoming).decision == "review"
    match = resolve(state, calibrated(config), incoming)
    assert match.selected == A
    assert match.trace.route == "scored_match"
    only_name = observation({"organization.name": "Fixture Ltd"})
    assert resolve(state, calibrated(config), only_name).decision == "review"


def test_alias_only_similarity_and_weak_sku_never_auto_link() -> None:
    config = calibrated(profile())
    state = registry(config, [{"attributes": {"organization.name": "Fixture Products"}}])
    candidate = observation({"organization.name": "Fixture Product"}, aliases=(A,))
    match = resolve(state, config, candidate)
    assert match.trace.route == "alias"
    assert match.decision == "review"
    assert any(feature.outcome == "similar" for feature in match.candidates[0].features)

    offer = calibrated(profile("core.supplier_offer"))
    state = registry(offer, [{"attributes": {"offer.sku": "00042"}}])
    assert resolve(state, offer, observation({"offer.sku": "00042"})).candidates == ()


def test_order_is_stable_and_ties_never_link_with_zero_margin() -> None:
    config = calibrated(profile())
    config = Profile.model_validate({**config.model_dump(), "minimum_margin": 0})
    attributes = {"organization.domain": "example.com", "organization.country": "GB"}
    state = registry(config, [{"attributes": attributes}, {"attributes": attributes}])
    result = resolve(state, config, observation(attributes))
    assert result.decision == "review"
    assert tuple(item.kn_id for item in result.candidates) == (A, B)


def test_authority_conflict_preserves_existing_source_ownership() -> None:
    from kn.identity.model import Link

    config = profile()
    state = registry(
        config, [{"attributes": {}}, {"attributes": {}, "lei": "00000000000000000042"}]
    )
    existing = observation({})
    state = replay(
        append(tuple(state.events), Link(record=existing.record, kn_id=A, method="minted"))
    )
    assert resolve(state, config, existing).selected == A
    assert resolve(state, config, existing).trace.route == "existing_link"
    conflicting = observation({}, lei="00000000000000000042")
    result = resolve(state, config, conflicting)
    assert result.trace.route == "conflict"
    assert result.decision == "review"
    assert tuple(item.kn_id for item in result.candidates) == (A, B)


def test_authoritative_identifier_validity_and_issuer() -> None:
    from datetime import timedelta

    config = profile()
    state = registry(config, [{"attributes": {}}, {"attributes": {}}])
    key = observation({}, lei="00000000000000000042")
    base = Identifier(
        kn_id=A,
        namespace="lei",
        issuer="fixture:lei",
        value=key.authoritative[0].value,
        authority="authoritative",
        valid_from=NOW - timedelta(days=1),
        valid_to=NOW,
    )
    history = append(tuple(state.events), base)
    later = Identifier.model_validate(
        {**base.model_dump(), "kn_id": B, "valid_from": NOW, "valid_to": None}
    )
    current = replay(append(history, later))
    assert resolve(current, config, key).selected == B
    earlier = key.model_copy(update={"observed_at": NOW - timedelta(hours=1)})
    assert resolve(current, config, earlier).selected == A
    wrong_issuer = key.model_copy(
        update={"authoritative": (Key(namespace="lei", issuer="fixture:wrong", value=base.value),)}
    )
    assert resolve(current, config, wrong_issuer).decision == "review"


def test_recorded_score_replays_and_modified_features_refuse() -> None:
    from kn.identity.matching.scoring import verify_match

    config = profile()
    attributes = {"organization.domain": "example.com", "organization.country": "GB"}
    match = resolve(registry(config, [{"attributes": attributes}]), config, observation(attributes))
    verify_match(config, match)
    with pytest.raises(ValueError, match="profile version and digest"):
        verify_match(calibrated(config), match)
    candidate = match.candidates[0]
    likelihood_ratio = (0.98 / 0.01) * (0.85 / 0.25)
    odds = config.prior / (1 - config.prior) * likelihood_ratio
    assert candidate.score == pytest.approx(math.log(likelihood_ratio))
    assert candidate.probability == pytest.approx(odds / (1 + odds))
    with pytest.raises(ValueError, match="score or probability"):
        verify_candidate(config, candidate.model_copy(update={"score": candidate.score + 1}))
    features = candidate.features
    altered = (features[0].model_copy(update={"weight": features[0].weight + 1}), *features[1:])
    with pytest.raises(ValueError, match="comparator or weight"):
        verify_candidate(config, candidate.model_copy(update={"features": altered}))
