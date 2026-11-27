"""Validate five-field UTC schedules and measure the longest gap between their runs."""

import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from itertools import pairwise

_CRON_FIELDS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
_CRON_ITEM = re.compile(r"(\*|([0-9]{1,2})(?:-([0-9]{1,2}))?)(?:/([0-9]{1,2}))?")
_ANY = "*"
_DAYS_PER_WEEK = 7
_MINUTES_PER_HOUR = 60
_MINUTES_PER_DAY = 24 * _MINUTES_PER_HOUR
_SECONDS_PER_MINUTE = 60
# Weekdays and leap years repeat exactly every 400 Gregorian years.
_CYCLE_START = date(2000, 1, 1).toordinal()
_CYCLE_DAYS = 146097


@dataclass(frozen=True, slots=True)
class _Cron:
    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int] | None
    months: frozenset[int]
    weekdays: frozenset[int] | None


def _valid_item(item: str, minimum: int, maximum: int) -> bool:
    match = _CRON_ITEM.fullmatch(item)
    if match is None:
        return False
    base, first, last, step = match.groups()
    if step is not None and (int(step) < 1 or int(step) > maximum - minimum + 1):
        return False
    if base == _ANY:
        return True
    if step is not None and last is None:
        return False
    final = int(last) if last is not None else int(first)
    return minimum <= int(first) <= final <= maximum


def _values(field: str, minimum: int, maximum: int) -> frozenset[int]:
    values: set[int] = set()
    for item in field.split(","):
        match = _CRON_ITEM.fullmatch(item)
        assert match is not None
        base, first, last, step = match.groups()
        low, high = (minimum, maximum) if base == _ANY else (int(first), int(last or first))
        values.update(range(low, high + 1, int(step or 1)))
    return frozenset(values)


def _parse(expression: str) -> _Cron | None:
    """Support numeric fields, lists, ranges and positive steps on ranges or wildcards."""
    fields = expression.split()
    if len(fields) != len(_CRON_FIELDS) or not all(
        _valid_item(item, minimum, maximum)
        for field, (minimum, maximum) in zip(fields, _CRON_FIELDS, strict=True)
        for item in field.split(",")
    ):
        return None
    minutes, hours, days, months, weekdays = (
        _values(field, *bounds) for field, bounds in zip(fields, _CRON_FIELDS, strict=True)
    )
    return _Cron(
        minutes,
        hours,
        None if fields[2] == _ANY else days,
        months,
        None if fields[4] == _ANY else frozenset(day % _DAYS_PER_WEEK for day in weekdays),
    )


def _runs_on(cron: _Cron, day: date) -> bool:
    return (
        day.month in cron.months
        and (cron.days is None or day.day in cron.days)
        and (cron.weekdays is None or day.isoweekday() % _DAYS_PER_WEEK in cron.weekdays)
    )


@cache
def _longest_day_gap(cron: _Cron) -> int | None:
    """Return the most days between consecutive run days, or None when no date matches."""
    first: int | None = None
    previous: int | None = None
    longest = 0
    for ordinal in range(_CYCLE_START, _CYCLE_START + _CYCLE_DAYS):
        if _runs_on(cron, date.fromordinal(ordinal)):
            first = ordinal if first is None else first
            longest = longest if previous is None else max(longest, ordinal - previous)
            previous = ordinal
    if first is None or previous is None:
        return None
    return max(longest, first + _CYCLE_DAYS - previous)


def schedule_problem(expression: str) -> tuple[str, str] | None:
    """Return the rule and hint that refuse an expression, or None when it can run."""
    cron = _parse(expression)
    if cron is None:
        return "cron", "use a valid five-field numeric UTC expression"
    if cron.days is not None and cron.weekdays is not None:
        # Cron implementations disagree on whether both day fields must match or either one.
        return "cronDays", "restrict either the day of month or the day of week"
    if _longest_day_gap(cron) is None:
        return "cronNeverRuns", "use a schedule that matches at least one calendar date"
    return None


def longest_interval_seconds(expression: str) -> int:
    """Measure the largest gap between consecutive runs of a schedule that can run."""
    if schedule_problem(expression) is not None:
        raise ValueError("schedule cannot run")
    cron = _parse(expression)
    assert cron is not None
    times = sorted(
        hour * _MINUTES_PER_HOUR + minute for hour in cron.hours for minute in cron.minutes
    )
    day_gap = _longest_day_gap(cron)
    assert day_gap is not None
    within_day = max((later - earlier for earlier, later in pairwise(times)), default=0)
    overnight = day_gap * _MINUTES_PER_DAY - (times[-1] - times[0])
    return max(within_day, overnight) * _SECONDS_PER_MINUTE
