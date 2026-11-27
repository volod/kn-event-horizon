"""Read scoped Parquet batches and write sorted row groups."""

import os
from collections.abc import Iterable, Iterator
from itertools import batched
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from pydantic import ValidationError

from kn.archive.files import mkdirs, open_regular, sync_directory
from kn.archive.ledger_model import LEDGER_VERSION, CaptureScope, LedgerRow, PartitionKey
from kn.archive.model import ArchiveError, BatchKey

_ROW_GROUP_SIZE = 1024
_ARROW_ERRORS = (pa.ArrowException, OSError)
_TEXT = pa.string()
_INT = pa.int64()
_SCHEMA = pa.schema(
    [
        pa.field("record_id", _TEXT, nullable=False),
        pa.field("fetch_id", _TEXT, nullable=False),
        pa.field("domain", _TEXT, nullable=False),
        pa.field("source_id", _TEXT, nullable=False),
        pa.field("run_id", _TEXT, nullable=False),
        pa.field("batch_id", _TEXT, nullable=False),
        pa.field("fetched_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("revisit_of", _TEXT),
        pa.field("withdrawn_by", _TEXT),
        pa.field(
            "capture",
            pa.struct(
                [
                    pa.field("backend", _TEXT, nullable=False),
                    pa.field("relative_path", _TEXT, nullable=False),
                    pa.field("offset", _INT),
                    pa.field("length", _INT),
                    pa.field("kind", _TEXT, nullable=False),
                    pa.field("origin_uri", _TEXT, nullable=False),
                    pa.field("status", pa.int16()),
                    pa.field("mime_type", _TEXT),
                    pa.field("payload_sha256", _TEXT, nullable=False),
                    pa.field("payload_size", _INT, nullable=False),
                    pa.field("decoded_size", _INT),
                    pa.field("config_sha256", _TEXT, nullable=False),
                    pa.field("code_sha256", _TEXT, nullable=False),
                ]
            ),
        ),
    ],
    metadata={b"kn.fetch_ledger.version": str(LEDGER_VERSION).encode("ascii")},
)


def read_rows(
    path: Path,
    key: PartitionKey,
    scope: CaptureScope,
    *,
    outside: bool = False,
) -> Iterator[LedgerRow]:
    expression = ds.scalar(True)
    if scope.since is not None:
        expression = expression & (ds.field("fetched_at") >= scope.since)
    if scope.before is not None:
        expression = expression & (ds.field("fetched_at") < scope.before)
    if outside:
        expression = ~expression
    try:
        for batch in _dataset(path).to_batches(filter=expression, batch_size=_ROW_GROUP_SIZE):
            for values in batch.to_pylist():
                row = LedgerRow.model_validate(values)
                if (row.domain, row.source_id, row.fetched_at.date()) != (
                    key.domain,
                    key.source_id,
                    key.day,
                ):
                    raise ArchiveError("index_partition")
                yield row
    except (*_ARROW_ERRORS, ValidationError):
        raise ArchiveError("index_parquet") from None


def find_batch(path: Path, identifier: str) -> BatchKey | None:
    expression = (ds.field("record_id") == identifier) | (ds.field("fetch_id") == identifier)
    try:
        table = _dataset(path).head(1, columns=list(BatchKey.model_fields), filter=expression)
        return BatchKey.model_validate(table.to_pylist()[0]) if table.num_rows else None
    except (*_ARROW_ERRORS, ValidationError):
        raise ArchiveError("index_parquet") from None


def _dataset(path: Path) -> ds.Dataset:
    dataset = ds.dataset(str(path), format="parquet")
    if not dataset.schema.equals(_SCHEMA, check_metadata=True):
        raise ArchiveError("index_schema")
    return dataset


def write_rows(path: Path, rows: Iterable[LedgerRow]) -> tuple[int, int]:
    groups = batched(rows, _ROW_GROUP_SIZE)
    first = next(groups, ())
    if not first:
        return 0, 0
    mkdirs(path.parent)
    try:
        with pq.ParquetWriter(path, _SCHEMA, compression="zstd") as writer:
            total, retained = _write_group(writer, first)
            for group in groups:
                count, present = _write_group(writer, group)
                total += count
                retained += present
        with open_regular(path) as stream:
            os.fsync(stream.fileno())
        sync_directory(path.parent)
    except _ARROW_ERRORS:
        raise ArchiveError("index_parquet") from None
    return total, retained


def _write_group(writer: "pq.ParquetWriter", rows: tuple[LedgerRow, ...]) -> tuple[int, int]:
    writer.write_table(pa.Table.from_pylist([row.model_dump() for row in rows], schema=_SCHEMA))
    return len(rows), sum(row.capture is not None for row in rows)
