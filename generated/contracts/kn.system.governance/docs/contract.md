# kn.system.governance

Version: 1.0.0

Digest: `d11eb70b855741d6901677151d2b8bb048cf41b0aa074feae24f0db370c51d06`

Storage schema: `system`

## installed_contracts

One row per deployed storage contract: the installed-contract marker.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| contract_id | system.governance.installed_contracts.contract_id | string | True | True | ODCS id of the deployed storage contract |
| version | system.governance.installed_contracts.version | string | True | False | Semantic version of the deployed contract |
| digest | system.governance.installed_contracts.digest | string | True | False | Canonical SHA-256 digest of the contract and its reference catalog |
| storage_schema | system.governance.installed_contracts.storage_schema | string | True | False | KN schema that holds the contract's tables |
| managed_tables_json | system.governance.installed_contracts.managed_tables_json | string | True | False | Canonical JSON array of the contract's table names |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
