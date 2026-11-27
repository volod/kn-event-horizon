# Durable Raw Archive

The local archive commits approved captures and replays retained bytes by record ID or fetch ID.
It uses WARC 1.1 via `warcio` and streamed, SHA-256-addressed blobs. The Python entry point is
`kn.archive.Archive`. The operator commands are `kn raw verify` and `kn raw reindex`. See the
[raw archive specification](../../design/spec.md#raw-archive), the
[storage](../records/0055-raw-archive-warc-raw-store.md) and
[fetch ledger](../records/0056-raw-archive-raw-fetch-ledger.md) task records, and the
[group audit](../records/0057-raw-archive-raw-archive-implementation-audit.md).

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

Verification cannot see a batch directory that disappeared as a whole, because the archive keeps
no list of its batches. A later reindex against the previous fetch ledger view reports such a
loss, as described below.

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

Reindex compares the previous view with the archive in its scope. If a covered capture is no
longer in any committed batch and has no tombstone, reindex fails with `capture_lost` and keeps
the previous view. Restore the missing batches from a backup, or accept the loss by removing the
index root's contents and running a full reindex from the archive alone. A full reindex skips the
comparison when the previous view is unreadable, because it replaces that view.

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

The POSIX filesystem implementation stages commits and tombstones under
`staging/_sources/<domain>/<source-id>/` on the archive filesystem. It syncs the files and
directories, publishes one batch directory atomically, and syncs the publication path. Writers for
different sources use separate locks. A revisit commit and a withdrawal read only their own
source's batches. The next commit or withdrawal for a source removes the `pending-*` directories
that an interrupted writer for that source left. Reindex does the same for `staging/` in the index
root under its lock. Each committed directory
under `captures/<domain>/<source-id>/<run-id>/<batch-id>/` holds `manifest.json` and one subdirectory
per capture. Manifest version 1 records the capture time range, stable IDs, relative object paths,
sizes and SHA-256 digests, and per-record compressed offsets and lengths for WARC. Each capture
gets its own WARC segment or blob directory to support independent physical deletion. The WARC
metadata locator can be read directly without inflating the body.

`Archive.withdraw(record_or_fetch_id, reason, withdrawn_at, purge=False)` persists immutable
tombstones under `tombstones/`. The reason is an operator reason code. Tombstones hide affected
captures from lookup and replay, including revisits of a withdrawn target. With `purge=True`,
isolated objects are removed after each affected capture has a durable tombstone. Retrying a
withdrawal completes interrupted publication or removal. With an index root configured, the
withdrawal finds the capture's source through the ledger. Without one, it scans every manifest.

A tombstone whose batch is absent from the archive is kept as detached. It still counts as a
tombstone, makes a lookup of its record ID report `capture_tombstoned`, and suppresses the
capture and its revisits if the batch is restored later. A tombstone that names a capture which
its present batch lacks is refused with `tombstone_capture`.

Engine integration owns source approval and capture scheduling.
[`capture-retention-enforcement`](../plan.md#capture-retention-enforcement) owns expiry, claim
updates for withdrawn evidence, and durable purge records.

## Back up and restore

Back up `captures/` and `tombstones/` with their relative paths. `locks/` and `staging/` hold no
committed state. With writers running, copy `captures/` completely before `tombstones/`, or copy
from a filesystem snapshot. A batch either appears whole or is absent, a purge removes objects only
after their tombstone is durable, and a tombstone copied without its batch stays detached. Copying
in the other order can capture a purge midway without its tombstone, which verification refuses.

To restore, copy the backup to any archive root and apply the current tombstones before opening
reader access. Then run `kn raw verify`, and run `kn raw reindex` with `KN_RAW_INDEX_DIR` pointing
to an empty root or to a retained index. A retained index that covers captures committed after the
backup makes reindex report `capture_lost`. That report names the recovery point; accept it as
described above. Replay by ID works from the archive alone with the index root unset.

## Independent checks and verification

`tests/archive/test_independent.py` reads a segment of every record kind with FastWARC
(`fastwarc`, pinned in the development extra), a WARC parser independent of `warcio`, in
`make ci`. It checks the version, record types, IDs, member offsets, block
digests, HTTP payload digests and revisit references. FastWARC defines a payload only for HTTP
messages. For resource and metadata records KN writes a payload digest equal to the block digest,
and a revisit names its target's payload digest, as WARC 1.1 allows. `fastwarc check` therefore
passes on block digests and reports payload failures for those records with `-p`. GNU `gzip -t`
accepts every segment.

`tests/fixtures/archive/committed-v1/` holds uncompressed records, descriptors and tombstones
written by the audited release, with the metadata and replay digests that it read back.
`tests/archive/test_committed.py` compresses each record into its own member, rebuilds the
archive, and requires the current code to read it identically. Never regenerate it. Add a new
fixture directory for a new format version. Records are stored as `<role>.warc.txt` and blob
bodies as `blob.txt`, so `make fixture-check` scans them as text. The `.gitattributes` entry keeps
the CRLF framing of the records unchanged.

## Known limitations

- A purge is not recorded beyond its tombstone. Restoring a backup taken before a purge keeps the
  capture suppressed, but its bytes return without a report. Nothing withdraws a capture whose
  `expires_at` has passed. `capture-retention-enforcement` owns both.
- Read-time checks reapply the current default redaction. If a later release treats another
  query parameter or header value as a credential, older captures that hold one stop reading with
  `capture_redaction` or a related code. Withdraw and purge them, then fetch again. The
  `committed-v1` fixture makes such a change fail CI. Reopen if a planned redaction change has to
  keep such captures readable.
- A damaged manifest stops `kn raw verify`, `Archive.iter_metadata()`, reindex and lookups that
  scan the archive. With the index, lookups of other batches still resolve. Restore the batch from
  a backup. Reopen if recovery needs partial replay while a batch is lost.
- Request records hold the request line and the approved headers. They have no `Host` header,
  because the target is in `WARC-Target-URI`. Reopen if an external replay tool needs one.
- Metadata-only reads and reindex check object presence and size, not body digests. Replay and
  verification check every digest.
- `staging/pending-*` directories left by releases before this audit are not reclaimed. Remove
  them when no writer, withdrawal or reindex is running.
