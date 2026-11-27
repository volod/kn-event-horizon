CREATE TABLE system.source_checkpoints (
	source_id TEXT NOT NULL,
	scope TEXT NOT NULL,
	cursor_namespace TEXT NOT NULL,
	revision BIGINT NOT NULL,
	run_id TEXT NOT NULL,
	batch_id TEXT NOT NULL,
	cursor_strategy TEXT NOT NULL,
	cursor_token TEXT,
	watermark_at TIMESTAMP WITH TIME ZONE,
	advanced_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_source_checkpoints PRIMARY KEY (source_id, scope, cursor_namespace, revision),
	CONSTRAINT ck_source_checkpoints_cursor_strategy_enum CHECK (cursor_strategy IN ('snapshot_hash', 'updated_since', 'id_range', 'window')),
	CONSTRAINT ck_source_checkpoints_cursor_value_presence CHECK (num_nonnulls(cursor_token, watermark_at) = 1)
);

CREATE TABLE system.source_loaded_batches (
	source_id TEXT NOT NULL,
	scope TEXT NOT NULL,
	cursor_namespace TEXT NOT NULL,
	run_id TEXT NOT NULL,
	batch_id TEXT NOT NULL,
	attempt BIGINT NOT NULL,
	archive_run_id TEXT NOT NULL,
	archive_batch_id TEXT NOT NULL,
	loaded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_source_loaded_batches PRIMARY KEY (source_id, scope, cursor_namespace, run_id, batch_id)
);

CREATE TABLE system.source_run_attempts (
	source_id TEXT NOT NULL,
	scope TEXT NOT NULL,
	cursor_namespace TEXT NOT NULL,
	run_id TEXT NOT NULL,
	attempt BIGINT NOT NULL,
	mode TEXT NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	status TEXT,
	config_sha256 TEXT NOT NULL,
	code_sha256 TEXT NOT NULL,
	incomplete_reason TEXT,
	record_count BIGINT,
	claim_count BIGINT,
	reject_count BIGINT,
	quarantine_count BIGINT,
	bytes_received BIGINT,
	requests_used BIGINT,
	request_budget BIGINT,
	cursor_lag_seconds BIGINT,
	CONSTRAINT pk_source_run_attempts PRIMARY KEY (source_id, scope, cursor_namespace, run_id, attempt),
	CONSTRAINT ck_source_run_attempts_mode_enum CHECK (mode IN ('fetch', 'replay')),
	CONSTRAINT ck_source_run_attempts_status_enum CHECK (status IN ('success', 'partial', 'not_modified', 'blocked', 'failed', 'skipped')),
	CONSTRAINT ck_source_run_attempts_terminal_outcome_presence CHECK (num_nonnulls(finished_at, status) IN (0, 2))
);

CREATE TABLE system.source_run_errors (
	source_id TEXT NOT NULL,
	scope TEXT NOT NULL,
	cursor_namespace TEXT NOT NULL,
	run_id TEXT NOT NULL,
	attempt BIGINT NOT NULL,
	error_no BIGINT NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	error_code TEXT NOT NULL,
	CONSTRAINT pk_source_run_errors PRIMARY KEY (source_id, scope, cursor_namespace, run_id, attempt, error_no),
	CONSTRAINT ck_source_run_errors_error_code_enum CHECK (error_code IN ('transient_network', 'rate_limited', 'auth_failed', 'permission_denied', 'payload_invalid', 'schema_drift', 'integrity_lost', 'budget_exhausted', 'not_modified'))
);

ALTER TABLE system.source_checkpoints ADD CONSTRAINT fk_source_checkpoints_source_id_scope_cursor_namespace_be42fe5c FOREIGN KEY(source_id, scope, cursor_namespace, run_id, batch_id) REFERENCES system.source_loaded_batches (source_id, scope, cursor_namespace, run_id, batch_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX source_checkpoints_batch_idx ON system.source_checkpoints USING btree (source_id, scope, cursor_namespace, run_id, batch_id);

COMMENT ON TABLE system.source_checkpoints IS 'Append-only checkpoint advances, each linked to a loaded batch in the same stream.';

COMMENT ON COLUMN system.source_checkpoints.source_id IS 'Domain-qualified source identifier shared with the catalogue and archive';

COMMENT ON COLUMN system.source_checkpoints.scope IS 'Stable source-local synchronization stream';

COMMENT ON COLUMN system.source_checkpoints.cursor_namespace IS 'Live or configured backfill cursor namespace within the stream';

COMMENT ON COLUMN system.source_checkpoints.revision IS 'One-based checkpoint generation; the greatest committed revision is current';

COMMENT ON COLUMN system.source_checkpoints.run_id IS 'Logical run of the batch justifying the advance';

COMMENT ON COLUMN system.source_checkpoints.batch_id IS 'Logical batch justifying the advance';

COMMENT ON COLUMN system.source_checkpoints.cursor_strategy IS 'Crawler cursor strategy used for this stream';

COMMENT ON COLUMN system.source_checkpoints.cursor_token IS 'Snapshot SHA-256 or opaque stable source position for id_range';

COMMENT ON COLUMN system.source_checkpoints.watermark_at IS 'UTC resume watermark for updated_since or exclusive end of a processed window';

COMMENT ON COLUMN system.source_checkpoints.advanced_at IS 'UTC instant recorded by the loader when applying this advance';

ALTER TABLE system.source_loaded_batches ADD CONSTRAINT fk_source_loaded_batches_source_id_scope_cursor_namesp_e43b4b6d FOREIGN KEY(source_id, scope, cursor_namespace, run_id, attempt) REFERENCES system.source_run_attempts (source_id, scope, cursor_namespace, run_id, attempt) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX source_loaded_batches_archive_idx ON system.source_loaded_batches USING btree (source_id, scope, cursor_namespace, archive_run_id, archive_batch_id);

COMMENT ON TABLE system.source_loaded_batches IS 'A batch applied in the loader transaction and its committed raw archive manifest reference.';

COMMENT ON COLUMN system.source_loaded_batches.source_id IS 'Domain-qualified source identifier shared with the catalogue and archive';

COMMENT ON COLUMN system.source_loaded_batches.scope IS 'Stable source-local synchronization stream';

COMMENT ON COLUMN system.source_loaded_batches.cursor_namespace IS 'Live or configured backfill cursor namespace within the stream';

COMMENT ON COLUMN system.source_loaded_batches.run_id IS 'Stable logical run identifier reused by its retries';

COMMENT ON COLUMN system.source_loaded_batches.batch_id IS 'Logical batch identifier within the run, stable across attempts';

COMMENT ON COLUMN system.source_loaded_batches.attempt IS 'Attempt that committed the batch';

COMMENT ON COLUMN system.source_loaded_batches.archive_run_id IS 'Run component of the retained raw archive BatchKey';

COMMENT ON COLUMN system.source_loaded_batches.archive_batch_id IS 'Batch component of the retained raw archive BatchKey';

COMMENT ON COLUMN system.source_loaded_batches.loaded_at IS 'UTC instant recorded by the loader when applying the batch';

CREATE INDEX source_run_attempts_started_idx ON system.source_run_attempts USING btree (source_id, scope, cursor_namespace, started_at);

COMMENT ON TABLE system.source_run_attempts IS 'One execution attempt of a logical ingestion run, including its outcome and health observations.';

COMMENT ON COLUMN system.source_run_attempts.source_id IS 'Domain-qualified source identifier shared with the catalogue and archive';

COMMENT ON COLUMN system.source_run_attempts.scope IS 'Stable source-local synchronization stream';

COMMENT ON COLUMN system.source_run_attempts.cursor_namespace IS 'Live or configured backfill cursor namespace within the stream';

COMMENT ON COLUMN system.source_run_attempts.run_id IS 'Stable logical run identifier reused by its retries';

COMMENT ON COLUMN system.source_run_attempts.attempt IS 'One-based execution attempt within the logical run';

COMMENT ON COLUMN system.source_run_attempts.mode IS 'Whether the input comes from a source or retained archive captures';

COMMENT ON COLUMN system.source_run_attempts.started_at IS 'UTC instant at which the attempt was registered';

COMMENT ON COLUMN system.source_run_attempts.finished_at IS 'UTC instant the outcome was recorded; null for an unfinished attempt';

COMMENT ON COLUMN system.source_run_attempts.status IS 'Terminal run outcome; null until recorded';

COMMENT ON COLUMN system.source_run_attempts.config_sha256 IS 'SHA-256 of the crawler configuration used by this attempt';

COMMENT ON COLUMN system.source_run_attempts.code_sha256 IS 'SHA-256 of the code used by this attempt';

COMMENT ON COLUMN system.source_run_attempts.incomplete_reason IS 'Reviewed reason identifier for accepting incomplete or invalid input as success';

COMMENT ON COLUMN system.source_run_attempts.record_count IS 'Native records read by the attempt; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.claim_count IS 'Claims committed by the attempt; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.reject_count IS 'Records rejected by the attempt; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.quarantine_count IS 'Records quarantined by the attempt; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.bytes_received IS 'Response entity bytes received by the attempt; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.requests_used IS 'Source requests counted against the attempt budget; null if unmeasured';

COMMENT ON COLUMN system.source_run_attempts.request_budget IS 'Request limit applied to this attempt; null if inapplicable';

COMMENT ON COLUMN system.source_run_attempts.cursor_lag_seconds IS 'Cursor lag in whole seconds when this attempt finished; null if unknown or inapplicable';

ALTER TABLE system.source_run_errors ADD CONSTRAINT fk_source_run_errors_source_id_scope_cursor_namespace__9feede0c FOREIGN KEY(source_id, scope, cursor_namespace, run_id, attempt) REFERENCES system.source_run_attempts (source_id, scope, cursor_namespace, run_id, attempt) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE system.source_run_errors IS 'Ordered standard source error and disposition history for each attempt.';

COMMENT ON COLUMN system.source_run_errors.source_id IS 'Domain-qualified source identifier shared with the catalogue and archive';

COMMENT ON COLUMN system.source_run_errors.scope IS 'Stable source-local synchronization stream';

COMMENT ON COLUMN system.source_run_errors.cursor_namespace IS 'Live or configured backfill cursor namespace within the stream';

COMMENT ON COLUMN system.source_run_errors.run_id IS 'Stable logical run identifier reused by its retries';

COMMENT ON COLUMN system.source_run_errors.attempt IS 'One-based execution attempt within the logical run';

COMMENT ON COLUMN system.source_run_errors.error_no IS 'One-based occurrence number within the attempt';

COMMENT ON COLUMN system.source_run_errors.observed_at IS 'UTC instant at which the source condition was observed';

COMMENT ON COLUMN system.source_run_errors.error_code IS 'Standard source condition code; retry class follows the crawler vocabulary';
