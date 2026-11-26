# Human Verification Projections

## Work contract

```markdown
#### human-verification-projections

All existing datasets and later domains need the same queryable human verification metadata;
adding a column to one domain would leave labels, links and other facts uncovered.

- Serves: `evidence-model` -- [Human verification metadata](../design/spec.md#human-verification-metadata)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [50-table coverage inventory](records/0028-adhoc-human-verification-model-review.md)
  and [design](../design/human-verification.md), reviewed semantic snapshots and SATCOM fixtures.
- User-visible outcome: Every current record and addressable field has optional human verification
  metadata through its KN read projection, including semantic labels/mappings and snapshot-qualified
  SATCOM data. Unchecked or changed content exposes null; prior human decisions remain available.
- Scope boundary: Coverage declarations for all current tables, shared projections and target
  resolvers, content-version invalidation, durable replay and pending/orphan reports, rights
  filtering, and registration checks for future contracts. Keep source CSV headers, archive bytes
  and imported verification labels unchanged. Do not auto-approve existing data or add a workflow UI.
  Apply coverage to the current registry. Require every subsequent domain and exchange contract
  to supply coverage and replay fixtures at registration. Fixture replay is sufficient;
  a running engine, review CLI or live source is not a prerequisite.
- Data and artifact paths: `src/kn/review/`, `src/kn/semantic/`, `src/kn/domains/space/satcom/`,
  `src/kn/db/`, `src/kn/contracts/resources/`, `tests/review/`, `tests/integration/`,
  `$DATA_DIR/decisions/` and `$DATA_DIR/human-verification/<run-id>/`.
- Execution path: Enumerate the deployed registry, apply the common metadata to each projection,
  and review fixture rows and individual fields. Rebuild twice from seed/source fixtures and the
  durable log, then re-import unchanged and edited data. Exercise a missing target and denied read.
- Acceptance gates: All registered tables, including the 50-table review baseline, have coverage;
  registration without a declared strategy is refused. Each unreviewed row/value returns null.
  A label/locale, unit/condition, value or
  target-version change never inherits an unrelated stamp; a field review never approves the row.
  Unchanged re-delivery preserves matching approval. Two rebuilds preserve exact times, actors
  and decision IDs; unresolved targets remain pending or reported rather than silently verified.
  All SATCOM raw cells and files remain exact, legacy verification states create no human dates,
  and restricted reviewers/evidence do not leak. `make ci` and `make ci-local` pass.
- Documentation target: `current/evidence-model.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

All 73 registered tables, including all 50 tables in the original review, declare a verification
strategy and a field context for all 707 stable fields. Registration rejects missing declarations
or field contexts. The combined model checkpoint requires representative data from every owner
and table. The pinned extension and generated artifacts reflect the declarations.

- `kn.review.projection.read` returns current typed values and separate nullable row and field
  stamps. The audience policy gates the row, the declared review context, and the reviewer and
  evidence of the exact-target decision history. The shared decision-log projection also checks
  rights to its own event payload.
- The contract uses the declared record as a conservative default field context. Snapshot IDs,
  label locales, measurement units and conditions, and relevant evidence remain bound to the
  target. The field scope still identifies only the reviewed field. Transport fields excluded
  from an existing record digest remain individually addressable.
- The durable journal remains authoritative. Rebuild restores matching decisions after identity
  and reviewed seeds, and SATCOM import reapplies reviews for restored snapshots. Pending, orphan,
  stale and incompatible targets stay in the journal. Normal commands publish private replay
  reports after commit. The fixture tests exercise replay again after loading deferred inputs.

| Finding | Severity | Evidence and consumer | Owner and disposition |
| --- | --- | --- | --- |
| HVP-01 | major | A retire/restore cycle restored the original active object row and falsely resurfaced its earlier factual stamp. `test_restoring_an_identity_starts_a_new_verification_revision` reproduced it. | Identity and review. Fixed with a durable lifecycle-derived `objects.revision_event` in the editable baseline. |
| HVP-02 | minor | A review of a decision-log row depends on the original event's SQL row, whose target may arrive during the replay pass. | Review. Fixed by processing audit targets after ordinary input and retrying unresolved audit dependencies while progress is possible. The combined fixture checks a SATCOM decision's audit review. |
| HVP-03 | minor | Unconditional replay-directory resolution made upgrade and verify depend on the working directory. The dispatch regression observed three lookups for one rebuild. | Database CLI. Fixed by resolving the report directory only for rebuild. |

## Acceptance evidence

Status: accepted. All required gates passed. Initial `make plan-status`: 113 tasks, 101 agent, 12 human.
CLEAR=88, RUN NEEDED=13, BLOCKED BY HUMAN=3, HUMAN-GATED=9. MODEL=12, DELIVERY=101.

- Initial coverage regressions failed because missing coverage was accepted and no deployed
  resolver factory existed. `tests/review/test_coverage.py` and
  `tests/contracts/test_registry.py` now exercise full coverage and registration refusal.
- `make contract-compile`, `make format typecheck complexity-gate` and `make lint-md` passed.
  The editable storage version is `1.0.0`. Identity adds one projected field and no new event type.
- `make model-baseline`: passed. The two typed snapshots have identical SHA-256 digests and
  contain the original review events. Results, fixtures and replay reports are under
  `$DATA_DIR/model-baseline/check-EoxBSZeD/`. The first rebuild sees pending unimported targets,
  and both rebuilds recover all five exact decisions after fixture input is restored. Locale
  changes, a label edit and a changed SATCOM snapshot expose no old stamp. All original SATCOM
  cells and archived files match.
- Focused PostgreSQL suite: 13 passed across `test_rebuild_cli.py`,
  `test_review_projections.py`, `test_evidence_verification.py` and
  `test_identity_lifecycle_review.py`. These cover the normal rebuild and SATCOM CLI, reviewer,
  evidence and content rights, missing and incompatible targets, stale measurements and
  identity restoration. The dispatch regression and CLI contract goldens were also checked.
- The initial unit gate found a SQLite CLI test missing a mock for PostgreSQL review locks,
  outdated CLI contract digests and a direct object constructor missing its revision event.
  The fixtures were updated. Final `make ci`: 1,413 passed, 130 local tests deselected.
- The first full `make ci-local` run passed all 130 local tests and stopped at the Jena check
  because the pinned Temurin runtime was absent. `make skos-reference-tools` installed
  Temurin 21.0.13.1+2 using the registered SHA-512 pin. The final `make ci-local` passed
  1,413 unit tests, 130 local tests and all 16 Apache Jena RIOT checks. No gate was skipped.
  The Jena summary is `$DATA_DIR/skos-reference/3e698e7c6df148c88ed308e62f14fa66/summary.json`.
  Local hostname resolution was available in the same execution environment as PostgreSQL.
- The original-profile `make db-up` started PostgreSQL but failed its governance upgrade.
  An isolated Compose project on loopback passed startup and the explicit development rebuild.
  Both test containers were stopped. The original-profile volume was preserved.
- Acceptance logs, coverage inventory and snapshot checksums are retained under
  `$DATA_DIR/human-verification/projections-Hf5eTFjA/`.

## Handoff

Plan transition: 113 to 112 total, 101 to 100 agent, 12 human. CLEAR=87, RUN NEEDED=13,
BLOCKED BY HUMAN=3, HUMAN-GATED=9. MODEL=11, DELIVERY=101. The next agent task is
`review-queue-cli`, which consumes the shared projections and replay. The
`evidence-model` capability remains planned pending that workflow and its group audit.
