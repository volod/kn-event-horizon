# kn.system.ingestion_state

Version: 1.0.0

Digest: `e97701e180d7b762d6b6aa041ccc71a9815d2e6f51a79f159985c949a847bc65`

Storage schema: `system`

## source_checkpoints

Append-only checkpoint advances, each linked to a loaded batch in the same stream.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| source_id | system.source_checkpoints.source_id | string | True | True | Domain-qualified source identifier shared with the catalogue and archive |
| scope | system.source_checkpoints.scope | string | True | True | Stable source-local synchronization stream |
| cursor_namespace | system.source_checkpoints.cursor_namespace | string | True | True | Live or configured backfill cursor namespace within the stream |
| revision | system.source_checkpoints.revision | integer | True | True | One-based checkpoint generation; the greatest committed revision is current |
| run_id | system.source_checkpoints.run_id | string | True | False | Logical run of the batch justifying the advance |
| batch_id | system.source_checkpoints.batch_id | string | True | False | Logical batch justifying the advance |
| cursor_strategy | system.source_checkpoints.cursor_strategy | string | True | False | Crawler cursor strategy used for this stream |
| cursor_token | system.source_checkpoints.cursor_token | string | False | False | Snapshot SHA-256 or opaque stable source position for id_range |
| watermark_at | system.source_checkpoints.watermark_at | timestamp | False | False | UTC resume watermark for updated_since or exclusive end of a processed window |
| advanced_at | system.source_checkpoints.advanced_at | timestamp | True | False | UTC instant recorded by the loader when applying this advance |

## source_loaded_batches

A batch applied in the loader transaction and its committed raw archive manifest reference.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| source_id | system.source_loaded_batches.source_id | string | True | True | Domain-qualified source identifier shared with the catalogue and archive |
| scope | system.source_loaded_batches.scope | string | True | True | Stable source-local synchronization stream |
| cursor_namespace | system.source_loaded_batches.cursor_namespace | string | True | True | Live or configured backfill cursor namespace within the stream |
| run_id | system.source_loaded_batches.run_id | string | True | True | Stable logical run identifier reused by its retries |
| batch_id | system.source_loaded_batches.batch_id | string | True | True | Logical batch identifier within the run, stable across attempts |
| attempt | system.source_loaded_batches.attempt | integer | True | False | Attempt that committed the batch |
| archive_run_id | system.source_loaded_batches.archive_run_id | string | True | False | Run component of the retained raw archive BatchKey |
| archive_batch_id | system.source_loaded_batches.archive_batch_id | string | True | False | Batch component of the retained raw archive BatchKey |
| loaded_at | system.source_loaded_batches.loaded_at | timestamp | True | False | UTC instant recorded by the loader when applying the batch |

## source_run_attempts

One execution attempt of a logical ingestion run, including its outcome and health observations.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| source_id | system.source_run_attempts.source_id | string | True | True | Domain-qualified source identifier shared with the catalogue and archive |
| scope | system.source_run_attempts.scope | string | True | True | Stable source-local synchronization stream |
| cursor_namespace | system.source_run_attempts.cursor_namespace | string | True | True | Live or configured backfill cursor namespace within the stream |
| run_id | system.source_run_attempts.run_id | string | True | True | Stable logical run identifier reused by its retries |
| attempt | system.source_run_attempts.attempt | integer | True | True | One-based execution attempt within the logical run |
| mode | system.source_run_attempts.mode | string | True | False | Whether the input comes from a source or retained archive captures |
| started_at | system.source_run_attempts.started_at | timestamp | True | False | UTC instant at which the attempt was registered |
| finished_at | system.source_run_attempts.finished_at | timestamp | False | False | UTC instant the outcome was recorded; null for an unfinished attempt |
| status | system.source_run_attempts.status | string | False | False | Terminal run outcome; null until recorded |
| config_sha256 | system.source_run_attempts.config_sha256 | string | True | False | SHA-256 of the crawler configuration used by this attempt |
| code_sha256 | system.source_run_attempts.code_sha256 | string | True | False | SHA-256 of the code used by this attempt |
| incomplete_reason | system.source_run_attempts.incomplete_reason | string | False | False | Reviewed reason identifier for accepting incomplete or invalid input as success |
| record_count | system.source_run_attempts.record_count | integer | False | False | Native records read by the attempt; null if unmeasured |
| claim_count | system.source_run_attempts.claim_count | integer | False | False | Claims committed by the attempt; null if unmeasured |
| reject_count | system.source_run_attempts.reject_count | integer | False | False | Records rejected by the attempt; null if unmeasured |
| quarantine_count | system.source_run_attempts.quarantine_count | integer | False | False | Records quarantined by the attempt; null if unmeasured |
| bytes_received | system.source_run_attempts.bytes_received | integer | False | False | Response entity bytes received by the attempt; null if unmeasured |
| requests_used | system.source_run_attempts.requests_used | integer | False | False | Source requests counted against the attempt budget; null if unmeasured |
| request_budget | system.source_run_attempts.request_budget | integer | False | False | Request limit applied to this attempt; null if inapplicable |
| cursor_lag_seconds | system.source_run_attempts.cursor_lag_seconds | integer | False | False | Cursor lag in whole seconds when this attempt finished; null if unknown or inapplicable |

## source_run_errors

Ordered standard source error and disposition history for each attempt.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| source_id | system.source_run_errors.source_id | string | True | True | Domain-qualified source identifier shared with the catalogue and archive |
| scope | system.source_run_errors.scope | string | True | True | Stable source-local synchronization stream |
| cursor_namespace | system.source_run_errors.cursor_namespace | string | True | True | Live or configured backfill cursor namespace within the stream |
| run_id | system.source_run_errors.run_id | string | True | True | Stable logical run identifier reused by its retries |
| attempt | system.source_run_errors.attempt | integer | True | True | One-based execution attempt within the logical run |
| error_no | system.source_run_errors.error_no | integer | True | True | One-based occurrence number within the attempt |
| observed_at | system.source_run_errors.observed_at | timestamp | True | False | UTC instant at which the source condition was observed |
| error_code | system.source_run_errors.error_code | string | True | False | Standard source condition code; retry class follows the crawler vocabulary |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
