# Identity Registry Contracts

## Work contract

```markdown
#### identity-registry-contracts

Every later capability needs one durable KN ID per object before any claim refers to it.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [semantic meta-model](current/ontology-taxonomy.md) and
  [shared human verification protocol](current/evidence-model.md).
- User-visible outcome: The `identity` schema holds objects, identifiers with authority levels,
  identity attributes, source records with versions, links, match records, lifecycle events, and
  redirects. `kn db rebuild` replays the append-only identity event log in `$DATA_DIR/identity/`
  before any raw record, so every KN ID survives a rebuild.
- Scope boundary: Contracts with the `kn.identity` extension, including source record keys;
  constraints (no reused KN ID, one active link per source record, identifiers unique per
  namespace within their validity, links only to active objects); the event log format and its
  replay; UUIDv7 minting keyed by the anchoring record. Lifecycle commands, matching execution and change
  detection come in later tasks.
  Define source-record versions, change-set/per-field hash storage, matching-record features,
  scores/profile versions and lifecycle decision references now; later matching/tracking tasks
  execute those rules without redesigning the storage. Include the shared verification trait.
- Data and artifact paths: `contracts/core/identity/`, `src/kn/identity/`, `$DATA_DIR/identity/`,
  `tests/identity/`.
- Execution path: Write the contracts and the log schema, compile, and test replay against the
  integration database. Fixture logs cover every event type and every invalid transition.
- Acceptance gates: Replaying one log twice gives identical tables. Dropping the database and
  rebuilding keeps every KN ID. A reused ID, a link to a retired object, and a merge into a merged
  object are rejected. A merged ID resolves to its survivor. `make ci` passes.
- Documentation target: A new `current/object-identity.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Registered `kn.core.identity` adds ten identity tables and 71 stable fields to the editable
`1.0.0` baseline, bringing the deployment set to 61 tables and 544 fields. The contract declares
`kn.identity` on object/source keys and shared `kn.humanVerification` coverage on every table.
The wire schemas cover all eight lifecycle events plus identifier, attribute, version, match and
change-set recording. Structural match profiles are available for downstream model authors.
No dependency or release migration was added.

- Source-qualified anchors mint and persist random UUIDv7 IDs once. File locking serializes
  concurrent minting and preserves IDs after failed SQL transactions or complete database loss.
- The private, fsynced ASCII JSON Lines journal has versioned, hash-chained events. Replay rejects
  malformed/torn history, changed digests, sequence gaps and invalid transitions before appending.
  SQL application uses READ COMMITTED, an advisory lock, savepoints and validated event prefixes.
- The replay validator enforces no reused IDs/anchors, nonoverlapping namespace validity, active
  object targets, same-class active merges, complete split ownership, retired-only restoration,
  reclassification successors and explicit lifecycle decision references. Stored match features,
  versions, field hashes and change sets define later writers' storage without running them now.
- A bounded `kn.index.whereNull` extension compiles the unique active-source-link index through
  SQLAlchemy. It rejects unknown/nonnullable predicate fields. PostgreSQL metadata retains the
  predicate, and compiled-catalog verification rejects a missing or changed predicate. The local
  extension schema pin was refreshed; the vendored ODCS schema was unchanged.
- Rebuild takes the identity lock before schema removal, replays the journal before reviewed
  seeds and subsequent raw imports, and rolls back the entire group if replay fails. Combined
  model fixtures now include every identity table and compare full snapshots across rebuilds.
- Regression fixtures exposed UTC `+00:00` versus canonical `Z` digest mismatch, pending deferred
  foreign-key events before an in-transaction drop, Pydantic copies bypassing append validation,
  and recursion failure on a 1,100-node redirect chain. The fixes normalize before hashing, check
  deferred references before returning, revalidate at append and resolve iteratively.
- Bilingual contract-list goldens include the new registered contract. Operator lifecycle and
  review workflows, scored matching, change detection, lineage commands and calibration remain
  their existing tasks. Human decision references do not fabricate verification stamps.

## Acceptance evidence

Status: accepted. All declared gates passed. Initial `make plan-status`: 117 tasks,
104 agent, 13 human; CLEAR=95, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10;
MODEL=17, DELIVERY=100.

- `make contract-compile`: passed; 38 identity artifacts generated and reviewed.
- `make format typecheck complexity-gate lint-md lint-spec-plan`: passed. New Python modules stay
  below the approximate 250-line guideline. Production storage remains typed and uses the normal
  SQLAlchemy/Alembic entry points.
- `.venv/bin/python -m pytest tests/identity -q`: 42 passed after the fixes. The active-index,
  copied-event and long-chain regressions each failed before their fix.
- PostgreSQL acceptance uses a disposable database, leaving the pre-existing shared development
  database intact. The retained runner creates the test database, applies the normal baseline,
  invokes pytest and drops only that database in a `finally` block. Tests also roll back probes
  and clean their own committed database-drop/concurrency fixtures. The local Compose service
  was already running. Initial `make db-up` correctly refused the old installed-contract set;
  no destructive shared-database rebuild was performed. Docker/loopback access needed sandbox
  escalation.
- Reproduction command (after sourcing `scripts/shared/common.sh`, `kn_load_env` and
  `kn_db_test_env`): `.venv/bin/python
  "$DATA_DIR/identity/contracts-20261123/run_acceptance.py" tests/integration`.
  Full integration result: 89 passed, zero skipped, with JUnit and full-model snapshots under
  `$DATA_DIR/identity/acceptance-9901e4a1/`. Earlier focused acceptance passed six replay/baseline
  checks under `acceptance-692a8ecf/` and three committed recovery/concurrency checks under
  `acceptance-850bb0d4/`.
- The final focused run covers replay twice, complete database drop/recreation through the CLI
  in both locales, rejected invalid transitions, SQL/journal disagreement, caught SQL failure,
  concurrent SQL minting, malformed-log rebuild rollback, partial-index enforcement/drift and
  combined-model replay: 11 passed, zero skipped, after the append/redirect fixes. JUnit and
  snapshots are retained under `$DATA_DIR/identity/acceptance-237eb10e/`.
- Initial `make ci`: 908 passed and two missing bilingual contract-list goldens, since fixed.
- Final `make ci`: passed, 924 unit tests and 89 service tests intentionally deselected; those
  service tests passed separately as recorded above. The final log is
  `$DATA_DIR/identity/contracts-20261123/ci-final-reviewed.log`. No declared acceptance gate was
  skipped. `make quality` and the unchanged Jena SKOS check were not required or run for this task.
- Final `make lint-md lint-spec-plan`, `make plan-status`, ASCII checks and `git diff --check`
  passed. Disposable databases were removed; the pre-existing database service remains running.

## Handoff

The accepted-task transition removes `identity-registry-contracts` and its downstream Requires
references. Final plan counts: 116 total, 103 agent, 13 human; CLEAR=94, RUN NEEDED=9,
BLOCKED BY HUMAN=3, HUMAN-GATED=10; MODEL=16, DELIVERY=100. Baseline model prerequisites shrink
from 15 to 14. Next required agent priority is `warc-raw-store`.

`object-identity` remains planned: registry contracts/replay are available, while lifecycle
commands and trusted review integration, matching, partial-update execution, lineage and
calibration remain open. Its registry row links the new current-state page. The lifecycle task
now explicitly reuses registry validators and the shared review protocol; the matching task links
the early profile schema. `data-contracts` gains identity fixture coverage without accepting the
remaining integrated model checkpoint. Known trust and whole-log replay boundaries are documented
on the current-state page. No commit or push was made.
