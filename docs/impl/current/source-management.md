# Source Management

A [development rebuild](data-contracts/rebuild.md) loads 37 space, 65 microelectronics, and
17 GDELT candidates into `system.source_catalogue`. All 119 start in `candidate` with
`access_verification=unverified`. Scheduling requires a separately reviewed
crawler configuration and approval. Catalogue rows carry no scheduling authority.

## List sources

Set `KN_DATABASE_URL` and `KN_DATABASE_PASSWORD_FILE` for the rebuilt database before running
`kn source list`.

```bash
kn --locale en source list
kn --locale uk source list
kn --json source list
```

The command can connect as a database login with the `kn_system_reader` role. It lists sources
by domain and original worksheet row. The headings, lifecycle labels, and access status use
the selected interface language. Names and cadence retain the original proposal text. The
`--json` output is identical in both locales. Each entry includes the catalogue ID, domain,
nullable original ID, label, priority, cadence, structured access notes, access verification
status, and lifecycle state. A newly upgraded empty database lists zero candidates until its
first development rebuild.

## Reviewed inputs and identifiers

The [ODCS contract](../../../contracts/core/system/source-catalogue.odcs.json) deploys beside
system governance. Its eight lifecycle values are `candidate`, `investigating`,
`sampling_authorized`, `approved`, `enabled`, `paused`, `retired`, and `rejected`.

Each `domains/<domain>/seeds/sources.json` points to the packaged reviewed snapshot.
Microelectronics uses exact native IDs such as `microelectronics:D01`. Space and GDELT
use the original worksheet row number as a fixed local ID, such as `space:row-4` or
`gdelt:row-5`, with a null `original_id`. These keys stay fixed when listing or ordering
changes. Preserve each assigned key when adding a later proposal version. Every row retains
its workbook name, SHA-256, sheet name, row number, and every original cell. Coverage,
watchlist, and ingestion-order guidance sheets stay with their original proposals.

Proposal access statements, including source-provided review labels, remain unverified metadata.
A [human verification decision](evidence-model.md) requires an authorized actor and an exact
target and version. Proposal priority `P0`, `P1`, or `P2` is an investigation priority.

The reviewed [source rank policy](../../../contracts/core/policies/source-ranks.yaml) starts
with an empty `overrides` list. Each override has an exact qualified `source_id`, a
[rank class](../../design/spec.md#update-policy) in `rank`, and an optional `field_group`.
Rebuild refuses unknown IDs, invalid classes, and duplicate scopes before inserting candidates.
Claim ranking and field-group resolution belong to `canonical-fact-selection`.

Reapplying reviewed seeds preserves identical rows. A conflicting row aborts the catalogue
seed load and rolls back any partial insert.

## Verification

- `make ci` reconciles every seed against its original proposal row, validates malformed
  inputs and rank references, checks both CLI locales, and detects generated-contract drift.
- `make test-integration` checks repeated PostgreSQL rebuilds, the reader role, and rollback
  on seed conflicts or unknown override IDs. The [combined baseline](data-contracts/model-baseline.md)
  compares all stored catalogue fields across two rebuilds.

[Task record 0035](../records/0035-source-management-source-catalogue-import.md) preserves the
acceptance evidence. Crawler configuration validation and onboarding remain in the
[forward plan](../plan.md#crawler-config-schema).
