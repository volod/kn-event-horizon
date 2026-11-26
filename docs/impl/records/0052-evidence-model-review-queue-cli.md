# Review Queue CLI

## Work contract

```markdown
#### review-queue-cli

Human decisions on conflicts and candidates need a workflow that survives rebuilds.

- Serves: `evidence-model` -- [Evidence model](../design/spec.md#evidence-model)
- Agent status: CLEAR
- Dependencies: The durable [identity review match rows](current/object-identity.md#match-resolution)
  and [shared verification projections and replay](current/evidence-model.md#current-verification-reads).
- User-visible outcome: `kn review list` and `kn review decide` handle fact
  conflicts, identity match candidates, and identity drift. Decisions are appended to
  `$DATA_DIR/decisions/<domain>/` and applied to review items.
- Scope boundary: The CLI, the decision log format, and re-attachment by deterministic keys with an
  orphan report. Item types are registered, so later capabilities such as exchange conflicts reuse
  the queue. Rebuild-time replay comes in `rebuild-from-raw`.
  Record/field verification items reuse the shared log and target/version protocol. Resolve the
  authorized human reviewer at the operator boundary, show the reviewed scope/version, and expose
  acceptance, rejection and revocation without accepting actor identity from source data.
  Derive the selector's [accepted reviews](current/evidence-model.md#canonical-selection) from
  applied decisions, and report each source's dispute rate to support rank overrides.
- Data and artifact paths: `src/kn/review/`, `src/kn/cli.py`, `$DATA_DIR/decisions/`,
  `tests/review/`.
- Execution path: Write an append-only JSON Lines log with the reviewer, reason, and time.
- Acceptance gates: Decisions apply idempotently. A decision whose claim key disappears is
  reported as orphaned. Verification timestamps appear only for accepted human decisions on the
  matching scope/version; rejecting or revoking clears the active stamp and keeps history.
  `kn review list --overrides` lists the flagged owner overrides. An accepted identity match links
  the record and records its authoritative keys and identity attributes, as an automatic link
  does. Golden outputs cover English text and stable JSON.
- Documentation target: `current/evidence-model.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The prerequisites were available: durable match events/SQL rows and the shared human verification
protocol, authenticated submission and exact-target read projections. The working tree was clean.
No external data or human decisions were required for fixture acceptance.

- Added `kn review list|decide|replay`, typed record/field query preparation, English and stable JSON
  output, full owner-override listing and per-source dispute rates.
- Kept the shared v1 decision format; its optional queue choice binds the registered item kind,
  deterministic key, candidate set and selection. Old events omit this member and retain hashes.
  Updated the published request/decision and identity event schemas. No dependency or storage
  contract change was needed.
- New CLI decisions use private, fsynced domain journals. Explicit reattachment preserves decisions
  across two fixture rebuilds, including orphan reports before their targets are restored.
- Extracted the existing identity CLI's local authorization into a shared boundary. Both commands
  require the actual OS account, private storage and controlling-terminal approval. The prompt
  displays escaped values and exact scope/version; source payloads cannot supply an actor.
- Applied fact decisions feed the selector through historical `Reviews` snapshots. Revocation
  clears current acceptance and retains its earlier effect. Generic record/field verification
  uses exact registered targets independently of queue workflow acceptance.
- Accepted identity choices reuse automatic observation registration for links, authoritative keys
  and normalized attributes. New review matches persist the original observation/profile. Identity
  drift opens review; conflicting authoritative ownership is refused before durable acceptance.
- Recovery uses append-before-apply ordering, reproducible identity batches and a replay savepoint.
  Explicit replay is in scope; automatic replay after raw restoration remains `rebuild-from-raw`.
- Current domain policies remain with their domain contracts. None is registered yet. The CLI
  refreshes fields with declared policies; a fixture policy proves acceptance and revocation update
  canonical history idempotently. The queue never invents a default policy.

### Findings fixed during implementation

| ID | Severity | Evidence and affected consumer | Disposition |
| --- | --- | --- | --- |
| RQC-01 | major | `test_existing_record_identity_attribute_drift_opens_review` initially returned `link` for a changed discriminating attribute. Source identity ownership could change silently. | Fixed by a comparator-based drift guard and preserved observation/profile context. Existing as-of matching fixtures now state an explicitly accepted reading. |
| RQC-02 | major | `test_domain_journal_syncs_the_decisions_directory_entry` initially omitted the DATA_DIR sync when creating a domain log. A crash could lose its new `decisions/` entry. | Fixed by syncing the data directory as well as the file and nested directories. |
| RQC-03 | major | `test_accepting_a_candidate_cannot_ignore_an_authoritative_key_owned_elsewhere` initially accepted an object while silently skipping its conflicting key. | Fixed by validating authoritative owner, issuer and validity before constructing effects. |
| RQC-04 | major | `test_caught_replay_failure_rolls_back_the_entire_sql_batch` initially retained one review row after a caught second-event failure. | Fixed by a savepoint around the complete reattachment batch; durable history remains retryable. |
| RQC-05 | major | `test_pending_identity_choice_cannot_replace_a_newer_observation` initially allowed a pending old choice to rebind a record after a newer match. | Fixed by refusing stale observations before application and reporting them during replay. |

## Acceptance evidence

Status: accepted. All task acceptance gates passed.

- Initial `make plan-status`: 112 tasks, 100 agent, 12 human.
- `make bootstrap` created the missing locked Python environment. `make db-up` started the local
  test database; database commands required sandbox escalation for loopback/Docker access.
- Focused unit tests passed for queue graphs, revocation snapshots, request/path safety, exact
  claim reconstruction, local authentication, matching and English/JSON golden output.
- PostgreSQL fixtures cover accepted/rejected/revoked choices, idempotency, missing claims,
  field/record stamp isolation, cross-domain request refusal, rollback recovery, two rebuilds,
  identity links/keys/attributes, real CLI terminal approval and settled owner-override flags.
- Final PostgreSQL acceptance: 23 passed, zero failures/errors/skips. JUnit and fixture artifacts
  are retained at `$DATA_DIR/review-queue/check-wLtFc8UK/`.
- `make lint-md`, `make lint-spec-plan` and `git diff --check` passed.
- The first complete unit run exposed two outdated root-help golden expectations after adding the
  command. They were updated and their focused CLI tests passed.
- Final `make ci`: 1,427 passed, 140 local/service/heavy tests deselected by the standard unit
  selection, no failures. Contract, catalog, formatting, Ruff, mypy, complexity, shell, fixture,
  documentation and spec-plan checks all passed. The 23 affected database acceptance tests ran
  separately, with no skips. The unrelated full `ci-local` and optional `quality` suites were not
  task acceptance gates and were not run.

### Reproduce the database acceptance checks

```bash
source scripts/shared/common.sh && kn_load_env && kn_db_test_env
mkdir -p "$DATA_DIR/review-queue"
review_artifacts=$(mktemp -d "$DATA_DIR/review-queue/check-XXXXXXXX")
.venv/bin/python -m pytest \
  tests/integration/test_review_queue.py \
  tests/integration/test_review_recovery.py \
  tests/integration/test_review_operator.py \
  tests/integration/test_review_refresh.py \
  tests/integration/test_identity_review_recovery.py \
  tests/integration/test_identity_resolution.py \
  tests/integration/test_identity_lifecycle.py \
  tests/integration/test_evidence_verification.py \
  tests/integration/test_review_projections.py \
  --basetemp "$review_artifacts/fixtures" --junitxml "$review_artifacts/results.xml" -q
```

The rebuild fixture flushes deferred evidence constraints before each repeated rebuild, emulating
committed inputs while retaining the harness's final rollback. Database fixtures and JSONL logs
remain under the run's `fixtures/` directory. No real review decisions were submitted.
The installed `kn review list --json` also passed against the empty local database and returned
empty `items`, `dispute_rates` and `orphans`. The database started for these checks was stopped
with `make db-down`; data and evidence were retained.

## Handoff

Removed `review-queue-cli` from the forward plan and its audit prerequisite. The evidence-model
implementation audit is now the next required ready task. Before/after counts: 112 -> 111 total,
100 -> 99 agent, 12 -> 12 human. The affected capabilities are evidence selection/verification
and object identity review. The evidence-model registry stays `planned` until its separate closing
audit; this task does not claim that audit. Available interfaces, verification methods and the
legacy/profile, policy, internal-audience and identity-operation limits are documented in
[current evidence state](../current/evidence-model.md#operator-review-queue).
