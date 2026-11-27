"""Acquire one loopback HTTPS response and commit it before transformation."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.client import HTTPException, HTTPSConnection
from io import BytesIO

from kn.archive import Archive
from kn.archive.model import ArchiveError, BatchKey, Capture, HttpExchange, Metadata, Retention
from kn.engine.outcomes import ErrorCode, Metrics, RunFailure
from kn.engine.profile import SnapshotProfile

SNAPSHOT_BATCH = "snapshot"
CAPTURE_KEY = "response"
LOOPBACK = "127.0.0.1"
_INTERNAL = "internal"
_HTTP_ERRORS: dict[int, ErrorCode] = {
    401: "auth_failed",
    403: "permission_denied",
    429: "rate_limited",
}


def _capture(profile: SnapshotProfile, code_digest: str, metrics: Metrics) -> Iterator[Capture]:
    # Connect directly to loopback. The HTTPS peer must authenticate the loopback IP.
    connection = HTTPSConnection(LOOPBACK, profile.port, timeout=profile.timeout)
    headers = {"Accept": ", ".join(sorted(profile.content_types)), "Accept-Encoding": "identity"}
    try:
        metrics.requests_used += 1
        connection.request("GET", profile.path, headers=headers)
        with connection.getresponse() as response:
            limit = min(profile.limits.max_payload_bytes, profile.limits.max_decoded_bytes)
            body = response.read(limit + 1)
            metrics.bytes_received = len(body)
            if len(body) > limit:
                raise RunFailure("budget_exhausted")
            if response.length:
                raise RunFailure("transient_network")
            http = HttpExchange(
                method="GET",
                status=response.status,
                protocol="HTTP/1.0" if response.version == 10 else "HTTP/1.1",
                request_headers=tuple(headers.items()),
                response_headers=tuple(response.getheaders()),
            )
    except (HTTPException, OSError):
        raise RunFailure("transient_network") from None
    finally:
        connection.close()
    fetched_at = datetime.now(UTC)
    yield Capture(
        key=CAPTURE_KEY,
        origin_uri=profile.endpoint,
        fetched_at=fetched_at,
        body=BytesIO(body),
        config_sha256=profile.config_digest,
        code_sha256=code_digest,
        retention=Retention(
            access=_INTERNAL,
            deletion_scope=profile.stream.source_id.replace(":", "."),
            expires_at=fetched_at + timedelta(days=profile.retention_days),
        ),
        http=http,
    )


def archived_snapshot(
    archive: Archive,
    profile: SnapshotProfile,
    key: BatchKey,
    code_digest: str,
    metrics: Metrics,
    *,
    fetch: bool,
) -> tuple[Metadata, bytes]:
    try:
        # The archive only consumes the iterator if the batch needs to be captured.
        manifest = (
            archive.commit(key, _capture(profile, code_digest, metrics), limits=profile.limits)
            if fetch
            else archive.batch(key)
        )
        if len(manifest.captures) != 1 or manifest.captures[0].key != CAPTURE_KEY:
            raise RunFailure("integrity_lost")
        with BytesIO() as payload:
            metadata = archive.replay(manifest.captures[0].record_id, payload)
            _validate_response(profile, key, code_digest, metadata)
            return metadata, payload.getvalue()
    except (ArchiveError, OSError):
        raise RunFailure("integrity_lost") from None


def _validate_response(
    profile: SnapshotProfile, key: BatchKey, code_digest: str, metadata: Metadata
) -> None:
    if (
        metadata.batch != key
        or metadata.config_sha256 != profile.config_digest
        or metadata.code_sha256 != code_digest
        or metadata.kind != "response"
        or metadata.http is None
    ):
        raise RunFailure("integrity_lost")
    if metadata.status != 200:
        raise RunFailure(_HTTP_ERRORS.get(metadata.status or 0, "payload_invalid"))
    mime_type = (metadata.mime_type or "").partition(";")[0].strip().lower()
    if mime_type not in profile.content_types or any(
        name == "content-encoding" and value.lower() != "identity"
        for name, value in metadata.http.response_headers
    ):
        raise RunFailure("payload_invalid")
