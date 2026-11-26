# kn.core.human_verification

Version: 1.0.0

Digest: `5fce8e3b635a0bd6a49f2e31f4e20905a541ed7696909e464922628d6be73e35`

Storage schema: `evidence`

## human_verification_decisions

Append-only SQL projection of the trusted durable human decision journal.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| decision_id | evidence.human_verification_decisions.decision_id | string | True | True | Deterministic SHA-256 of the canonical typed event |
| target_id | evidence.human_verification_decisions.target_id | string | True | False | SHA-256 of the exact typed target including scope, version and purpose |
| request_key | evidence.human_verification_decisions.request_key | string | True | False | SHA-256 of authenticated reviewer and client request ID |
| reviewer | evidence.human_verification_decisions.reviewer | string | True | False | Authenticated authorized human principal reference |
| performed_at | evidence.human_verification_decisions.performed_at | timestamp | True | False | Actual UTC instant of the human decision |
| recorded_at | evidence.human_verification_decisions.recorded_at | timestamp | True | False | Separate trusted UTC journal recording time |
| outcome | evidence.human_verification_decisions.outcome | string | True | False | Append-only acceptance, rejection, revocation or supersession |
| event_json | evidence.human_verification_decisions.event_json | string | True | False | Canonical human-verification v1 event; authoritative replay payload |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
