"""Prepare approved captures before any archive identifiers or records are written."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import SplitResult, unquote, unquote_plus, urlsplit

from kn.archive.model import (
    ArchiveError,
    Capture,
    Headers,
    Kind,
    Redaction,
)

_HEADER_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_SECRET_QUERY = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "client_secret",
        "credential",
        "key",
        "password",
        "secret",
        "signature",
        "token",
    }
)
_SECRET_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token"}
)
_REQUEST_HEADERS = frozenset(
    {
        "accept",
        "accept-charset",
        "accept-encoding",
        "accept-language",
        "content-type",
        "if-match",
        "if-modified-since",
        "if-none-match",
        "if-unmodified-since",
        "range",
    }
)
_RESPONSE_HEADERS = frozenset(
    {
        "cache-control",
        "content-encoding",
        "content-language",
        "content-range",
        "content-type",
        "date",
        "etag",
        "expires",
        "last-modified",
        "vary",
    }
)


@dataclass(frozen=True, slots=True)
class Prepared:
    origin_uri: str
    fetched_at: datetime
    kind: Kind
    mime_type: str | None
    request_headers: Headers
    response_headers: Headers
    request_sha256: str | None
    encoding: str


def _printable(value: str) -> bool:
    return value.isascii() and all(32 <= ord(char) < 127 for char in value)


def _has_secret(value: str, secrets: tuple[str, ...]) -> bool:
    decoded = unquote_plus(value).casefold()
    return any(
        secret.casefold() in decoded or secret.casefold() in value.casefold()
        for secret in secrets
        if secret
    )


def _header_secrets(capture: Capture, policy: Redaction) -> tuple[str, ...]:
    if capture.http is None:
        return ()
    names = _SECRET_HEADERS | {name.casefold() for name in policy.header_names}
    secrets: list[str] = []
    for name, value in (*capture.http.request_headers, *capture.http.response_headers):
        name = name.casefold()
        if name in names and value:
            secrets.extend(_credential_values(name, value))
    return tuple(secrets)


def _credential_values(name: str, value: str) -> tuple[str, ...]:
    if name in {"authorization", "proxy-authorization"}:
        return (value.split(maxsplit=1)[-1],) if value.strip() else ()
    if name in {"cookie", "set-cookie"}:
        cookies = value.split(";") if name == "cookie" else value.split(";", 1)[:1]
        return tuple(cookie.partition("=")[2].strip().strip('"') for cookie in cookies)
    return (value.strip(),)


def _query(parsed: SplitResult, policy: Redaction) -> tuple[list[str], tuple[str, ...]]:
    names = _SECRET_QUERY | {name.casefold() for name in policy.query_parameters}
    parts = parsed.query.split("&") if parsed.query else []
    kept = []
    secrets: list[str] = []
    for part in parts:
        name, _, value = part.partition("=")
        name = unquote_plus(name).casefold()
        if name in names or name.startswith(("x-amz-", "x-goog-")):
            if value:
                secrets.append(unquote_plus(value))
        else:
            kept.append(part)
    return kept, tuple(secrets)


def _origin(
    uri: str, policy: Redaction, header_secrets: tuple[str, ...], *, http: bool
) -> tuple[str, tuple[str, ...], bool]:
    if len(uri) > 8192 or not _printable(uri) or " " in uri or "\\" in uri:
        raise ArchiveError("origin_uri")
    try:
        parsed = urlsplit(uri)
        _ = parsed.port  # Reject malformed ports and authorities.
    except ValueError:
        raise ArchiveError("origin_uri") from None
    schemes = {"http", "https"} if http else {"http", "https", "file", "urn"}
    if parsed.scheme not in schemes or (parsed.scheme in {"http", "https"} and not parsed.hostname):
        raise ArchiveError("origin_uri")
    kept, secrets = _query(parsed, policy)
    userinfo, sep, authority = parsed.netloc.rpartition("@")
    user_secrets = tuple(unquote(value) for value in userinfo.split(":", 1)) if sep else ()
    inferred = (*secrets, *user_secrets, *header_secrets)
    # Explicit values are checked even when short. Avoid incidental substring matches for short
    # inferred values, whose original credential fields have already been removed.
    secrets = (*policy.secret_values, *(value for value in inferred if len(value) >= 4))
    sanitized = parsed._replace(netloc=authority, query="&".join(kept), fragment="").geturl()
    if _has_secret(sanitized, secrets):
        raise ArchiveError("origin_uri_secret")
    return sanitized, secrets, sanitized != uri


def _headers(
    headers: Headers, allowed: frozenset[str], names: frozenset[str], secrets: tuple[str, ...]
) -> Headers:
    selected: list[tuple[str, str]] = []
    size = 0
    for name, value in headers:
        lower = name.lower()
        if lower not in allowed or lower in names or _has_secret(value, secrets):
            continue
        if not _printable(value):
            raise ArchiveError("http_headers")
        size += len(lower) + len(value) + 4
        if size > 32 * 1024:
            raise ArchiveError("http_headers")
        selected.append((lower, value.strip()))
    return tuple(selected)


def _encoding(headers: Headers) -> str:
    values = [
        value.strip().casefold() for name, value in headers if name.lower() == "content-encoding"
    ]
    if not values:
        return "identity"
    if len(values) != 1 or values[0] not in {"identity", "gzip", "x-gzip", "deflate"}:
        raise ArchiveError("content_encoding")
    return values[0]


def _prepare_http(
    capture: Capture, origin: str, secrets: tuple[str, ...], policy: Redaction, changed: bool
) -> tuple[Headers, Headers, str | None, str]:
    http = capture.http
    if http is None:
        return (), (), None, "identity"
    if (
        not _HEADER_TOKEN.fullmatch(http.method)
        or len(http.method) > 32
        or http.protocol not in {"HTTP/1.0", "HTTP/1.1"}
        or type(http.status) is not int
        or not 100 <= http.status <= 599
        or _has_secret(http.method, secrets)
    ):
        raise ArchiveError("http_exchange")
    names = frozenset(name.lower() for name in policy.header_names)
    sent = _headers(http.request_headers, _REQUEST_HEADERS, names, secrets)
    received = _headers(http.response_headers, _RESPONSE_HEADERS, names, secrets)
    encoding = _encoding(http.response_headers)
    if encoding != _encoding(received):
        raise ArchiveError("content_encoding")
    # Only requests fully represented by the retained, bodyless request can share a payload.
    comparable = (
        http.method in {"GET", "HEAD"} and not changed and len(sent) == len(http.request_headers)
    )
    fingerprint = request_digest(origin, http.method, http.protocol, sent) if comparable else None
    return sent, received, fingerprint, encoding


def request_digest(origin: str, method: str, protocol: str, headers: Headers) -> str:
    value = json.dumps((origin, method, protocol, headers), ensure_ascii=True)
    return sha256(value.encode("ascii")).hexdigest()


def valid_key(value: str) -> bool:
    return _IDENTIFIER.fullmatch(value) is not None


def prepare(capture: Capture, policy: Redaction) -> Prepared:
    if not valid_key(capture.key) or _has_secret(capture.key, policy.secret_values):
        raise ArchiveError("capture_key")
    if capture.fetched_at.utcoffset() is None:
        raise ArchiveError("capture_time")
    if capture.backend not in {"warc", "blob"}:
        raise ArchiveError("capture_backend")
    origin, secrets, changed = _origin(
        capture.origin_uri, policy, _header_secrets(capture, policy), http=capture.http is not None
    )
    sent, received, fingerprint, encoding = _prepare_http(capture, origin, secrets, policy, changed)
    mime = capture.mime_type or next(
        (value for name, value in received if name == "content-type"), None
    )
    if mime is not None and (not _printable(mime) or len(mime) > 256 or _has_secret(mime, secrets)):
        raise ArchiveError("capture_mime_type")
    kind: Kind = "resource"
    if capture.revisit_of is not None:
        if capture.backend != "warc" or fingerprint is None:
            raise ArchiveError("revisit_request")
        kind = "revisit"
    elif capture.backend == "blob":
        kind = "blob"
    elif capture.http is not None:
        kind = "response"
    return Prepared(
        origin,
        capture.fetched_at.astimezone(UTC),
        kind,
        mime,
        sent,
        received,
        fingerprint,
        encoding,
    )
