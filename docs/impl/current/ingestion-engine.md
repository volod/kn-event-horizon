# Ingestion Engine

## Run and replay a snapshot

```bash
kn --json source run PROFILE.yaml
kn --json source replay PROFILE.yaml --archive-run-id FETCH_RUN_ID
```

Set `KN_DATABASE_URL` and `KN_DATABASE_PASSWORD_FILE` for the governed PostgreSQL database.
Configure the [raw archive root](raw-archive.md#configure-and-verify) separately. Load the
checkout's `.env` with `source scripts/shared/common.sh && kn_load_env` when using its local
settings. Both commands accept `--data-dir` and use the identity journal under `DATA_DIR` by
default. Keep that journal with the archive to reproduce the same KN IDs on replay.

Execution requires passing [crawler enablement evidence](source-management.md#enablement-evidence)
and an `enabled` row in the deployed catalogue. The current runner supports one unauthenticated
JSON response, one `snapshot_hash` checkpoint stream (`default`, `live`), and WARC captures.
The profile names an HTTPS endpoint under `.localhost` with an explicit port. Transport opens
IPv4 loopback directly and verifies a certificate for `127.0.0.1`. The test harness loads
the local adapter in the reviewed parser namespace and supplies its own trust root.

The loader resolves the native record key through the identity registry and tracks changes
to the declared text fields. The text claim keeps the exact original, source language, and a
JSON Pointer into its WARC response. Use the [shared text selector](localization.md#source-data-and-translations)
to display an original when the requested language and English are unavailable. Missing language
is `und`. Claim and evidence recording times derive from the archived observation time for
deterministic replay. The attempt and batch keep the actual load times.

The command writes an attempt and reports its run ID, attempt number, status, record and claim
counts, request use, received bytes, and committed checkpoint revision in JSON. `success` marks
an applied snapshot, `not_modified` marks identical bytes under the same configuration and code,
and `skipped` marks an already applied or superseded archive batch. `failed` and `blocked` exit
with status 1 and report a stable error code. Admission errors use `E_SOURCE_CONFIG` before
acquisition. The parser validates the entire snapshot before loading. A malformed body, schema
drift, or invalid record key leaves the previous checkpoint and claims in place.

## Retry and replay

The session lock covers registration, acquisition, and the load commit for one source and scope.
A run keeps one batch named `snapshot` under
`$KN_RAW_ARCHIVE_DIR/captures/<domain>/<source-id>/<run-id>/`. A fresh run retains a new response
even when its bytes match the checkpoint. Unchanged bytes under the same profile and code produce
no new identity events, claims, or revision.

After interruption, rerun the same command with the same profile and adapter version. The next
attempt resumes the logical run from the committed checkpoint. A finalized WARC batch supplies
the original capture and the resumed attempt makes zero requests. Identity recovery completes a
pending match before applying the remaining records. Claims, loaded batch, checkpoint and
successful outcome commit together. An unfinished attempt can have unmeasured request counters.

Replay selects the original fetch run by ID and opens its committed manifest. It runs without
source transport and checks the profile digest and the digest of the engine and parser code.
Apply available batches
in capture order when restoring a new stream. An older capture cannot move a live checkpoint
backward. The fixture harness rebuilds the database with the same identity journal and compares
every restored claim and evidence field with the original load.

## Registered storage

The registered `kn.system.ingestion_state` version `1.0.0`
[ODCS contract](../../../contracts/core/system/ingestion-state.odcs.json) defines four tables in
the `system` schema. The development Alembic baseline installs them through the existing
registry. [Generated contract artifacts](../../../generated/contracts/kn.system.ingestion_state/docs/contract.md)
include PostgreSQL DDL and stable field IDs. All four tables use the shared external
[record and field verification projection](evidence-model.md#current-verification-reads).

## Run history and health

Every row belongs to a stream keyed by `(source_id, scope, cursor_namespace)`. The source ID is
domain-qualified and shared with the catalogue and raw archive. Scope is a stable source-local
identifier for the input being synchronized. Ordinary ingestion uses `live`. Backfills use the
namespace declared by the crawler and keep independent checkpoints.

| Table | Key within the stream | Meaning |
| --- | --- | --- |
| `source_run_attempts` | `run_id, attempt` | A logical run can have multiple one-based attempts. Each attempt carries its mode (`fetch` or `replay`), configuration and code digests, times, outcome, and measured health data. |
| `source_run_errors` | `run_id, attempt, error_no` | Ordered observations with one-based occurrence numbers, observation times, and the [standard source codes](source-management.md#error-codes-and-pagination). Repeated codes can have distinct occurrences. |
| `source_loaded_batches` | `run_id, batch_id` | One applied batch per logical run across retries. It links to the writing attempt and the raw archive manifest. |
| `source_checkpoints` | `revision` | Ordered checkpoint advances. Each revision references a loaded batch in the same stream. |

An attempt has a start instant. Its finish instant and terminal status are both present or both
null. Null records an unfinished attempt, including one left open by interruption. A retry adds
an attempt under the same logical run ID. Terminal statuses are `success`, `partial`,
`not_modified`, `blocked`, `failed`, and `skipped`. If reviewed policy accepts incomplete or
invalid data as success, the writer supplies `incomplete_reason` as a reviewed reason identifier.

Health inputs include record, claim, reject and quarantine counts, received bytes, requests used
and their budget, and cursor lag in whole seconds at completion. Null represents an unmeasured
or inapplicable value. Zero represents a measured zero. Event timestamps are PostgreSQL
`timestamptz` instants. Writers supply offset-aware times. Occurrence numbers and checkpoint
revisions give stable order even when clocks tie. Monitoring derives last attempt, last success,
last error, and staleness from the history and crawler thresholds.

The stored archive run and batch IDs join the source ID and its domain prefix to form an
[archive BatchKey](raw-archive.md#commit-and-replay). A stream can apply that archive batch once.
A replay attempt can reference the original archive run even when its logical run ID differs.
Evidence resolves individual captures by their stable record or fetch IDs.

## Checkpoint transaction

`kn.engine.checkpoints.latest_checkpoint(connection, stream)` reads the highest revision visible
to the transaction. Revision zero represents an empty stream. Pass the revision used to select
the input range as `expected_revision` to `advance_checkpoint`. A stale or competing writer gets
`CheckpointConflict` and must roll back its load and reread the stream before retrying. A revision
links to exactly one applied batch, and a batch can advance its stream once.

The loader applies the records and claims, registers the loaded batch, and appends any checkpoint
in one caller-owned PostgreSQL transaction. The deferred batch and attempt references must resolve
at commit. A rollback leaves the previous checkpoint visible and the committed archive available
to reuse. Partial work can be applied without a checkpoint. The caller determines whether the
batch completes a contiguous prefix and verifies the archive reference through the archive API.

`snapshot_hash` uses a lowercase SHA-256 digest. `id_range` uses an opaque source position
represented as nonempty text. Keep source keys and cursor positions free of credentials.
`updated_since` and `window` use offset-aware watermarks normalized to UTC. A window watermark is
the exclusive end of the processed interval before applying the configured overlap for the next
read. The writer rejects backward time watermarks and strategy changes within a stream. Source
ordering for opaque positions follows the crawler's cursor strategy.

## Verification

`make ci` checks vocabulary parity with the crawler schema and compares the compiled artifacts
byte for byte. `make test-integration` exercises duplicate keys, invalid outcomes, foreign keys,
backfill isolation, stale writers, actual concurrent advances, and rollback of claims, batch and
checkpoint together. The rollback fixture then reuses the retained archive on retry.

`make model-baseline` replays interrupted and retried fixture attempts, their errors, the linked
archive batch and checkpoint through two development rebuilds. It compares every field in the
registered subset. The [task record](../records/0058-ingestion-engine-ingestion-state-contracts.md)
contains the acceptance results.

The [engine fixture suite](../../../tests/engine/test_snapshot.py) exercises the operator commands
over loopback HTTPS and a disposable PostgreSQL database. It uses OpenSSL 3 to create an
ephemeral test certificate. The synthetic
[profile](../../../domains/fixture/snapshot.yaml) and
[payload](../../../tests/fixtures/fixture/snapshot.json) run only in that harness. With the local
database running, use `make ci-local` or run the engine suite directly after loading the test
environment.

```bash
source scripts/shared/common.sh && kn_load_env && kn_db_test_env
.venv/bin/python -m pytest tests/engine tests/integration/test_ingestion_state.py
```

The [engine skeleton record](../records/0059-ingestion-engine-engine-skeleton.md) contains
acceptance evidence and recovery findings.
[Source status](source-management.md#source-health-and-freshness) derives operator health from
these tables, including committed checkpoint lag and the last fetch confirmation.

## Known limitations

- [HTTP fetch safety](../plan.md#http-fetch-safety) owns real endpoints, conditional requests,
  pagination controls, retries, and credentials. The fixture transport reads one bounded response.
- [Mapping and quality rules](../plan.md#mapping-and-quality-rules) owns generalized validation and
  per-record quarantine. The fixture engine accepts or stops the snapshot as a unit.
- [Rebuild from raw](../plan.md#rebuild-from-raw) owns automatic discovery and full rebuild replay.
  The fixture engine replays one explicitly selected batch. After `kn db rebuild`, replay each
  archived run of a loaded source before its next `kn source run`. A fetch first ends in
  `E_INPUT` and leaves an unfinished attempt that each retry resumes. Replay also requires an
  enabled profile and catalogue row, so a paused source cannot be restored yet.
