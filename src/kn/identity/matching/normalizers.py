"""Stable text preparation for identity fields."""

import re
import unicodedata
from collections.abc import Callable
from functools import cache
from urllib.parse import urlsplit

import idna
from publicsuffixlist import PublicSuffixList

LEGAL_SUFFIXES = frozenset(
    {"ag", "corp", "corporation", "gmbh", "inc", "incorporated", "limited", "llc", "ltd", "plc"}
)
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
GTIN_LENGTHS = frozenset({8, 12, 13, 14})
GTIN_WIDTH = 14


def folded(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def legal_name(value: str) -> str:
    tokens = re.findall(r"[^\W_]+", folded(value))
    while len(tokens) > 1 and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def mpn(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().upper()


@cache
def _suffixes() -> PublicSuffixList:
    return PublicSuffixList(accept_unknown=False)


def domain(value: str) -> str | None:
    value = value.strip()
    if CONTROL.search(value):
        return None
    try:
        url = urlsplit(value if "://" in value or value.startswith("//") else f"//{value}")
        if url.scheme not in {"", "http", "https"} or url.username is not None:
            return None
        host = idna.encode(url.hostname or "", uts46=True).decode("ascii").removesuffix(".")
    except ValueError:
        return None
    if len(host) > 253 or any(not HOST_LABEL.fullmatch(part) for part in host.split(".")):
        return None
    result: str | None = _suffixes().privatesuffix(host)
    return result


def gtin(value: str) -> str | None:
    value = value.strip()
    if len(value) not in GTIN_LENGTHS or not re.fullmatch(r"[0-9]+", value):
        return None
    digits = [int(char) for char in reversed(value)]
    if sum(digit * (3 if i % 2 else 1) for i, digit in enumerate(digits)) % 10:
        return None
    return value.zfill(GTIN_WIDTH)


NORMALIZERS: dict[str, Callable[[str], str | None]] = {
    "identity-v1": lambda value: value,
    "casefold-v1": folded,
    "identifier-v1": str.strip,
    "upper-identifier-v1": mpn,
    "mpn-v1": mpn,
    "legal-name-v1": legal_name,
    "registrable-domain-v1": domain,
    "gtin-v1": gtin,
}


def normalize(normalizer: str, value: str) -> str | None:
    result = NORMALIZERS[normalizer](value)
    return result if result and result.strip() else None
