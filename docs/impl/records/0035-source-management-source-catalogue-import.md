# Source Catalogue Import

## Work contract

```markdown
#### source-catalogue-import

Every candidate source must be visible and disabled before any crawler exists.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [reviewed seed hook](current/data-contracts/rebuild.md#reviewed-seed-hook), the
  [deployment set](current/data-contracts.md#deployment-set) that registers the catalogue contract
  beside the governance contract in `system`, and the data-source proposal JSON for space,
  microelectronics, and GDELT; the [shared verification protocol](current/evidence-model.md).
- User-visible outcome: Every rebuild loads `system.source_catalogue` with 37 space, 65
  microelectronics, and 17 GDELT candidates. `kn source list` shows them in both locales.
- Scope boundary: The catalogue contract, original IDs, lifecycle states, and access notes marked
  unverified. Source rank overrides are validated against catalogue IDs. No crawler
  configuration and no enablement.
- Data and artifact paths: `contracts/core/system/`, `domains/<domain>/seeds/sources.json`,
  `src/kn/sources/`, `tests/sources/`.
- Execution path: Write reviewed seed files from the proposals and add a catalogue loader to the
  rebuild hook.
- Acceptance gates: Every proposal row is loaded or rejected with a reason. Every row is
  `candidate`. Nothing is schedulable from the catalogue.
- Documentation target: A new `current/source-management.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The catalogue contract deploys beside system governance. The rebuild hook loads the three
packaged seed snapshots as `kn_system_loader` within the rebuild transaction. Each row retains
its proposal cells and workbook locator. Microelectronics preserves its native IDs. Space and
GDELT use fixed IDs derived from their original row numbers because their sheets omit an ID column.

The loader sets every row to `candidate` and every access note to `unverified`. The rank policy
starts empty and validates exact catalogue IDs and unique source or field-group scopes before
loading rows. `kn source list` reads the table through the standard database connection and uses
localized interface labels with locale-independent JSON.

| Finding | Severity | Evidence and disposition |
| --- | --- | --- |
| SC-01 | minor | `make ci` found a Radon D (22) reconciliation test. The catalogue import split candidate and per-domain reconciliation assertions. The complexity gate passed. |
| SC-02 | minor | Full pytest collection imported the localization and source CLI tests under the same module name. The catalogue import added the source test package marker. |
| SC-03 | blocker | `test_reviewed_seeds_rebuild_twice_idempotency_and_conflict` found a duplicate key on reapplying seeds. The catalogue and semantic loaders now share idempotent inserts with conflict detection. A catalogue regression checks that a conflict rolls back partial inserts. |
| SC-04 | minor | The compiler directory assertion and bilingual CLI goldens still expected the old registry and root command list. The compiler test now follows the registry, and the updated goldens include source help. |

## Acceptance evidence

Accepted. All declared gates passed.

All 119 rows of the three source sheets reconcile exactly, with zero rejected rows. Tests
also reject malformed or duplicate rows with a location and reason. `kn source run` returns
`E_ARGUMENTS` for catalogue candidates.

- `KN_ENVIRONMENT=development make db-rebuild` ran twice against an isolated PostGIS project.
  `make db-verify` passed. Before rebuild the listing was empty. After each rebuild,
  `kn --json --locale en source list` and `kn --json --locale uk source list` returned
  byte-identical output with 37 space, 65 microelectronics, and 17 GDELT candidates. The
  human-readable listings each contained 119 rows under a localized heading. A third rebuild
  after the idempotency fix reproduced the same listings.
- `make ci` passed all checks and 944 tests. `make test-integration` passed all 92 tests,
  including candidate reads as `kn_system_reader`, seed retry, and rollback on seed conflicts and
  unknown rank overrides. `make model-baseline` passed and reproduced all 62 registered tables
  across two rebuilds.
- `make seed-check` reconciled all 1,173 vocabulary and proposal rows. `make lint-md` and
  `git diff --check` passed.
- `UV_OFFLINE=1 make build` built the wheel and source distribution. The extracted wheel
  loaded the 119 candidates and all six registered contracts outside the checkout.
- Evidence is under `$DATA_DIR/source-catalogue/check-hi9uFtuR/`.

## Handoff

The forward plan changed from 125 to 124 tasks, from 112 to 111 in the agent lane and with 13
in the human lane. MODEL changed from 16 to 15 and DELIVERY remains 109. `crawler-config-schema`
now depends on the documented catalogue and qualified IDs. The source admission audit retains
the catalogue evidence through this record. `canonical-fact-selection` consumes the override
format. The source-management capability remains planned while its crawler configuration,
onboarding and status gates are open.
