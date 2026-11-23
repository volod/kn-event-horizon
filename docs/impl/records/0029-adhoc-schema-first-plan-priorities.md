# Schema-First Plan Priorities

## Work contract

Review every open implementation task for schema/model changes and prioritize those changes early,
respecting real dependencies, so later development needs fewer breaking changes. Preserve the
human-verification design and other in-progress documentation from record 0028. This task updates
planning and its scheduler; it does not implement domain schemas or mutate the database.

## Implementation and decisions

Reviewed the complete 113-task starting inventory, including schema changes hidden inside runtime
tasks. All original task IDs remain open; no implementation acceptance is claimed by this review.

### Findings and disposition

| Finding | Impact | Disposition |
| --- | --- | --- |
| Registry order schedules identity workflows before later shared/domain models | Consumers accumulate before the full model is available | Introduce checked MODEL/DELIVERY scheduling; move the shared verification contract first |
| Supply contracts require the scored matcher; GDELT and microelectronics contracts require full raw replay | Runtime implementations delay shapes they can validate with fixtures | Replace these dependencies with identity/evidence/supply/run-state providers; retain live/replay checks on runtime tasks |
| Ingestion state and exchange bindings first appear inside engine/synchronization work | Late runs, checkpoints, plans and receipts introduce further core storage changes | Split `ingestion-state-contracts` and `exchange-ledger-contracts` ahead of their runtime consumers |
| Interchange schema and runtime packaging share one task | Canonical selection and change tracking delay the compatibility boundary | Keep record/manifest/evolution checks in MODEL; add `interchange-package-export` for the original runtime acceptance |
| Later matching, update, review and selection tasks implicitly own more storage | A contract-only pass could miss known future tables and profile formats | Expand identity/evidence owners to cover known change sets, hashes, match profiles, decision and selection history now |
| Supply and microelectronics share units, attributes and condition-bound observations | Independent implementations could introduce competing base types | Assign shared definitions to supply; microelectronics extends them |
| Existing SATCOM snapshot projections and new canonical space tables may share names | A future model could silently change source-table meaning or collide | Require explicit table/field-ID ownership and adapter/backfill mappings before accepting space contracts |
| Per-task compilation does not prove cross-model compatibility | Each individual model can pass while the combined baseline fails | Add `development-model-baseline`, followed by an optional implementation audit |

### Scheduling and dependency rules

- `Execution stage: MODEL` is explicit; existing unmarked tasks default to DELIVERY. Required work
  precedes optional work; eligible MODEL work precedes DELIVERY; registry/document order breaks
  ties. Open `Requires` are filtered before selection. Status and external/manual checks still
  apply before starting; a stage never grants permission or completes a prerequisite.
- Reject invalid stages and MODEL tasks requiring open DELIVERY tasks. Split mixed work instead
  of hiding a runtime prerequisite in prose. Regression fixtures exercise priority across groups,
  required versus optional work, malformed stages, and human-lane prerequisites.
- The model chain fixes verification, identity/source/archive, evidence/supply/configuration/run
  state, interchange/ledger/domain models, registry-wide verification projections, then the
  integrated baseline. The actual dry selection order is retained in `schedule.json`.
- Gate the first lifecycle, canonical selection, ingestion and exchange writers on the baseline,
  directly or transitively. Later runtime tasks consume these shapes rather than inventing them.
  Move the removed GDELT/microelectronics raw-replay prerequisite to their first dictionary and
  benchmark loader tasks, so early contract acceptance cannot bypass engine readiness.
- The human vocabulary URI decision is MODEL but stays human-gated. It is not a fabricated
  prerequisite for internal typed keys. Optional audits do not block required model acceptance.

### Later schema work reviewed

| Remaining task family | Reason to retain DELIVERY |
| --- | --- |
| Analytics marts, dashboard and analyst read models | Additive derived views over the early contracts |
| Source dictionaries, mappings and domain source adapters | Source-specific data/profiles and additive source tables; preserve common keys and traits |
| InvenTree schema registry and adapter profiles | External snapshots/configuration over the early interchange/evolution/ledger boundary |
| Optional GDELT native streams | Explicit additive native tables, with no reinterpretation of core claims |
| Obsidian, AI extraction and workflow profiles | Adapters/artifacts over established provenance and review interfaces |
| Service setup, orchestration, proxy and host operations | Service-owned configuration/storage outside the canonical model |
| Release migration mode | Release freeze and migration discipline after owner approval |

The [schema-first guide](../../guide/schema-first-development.md) records model ownership, waves,
late-change boundaries and adoption. Individual model tasks use isolated or transaction-scoped
fixtures. The integrated checkpoint explicitly adopts the combined development baseline with
recovery/backfill evidence. This reduces repeated rollouts without promising a permanent schema
freeze. Unexpected changes to core keys, meaning or review scope still require explicit work.

Updated the specification, forward plan, current data-contracts page, planning/development guides
and navigation. The data-contracts registry status is planned for the new combined acceptance;
its existing compiler and guarded rebuild remain available. Record 0028 and its design remain
preserved. No domain schema or database mutation is part of this planning review.

## Acceptance evidence

Status: accepted as a planning and scheduling change. Initial plan: 113 tasks, 100 agent, 13 human;
CLEAR=91, RUN NEEDED=9,
BLOCKED BY HUMAN=3, HUMAN-GATED=10. Initial agent priority: `identity-registry-contracts`.
Before-task inventory is retained under
`$DATA_DIR/plan-review/schema-priority-20261123T085823Z/before.json`.

- New scheduling regressions initially failed on the previous scheduler/validator: seven failed,
  two passed. After implementation, the focused stage/summary/integrity run passed 34 tests.
- `make format typecheck complexity-gate`: passed. No new dependency was added.
- `make lint-md lint-spec-plan plan-status`: passed, with zero broken links or integrity findings.
- `verify_schedule.py` exercised the real scheduler against an in-memory copy, removing each
  simulated accepted prerequisite. All 113 original IDs remain, all 17 agent MODEL tasks precede
  DELIVERY, `human-verification-contracts` is first, `development-model-baseline` is last, and
  `object-lifecycle-operations` is the first DELIVERY candidate. This does not execute tasks,
  approve human decisions, or waive their external prerequisites. `after.json` and `schedule.json`
  retain the full inventory, model order, new IDs and removed-dependency audit beside the script.
- `dependency-checks.json` confirms the baseline transitively requires every other agent MODEL
  task, all eight checked first runtime writers/loaders require that baseline, and the first
  GDELT/microelectronics loaders retain explicit raw-replay prerequisites.
- `make ci`: passed; 824 tests passed, 64 service/heavy tests deselected. Catalogs, generated
  contracts, formatting, lint, typing, complexity, shell, links and spec/plan integrity passed.
  Output is retained as `ci.log` in the same evidence directory. `make ci-local` was not run:
  this change affects planning tools and documentation, without model or database behavior changes.
- Final Markdown/link/spec-plan checks, dry scheduling, `git diff --check` and an ASCII scan passed.
  The 113 original task IDs remain; no task or human gate was accepted by the dry run.
- Revised plan: 118 tasks, 105 agent, 13 human; CLEAR=96, RUN NEEDED=9,
  BLOCKED BY HUMAN=3, HUMAN-GATED=10. Stages: MODEL=18 (17 agent, one human), DELIVERY=100.
  Agent priority: `human-verification-contracts`; human priority: `decide-vocabulary-uri-namespace`.

## Handoff

The five added IDs are `ingestion-state-contracts`, `exchange-ledger-contracts`,
`interchange-package-export`, `development-model-baseline` and
`model-baseline-implementation-audit` (optional). The splits retain the previous runtime promises;
the checkpoint adds combined acceptance. No prior task is removed or marked implemented.

Affected capabilities: documentation integrity, data contracts, evidence, identity, raw archive,
supply, source management, ingestion, interchange, and the space/GDELT/microelectronics models.
Implementation remains open in the plan. Start with `human-verification-contracts` after checking
its work contract and opening its own numbered record. No acceptance gate remains for this review;
the model implementations and integrated database acceptance remain open plan work.
