# kn.system.source_catalogue

Version: 1.0.0

Digest: `0ce10ede802cc012d5d122c7d94c03769f20baef4860d7eb1163bbc2b0a3df06`

Storage schema: `system`

## source_catalogue

Source discovery and lifecycle catalogue. Catalogue rows confer no execution authority.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| source_id | system.source_catalogue.source_id | string | True | True | The stable domain-qualified catalogue identifier |
| domain | system.source_catalogue.domain | string | True | False | The owning knowledge domain |
| original_id | system.source_catalogue.original_id | string | False | False | Native proposal identifier when the sheet supplies one |
| label | system.source_catalogue.label | string | True | False | Original proposal resource name in the source language |
| priority | system.source_catalogue.priority | string | True | False | Original proposal priority for investigation |
| cadence | system.source_catalogue.cadence | string | True | False | Original cadence as stated in the proposal |
| access_notes_json | system.source_catalogue.access_notes_json | string | True | False | Canonical JSON of provisional access and limitation cells |
| access_verification | system.source_catalogue.access_verification | string | True | False | Verification status of the proposal access notes |
| lifecycle_state | system.source_catalogue.lifecycle_state | string | True | False | Lifecycle designation, independent of execution approval |
| proposal_workbook | system.source_catalogue.proposal_workbook | string | True | False | Original workbook file name |
| proposal_sheet | system.source_catalogue.proposal_sheet | string | True | False | Original workbook sheet name |
| proposal_sha256 | system.source_catalogue.proposal_sha256 | string | True | False | SHA-256 of the original proposal workbook |
| proposal_row | system.source_catalogue.proposal_row | integer | True | False | One-based row number in the original workbook |
| proposal_values_json | system.source_catalogue.proposal_values_json | string | True | False | All proposal cells as canonical JSON including source text and nulls |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
