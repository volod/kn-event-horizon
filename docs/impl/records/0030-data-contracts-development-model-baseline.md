# Development Model Baseline

## Work contract

Original plan task, preserved before implementation:

```markdown
#### development-model-baseline

Shared models need one integrated, rebuildable baseline before runtime features create persistent
references to their keys and column meanings.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `human-verification-projections`, `interchange-schema-evolution`
- Dependencies: The [schema-first sequence](../guide/schema-first-development.md), registered
  core/domain contracts, reviewed seeds and deterministic fixture data. No live source is needed.
- User-visible outcome: One compiled development baseline contains the identity, evidence, human
  verification, supply/measurement, source/run, exchange and three domain models together.
  Runtime tasks can use these definitions without introducing another interpretation of a key,
  timestamp, unit, missing reason or review scope.
- Scope boundary: Cross-contract compatibility, common traits and field IDs, constraints, seed
  references, permissions, rebuild/backfill and fixture round trips. This is a development
  checkpoint, not the release freeze or a promise that no future additive fields will be needed.
- Data and artifact paths: `contracts/`, `src/kn/contracts/resources/`, `generated/contracts/`,
  `src/kn/db/`, `tests/integration/`, `$DATA_DIR/model-baseline/<run-id>/`.
- Execution path: Compile the complete registry, load representative fixtures for every model,
  rebuild twice, and compare identifiers, values, review metadata and all contract markers.
- Acceptance gates: Every registered contract compiles and rebuilds as one set. IDs and references,
  typed measurements, multilingual text, verification targets, cursors and exchange keys agree
  across owners. The real SATCOM fixture remains lossless. Two rebuilds preserve deterministic
  model data and human decision provenance; no live fetch or runtime engine is required. Review
  the generated diff as one baseline. `make ci` and `make ci-local` pass.
  Existing snapshot-shaped SATCOM tables and new canonical tables have explicit ownership and
  non-colliding names/field IDs; original source fields are not silently reinterpreted.
- Documentation target: [Data contracts](current/data-contracts.md).

```

## Implementation and decisions

Status: open. The task has 16 open transitive prerequisites. The available registry contains only
`kn.system.governance`, `kn.space.satcom` and `kn.core.semantic` (50 tables, 465 fields).
This session prepares combined-registry fixture validation without accepting missing models,
removing prerequisites or adopting an incomplete baseline on the shared database.

- Added `make model-baseline` and `tests/integration/test_model_baseline.py`. It compiles/checks
  every registered contract and performs two normal Alembic rebuilds in a transaction that rolls
  back at teardown. Reviewed seeds, the real 168-row SATCOM mixture and the synthetic semantic
  fixture load together under their schema loader roles. Every table must contain representative
  data. All typed rows, original CSV cells, semantic values and complete markers are compared,
  and unchanged SATCOM reimport must be a no-op.
- Extracted the existing semantic fixture and native scalar decoding into
  `tests/integration/semantic_fixtures.py`, shared with the existing semantic round-trip test.
  The combined test includes multilingual labels, translation review references, explicit nulls,
  decimals, condition values and aware timestamps. These existing review references are not
  claimed as universal human verification metadata.
- Fixture-owner coverage is explicit. Registering a new contract fails the combined check until
  its owner adds fixture replay and independent expected-value assertions. Generic snapshots
  include every table and column, ordered by primary key.
- Deferred fixture references are checked with named schema-qualified constraints before another
  rebuild. This avoids pending trigger events in the rollback-only transaction and does not
  change unrelated callers' constraint timing.
- Fixed incomplete installed-marker verification. `verify_contracts()` previously checked only
  ID/version/digest, accepting a wrong storage schema or managed-table list. Two planted cases
  failed with `DID NOT RAISE` before the fix (five existing cases passed). Marker writing and
  verification now share one full-field definition. No contract or generated artifact changes
  are required.
- Updated the network-free governance mock for complete marker mappings and added schema/list
  corruption cases there too. The Make path regression now checks `model-baseline` with a
  `DATA_DIR` containing spaces.
- Evidence is stored beneath `$DATA_DIR/model-baseline/`, with per-run compiled artifacts, two
  typed JSON snapshots and JUnit results. The [current reference](../current/data-contracts/model-baseline.md)
  records the command, transaction boundary, fixture coverage and extension requirements.

## Acceptance evidence

Initial plan: 118 tasks, 105 agent, 13 human; MODEL=18, DELIVERY=100.

| Gate | Evidence and result |
| --- | --- |
| Existing registered set compiles together | `make model-baseline`: all three contracts compile and exact-byte recompilation checks pass |
| Two rebuilds preserve available model data | `make model-baseline`: passed, 1 test; `$DATA_DIR/model-baseline/check-9IUvhNfu/` contains identical JSON snapshots, 50 nonempty tables and 2,880 rows each |
| Real SATCOM fixture remains lossless | All 168 typed rows and every raw CSV cell equal the parsed fixture; stable snapshot ID and unchanged redelivery pass after both rebuilds |
| Reviewed seeds and semantic fixture round-trip | Every expected field equals stored native values, including decimals, timestamps, multilingual text and translation review references |
| All installed-marker fields agree | Before fix: two new corruption regressions failed, five existing refusal cases passed; after fix: all refusal cases pass in the 67-test local suite, with network-free coverage too |
| Generated baseline diff reviewed | No changes to `contracts/`, packaged contract resources, Alembic baseline or `generated/contracts/`; existing physical ownership and field IDs stay intact |
| Full model and shared database adoption | Open: missing prerequisite definitions, cross-owner assertions and durable identity/human-decision replay; no shared-data adoption or backfill performed |
| Required CI/local gates | `make ci-local` passed, including `make ci`: 825 unit tests and 67 local-only tests; all SKOS exports pass Apache Jena RIOT. See `$DATA_DIR/model-baseline/gates-fTVy8Aqz/ci-local-final.log` |

The initial `make ci` passed (824 tests, 64 deselected). An unprivileged `make db-up` and local-only
suite could not reach Docker/PostGIS from the sandbox. Repeating with local-service access started
no new container: the existing PostgreSQL container was already running and healthy. No volume was
reset, no source was fetched and no database rebuild was committed. The final `make ci-local`
passed with the needed local-service access. `make lint-md lint-spec-plan plan-status` passed
before that run, with no link or plan-integrity findings. A temporary complexity finding in the
shared fixture converter was fixed by separating scalar decoding;
`make format typecheck complexity-gate` passed.
The first final-gate attempt exposed the older partial-result unit mock (one failure, 823 passed)
before local tests; that mock was corrected and its focused suite passed. The final gate reruns
all checks successfully. The earlier failed attempt remains in `ci-local.log` beside the final log.
The final 14-file ASCII scan and `git diff --check` passed. The shared database is left in place;
the integration harness cleans up its scratch schemas and rolls back all-schema rebuild probes.
After the suite, `make db-verify` passed with schemas and roles verified.

## Handoff

The task remains open; its two direct prerequisites and all runtime consumers retain their
`Requires` entries. No capability changes to shipped and no task is removed. Plan counts remain
118 tasks (105 agent, 13 human); statuses BLOCKED BY HUMAN=3, CLEAR=96, HUMAN-GATED=10,
RUN NEEDED=9; stages MODEL=18, DELIVERY=100. Affected capability: `data-contracts`.

The next eligible model task is `human-verification-contracts`. Remaining prerequisite order,
computed from the real plan and saved as `readiness.json` beside the final gate log:

1. `human-verification-contracts`
2. `identity-registry-contracts`
3. `source-catalogue-import`
4. `evidence-claim-contracts`
5. `space-domain-contracts`
6. `crawler-config-schema`
7. `warc-raw-store`
8. `ingestion-state-contracts`
9. `gdelt-domain-contracts`
10. `vendor-information-coverage`
11. `supply-model-contracts`
12. `microelectronics-domain-contracts`
13. `interchange-contract`
14. `exchange-ledger-contracts`
15. `human-verification-projections`
16. `interchange-schema-evolution`

Extend combined fixture coverage as these models register. Accept the full baseline only after
all owning tasks, shared-model compatibility, durable decision provenance, canonical/SATCOM
ownership, recovery/backfill and the original CI/local gates have evidence. This partial check
does not waive any original acceptance gate.

## Revised scheduling

The [delivery-group review](0034-adhoc-delivery-group-audit.md) moves full-model acceptance to
the release path. The original work contract above records the earlier sequence. Full registry
and rebuild gates remain open. Each group exercises its registered subset as it grows.
