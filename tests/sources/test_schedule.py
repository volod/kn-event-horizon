"""Measure UTC schedules and refuse ones that never run or have ambiguous day fields."""

from datetime import date
from pathlib import Path

import pytest

from kn.contracts.document import read_document
from kn.sources.config import load_crawler_config
from kn.sources.config.schedule import longest_interval_seconds
from kn.sources.config.schema import CrawlerConfigError
from tests.sources.test_config import CONFIGS, write_config

DAY = 86400


@pytest.mark.parametrize(
    ("cron", "seconds"),
    [
        ("* * * * *", 60),
        ("0 */2 * * *", 7200),
        ("30 6,18 * * *", 12 * 3600),
        ("*/15 9-17 * * 1-5", (2 * 24 + 15) * 3600 + 15 * 60),
        ("0 12 * * 7", 7 * DAY),
        ("0 12 * * 0", 7 * DAY),
        ("0 0 31 * *", 61 * DAY),
        ("0 0 1 1 *", 366 * DAY),
        ("0 0 29 2 *", (date(2104, 2, 29) - date(2096, 2, 29)).days * DAY),
    ],
)
def test_longest_interval_spans_the_largest_gap_between_runs(cron: str, seconds: int) -> None:
    assert longest_interval_seconds(cron) == seconds


@pytest.mark.parametrize(
    ("cron", "rule"),
    [
        ("0 0 30 2 *", "cronNeverRuns"),
        ("0 0 31 4,6,9,11 *", "cronNeverRuns"),
        ("0 0 1 * 1", "cronDays"),
        ("0 0 */2 * 1-5", "cronDays"),
        ("0 0 * *", "cron"),
    ],
)
def test_unusable_schedules_are_refused(tmp_path: Path, cron: str, rule: str) -> None:
    config = read_document(CONFIGS / "http.yaml")
    config["schedule"]["cron"] = cron
    with pytest.raises(CrawlerConfigError) as caught:
        load_crawler_config(write_config(tmp_path, config))
    assert (caught.value.path, caught.value.rule) == ("$/schedule/cron", rule)
