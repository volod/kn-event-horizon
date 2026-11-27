"""Capture inputs and versioned on-disk archive contracts."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, BinaryIO, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

Backend = Literal["warc", "blob"]
Kind = Literal["response", "resource", "revisit", "blob"]
Headers = tuple[tuple[str, str], ...]
Segment = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
RecordID = Annotated[str, Field(pattern=r"^urn:uuid:[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$")]
ByteCount = Annotated[int, Field(ge=0)]
Status = Annotated[int, Field(ge=100, le=599)]

MIB = 1024 * 1024
MAX_WARC_BODY = 16 * MIB
MAX_WARC_MEMBER = MAX_WARC_BODY + MIB
MAX_DESCRIPTOR = 64 * 1024
MAX_MANIFEST = MIB
MAX_CAPTURES = 256
CHUNK_SIZE = 64 * 1024


class ArchiveError(ValueError):
    """Archive error with a fixed, credential-free diagnostic code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Document(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, hide_input_in_errors=True)


def _version_one(value: object) -> Literal[1]:
    if type(value) is not int or value != 1:
        raise ValueError("expected integer version 1")
    return 1


VersionOne = Annotated[Literal[1], BeforeValidator(_version_one)]


class BatchKey(Document):
    domain: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,127}$")]
    source_id: Annotated[
        str, Field(pattern=r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9_.-]*$", max_length=257)
    ]
    run_id: Segment
    batch_id: Segment

    def parts(self) -> tuple[str, str, str, str]:
        if self.domain != self.source_id.partition(":")[0]:
            raise ArchiveError("batch_scope")
        return self.domain, self.source_id, self.run_id, self.batch_id


class Retention(Document):
    """Caller-supplied identifiers from an approved retention policy."""

    access: Segment
    deletion_scope: Segment
    expires_at: AwareDatetime | None = None


@dataclass(frozen=True, slots=True)
class HttpExchange:
    method: str
    status: int
    request_headers: Headers = field(default=(), repr=False)
    response_headers: Headers = field(default=(), repr=False)
    protocol: Literal["HTTP/1.0", "HTTP/1.1"] = "HTTP/1.1"


@dataclass(frozen=True, slots=True)
class Capture:
    """Approved input. The body is read from its current position and left open."""

    key: str
    origin_uri: str = field(repr=False)
    fetched_at: datetime
    body: BinaryIO = field(repr=False)
    config_sha256: str
    code_sha256: str
    retention: Retention
    backend: Backend = "warc"
    mime_type: str | None = None
    http: HttpExchange | None = None
    revisit_of: str | None = None


@dataclass(frozen=True, slots=True)
class Limits:
    max_payload_bytes: int
    max_decoded_bytes: int


@dataclass(frozen=True, slots=True)
class Redaction:
    query_parameters: frozenset[str] = frozenset()
    header_names: frozenset[str] = frozenset()
    secret_values: tuple[str, ...] = field(default=(), repr=False)


class HttpMetadata(Document):
    method: Annotated[str, Field(min_length=1, max_length=32)]
    protocol: Literal["HTTP/1.0", "HTTP/1.1"]
    request_headers: Headers
    response_headers: Headers


class Metadata(Document):
    schema_version: Literal[2] = 2
    key: Segment
    batch: BatchKey
    record_id: RecordID
    fetch_id: RecordID
    origin_uri: Annotated[str, Field(min_length=1, max_length=8192)]
    fetched_at: AwareDatetime
    kind: Kind
    status: Status | None
    mime_type: Annotated[str, Field(max_length=256)] | None
    payload_sha256: Digest
    payload_size: ByteCount
    config_sha256: Digest
    code_sha256: Digest
    retention: Retention
    http: HttpMetadata | None
    request_sha256: Digest | None
    revisit_of: RecordID | None
    decoded_size: ByteCount | None


class ObjectInfo(Document):
    size: ByteCount
    sha256: Digest


class Member(Document):
    offset: ByteCount
    length: Annotated[int, Field(gt=0, le=MAX_WARC_MEMBER)]


class Entry(Document):
    key: Segment
    record_id: RecordID
    fetch_id: RecordID
    backend: Backend
    payload_path: str
    metadata_path: str
    payload: ObjectInfo
    metadata: ObjectInfo
    payload_member: Member | None = None
    metadata_member: Member | None = None
    request_member: Member | None = None
    revisit_of: RecordID | None
    payload_sha256: Digest
    fetched_at: AwareDatetime


class Manifest(Document):
    version: VersionOne
    batch: BatchKey
    first_capture_at: AwareDatetime
    last_capture_at: AwareDatetime
    captures: Annotated[tuple[Entry, ...], Field(min_length=1, max_length=MAX_CAPTURES)]


class Tombstone(Document):
    version: VersionOne
    record_id: RecordID
    payload_sha256: Digest
    batch: BatchKey
    objects: tuple[str, ...]
    reason: Segment
    withdrawn_at: AwareDatetime


def stable_id(batch: BatchKey, key: str, role: str) -> str:
    name = json.dumps(("kn:raw", *batch.parts(), key, role), separators=(",", ":"))
    return uuid5(NAMESPACE_URL, name).urn


def record_directory(record_id: str) -> str:
    return record_id.removeprefix("urn:uuid:")


def object_paths(record_id: str, backend: Backend, digest: str) -> tuple[str, str]:
    directory = record_directory(record_id)
    if backend == "warc":
        path = f"{directory}/capture.warc.gz"
        return path, path
    return f"{directory}/{digest}.blob", f"{directory}/capture.json"


def encode(document: Document) -> bytes:
    return (
        json.dumps(document.model_dump(mode="json"), ensure_ascii=True, sort_keys=True) + "\n"
    ).encode("ascii")


def decode[T: Document](schema: type[T], raw: bytes, code: str) -> T:
    try:
        return schema.model_validate_json(raw)
    except ValidationError:
        raise ArchiveError(code) from None


def decode_metadata(raw: bytes) -> Metadata:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ArchiveError("capture_metadata") from None
    if not isinstance(data, dict):
        raise ArchiveError("capture_metadata")
    version = data.get("schema_version")
    if type(version) is int and version == 1 and "decoded_size" not in data:
        data.update(schema_version=2, decoded_size=None)
        return decode(Metadata, json.dumps(data).encode("ascii"), "capture_metadata")
    if type(version) is not int or version != 2:
        raise ArchiveError("capture_schema_version")
    return decode(Metadata, raw, "capture_metadata")
