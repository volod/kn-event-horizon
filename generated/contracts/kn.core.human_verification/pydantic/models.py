"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class HumanVerificationDecisions(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    decision_id: _kn_builtins.str = _kn_pydantic.Field(alias='decision_id', description='Deterministic SHA-256 of the canonical typed event', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.decision_id'}})
    target_id: _kn_builtins.str = _kn_pydantic.Field(alias='target_id', description='SHA-256 of the exact typed target including scope, version and purpose', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.target_id'}})
    request_key: _kn_builtins.str = _kn_pydantic.Field(alias='request_key', description='SHA-256 of authenticated reviewer and client request ID', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.request_key'}})
    reviewer: _kn_builtins.str = _kn_pydantic.Field(alias='reviewer', description='Authenticated authorized human principal reference', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.reviewer'}})
    performed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='performed_at', description='Actual UTC instant of the human decision', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.performed_at'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='Separate trusted UTC journal recording time', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.recorded_at'}})
    outcome: _kn_typing.Literal['accept', 'reject', 'revoke', 'supersede'] = _kn_pydantic.Field(alias='outcome', description='Append-only acceptance, rejection, revocation or supersession', json_schema_extra={'x-kn': {'enum': ['accept', 'reject', 'revoke', 'supersede'], 'fieldId': 'evidence.human_verification_decisions.outcome'}})
    event_json: _kn_builtins.str = _kn_pydantic.Field(alias='event_json', description='Canonical human-verification v1 event; authoritative replay payload', json_schema_extra={'x-kn': {'fieldId': 'evidence.human_verification_decisions.event_json'}})
