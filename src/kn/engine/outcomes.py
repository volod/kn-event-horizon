"""Run outcomes and value-free failures shared by ingestion stages."""

from dataclasses import dataclass
from typing import Literal

type Status = Literal["success", "partial", "not_modified", "blocked", "failed", "skipped"]
type ErrorCode = Literal[
    "transient_network",
    "rate_limited",
    "auth_failed",
    "permission_denied",
    "not_modified",
    "payload_invalid",
    "schema_drift",
    "integrity_lost",
    "budget_exhausted",
]


class RunFailure(Exception):
    def __init__(self, code: ErrorCode, status: Status = "failed") -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(slots=True)
class Metrics:
    requests_used: int = 0
    bytes_received: int = 0
    record_count: int = 0
    claim_count: int = 0
