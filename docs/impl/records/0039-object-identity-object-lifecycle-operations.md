# 0039 Object lifecycle operations

## Work contract

```markdown
#### object-lifecycle-operations

Merges, splits, and retirements must be explicit, reviewed, and kept as reversible history.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: The [registry replay APIs](current/object-identity.md#replay-and-integrity) and
  [shared trusted review protocol](current/evidence-model.md#trusted-decision-application).
- User-visible outcome: `kn identity show|resolve|history|merge|split|retire|restore` work in `en`
  and `uk`. Each state change writes a review decision and the identity event that cites it. It
  moves links, so claims follow their source records, and old IDs stay resolvable.
- Scope boundary: The lifecycle state machine from the specification; merge and split semantics,
  with each link assigned to exactly one successor; reclassification as retirement plus a successor
  mint; forced merges on a shared authoritative identifier; redirect collapse. Review queue items
  for match candidates come in `review-queue-cli`.
- Data and artifact paths: `src/kn/identity/lifecycle.py`, `src/kn/cli.py`, `$DATA_DIR/decisions/`,
  `tests/identity/`.
- Execution path: Extend the registry replay validators with fixture-first operation and review
  tests, then implement the lifecycle workflow and CLI with localized messages.
- Acceptance gates: A merge followed by a split restores links deterministically with full history.
  A cross-class merge is refused. A redirect chain resolves in one step. A lookup by a split ID
  returns its successors. Golden outputs exist in both locales.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The registry replay and shared review protocol prerequisites were available. The CLI now reads
the durable identity journal for show, resolve and history and uses the shared review writer for
merge, split, retire, restore and reclassification. Current link IDs and record keys survive
ownership moves. Replay maintains terminal redirects for one lookup and retains direct successors
for history.

The local Unix journal owner approves the version-bound proposal at a controlling terminal.
The reviewed mutation cites the accepted decision after a durable append. Rebuild checks those
references and restores their SQL rows. Reclassifying mints a UUIDv7 with a fresh source anchor.
Trusted ingestion can supply the opposing object's authoritative observation in a merge event.
This keeps the existing identifier interval unique and preserves the v1 hash of earlier events.

| Finding | Severity | Evidence and disposition |
| --- | --- | --- |
| LIFECYCLE-01 | Major | Interrupting after the decision append could leave approval without an identity event. Fixed in the lifecycle writer. The decision binds the exact prior head, retries preserve the receipt and a stale head refuses. Covered by `test_decision_only_interruption_and_retry` and `test_pending_approval_does_not_apply_against_changed_snapshot`. |
| LIFECYCLE-02 | Minor | Resolver previously walked redirect chains at lookup time. Fixed in registry replay with a flattened map, including split successors. Covered by the long-chain fixture and the merge/split CLI integration fixture. |

## Acceptance evidence

Status: accepted. `make ci` passed with 1,104 tests and 98 local-only tests deselected.

The focused PostgreSQL regression run passed 42 tests, covering repeat rebuilds, cross-class
refusal, localized CLI writes, preserved link and review identities,
reclassification, stale reviews and both write interruption points. It used the following command
after `source scripts/shared/common.sh && kn_load_env && kn_db_test_env`.

```bash
artifact_dir="$DATA_DIR/identity/lifecycle-lMsiSao8"
.venv/bin/python -m pytest tests/integration/test_identity*.py \
  tests/integration/test_human_verification.py tests/integration/test_rebuild*.py \
  tests/integration/test_model_baseline.py --junitxml "$artifact_dir/results.xml"
```

`make test-bilingual` passed 100 tests. Evidence is in
`$DATA_DIR/e2e/bilingual-lXGXnswP/manifest.json`, with English and Ukrainian lookup and CLI help
outputs. `make lint-md` and `git diff --check` passed.

The existing default database failed `make db-up` during verification due to contract digest
drift. The test service was healthy and the acceptance fixtures used their governed scratch
databases and rollback transactions. The service was stopped after the run. This task ran the
focused PostgreSQL suites. The remaining local-only and release gates are outside its acceptance
scope.

## Handoff

The plan went from 121 to 120 tasks, with 108 to 107 agent tasks and 13 human tasks. The
object identity capability now has reviewed lifecycle operations. `identity-match-engine` is
the next agent task, and `identity-resolution-implementation-audit` uses this acceptance record
with the future matching record. The capability remains planned until its other evaluation
gates are met.
