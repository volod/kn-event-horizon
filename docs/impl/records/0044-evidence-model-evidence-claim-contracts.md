# 0044 Evidence claim contracts

## Work contract

```markdown
#### evidence-claim-contracts

Claims, evidence, and canonical facts need contracts that carry every provenance field.

- Serves: `evidence-model` -- [Evidence model](../design/spec.md#evidence-model)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [qualified catalogue IDs](current/source-management.md#reviewed-inputs-and-identifiers).
- User-visible outcome: The `evidence` schema holds alias, claim, claim confirmation, evidence,
  relation assertion, canonical fact, and review item datasets with value-or-missing-reason
  constraints. Every claim refers to a KN ID and to its source record version.
- Scope boundary: Contracts, constraints, deterministic claim keys, and as-of views. Objects and
  identifiers come from the identity registry. Selection policies come in
  `canonical-fact-selection`. Claims and canonical fact projections reuse the shared optional,
  version-bound human verification model instead of defining another timestamp convention.
  Include the review-item/decision shapes, claim confirmations, field-change lineage, selection
  outcome/history and source-rank/update-policy formats needed by later writers. Those tasks
  implement behavior over this model rather than adding another core state layout.
- Data and artifact paths: `contracts/core/evidence/`, `src/kn/evidence/`, `tests/evidence/`.
- Execution path: Write the contracts with `kn.temporalProfile` and `kn.evidence` extensions, and
  compile and test the constraints against the integration database.
- Acceptance gates: A claim without an origin URI, a fetch time, or a value-or-missing-reason is
  rejected. Re-inserting the same claim key is a no-op. As-of views are deterministic on fixtures.
  A claim that cites a deprecated or replaced concept appears in the
  [lifecycle report](current/ontology-taxonomy.md#lifecycle-report) as an external use, with the
  concept's successor.
  Multilingual text projections preserve originals, language tags, and translation provenance under
  the [localization policy](../design/spec.md#localization), without duplicating facts per locale.
  A changed claim version has no inherited human verification; an unreviewed claim keeps null
  metadata, regardless of its imported source verification label.
- Documentation target: A new `current/evidence-model.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The prerequisite [qualified catalogue IDs](../current/source-management.md#reviewed-inputs-and-identifiers)
were available. Registered `kn.core.evidence` adds 11 tables and 148 fields to the `evidence`
schema beside the human verification decision log, bringing the deployment set to 73 tables and
706 fields. The editable baseline stays at `1.0.0`; no dependency or Alembic revision was added,
because the baseline creates every registered contract from its metadata.

- Tables: evidence records, claims, claim confirmations, aliases, text translations, relation
  assertions and supports, canonical fact versions, selection outcomes, review items and review
  decisions. Claims carry every [rule 3](../../design/spec.md#knowledge-integrity-rules) field
  directly or through their required evidence row: origin URI, fetch time and fetch ID on the
  claim; locator, rights, archive record and code and contract digests on the evidence.
- Value or missing reason: the compiler gained the bounded table extension `kn.presence`
  (`exactly_one`, `all_or_none`). It compiles to named `num_nonnulls` checks and to matching JSON
  Schema and Pydantic rules. Tables without rules keep byte-identical artifacts, so the other five
  contracts' generated output is unchanged. The extension schema pin was refreshed; the vendored
  ODCS schema is unchanged.
- `kn.evidence` gained `assertionField` as an alternative to a fixed `assertionType`, because the
  assertion type of a claim is per row. Exactly one of them is required.
- Keys reuse the human verification `content_version` digest over identifying columns. Recording
  times are first-seen columns outside the key, so a rerun of one raw record with the same code
  yields the same keys. Cross-contract references (KN IDs, source versions, change sets,
  concepts) stay engine-checked, per the registry rule against cross-contract foreign keys.
- Relations: an assertion per relation key and opening claim, supported by claims, with a partial
  unique index on the relation key while open. Facts: knowledge-time versions keyed by content and
  knowledge start, one current version per fact key, and a claim or unresolved reason.
- `kn.evidence` provides typed rows with validation, an idempotent savepoint writer that refuses
  changed content under a stored key, as-of selects, the multilingual text projection over
  `kn.i18n.data`, claim concept uses for the semantic lifecycle report, update-policy and
  criteria formats, and human verification targets.
- Review findings during implementation: psycopg reported `rowcount = -1` for
  `INSERT ... ON CONFLICT DO NOTHING`, so the writer now counts `RETURNING` rows (the baseline
  fixture's rerun assertion failed first). A free-form criteria mapping on facts was replaced by
  the typed `Criteria` format. Splitting `_special` reference resolution kept the cognitive
  complexity gate at 15. Two planted database cases were corrected because PostgreSQL reported an
  earlier failing check (text without language) and the partial-date pattern checks shape only.

## Acceptance evidence

Status: accepted. Initial `make plan-status`: 118 tasks, 106 agent, 12 human; BLOCKED BY HUMAN=3,
CLEAR=93, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=105, MODEL=13.

| Gate | Evidence |
| --- | --- |
| A claim without an origin URI, a fetch time, or a value-or-missing-reason is rejected | `tests/evidence/test_model.py` refuses the typed rows; `tests/evidence/test_contract.py` shows the generated JSON Schema and Pydantic models reject them; `tests/integration/test_evidence.py` shows PostgreSQL `NOT NULL` and `ck_claims_value_or_reason_presence` failures, plus unit, time precision, enum and partial-date checks |
| Re-inserting the same claim key is a no-op | `test_every_reference_resolves_and_reinserting_a_key_is_a_no_op`: a second write and a later rerun add zero rows and leave every table unchanged; changed content under a stored key fails the batch |
| As-of views are deterministic on fixtures | `test_as_of_views_are_deterministic_and_half_open`: three shuffled insert orders give identical claim and fact views at seven knowledge/valid instants, matching expected keys |
| A claim citing a deprecated or replaced concept appears in the lifecycle report with its successor | `tests/evidence/test_concepts.py` |
| Multilingual text projections preserve originals, tags and translation provenance without duplicating facts | `tests/evidence/test_text.py` covers requested, English and original fallback, duplicate and foreign translations, and an unchanged fact |
| A changed claim version has no inherited human verification; an imported label keeps null metadata | `tests/evidence/test_verification.py` and `tests/integration/test_evidence_verification.py` submit a real acceptance for one stored claim; the changed claim, the labeled claim and a fact selecting another claim stay unreviewed; tampered content is stale |

- `make contract-compile`: 40 `kn.core.evidence` artifacts generated and reviewed; other contracts
  unchanged.
- `.venv/bin/python -m pytest tests/evidence tests/contracts -q`: passed.
- PostgreSQL acceptance used a disposable database with the normal baseline; the shared
  development database refused the changed contract set, as designed, and was not rebuilt. After
  `source scripts/shared/common.sh`, `kn_load_env` and `kn_db_test_env`, the runner is
  `.venv/bin/python "$DATA_DIR/evidence/claims-20261125/run_acceptance.py" [targets]`. The
  focused evidence, verification and combined-baseline run passed 16 of 16
  (`$DATA_DIR/evidence/acceptance-63a15bc9/`). The full `tests/integration` run passed 116 of 116
  with zero skipped (`$DATA_DIR/evidence/acceptance-fed938fb/`), including both model-baseline
  rebuild snapshots with every evidence table populated by the evidence loader.
- Final `make ci`: passed, with the integration tests deselected and run separately as above.
- `make lint-md`, `make lint-spec-plan`, `git diff --check`: passed.

## Handoff

The task left the plan. `partial-update-tracking` and `canonical-fact-selection` lost their only
`Requires` entry and now link the claim and selection shapes in `Dependencies`;
`object-identity-implementation-audit` no longer lists the task. Final `make plan-status`:
117 tasks, 105 agent, 12 human; BLOCKED BY HUMAN=3, CLEAR=92, HUMAN-GATED=9, RUN NEEDED=13;
DELIVERY=105, MODEL=12. Next required agent priority is `partial-update-tracking`.

`evidence-model` and `object-identity` remain `planned`: tracking, selection, lineage, review
queue journals and dataset-wide verification projections are their open tasks. The registry row
for `evidence-model` now names the evidence contracts. No commit or push was made.
