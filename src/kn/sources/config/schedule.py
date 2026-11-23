"""Validate five-field UTC schedules without expanding their run times."""

import re

_CRON_FIELDS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
_CRON_ITEM = re.compile(r"(\*|([0-9]{1,2})(?:-([0-9]{1,2}))?)(?:/([0-9]{1,2}))?")


def _valid_item(item: str, minimum: int, maximum: int) -> bool:
    match = _CRON_ITEM.fullmatch(item)
    if match is None:
        return False
    base, first, last, step = match.groups()
    if step is not None and (int(step) < 1 or int(step) > maximum - minimum + 1):
        return False
    if base == "*":
        return True
    if step is not None and last is None:
        return False
    final = int(last) if last is not None else int(first)
    return minimum <= int(first) <= final <= maximum


def valid_cron(expression: str) -> bool:
    """Support numeric fields, lists, ranges and positive steps on ranges or wildcards."""
    fields = expression.split()
    if len(fields) != len(_CRON_FIELDS):
        return False
    return all(
        _valid_item(item, minimum, maximum)
        for field, (minimum, maximum) in zip(fields, _CRON_FIELDS, strict=True)
        for item in field.split(",")
    )
