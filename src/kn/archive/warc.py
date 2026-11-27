"""The KN profile of WARC 1.1 with one gzip member per record."""

import base64
import zlib
from datetime import datetime
from hashlib import sha256
from http import HTTPStatus
from io import BytesIO
from typing import BinaryIO
from urllib.parse import urlsplit

from warcio.exceptions import ArchiveLoadFailed  # type: ignore[import-untyped]
from warcio.recordloader import ArcWarcRecordLoader  # type: ignore[import-untyped]
from warcio.statusandheaders import (  # type: ignore[import-untyped]
    StatusAndHeaders,
    StatusAndHeadersParserException,
)
from warcio.warcwriter import WARCWriter  # type: ignore[import-untyped]

from kn.archive.model import (
    CHUNK_SIZE,
    MAX_WARC_MEMBER,
    ArchiveError,
    Member,
    Metadata,
    stable_id,
)

REVISIT_PROFILE = "http://netpreserve.org/warc/1.1/revisit/identical-payload-digest"
_JSON = "application/json"
_HTTP_REQUEST = "application/http; msgtype=request"
_HTTP_RESPONSE = "application/http; msgtype=response"
_END_OF_RECORD = b"\r\n\r\n"


def _digest(hex_digest: str) -> str:
    return "sha256:" + base64.b32encode(bytes.fromhex(hex_digest)).decode("ascii")


def _date(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _http_headers(metadata: Metadata, *, request: bool) -> StatusAndHeaders:
    http = metadata.http
    assert http is not None
    if request:
        uri = urlsplit(metadata.origin_uri)
        target = uri.path or "/"
        if uri.query:
            target += "?" + uri.query
        if http.method == "CONNECT":
            target = uri.netloc
        return StatusAndHeaders(
            f"{target} {http.protocol}", http.request_headers, protocol=http.method
        )
    assert metadata.status is not None
    try:
        reason = HTTPStatus(metadata.status).phrase
    except ValueError:
        reason = ""
    return StatusAndHeaders(
        f"{metadata.status} {reason}", http.response_headers, protocol=http.protocol
    )


def _header_block(headers: StatusAndHeaders | None) -> bytes:
    if headers is None:
        return b""
    headers.compute_headers_buffer()
    return bytes(headers.headers_buff)


def _fields(
    metadata: Metadata, role: str, content_digest: str, target: Metadata | None
) -> dict[str, str]:
    record_id = metadata.record_id
    fields = {
        "WARC-Date": _date(metadata.fetched_at),
        "WARC-Payload-Digest": _digest(content_digest),
    }
    if role != metadata.kind:
        record_id = stable_id(metadata.batch, metadata.key, role)
        reference = "WARC-Refers-To" if role == "metadata" else "WARC-Concurrent-To"
        fields[reference] = f"<{metadata.record_id}>"
    if target is not None and role == "revisit":
        fields.update(
            {
                "WARC-Profile": REVISIT_PROFILE,
                "WARC-Refers-To": f"<{target.record_id}>",
                "WARC-Refers-To-Target-URI": target.origin_uri,
                "WARC-Refers-To-Date": _date(target.fetched_at),
                "WARC-Truncated": "length",
            }
        )
    fields["WARC-Record-ID"] = f"<{record_id}>"
    return fields


def _write_member(
    writer: WARCWriter,
    stream: BinaryIO,
    metadata: Metadata,
    role: str,
    content_type: str,
    payload: BinaryIO,
    length: int,
    digest: str,
    headers: StatusAndHeaders | None = None,
    target: Metadata | None = None,
) -> Member:
    block_digest = sha256(_header_block(headers))
    while chunk := payload.read(CHUNK_SIZE):
        block_digest.update(chunk)
    payload.seek(0)
    fields = _fields(metadata, role, digest, target)
    fields["WARC-Block-Digest"] = _digest(block_digest.hexdigest())
    offset = stream.tell()
    record = writer.create_warc_record(
        metadata.origin_uri,
        role,
        payload=payload,
        length=length,
        warc_content_type=content_type,
        warc_headers_dict=fields,
        http_headers=headers,
    )
    writer.write_record(record)
    return Member(offset=offset, length=stream.tell() - offset)


def write_warc(
    stream: BinaryIO,
    metadata: Metadata,
    raw_metadata: bytes,
    body: BinaryIO,
    target: Metadata | None,
) -> tuple[Member, Member, Member | None]:
    writer = WARCWriter(stream, gzip=True, warc_version="1.1")
    payload = _write_member(
        writer,
        stream,
        metadata,
        metadata.kind,
        _HTTP_RESPONSE if metadata.http else metadata.mime_type or "application/octet-stream",
        BytesIO() if target else body,
        0 if target else metadata.payload_size,
        metadata.payload_sha256,
        _http_headers(metadata, request=False) if metadata.http else None,
        target,
    )
    request = None
    if metadata.http is not None:
        request = _write_member(
            writer,
            stream,
            metadata,
            "request",
            _HTTP_REQUEST,
            BytesIO(),
            0,
            sha256().hexdigest(),
            _http_headers(metadata, request=True),
        )
    descriptor = _write_member(
        writer,
        stream,
        metadata,
        "metadata",
        _JSON,
        BytesIO(raw_metadata),
        len(raw_metadata),
        sha256(raw_metadata).hexdigest(),
    )
    return payload, descriptor, request


def _inflate(stream: BinaryIO, member: Member, limit: int) -> bytes:
    stream.seek(member.offset)
    decoder = zlib.decompressobj(zlib.MAX_WBITS + 16)
    try:
        compressed = stream.read(member.length)
        raw = decoder.decompress(compressed, limit + 1)
    except zlib.error:
        raise ArchiveError("warc_gzip") from None
    if len(raw) > limit:
        raise ArchiveError("warc_member_size")
    if len(compressed) != member.length or not decoder.eof or decoder.unused_data:
        raise ArchiveError("warc_gzip")
    return raw


def read_member(
    stream: BinaryIO, member: Member, *, limit: int = MAX_WARC_MEMBER
) -> tuple[dict[str, str], bytes]:
    raw = _inflate(stream, member, limit)
    if not raw.startswith(b"WARC/1.1\r\n"):
        raise ArchiveError("warc_version")
    reader = BytesIO(raw)
    try:
        record = ArcWarcRecordLoader().parse_record_stream(reader, no_record_parse=True)
        headers = {name.casefold(): value for name, value in record.rec_headers.headers}
        block = record.raw_stream.read()
    except (ArchiveLoadFailed, StatusAndHeadersParserException, OverflowError, ValueError):
        raise ArchiveError("warc_record") from None
    if (
        len(headers) != len(record.rec_headers.headers)
        or headers.get("content-length") != str(len(block))
        or reader.read() != _END_OF_RECORD
    ):
        raise ArchiveError("warc_record")
    if headers.get("warc-block-digest") != _digest(sha256(block).hexdigest()):
        raise ArchiveError("warc_block_digest")
    return headers, block


def verify_member(
    headers: dict[str, str],
    block: bytes,
    metadata: Metadata,
    role: str,
    target: Metadata | None = None,
) -> bytes:
    if role == "request":
        content_type = _HTTP_REQUEST
        prefix = _header_block(_http_headers(metadata, request=True))
    elif role in ("response", "revisit"):
        content_type = _HTTP_RESPONSE
        prefix = _header_block(_http_headers(metadata, request=False))
    else:
        content_type = (
            _JSON if role == "metadata" else metadata.mime_type or "application/octet-stream"
        )
        prefix = b""
    if not block.startswith(prefix):
        raise ArchiveError("warc_http_headers")
    payload = block[len(prefix) :]
    digest = metadata.payload_sha256 if role == "revisit" else sha256(payload).hexdigest()
    expected = _fields(metadata, role, digest, target)
    expected.update(
        {
            "WARC-Target-URI": metadata.origin_uri,
            "WARC-Type": role,
            "Content-Type": content_type,
        }
    )
    if any(headers.get(name.casefold()) != value for name, value in expected.items()):
        raise ArchiveError("warc_record_fields")
    if role in ("request", "revisit") and payload:
        raise ArchiveError("warc_unexpected_body")
    if role in ("resource", "response") and (
        digest != metadata.payload_sha256 or len(payload) != metadata.payload_size
    ):
        raise ArchiveError("payload_digest")
    return payload
