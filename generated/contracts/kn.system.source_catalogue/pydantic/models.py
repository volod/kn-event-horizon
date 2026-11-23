"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class SourceCatalogue(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='The stable domain-qualified catalogue identifier', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.source_id'}})
    domain: _kn_typing.Literal['space', 'microelectronics', 'gdelt'] = _kn_pydantic.Field(alias='domain', description='The owning knowledge domain', json_schema_extra={'x-kn': {'enum': ['space', 'microelectronics', 'gdelt'], 'fieldId': 'system.source_catalogue.domain'}})
    original_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='original_id', description='Native proposal identifier when the sheet supplies one', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.original_id'}})
    label: _kn_builtins.str = _kn_pydantic.Field(alias='label', description='Original proposal resource name in the source language', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.label'}})
    priority: _kn_typing.Literal['P0', 'P1', 'P2'] = _kn_pydantic.Field(alias='priority', description='Original proposal priority for investigation', json_schema_extra={'x-kn': {'enum': ['P0', 'P1', 'P2'], 'fieldId': 'system.source_catalogue.priority'}})
    cadence: _kn_builtins.str = _kn_pydantic.Field(alias='cadence', description='Original cadence as stated in the proposal', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.cadence'}})
    access_notes_json: _kn_builtins.str = _kn_pydantic.Field(alias='access_notes_json', description='Canonical JSON of provisional access and limitation cells', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.access_notes_json'}})
    access_verification: _kn_typing.Literal['unverified'] = _kn_pydantic.Field(alias='access_verification', description='Verification status of the proposal access notes', json_schema_extra={'x-kn': {'enum': ['unverified'], 'fieldId': 'system.source_catalogue.access_verification'}})
    lifecycle_state: _kn_typing.Literal['candidate', 'investigating', 'sampling_authorized', 'approved', 'enabled', 'paused', 'retired', 'rejected'] = _kn_pydantic.Field(alias='lifecycle_state', description='Lifecycle designation, independent of execution approval', json_schema_extra={'x-kn': {'enum': ['candidate', 'investigating', 'sampling_authorized', 'approved', 'enabled', 'paused', 'retired', 'rejected'], 'fieldId': 'system.source_catalogue.lifecycle_state'}})
    proposal_workbook: _kn_builtins.str = _kn_pydantic.Field(alias='proposal_workbook', description='Original workbook file name', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.proposal_workbook'}})
    proposal_sheet: _kn_builtins.str = _kn_pydantic.Field(alias='proposal_sheet', description='Original workbook sheet name', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.proposal_sheet'}})
    proposal_sha256: _kn_builtins.str = _kn_pydantic.Field(alias='proposal_sha256', description='SHA-256 of the original proposal workbook', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.proposal_sha256'}})
    proposal_row: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='proposal_row', description='One-based row number in the original workbook', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.proposal_row'}})
    proposal_values_json: _kn_builtins.str = _kn_pydantic.Field(alias='proposal_values_json', description='All proposal cells as canonical JSON including source text and nulls', json_schema_extra={'x-kn': {'fieldId': 'system.source_catalogue.proposal_values_json'}})
