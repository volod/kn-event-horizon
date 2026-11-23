# Human Verification Contracts

## Work contract

```markdown
#### human-verification-contracts

Application data has no common optional timestamp proving that a human checked its exact content.
Existing verification labels cannot identify the reviewer, scope, version or review time.

- Serves: `evidence-model` -- [Human verification metadata](../design/spec.md#human-verification-metadata)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [model review](records/0028-adhoc-human-verification-model-review.md),
  [shared design](../design/human-verification.md), current contract registry and stable field IDs.
- User-visible outcome: One typed verification decision/history contract can attach optional
  `human_verified_at`, reviewer and decision provenance to record or field targets without
  requiring every datum to be reviewed. Existing data remains unverified by default.
- Scope boundary: Shared target/key/version and purpose encoding, UTC/null rules, authenticated
  actor boundary, append-only accept/reject/revoke/supersede events, idempotent application and
  durable decision-log protocol. Define `kn.humanVerification` coverage metadata and resolver
  interfaces for existing and future datasets. Reuse this protocol in the future review CLI;
  queue screens, assignment and notifications are outside this task.
  Define the common trait before new identity/domain contracts are authored. Validate trusted
  reviewer context with fixtures; live operator authentication belongs to the later workflow.
- Data and artifact paths: `contracts/core/evidence/`, `src/kn/review/`,
  `src/kn/contracts/resources/`, `tests/review/`, `$DATA_DIR/decisions/`.
- Execution path: Write failing fixtures for typed composite targets, field scope, version
  changes, human and automated actors, partial metadata and timestamp errors. Compile the
  contracts, register the durable log, and test transactional application in PostgreSQL.
- Acceptance gates: Timestamp/reviewer/decision metadata is all null or all present for a valid
  human acceptance. Source `verified` text, an agent or import cannot set it. A row review and
  field review remain distinct; an unknown target/field or incomplete key is refused. Duplicate
  and concurrent decisions are deterministic; rejection/revocation retains history without an
  active acceptance stamp. Conflicting concurrent outcomes remain visible with no active stamp
  until explicitly resolved. Offset times normalize to UTC; naive, invalid and future times fail.
  The same decision replays identically without fabricated dates or actors. `make ci` passes;
  service tests pass through `make ci-local`.
- Documentation target: A new `current/evidence-model.md` page listed in the
  [areas index](current.md#areas).

```

## Implementation and decisions

The shared protocol lives in `src/kn/review/`; its versioned wire schemas live under
`contracts/core/evidence/`. Registered ODCS contract `kn.core.human_verification` adds one decision
table in `evidence`, compiled through the existing registry and editable `1.0.0` baseline. The
registry now has 51 tables and 473 fields. No dependency or release migration was introduced.

- Typed complete keys preserve leading zeroes, composite keys, locale and native scalar types.
  Record/field scope, exact content digest and explicit purpose stay in target identity.
- Only trusted authenticated human reviewer contexts can create decisions. Requests cannot supply
  their actor, recording time or verification stamp. UTC normalization, controlled clocks,
  all-null/all-present stamps and immutable event digests apply on creation and replay.
- Added validated `kn.humanVerification` declarations and explicit coverage/resolver interfaces.
  The contract resolver locks and checks exact row content, refusing unknown, incomplete,
  mistyped and stale targets. Missing coverage grants nothing. This task defines the trait;
  all-dataset coverage remains the later projection task.
- The operator-owned journal uses private files, exclusive file locks and file/directory fsync
  under `$DATA_DIR/decisions/`. PostgreSQL application uses a caller-owned READ COMMITTED
  transaction, an advisory lock and savepoint. The write-ahead file can retain a pending event
  after SQL rollback; exact-target replay recovers it without new dates, actors or IDs.
- Causal event heads determine active acceptance. Concurrent branches expose a conflict, with
  no time-based winner. Explicit supersession resolves heads; revocation retains all history.
  Principal/request-ID retries append once and reject changed payloads.
- Added a composite-key label review to the combined registered-model fixture checkpoint. Its
  two rebuilds compare original decision content, times, reviewers, IDs and full contract markers.
  Scratch-schema and rebuild tests clean up or roll back, preserving the shared database.
- Regression tests first exposed ordinary acceptance resolving multiple conflict branches and
  signed decimal zero producing two key identities. Both were corrected. The complete unit run
  also found bilingual contract-list goldens missing the newly registered contract; both locales
  now retain their existing messages and include its expected line.

## Acceptance evidence

Status: accepted. All declared gates passed. Initial `make plan-status`: 118 tasks, 105 agent,
13 human; CLEAR=96, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10; MODEL=18, DELIVERY=100.

- Initial failing fixtures: `.venv/bin/python -m pytest tests/review/test_protocol.py -q` failed
  collection because `kn.review` did not exist. Later conflict/zero regressions each failed
  before their fixes. `tests/review/` now checks scope/purpose, UTC/null metadata, typed keys,
  authority, schema drift, unknown fields, history, corruption, symlinks and retry identity.
- `make contract-compile`: passed; registered generated artifacts reviewed, with no source
  archive, CSV or legacy verification-label changes.
- `make format typecheck complexity-gate`: passed. Cohesive review modules and test support stay
  below the approximate 250-line guideline. No production SQL strings or fabricated timestamps.
- `source scripts/shared/common.sh && kn_load_env && kn_db_test_env &&
  .venv/bin/python -m pytest tests/integration/test_human_verification.py -q`: 12 passed,
  including real PostgreSQL concurrency, caught partial-application failure, rollback/replay,
  unknown/stale targets and refused automated actors.
- `make model-baseline`: passed, one two-rebuild checkpoint. Retained artifacts are under
  `$DATA_DIR/model-baseline/check-jziAb0EL/`, including compiled contracts, the durable fixture
  journal and two identical typed snapshots. Run output and matching snapshot/journal digests are
  retained as `model-baseline.log` and
  `rebuild-evidence.json` under `$DATA_DIR/human-verification/contracts-20261123/`.
- The initial `make ci` and nested `make ci-local` unit gates reported 880 passed and two failing
  bilingual contract-list goldens, since corrected.
- Final `make ci-local`: passed, including `make ci` (882 unit tests passed; 79 local tests
  deselected), all 79 local service tests (882 unit tests deselected), and Apache Jena RIOT
  validation of every SKOS export. No required gate was skipped. Full output is retained in
  `$DATA_DIR/human-verification/contracts-20261123/ci-local-final.log`; the Jena summary is
  `$DATA_DIR/skos-reference/8c9e18b1bbc145fb94a03cf41f993848/summary.json`.
- `make lint-md lint-spec-plan`, `make plan-status` and `git diff --check`: passed on the final
  documentation and plan transition. The shared database was already running; sandbox access
  required escalation for
  Docker/loopback. Normal startup correctly refused digest drift from the edited development
  baseline. No destructive shared-database rebuild was performed; tests use rolled-back or
  scratch-schema transactions.

## Handoff

The accepted-task transition removes `human-verification-contracts` and its downstream Requires
references. Final plan counts: 117 total, 104 agent, 13 human; CLEAR=95, RUN NEEDED=9,
BLOCKED BY HUMAN=3, HUMAN-GATED=10; MODEL=17, DELIVERY=100. Baseline prerequisites shrink from
16 to 15. Next required agent priority is `identity-registry-contracts`.

`evidence-model` remains planned because claims, selection and all-dataset projections are still
open; its registry row now links the available shared protocol. `human-verification-projections`
owns universal coverage, current read metadata, restore/identity invalidation, pending/stale/orphan
reports, all-target rebuild integration, rights filtering and exchange trust/loss behavior.
Future `review-queue-cli` owns live operator authentication and the review workflow. Data-contract
fixture validation now includes the shared log without accepting the remaining integrated-model
checkpoint. All pre-existing working-tree changes are preserved; no commit or push was made.
