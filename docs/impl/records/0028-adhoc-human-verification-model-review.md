# Human Verification Model Review

## Work contract

The owner asked to review the application data model so every piece of data can carry an optional
human-verification timestamp, enabling future verification workflows. This is a model review and
specification/planning update; production schemas, data and workflows are not changed.

The review treats a piece of data as a record or a field-level fact. The owner was offered a scope
choice; in the absence of a narrower preference, both scopes are covered independently.

## Implementation and decisions

The reviewed surface is the registered governance, semantic and SATCOM contracts, the SATCOM
importer, semantic publication and terminology review metadata, development rebuild, and the
planned claim, selection, review, replay and interchange paths. The new requirement belongs to
`evidence-model`; its registry entry remains planned. No new capability or production dependency
was needed.

### Findings

| ID | Severity | Evidence and impact | Disposition |
| --- | --- | --- | --- |
| HV-01 | major | The 50-table/465-field inventory has zero common human-verification timestamps. This includes semantic labels, links and mappings, not only SATCOM observations. A domain-only field would leave substantial data uncovered. | Specify shared nullable UTC metadata and explicit coverage for every registered dataset; schedule `human-verification-contracts` and `human-verification-projections`. |
| HV-02 | major | `satcom/1.0.0.json` contains `verification_status` on sources and evidence claims; `importer.import_package` copies source values into the projection. These assertions cannot identify an actual KN human verification. | Keep source assertions independent; prohibit automated or source-derived population of human timestamps. Bind the new stamp to an authenticated human acceptance. |
| HV-03 | major | SATCOM rows have snapshot-qualified composite keys; semantic labels also key by locale, and alternatives include label text in their key. A bare time on an entity could certify unrelated fields, another snapshot or another language after an edit. | Typed complete targets, separate record/field scopes, stable field IDs and content-version binding, with stale/orphan handling. |
| HV-04 | major | `semantic.verification.VerificationReport.reviewed_on` is a date, while the label tables carry optional `review_reference` but no common actor/time. These records must not be converted into invented human instants. | Retain existing meanings and leave unknown human dates null. Add reviewer and decision references together with any active timestamp. |
| HV-05 | major | `db.rebuild.rebuild` drops the KN schemas and reloads seeds. SQL-only verification metadata would disappear; identity/claim review replay is still forward work. | One durable append-only history under DATA_DIR with exact replay, pending missing targets, revocation and no automatic approval of changed content. Amend replay and review tasks. |
| HV-06 | minor | The existing plan has domain review/selection and dashboard/exchange tasks, but no cross-cutting verification coverage or consistent metadata exposure. | Amend their scope, dependencies and acceptance checks to reuse the same model, including rights filtering and exchange trust/loss behavior. |

These findings describe a gap against the owner's new requirement, not a claim that the previous
contract promised an implemented universal human-review ledger.

### Model decisions

- Standard read metadata: nullable `human_verified_at` (UTC timestamptz), `human_verified_by`,
  and `human_verification_decision_id`; active acceptance supplies all three or none.
- Record and independently addressable field/fact scopes are separate. Neither stamps the other
  implicitly. All existing datasets, including labels, edges and technical metadata, receive an
  explicit coverage strategy. New contract registration must not silently omit coverage.
- A central append-only decision model is authoritative; nullable fields or joined read views
  expose consistent projections. No source CSV, archive payload or original verification label
  is modified. No timestamp column is duplicated for every source cell.
- Human actor authority, exact content version and review purpose are essential. Imported text,
  agent/model output, source rank or a content checksum cannot manufacture a human acceptance.
- No default-now or epoch stamp; date-only legacy reviews do not become invented UTC instants.
  Changed content, rejection and revocation keep history but lose active acceptance. Untouched
  or unreviewed data remains usable with null metadata.
- The durable history must survive rebuilds and re-imports with exact times and identities.
  Unresolved targets remain pending/orphaned rather than silently reassigned. Future workflows
  reuse this foundation; assignment, scheduling, notifications and UI implementation stay later.

The [specification](../../design/spec.md#human-verification-metadata) now states the cross-domain
requirement and evaluation. The detailed [design](../../design/human-verification.md) defines the
coverage inventory, optional fields, event target, time/version rules, replay, exchange and valid
null/legacy outcomes. The [current-state page](../current/data-contracts.md#human-verification-metadata)
explicitly records that the metadata is not implemented.

## Acceptance evidence

Status: accepted as a model review and specification/planning change. Implementation remains planned.

- Initial working tree: clean. Initial `make plan-status`: 111 tasks, 98 agent, 13 human;
  CLEAR=89, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10.
- Enumerated every table and field of `registered_contracts()` without connecting to a database.
  The machine-readable inventory is retained under
  `$DATA_DIR/model-review/human-verification-20261123T073936Z/inventory.json`:
  18 semantic, 31 SATCOM and one governance table; 465 fields; zero common human timestamps.
- `make lint-md lint-spec-plan`: passed during review, including links, task dependencies,
  capability placement and closed-research register checks.
- Final `make ci`: passed; 815 unit tests passed and 64 integration tests were deselected.
  Formatting, lint, typing, complexity, shell, catalogs, generated-contract drift, documentation
  links and specification/plan checks passed. The full log is retained as `ci.log` beside the
  inventory. Service tests were not run for this documentation-only review; no production model
  or database state changed.
- `make lint-md lint-spec-plan`, `git diff --check`, and an ASCII/scope scan passed. Only files
  under `docs/` changed. Final `make plan-status`: 113 tasks, 100 agent, 13 human;
  CLEAR=91, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10.

## Handoff

Implementation remains open in `human-verification-contracts` and
`human-verification-projections`; this review does not implement their acceptance gates. The
existing claim, fact-selection, review-queue, rebuild, analyst fact-explanation and interchange
work now carries the shared requirement. The evidence-model audit requires the two new tasks.

Plan counts: 111 to 113 total, 98 to 100 agent, 13 human unchanged; CLEAR=89 to 91,
RUN NEEDED=9, BLOCKED BY HUMAN=3 and HUMAN-GATED=10 unchanged. Capability `evidence-model` remains
planned; no shipped capability is represented as having acquired this runtime feature. The next
required agent priority is still `identity-registry-contracts`. No production Python, contract,
generated schema, source seed or live database was changed.
