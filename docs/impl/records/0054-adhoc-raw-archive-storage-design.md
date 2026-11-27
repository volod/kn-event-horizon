# Raw Archive Storage Design

## Work contract

Evaluate WARC 1.1, Avro and Apache Iceberg against the planned durable raw archive. Refine the
specification and implementation tasks where the comparison improves replay, schema evolution or
the path to a larger deployment. The archive build and its audit retain their own acceptance
gates. Before the review, the plan had 111 tasks, with 99 agent and 12 human tasks.
The follow-up asks for separately configured storage roots without a default under `DATA_DIR`.

The original `warc-raw-store` task combined WARC request, response, metadata, resource and revisit
records with redaction, limits, atomic writes, the tombstone format and a Parquet ledger.
It deferred the blob fallback until a source needed it. The group audit owned independent WARC
readability, integrity, interruption, reindex, retention, backup and target-volume growth.

## Implementation and decisions

KN needs byte-preserving replay across HTTP APIs, curated evidence, and owner-supplied packages.
The schema that changes during development is usually the parser's native schema or KN's typed
projection. Both can change while the captured bytes and evidence IDs stay fixed. An inspection
of the code and dependency lock found an existing SATCOM package archive and a development-only
Avro dependency. The shared raw archive and fetch ledger are still planned.

- **WARC 1.1.** The standard represents HTTP requests and responses, arbitrary resource bytes,
  capture metadata and revisits. Per-record gzip supports record-level reads using offsets and
  lengths. Independent WARC readers can read captures outside KN. Large or already compressed
  packages can use streamed, content-addressed blobs with their own capture descriptors.
  [IIPC WARC 1.1](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/)
  [warcio](https://github.com/webrecorder/warcio)
- **Avro.** Object container files embed a writer schema and store records in blocks. Reader/writer
  schema resolution helps when consumers exchange typed capture envelopes. A raw body stored in
  an Avro `bytes` field remains opaque, and KN would own the HTTP capture and revisit conventions.
  Explicit versions and compatibility fixtures for the compact metadata schema meet the initial
  archive requirements. [Apache Avro specification](https://avro.apache.org/docs/1.12.0/specification/)
- **Parquet.** A columnar projection supports scoped metadata queries while the archive preserves
  complete bodies and their provenance. File-level Parquet supplies metadata for column reads.
  KN owns publication and recovery of its multi-file index. Batching, partitioning and complete
  index publication fit the initial single-host deployment.
  [Apache Parquet file format](https://parquet.apache.org/docs/file-format/)
- **Iceberg.** A future metadata table can use Parquet data files and add atomic table commits,
  snapshot isolation, and field-ID and partition evolution. A catalog or equivalent atomic commit
  mechanism and maintenance for small files, metadata and snapshot expiry add operating cost.
  Use snapshots for table reads. Keep evidence retention and recovery anchored in the committed
  archive and tombstones. [Apache Iceberg specification](https://iceberg.apache.org/spec/)
  [Evolution](https://iceberg.apache.org/docs/latest/evolution/)
  [Maintenance](https://iceberg.apache.org/docs/latest/maintenance/)

Each committed batch has a manifest and a versioned capture schema. Manifest locators let reindex
read capture metadata without inflating payloads. Stable evidence IDs survive reindex and an index
backend change. See the [archive specification](../../design/spec.md#raw-archive).

`KN_RAW_ARCHIVE_DIR` holds captures, manifests, staging and tombstones. An explicitly configured
`KN_RAW_INDEX_DIR` holds the rebuildable Parquet data. This permits a separate archive volume with
its own backup policy and an independent index volume. Archive-only paths require only the archive
root. The existing SATCOM adapter still uses its standalone archive until the planned engine
integration. See the [storage root contract](../../design/spec.md#storage-roots).

The operations gate measures many sources across domains and one bulk-heavy source. If a table
bottleneck meets the reopening condition, compare scoped lookup and full recovery against Iceberg
and rebuild the candidate table from committed batches. Check row, tombstone and record-resolution
parity before switching readers.
If the limiting factor is payload capacity or restore throughput, evaluate object storage for the
payloads independently of the index. Site-specific timings, budgets and break-even points remain
open until the archive exists and is measured on the target host. See the
[performance gate](../plan.md#performance-gate).

## Acceptance evidence

Design review accepted. Runtime acceptance stays with the implementation tasks.

- An in-memory check using `.venv/bin/python` and the locked `fastavro` dependency wrote two
  container files with `fetch_id` and the same binary `body`. The v2 writer added a nullable
  `mime` field with default `null`. The v2 reader projected both files, supplied the default for
  v1, and preserved byte equality and SHA-256 for both bodies. This checked schema semantics.
- `make ci` passed with 1,441 tests and 141 deselected integration and heavy tests. `make lint-md`,
  `make lint-spec-plan`, and `git diff --check` passed.
- The same checks passed after the storage root follow-up. `bash -n .env.example` also passed.
  The follow-up kept 112 tasks and added root configuration and relocation checks to the archive
  tasks and audit.
- No target-host format throughput or cost comparison was run. The first measurements belong
  to the performance gate after archive implementation.

## Handoff

`warc-raw-store` owns capture, compatibility, commit and verification. `raw-fetch-ledger` owns the
derived Parquet index and index-loss recovery. Both gate `raw-archive-implementation-audit`. Replay,
prefetched package ingestion, backup and the target-host performance gate consume the revised
contract. The [closed question](../future-research.md#raw-archive-format-selection----avro-and-iceberg-for-the-raw-archive)
records when to reconsider the initial format choices.

`make plan-status` reports 112 tasks, up from 111. The agent lane grew from 99 to 100 and the
human lane has 12. `warc-raw-store` remains the first ready agent task.
