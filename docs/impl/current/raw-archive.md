# Durable Raw Archive

The local archive commits approved captures and replays retained bytes by record ID or fetch ID.
It uses WARC 1.1 via `warcio` and streamed, SHA-256-addressed blobs. The Python entry point is
`kn.archive.Archive`. The operator commands are `kn raw verify` and `kn raw reindex`. See the
[raw archive specification](../../design/spec.md#raw-archive) and the
[storage](../records/0055-raw-archive-warc-raw-store.md) and
[fetch ledger](../records/0056-raw-archive-raw-fetch-ledger.md) task records.

## Configure and verify

Set `KN_RAW_ARCHIVE_DIR` in the environment or the checkout's `.env`. The environment takes
precedence, and relative paths resolve from the checkout root. The archive root is required for
the command and for `Archive.configured()`. An archive-only run can leave `KN_RAW_INDEX_DIR` unset.

```bash
export KN_RAW_ARCHIVE_DIR=local/raw-archive
kn raw verify
kn --json raw verify
```

Verification reads committed manifests, objects, WARC records, revisit targets, and tombstones
without network or database access. It checks paths, byte lengths, SHA-256 digests, gzip member
boundaries, and capture schema versions. It reports batch, retained capture, and tombstone counts
on success. A failure exits with status 1. Archive diagnostics use `E_RAW_ARCHIVE` with a reason
that excludes paths and raw input values. Run full verification against a quiescent archive.

## Commit and replay

Pass a `BatchKey` and an iterable of `Capture` values to
`Archive.commit(batch, captures, limits=..., redaction=...)`. Capture inputs and policy types live
in `kn.archive.model`. The caller supplies the approved body stream, fetch time, crawler
configuration and code digests, and the approved access, expiry, and deletion scope. Use stable
run, batch, and capture keys. Reusing a committed batch key returns its manifest and IDs without
consuming the supplied streams. Allocate a new key for new input.

For HTTP, supply the entity body after transfer framing has been removed and before content
decoding. The archive writes a WARC response, a linked request with approved headers, and linked
JSON metadata. It retains no request body. Other WARC inputs produce resource records. A blob
capture stores the exact bytes under their SHA-256 with a separate JSON descriptor. For opaque
packages, unpacking and package-level limits belong to the package reader.

Redaction drops URI user information, fragments, common credential query parameters, and declared
secret query parameters. HTTP headers use allowlists. Pass source-specific secret header names and
known secret values through `Redaction` so reflected values can also be excluded. The caller
approves the unmodified response body for retention. Each capture must fit the caller's retained
and decoded byte budgets. HTTP identity, gzip, and zlib-wrapped deflate encodings are supported.
WARC is capped at 16 MiB of retained payload per capture and each batch holds up to 256 captures.

Set `Capture.revisit_of` to a previously committed WARC response's record ID and supply the
later response bytes. Reuse requires the same source, a matching retained GET or HEAD request,
identical payload bytes, and the same access, expiry, and deletion scope. A request that required
redaction or had omitted headers falls back to a full response when submitted without
`revisit_of`.

Use `Archive.metadata(record_or_fetch_id)` for a metadata-only read and
`Archive.replay(record_or_fetch_id, binary_output)` to verify and write the retained body.
`Archive.iter_metadata()` yields retained metadata ordered by UTC capture time and fetch ID.
Readers project version 1 metadata into version 2 with `decoded_size=None`. Other metadata
versions are rejected. `Archive.configured()` uses the ledger when configured. An explicit
`Archive(root, index_root=...)` can opt in, and `Archive.configured(use_index=False)` forces
archive-only operation. ID lookup uses the index to find the batch, confirms the ID against its
committed manifest, and applies current tombstones before reading. A missing row or unreadable
index falls back to committed manifests. `Archive.iter_metadata()` always reads from the archive.

## Rebuild and query the fetch ledger

Set `KN_RAW_INDEX_DIR` explicitly in the environment or checkout's `.env`. Use a dedicated
directory outside the archive, with neither root inside the other. Paths resolve as they do for
the archive. After losing the index or restoring the archive to a different root, run a full
reindex. The archive and its tombstones contain the data needed to rebuild it.

```bash
export KN_RAW_ARCHIVE_DIR=local/raw-archive
export KN_RAW_INDEX_DIR=local/raw-index
kn --json raw reindex
kn raw reindex --domain space --source space:example \
  --since 2026-01-01T00:00:00Z --before 2026-02-01T00:00:00Z
```

All scope options are optional. A qualified source ID implies its domain. Times include a UTC
offset, with an inclusive lower bound and an exclusive upper bound. A scoped rebuild keeps
coverage outside that scope, including outside rows on the same day. The result reports schema
version, partition count, covered captures, and retained captures as counted at publication.

`kn.archive.ledger.FetchLedger.configured()` exposes `query(CaptureScope(...))` for the published
metadata, `coverage()` for publication counts, and `covered(scope)` for the exact committed batch
and capture IDs included in those counts. `CaptureScope` lives in `kn.archive.ledger_model`.
Query rows are ordered by UTC fetch time and fetch ID, as in archive replay. Query results cover
the published inputs and apply current archive tombstones, including a revisit's target.
Captures committed since publication resolve by ID through `Archive` and enter the query view on
the next matching reindex.

The version 1 projection stores stable IDs, batch keys, UTC fetch time, revisit links, redacted
origin, HTTP status, MIME type, payload, configuration and code digests, sizes, and archive-relative
payload locators with WARC offset and length. A covered withdrawal records its ID and the
responsible tombstone without a capture payload locator or descriptor fields. Reindex reads
descriptors and checks live object lengths without decompressing response bodies. Use
`kn raw verify` to verify full object and payload digests.

Point lookup currently searches the partition ID columns with a Parquet predicate and reads a
single archive manifest on a hit. Time-scoped reindex scans manifests for the selected sources
and reads descriptors only for the selected captures.

Reindex stages Parquet files in batches by domain, qualified source, and UTC day under the index
root. It hard-links untouched partitions and atomically replaces `CURRENT` with the generation
and its coverage. A failure before replacement leaves the previous view readable. If the
directory sync fails after replacement, `index_publication_uncertain` means the new complete view
is visible but its durability is uncertain. Reindex can be retried. Readers pin their generation
and a later publication can reclaim old generations once those readers finish.

## Layout and withdrawal

The POSIX filesystem implementation stages writes under `staging/` on the archive filesystem.
It syncs the files and directories, publishes one batch directory atomically, and syncs the
publication path. Writers for different sources use separate locks. Each committed directory
under `captures/<domain>/<source-id>/<run-id>/<batch-id>/` holds `manifest.json` and one subdirectory
per capture. Manifest version 1 records the capture time range, stable IDs, relative object paths,
sizes and SHA-256 digests, and per-record compressed offsets and lengths for WARC. Each capture
gets its own WARC segment or blob directory to support independent physical deletion. The WARC
metadata locator can be read directly without inflating the body.

`Archive.withdraw(record_or_fetch_id, reason, withdrawn_at, purge=False)` persists immutable
tombstones under `tombstones/`. The reason is an operator reason code. Tombstones hide affected
captures from lookup and replay, including revisits of a withdrawn target. With `purge=True`,
isolated objects are removed after each affected capture has a durable tombstone. Retrying a
withdrawal completes interrupted publication or removal. Back up committed captures and tombstones
together and retain their relative paths.

[group audit](../plan.md#raw-archive-implementation-audit) owns independent format conformance and
restore acceptance. Engine integration owns source approval, capture scheduling, and claim
updates for withdrawn evidence.
