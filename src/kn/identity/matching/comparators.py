"""Deterministic comparisons for scalar and collection identity values."""

import json
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from fractions import Fraction
from typing import Literal

Comparator = Literal[
    "exact", "normalized_exact", "graded_string", "numeric_tolerance", "date_window", "set_overlap"
]
type Outcome = Literal["agree", "similar", "disagree", "missing", "invalid"]

COMPARISON_OUTCOMES = frozenset({"agree", "disagree"})
GRADED_OUTCOMES = COMPARISON_OUTCOMES | {"similar"}
AGREEING_OUTCOMES = frozenset({"agree", "similar"})
STRING_SIMILARITY = 0.85
MAX_GRADED_LENGTH = 512
DEFAULT_SET_OVERLAP = 0.5
NUMERIC_EXPONENT_LIMIT = 1000
MAX_NUMERIC_LENGTH = 512


def _equality(matches: bool) -> Outcome:
    return "agree" if matches else "disagree"


def _exact(left: str, right: str, tolerance: float | None) -> Outcome:
    return _equality(left == right)


def _graded(left: str, right: str, tolerance: float | None) -> Outcome:
    if max(len(left), len(right)) > MAX_GRADED_LENGTH:
        return "invalid"
    if left == right:
        return "agree"
    first, second = sorted((left, right))
    ratio = SequenceMatcher(None, first, second, autojunk=False).ratio()
    return "similar" if ratio >= STRING_SIMILARITY else "disagree"


def _number(value: str) -> Fraction:
    if len(value) > MAX_NUMERIC_LENGTH:
        raise ValueError("numeric identity value outside supported bounds")
    number = Decimal(value)
    if not number.is_finite() or abs(number.adjusted()) > NUMERIC_EXPONENT_LIMIT:
        raise ValueError("numeric identity value outside supported bounds")
    return Fraction(number)


def _numeric(left: str, right: str, tolerance: float | None) -> Outcome:
    if tolerance is None:
        return "invalid"
    try:
        difference = abs(_number(left) - _number(right))
    except (InvalidOperation, ValueError):
        return "invalid"
    return _equality(difference <= Fraction(str(tolerance)))


def _iso_date(value: str) -> date:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("date comparator requires YYYY-MM-DD")
    return date.fromisoformat(value)


def _date_window(left: str, right: str, tolerance: float | None) -> Outcome:
    try:
        days = abs((_iso_date(left) - _iso_date(right)).days)
    except ValueError:
        return "invalid"
    return _equality(days <= (tolerance if tolerance is not None else 0))


def _string_set(value: str) -> set[str]:
    items: object = json.loads(value)
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError("set comparator requires a JSON array of strings")
    return set(items)


def _overlap(left: str, right: str, tolerance: float | None) -> Outcome:
    try:
        a, b = _string_set(left), _string_set(right)
    except (ValueError, RecursionError):
        return "invalid"
    if not a or not b:
        return "missing"
    floor = DEFAULT_SET_OVERLAP if tolerance is None else tolerance
    return _equality(len(a & b) / len(a | b) >= floor)


COMPARATORS: dict[Comparator, Callable[[str, str, float | None], Outcome]] = {
    "exact": _exact,
    "normalized_exact": _exact,
    "graded_string": _graded,
    "numeric_tolerance": _numeric,
    "date_window": _date_window,
    "set_overlap": _overlap,
}


def compare(
    comparator: Comparator, left: str | None, right: str | None, tolerance: float | None
) -> Outcome:
    if left is None or right is None:
        return "missing"
    return COMPARATORS[comparator](left, right, tolerance)
