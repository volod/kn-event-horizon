"""The early profile schema accepts domain declarations without executing matching."""

import json
from pathlib import Path

import pytest

from kn.identity.profiles import Profile


def profile() -> Profile:
    return Profile.model_validate(
        {
            "profile_id": "fixture.organization",
            "version": "1.0.0",
            "entity_class": "core.organization",
            "blocking_keys": [["organization.name"]],
            "attributes": [
                {
                    "field_id": "organization.name",
                    "normalizer": "casefold-v1",
                    "comparator": "exact",
                    "authority": "weak",
                    "discriminating": False,
                    "agreements": [
                        {"outcome": "agree", "m": 0.8, "u": 0.1},
                        {"outcome": "disagree", "m": 0.2, "u": 0.9},
                    ],
                }
            ],
            "prior": 0.01,
            "review_threshold": 0.5,
            "link_threshold": 0.99,
            "minimum_margin": 0.1,
        }
    )


def test_profile_schema_and_digest_are_stable() -> None:
    path = Path(__file__).resolve().parents[2] / "contracts/core/identity/match-profile.schema.json"
    assert json.loads(path.read_text()) == Profile.model_json_schema()
    value = profile()
    assert Profile.model_validate_json(value.model_dump_json()).digest == value.digest
    assert not value.calibrated


@pytest.mark.parametrize(
    "changes",
    [
        {"prior": 0},
        {"prior": 1},
        {"prior": "0.5"},
        {"minimum_margin": -1},
        {"blocking_keys": [["missing"]]},
        {"blocking_keys": [[]]},
        {"review_threshold": 0.999},
        {"calibrated": True},
    ],
)
def test_invalid_profiles_fail_before_domain_deployment(changes: dict) -> None:
    with pytest.raises(ValueError):
        Profile.model_validate({**profile().model_dump(), **changes})
