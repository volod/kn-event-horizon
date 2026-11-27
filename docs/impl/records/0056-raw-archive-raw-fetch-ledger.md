# 0056 Raw Fetch Ledger

## Work contract

```markdown
#### raw-fetch-ledger

Operators need fast capture lookup, scoped reindex and a clear way to recover a lost index.

- Serves: `raw-archive` -- [Capture schema and fetch ledger](../design/spec.md#capture-schema-and-fetch-ledger)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: `pyarrow` for reading and writing the Parquet projection and the
  [committed raw archive interface](current/raw-archive.md).
- User-visible outcome: `kn raw reindex` recovers the fetch ledger from committed batches and
  tombstones. Readers can resolve records and query by domain, source and capture time.
- Scope boundary: Versioned logical row schema, a partitioned Parquet projection with batched
  writes, atomic index updates, index coverage, and an archive-only replay path. Keep payloads
  and authoritative commit state in the archive.
- Data and artifact paths: `src/kn/archive/`, `$KN_RAW_INDEX_DIR`, `tests/archive/`.
- Execution path: Derive rows from the archive reader, stage replacement data on the index
  filesystem, and publish a complete index view. Use manifest locators for metadata reads without
  decompressing bodies. Use stable IDs for parity checks and evidence resolution.
- Acceptance gates: Full reindex after deleting the projection yields the same logical rows and
  replay order. A scoped rebuild preserves unrelated partitions. Failed publication leaves a
  readable prior view with correct coverage. A record added after index publication resolves from
  the archive. Tombstones suppress records from stale and rebuilt views. A fixture mixes domains,
  sources, capture versions and both backends. Reindex requires an explicit `KN_RAW_INDEX_DIR` and
  publishes there. `make ci` passes.
- Documentation target: `current/raw-archive.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

`kn raw reindex` publishes the version 1 Parquet ledger to an explicitly configured index root.
It builds row groups from committed manifest entries and reads the metadata locators directly.
Partitions use domain, qualified source, and UTC capture day. A time-scoped rebuild merges
unchanged rows on boundary days and hard-links unaffected partitions. The atomic `CURRENT`
replacement publishes the generation and coverage together. Readers pin a generation while
iterating.

Coverage counts and capture receipts describe the published inputs, including tombstoned IDs.
Queries apply current tombstones. ID lookup uses the ledger to reach a committed manifest and
falls back to the archive for missing coverage or a damaged view. Replay always verifies bytes
from the committed archive. Reindex checks object presence and size without reading body bytes.
Same-size body corruption is checked by verification and replay.

## Acceptance evidence

The focused command `.venv/bin/python -m pytest tests/archive` passed all 35 tests. The ledger
fixture combines WARC and blob captures, v1 and v2 descriptors, multiple domains and sources,
and tied fetch times. It compares logical rows and replay order after deleting the index and
confirms that WARC reindex reads only metadata members. Other cases check exact scoped rebuilds
and unaffected partition reuse, a failed pointer replacement, pinned readers, batched Parquet
writes, post-publication lookup, damaged index recovery, and tombstone suppression before and
after purge. The CLI tests confirm explicit index configuration and relative `.env` paths.

The operator smoke run under `$DATA_DIR/raw-fetch-ledger/run-pddxf83u/` exercised full and
scoped reindex in JSON and text output, post-publication lookup, stale tombstone suppression,
index deletion, archive-only replay and verification, and full recovery. `acceptance.json`
records matching logical rows after recovery, four replay digests, and coverage of five captures,
including one tombstone, across three partitions.

A subprocess exited immediately before replacing `CURRENT`. The old rows and coverage remained
readable, the unindexed capture resolved through the archive, and a retry published both
captures. See `publication-fault.json` in the same run.

Accepted. The final `make ci` passed with 1,476 tests. It deselected 141 integration and heavy
tests under the lightweight test profile. The run's `ci.log` records the gate results.
`make lint-md`, `bash -n .env.example`, and `git diff --check` also passed.

## Handoff

The forward plan moves from 111 to 110 tasks and from 99 to 98 in the agent lane. The human lane
stays at 12. The
[raw archive group audit](0057-raw-archive-raw-archive-implementation-audit.md) can use the ledger
and its acceptance fixtures. The raw archive capability stays planned until the group audit
accepts format conformance and restore.
