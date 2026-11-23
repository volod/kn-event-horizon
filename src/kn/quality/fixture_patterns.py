"""Recognize common sensitive values without parsing or executing source content."""

import csv
import re
from html import unescape
from io import StringIO
from urllib.parse import unquote

_EMPTY_VALUES = {"", "null", "~", "[redacted]", "<redacted>"}
_EXAMPLE_DOMAINS = {"example.com", "example.net", "example.org", "example.test"}
_TEXT_ESCAPE = re.compile(r"\\(?:u([0-9a-fA-F]{4})|x([0-9a-fA-F]{2}))")
_EMAIL_CHARACTERS = r"\w.!#$%&'*+/=?^`{|}~-"
_EMAIL = re.compile(
    rf"(?<![{_EMAIL_CHARACTERS}])[{_EMAIL_CHARACTERS}]{{1,64}}"
    r"@([a-z0-9-]{1,63}(?:\.[a-z0-9-]{1,63})+)",
    re.I,
)
_CREDENTIAL_VALUE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{36,})\b"
    r"|\bAIza[A-Za-z0-9_-]{35}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{10,}\b"
    r"|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"|\b[a-zA-Z][a-zA-Z0-9+.-]{0,31}://[^\s/?#@`<>\"']+@"
)
_KEYS = {
    "credential": (
        "authorization",
        "proxy_authorization",
        "api_key",
        "x_api_key",
        "api_token",
        "token",
        "access_token",
        "auth_token",
        "refresh_token",
        "id_token",
        "client_secret",
        "secret",
        "secret_key",
        "aws_secret_access_key",
        "password",
        "passwd",
        "private_key",
        "cookie",
        "set_cookie",
        "session_id",
    ),
    "personal": (
        "email",
        "email_address",
        "personal_email",
        "phone",
        "phone_number",
        "telephone",
        "mobile_number",
        "street_address",
        "home_address",
        "postal_address",
        "full_name",
        "first_name",
        "last_name",
        "date_of_birth",
        "birth_date",
        "ssn",
        "social_security_number",
        "passport_number",
    ),
}


def _key_pattern(keys: tuple[str, ...]) -> str:
    return "(?:" + "|".join("[-_ ]?".join(key.split("_")) for key in keys) + ")"


_COLUMN = {rule: re.compile(_key_pattern(keys), re.I) for rule, keys in _KEYS.items()}
_VALUE = r"""("[^"\r\n]*"|'[^'\r\n]*'|(?:\[redacted\]|<redacted>)?[^,\r\n&<>}\]]*)"""
_ASSIGNMENT = {
    rule: re.compile(
        rf"""(?:(?<![\w-])["']?{key.pattern}["']?[ \t]*(?:=|:(?:[ \t]*\r?\n"""
        rf"""(?:[ \t]+|(?=["'])))?)[ \t]*"""
        rf"|<{key.pattern}(?:[ \t][^<>]*)?>[ \t\r\n]*){_VALUE}",
        re.I,
    )
    for rule, key in _COLUMN.items()
}
_DELIMITERS = {".csv": ",", ".tsv": "\t"}


def _decode_escape(match: re.Match[str]) -> str:
    value = chr(int(match[1] or match[2], 16))
    # Preserve encoded delimiters such as quotes, which form part of the fixture syntax.
    return match[0] if value in {'"', "'", "\\", "\r", "\n"} else value


def _normalized(text: str) -> str:
    return _TEXT_ESCAPE.sub(_decode_escape, unescape(unquote(text)))


def _reserved_email(domain: str) -> bool:
    return domain in _EXAMPLE_DOMAINS or domain.endswith((".example", ".test", ".invalid"))


def _has_value(rule: str, value: str) -> bool:
    value = _normalized(value.strip().strip("'\"")).strip().lower()
    if rule == "personal" and (email := _EMAIL.fullmatch(value)):
        return not _reserved_email(email[1])
    return value not in _EMPTY_VALUES


def sensitive_patterns(text: str) -> set[str]:
    """Find credential or personal data indicators in headers, assignments and text."""
    findings = _text_findings(text)
    normalized = _normalized(text)
    if normalized != text:
        findings.update(_text_findings(normalized))
    return findings


def _text_findings(content: str) -> set[str]:
    findings = {
        rule
        for rule, pattern in _ASSIGNMENT.items()
        if any(_has_value(rule, match[1]) for match in pattern.finditer(content))
    }
    if _CREDENTIAL_VALUE.search(content):
        findings.add("credential")
    if any(not _reserved_email(match[1].lower()) for match in _EMAIL.finditer(content)):
        findings.add("personal")
    return findings


def sensitive_columns(text: str, suffix: str) -> set[str]:
    """Inspect values under sensitive CSV/TSV headers, even in quoted or multiline cells."""
    if suffix not in _DELIMITERS:
        return set()
    rows = csv.reader(StringIO(text, newline=""), delimiter=_DELIMITERS[suffix])
    header = next(rows, [])
    sensitive = [
        (index, rule)
        for index, name in enumerate(header)
        for rule, pattern in _COLUMN.items()
        if pattern.fullmatch(_normalized(name).strip())
    ]
    if not sensitive:
        return set()
    return {
        rule
        for row in rows
        for index, rule in sensitive
        if index < len(row) and _has_value(rule, row[index])
    }
