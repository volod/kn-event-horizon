"""Derive source status thresholds from a validated crawler profile without a database."""

from typing import Any

import pytest

from kn.contracts.document import read_document
from kn.sources.status import MonitoringPolicy, monitoring_policy
from tests.sources.test_config import CONFIGS


@pytest.fixture
def config() -> dict[str, Any]:
    return read_document(CONFIGS / "http.yaml")


def test_freshness_defaults_to_twice_the_longest_schedule_interval(
    config: dict[str, Any],
) -> None:
    assert config["schedule"]["cron"] == "0 */2 * * *"
    assert "freshness_seconds" not in config["schedule"]
    assert monitoring_policy(config) == MonitoringPolicy(4 * 3600, 3)
    config["schedule"]["cron"] = "0 6 * * 1-5"
    assert monitoring_policy(config).freshness_seconds == 2 * 3 * 86400


def test_declared_threshold_overrides_the_schedule_default(config: dict[str, Any]) -> None:
    config["schedule"]["freshness_seconds"] = 60
    del config["monitoring"]["alert_thresholds"]["consecutive_failures"]
    assert monitoring_policy(config) == MonitoringPolicy(60, None)
