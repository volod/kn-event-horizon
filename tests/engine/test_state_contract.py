"""The compiled storage vocabulary agrees with source configuration."""

import json
from importlib.resources import files
from typing import get_args

from kn.engine.checkpoints import CursorStrategy
from kn.engine.state import ATTEMPTS, CHECKPOINTS, ERRORS, ingestion_contract


def test_storage_uses_the_crawler_error_codes_and_cursor_strategies() -> None:
    schema = json.loads(
        files("kn.sources.config").joinpath("crawler.schema.json").read_text(encoding="ascii")
    )
    definitions = schema["$defs"]
    expected_codes = {
        code
        for reference in definitions["errorRule"]["properties"]["code"]["anyOf"]
        for code in definitions[reference["$ref"].rsplit("/", 1)[1]]["enum"]
    }
    contract = ingestion_contract()
    errors = {field.name: field for field in contract.table(ERRORS).fields}
    cursor = {field.name: field for field in contract.table(CHECKPOINTS).fields}
    assert set(errors["error_code"].enum) == expected_codes
    strategies = set(definitions["cursor"]["properties"]["strategy"]["enum"])
    assert set(cursor["cursor_strategy"].enum) == strategies == set(get_args(CursorStrategy))


def test_attempt_statuses_and_monitoring_fields_are_registered() -> None:
    attempt = ingestion_contract().table(ATTEMPTS)
    fields = {field.name: field for field in attempt.fields}
    assert set(fields["status"].enum) == {
        "success",
        "partial",
        "not_modified",
        "blocked",
        "failed",
        "skipped",
    }
    assert not fields["status"].required
    assert fields["started_at"].logical_type == fields["finished_at"].logical_type == "timestamp"
    assert {
        "record_count",
        "claim_count",
        "reject_count",
        "quarantine_count",
        "bytes_received",
        "requests_used",
        "request_budget",
        "cursor_lag_seconds",
        "config_sha256",
        "code_sha256",
        "incomplete_reason",
    } <= fields.keys()
