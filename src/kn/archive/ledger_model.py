"""Version 1 of the logical fetch ledger and its published coverage."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import AwareDatetime, model_validator

from kn.archive.catalog import Located
from kn.archive.model import (
    ArchiveError,
    Backend,
    ByteCount,
    Digest,
    Document,
    Domain,
    Kind,
    Metadata,
    RecordID,
    Segment,
    SourceID,
    Status,
)

LEDGER_VERSION = 1


class CaptureScope(Document):
    domain: Domain | None = None
    source_id: SourceID | None = None
    since: AwareDatetime | None = None
    before: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_scope(self) -> "CaptureScope":
        if self.domain is not None and self.domain != self.effective_domain:
            raise ArchiveError("index_scope")
        if self.since is not None and self.before is not None and self.since >= self.before:
            raise ArchiveError("index_scope")
        return self

    @property
    def effective_domain(self) -> str | None:
        return self.source_id.partition(":")[0] if self.source_id else self.domain

    def contains(self, fetched_at: datetime) -> bool:
        return (self.since is None or self.since <= fetched_at) and (
            self.before is None or fetched_at < self.before
        )

    def is_full(self) -> bool:
        return self == CaptureScope()


class PartitionKey(Document):
    domain: Domain
    source_id: SourceID
    day: date

    @model_validator(mode="after")
    def check_domain(self) -> "PartitionKey":
        if self.source_id.partition(":")[0] != self.domain:
            raise ArchiveError("index_partition")
        return self

    def path(self, view: Path) -> Path:
        return view.joinpath(self.domain, self.source_id, f"{self.day.isoformat()}.parquet")

    def overlaps(self, scope: CaptureScope) -> bool:
        if scope.effective_domain not in (None, self.domain):
            return False
        if scope.source_id not in (None, self.source_id):
            return False
        first = datetime.combine(self.day, datetime.min.time(), tzinfo=UTC)
        last = datetime.combine(self.day, datetime.max.time(), tzinfo=UTC)
        return (scope.since is None or scope.since <= last) and (
            scope.before is None or first < scope.before
        )

    def order(self) -> tuple[date, str, str]:
        return self.day, self.domain, self.source_id


class LedgerCapture(Document):
    backend: Backend
    relative_path: str
    offset: ByteCount | None
    length: ByteCount | None
    kind: Kind
    origin_uri: str
    status: Status | None
    mime_type: str | None
    payload_sha256: Digest
    payload_size: ByteCount
    decoded_size: ByteCount | None
    config_sha256: Digest
    code_sha256: Digest


class CoverageRow(Document):
    record_id: RecordID
    fetch_id: RecordID
    domain: Domain
    source_id: SourceID
    run_id: Segment
    batch_id: Segment
    fetched_at: AwareDatetime
    revisit_of: RecordID | None
    withdrawn_by: RecordID | None


class LedgerRow(CoverageRow):
    capture: LedgerCapture | None

    @model_validator(mode="after")
    def check_row(self) -> "LedgerRow":
        if (self.withdrawn_by is None) != (self.capture is not None):
            raise ArchiveError("index_row")
        if self.withdrawn_by not in (None, self.record_id, self.revisit_of):
            raise ArchiveError("index_row")
        if self.fetched_at.utcoffset() != timedelta(0):
            raise ArchiveError("index_row")
        return self

    def order(self) -> tuple[datetime, str]:
        return self.fetched_at, self.fetch_id


class LedgerCoverage(Document):
    schema_version: int = LEDGER_VERSION
    partitions: ByteCount
    covered_captures: ByteCount
    published_retained: ByteCount


def ledger_row(
    root: Path, located: Located, metadata: Metadata | None, withdrawn_by: str | None
) -> LedgerRow:
    entry = located.entry
    return LedgerRow(
        **located.batch.model_dump(),
        record_id=entry.record_id,
        fetch_id=entry.fetch_id,
        fetched_at=entry.fetched_at.astimezone(UTC),
        revisit_of=entry.revisit_of,
        withdrawn_by=withdrawn_by,
        capture=None if metadata is None else _capture(root, located, metadata),
    )


def _capture(root: Path, located: Located, metadata: Metadata) -> LedgerCapture:
    entry = located.entry
    member = entry.payload_member
    return LedgerCapture(
        backend=entry.backend,
        relative_path=(located.directory / entry.payload_path).relative_to(root).as_posix(),
        offset=None if member is None else member.offset,
        length=None if member is None else member.length,
        kind=metadata.kind,
        origin_uri=metadata.origin_uri,
        status=metadata.status,
        mime_type=metadata.mime_type,
        payload_sha256=metadata.payload_sha256,
        payload_size=metadata.payload_size,
        decoded_size=metadata.decoded_size,
        config_sha256=metadata.config_sha256,
        code_sha256=metadata.code_sha256,
    )
