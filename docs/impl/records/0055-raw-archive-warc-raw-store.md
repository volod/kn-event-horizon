# WARC Raw Store

## Work contract

````markdown
#### warc-raw-store

Fetch once, transform many requires an archive that can replay original bytes on its own.

- Serves: `raw-archive` -- [Raw archive](../design/spec.md#raw-archive)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: `warcio` and the [storage design review](records/0054-adhoc-raw-archive-storage-design.md).
- User-visible outcome: Approved captures commit as WARC 1.1 batches or streamed content-addressed
  blobs and replay by stable IDs. `kn raw verify` checks the committed archive offline.
- Scope boundary: Request, response, metadata, resource and revisit records, blob descriptors,
  capture schema compatibility, commit manifests, redaction, size and decompression limits,
  and tombstones. Start with local filesystem storage, an explicit `KN_RAW_ARCHIVE_DIR`, and a
  single writer per source.
- Data and artifact paths: `src/kn/archive/`, `$KN_RAW_ARCHIVE_DIR`, `.env.example`, `tests/archive/`,
  `tests/fixtures/archive/`.
- Execution path: Wrap WARC and blob I/O behind the archive interface. Stage a batch, sync it and
  atomically publish its manifest and objects together. Record WARC member offsets and lengths for
  reads of the capture and its metadata. Generate compressed files in tests from sanitized text
  fixtures and synthetic bytes.
- Acceptance gates: Both backends round-trip exact bytes and digests. An interrupted write leaves
  no visible committed batch. Two sources can write independently, and retrying an already
  committed batch reuses its IDs. Old and current metadata read side by side. Verification rejects
  unknown schema versions, missing files and digest mismatches. Redaction keeps credentials out of
  records, URIs and diagnostics. Revisit and tombstone checks pass. Commands with a missing archive
  root fail before I/O, even when `DATA_DIR` is set. Capture and verification work with the index
  root unset. Relative roots resolve from the project root.
- Documentation target: A new `current/raw-archive.md` page listed in the
  [areas index](current.md#areas).
````

The plan opened with 112 tasks (100 agent and 12 human). The storage design review is accepted.

## Implementation and decisions

`kn.archive.Archive` owns approved capture, metadata lookup, replay, verification, and
withdrawal. `kn raw verify` provides the offline operator entry point. Configuration uses an
explicit `KN_RAW_ARCHIVE_DIR` from the environment or the project `.env`, with relative paths
rooted at the project checkout. No index or database is needed. The dependency lock adds
`warcio` and makes the existing `python-dotenv` package a runtime dependency.

Manifest version 1 publishes immutable batches by an atomic directory rename after syncing the
staged content. Source-local advisory locks serialize writes and withdrawals. Each capture gets
an isolated segment or blob directory so different expiry and deletion obligations can be honored.
WARC captures have separate gzip members for the record, request when present, and JSON metadata.
Both backends use SHA-256 and stable UUIDs derived from the batch key, capture key, and ID role.
Metadata version 2 adds `decoded_size` and projects version 1 with a missing value.

Only approved input bodies and selected redacted headers enter committed captures. The caller
supplies retained and decoded byte limits. The first implementation uses one WARC segment per
capture, a 16 MiB WARC payload ceiling, and at most 256 captures per batch. Revisit reuse requires a
matching GET or HEAD request and the same source and retention policy. Tombstones take effect on
lookup and replay before any optional physical removal.

## Acceptance evidence

Accepted. All 22 archive tests passed. The fixtures exercise both backends and exact digests,
compressed HTTP bodies and decoded
limits, metadata-only reads, simultaneous sources, idempotency, a writer process exit immediately
before publication, v1/v2 compatibility, corruption, missing files, redaction, revisit checks,
relocation, and interrupted withdrawal. CLI tests confirm root handling and verification with the
index root unset. The fixtures found and drove fixes for the gzip read mode, Base32 padding, and a
race in shared directory creation.

The smoke run committed and replayed four retained fixture captures across two batches and
verified one tombstone. Both CLI output formats and `warcio check` succeeded. The run is under
`$DATA_DIR/warc-raw-store/run-Jw42BOPe/`, including the archive, replay digests, and verification
reports.

The final `make ci` passed with 1,463 tests and 141 deselected integration and heavy tests.
`make lint-md`, `bash -n .env.example`, and `git diff --check` passed.

## Handoff

The forward plan drops from 112 to 111 tasks, from 100 to 99 in the agent lane. The human lane
remains at 12. The raw archive registry links its current implementation and remains planned
through the [fetch ledger](../plan.md#raw-fetch-ledger) and
[archive audit](../plan.md#raw-archive-implementation-audit). The fetch ledger is now the first
ready agent task. Independent WARC tool conformance and the full backup and restore acceptance
remain in the audit.
