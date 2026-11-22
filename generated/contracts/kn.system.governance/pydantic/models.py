"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class InstalledContracts(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    contract_id: _kn_builtins.str = _kn_pydantic.Field(alias='contract_id', description='ODCS id of the deployed storage contract', json_schema_extra={'x-kn': {'fieldId': 'system.governance.installed_contracts.contract_id'}})
    version: _kn_builtins.str = _kn_pydantic.Field(alias='version', description='Semantic version of the deployed contract', json_schema_extra={'x-kn': {'fieldId': 'system.governance.installed_contracts.version'}})
    digest: _kn_builtins.str = _kn_pydantic.Field(alias='digest', description='Canonical SHA-256 digest of the contract and its reference catalog', json_schema_extra={'x-kn': {'fieldId': 'system.governance.installed_contracts.digest'}})
    storage_schema: _kn_builtins.str = _kn_pydantic.Field(alias='storage_schema', description="KN schema that holds the contract's tables", json_schema_extra={'x-kn': {'fieldId': 'system.governance.installed_contracts.storage_schema'}})
    managed_tables_json: _kn_builtins.str = _kn_pydantic.Field(alias='managed_tables_json', description="Canonical JSON array of the contract's table names", json_schema_extra={'x-kn': {'fieldId': 'system.governance.installed_contracts.managed_tables_json'}})
