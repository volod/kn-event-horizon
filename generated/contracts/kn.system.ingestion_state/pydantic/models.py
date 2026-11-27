"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class SourceCheckpoints(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Domain-qualified source identifier shared with the catalogue and archive', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.source_id'}})
    scope: _kn_builtins.str = _kn_pydantic.Field(alias='scope', description='Stable source-local synchronization stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.scope'}})
    cursor_namespace: _kn_builtins.str = _kn_pydantic.Field(alias='cursor_namespace', description='Live or configured backfill cursor namespace within the stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.cursor_namespace'}})
    revision: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='revision', description='One-based checkpoint generation; the greatest committed revision is current', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.revision'}})
    run_id: _kn_builtins.str = _kn_pydantic.Field(alias='run_id', description='Logical run of the batch justifying the advance', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.run_id'}})
    batch_id: _kn_builtins.str = _kn_pydantic.Field(alias='batch_id', description='Logical batch justifying the advance', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.batch_id', 'foreignKey': {'fields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'batch_id'], 'table': 'source_loaded_batches', 'targetFields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'batch_id']}}})
    cursor_strategy: _kn_typing.Literal['snapshot_hash', 'updated_since', 'id_range', 'window'] = _kn_pydantic.Field(alias='cursor_strategy', description='Crawler cursor strategy used for this stream', json_schema_extra={'x-kn': {'enum': ['snapshot_hash', 'updated_since', 'id_range', 'window'], 'fieldId': 'system.source_checkpoints.cursor_strategy'}})
    cursor_token: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='cursor_token', description='Snapshot SHA-256 or opaque stable source position for id_range', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.cursor_token'}})
    watermark_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='watermark_at', description='UTC resume watermark for updated_since or exclusive end of a processed window', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.watermark_at'}})
    advanced_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='advanced_at', description='UTC instant recorded by the loader when applying this advance', json_schema_extra={'x-kn': {'fieldId': 'system.source_checkpoints.advanced_at'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'SourceCheckpoints':
        for _kn_exact, _kn_names in ((True, ('cursor_token', 'watermark_at')),):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class SourceLoadedBatches(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Domain-qualified source identifier shared with the catalogue and archive', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.source_id'}})
    scope: _kn_builtins.str = _kn_pydantic.Field(alias='scope', description='Stable source-local synchronization stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.scope'}})
    cursor_namespace: _kn_builtins.str = _kn_pydantic.Field(alias='cursor_namespace', description='Live or configured backfill cursor namespace within the stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.cursor_namespace'}})
    run_id: _kn_builtins.str = _kn_pydantic.Field(alias='run_id', description='Stable logical run identifier reused by its retries', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.run_id'}})
    batch_id: _kn_builtins.str = _kn_pydantic.Field(alias='batch_id', description='Logical batch identifier within the run, stable across attempts', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.batch_id'}})
    attempt: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='attempt', description='Attempt that committed the batch', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.attempt', 'foreignKey': {'fields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'attempt'], 'table': 'source_run_attempts', 'targetFields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'attempt']}}})
    archive_run_id: _kn_builtins.str = _kn_pydantic.Field(alias='archive_run_id', description='Run component of the retained raw archive BatchKey', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.archive_run_id'}})
    archive_batch_id: _kn_builtins.str = _kn_pydantic.Field(alias='archive_batch_id', description='Batch component of the retained raw archive BatchKey', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.archive_batch_id'}})
    loaded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='loaded_at', description='UTC instant recorded by the loader when applying the batch', json_schema_extra={'x-kn': {'fieldId': 'system.source_loaded_batches.loaded_at'}})

class SourceRunAttempts(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Domain-qualified source identifier shared with the catalogue and archive', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.source_id'}})
    scope: _kn_builtins.str = _kn_pydantic.Field(alias='scope', description='Stable source-local synchronization stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.scope'}})
    cursor_namespace: _kn_builtins.str = _kn_pydantic.Field(alias='cursor_namespace', description='Live or configured backfill cursor namespace within the stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.cursor_namespace'}})
    run_id: _kn_builtins.str = _kn_pydantic.Field(alias='run_id', description='Stable logical run identifier reused by its retries', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.run_id'}})
    attempt: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='attempt', description='One-based execution attempt within the logical run', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.attempt'}})
    mode: _kn_typing.Literal['fetch', 'replay'] = _kn_pydantic.Field(alias='mode', description='Whether the input comes from a source or retained archive captures', json_schema_extra={'x-kn': {'enum': ['fetch', 'replay'], 'fieldId': 'system.source_run_attempts.mode'}})
    started_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='started_at', description='UTC instant at which the attempt was registered', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.started_at'}})
    finished_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='finished_at', description='UTC instant the outcome was recorded; null for an unfinished attempt', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.finished_at'}})
    status: _kn_typing.Literal['success', 'partial', 'not_modified', 'blocked', 'failed', 'skipped'] | None = _kn_pydantic.Field(default=None, alias='status', description='Terminal run outcome; null until recorded', json_schema_extra={'x-kn': {'enum': ['success', 'partial', 'not_modified', 'blocked', 'failed', 'skipped'], 'fieldId': 'system.source_run_attempts.status'}})
    config_sha256: _kn_builtins.str = _kn_pydantic.Field(alias='config_sha256', description='SHA-256 of the crawler configuration used by this attempt', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.config_sha256'}})
    code_sha256: _kn_builtins.str = _kn_pydantic.Field(alias='code_sha256', description='SHA-256 of the code used by this attempt', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.code_sha256'}})
    incomplete_reason: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='incomplete_reason', description='Reviewed reason identifier for accepting incomplete or invalid input as success', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.incomplete_reason'}})
    record_count: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='record_count', description='Native records read by the attempt; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.record_count'}})
    claim_count: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='claim_count', description='Claims committed by the attempt; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.claim_count'}})
    reject_count: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='reject_count', description='Records rejected by the attempt; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.reject_count'}})
    quarantine_count: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='quarantine_count', description='Records quarantined by the attempt; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.quarantine_count'}})
    bytes_received: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='bytes_received', description='Response entity bytes received by the attempt; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.bytes_received'}})
    requests_used: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='requests_used', description='Source requests counted against the attempt budget; null if unmeasured', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.requests_used'}})
    request_budget: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='request_budget', description='Request limit applied to this attempt; null if inapplicable', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.request_budget'}})
    cursor_lag_seconds: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] | None = _kn_pydantic.Field(default=None, alias='cursor_lag_seconds', description='Cursor lag in whole seconds when this attempt finished; null if unknown or inapplicable', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_attempts.cursor_lag_seconds'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'SourceRunAttempts':
        for _kn_exact, _kn_names in ((False, ('finished_at', 'status')),):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class SourceRunErrors(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Domain-qualified source identifier shared with the catalogue and archive', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.source_id'}})
    scope: _kn_builtins.str = _kn_pydantic.Field(alias='scope', description='Stable source-local synchronization stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.scope'}})
    cursor_namespace: _kn_builtins.str = _kn_pydantic.Field(alias='cursor_namespace', description='Live or configured backfill cursor namespace within the stream', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.cursor_namespace'}})
    run_id: _kn_builtins.str = _kn_pydantic.Field(alias='run_id', description='Stable logical run identifier reused by its retries', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.run_id'}})
    attempt: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='attempt', description='One-based execution attempt within the logical run', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.attempt', 'foreignKey': {'fields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'attempt'], 'table': 'source_run_attempts', 'targetFields': ['source_id', 'scope', 'cursor_namespace', 'run_id', 'attempt']}}})
    error_no: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='error_no', description='One-based occurrence number within the attempt', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.error_no'}})
    observed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='observed_at', description='UTC instant at which the source condition was observed', json_schema_extra={'x-kn': {'fieldId': 'system.source_run_errors.observed_at'}})
    error_code: _kn_typing.Literal['transient_network', 'rate_limited', 'auth_failed', 'permission_denied', 'payload_invalid', 'schema_drift', 'integrity_lost', 'budget_exhausted', 'not_modified'] = _kn_pydantic.Field(alias='error_code', description='Standard source condition code; retry class follows the crawler vocabulary', json_schema_extra={'x-kn': {'enum': ['transient_network', 'rate_limited', 'auth_failed', 'permission_denied', 'payload_invalid', 'schema_drift', 'integrity_lost', 'budget_exhausted', 'not_modified'], 'fieldId': 'system.source_run_errors.error_code'}})
