# Ingestion Engine Storage

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

The [engine skeleton](../plan.md#engine-skeleton) owns loader wiring, parsing, and the run and
replay commands. [Source status monitoring](../plan.md#source-status-monitoring) owns status
computation, the CLI and operations mart.
