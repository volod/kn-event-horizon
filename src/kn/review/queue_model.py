"""Queue kind registry and safe domain path components."""

import re

from kn.review.model import QUEUE_KINDS
from kn.review.model import Choice as Choice


def domain_name(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", value):
        raise ValueError("use a domain slug")
    return value


KINDS = QUEUE_KINDS
