# Delivery groups and audit gates

## Work contract

Review the specification and forward plan against the project's purpose. Replace global
schema-first delivery priority with logical groups, order work by actual prerequisites,
and put an actionable audit after each group. Preserve existing accepted work and operator
authorization boundaries.

## Findings and decisions

| Finding | Change and verification |
| --- | --- |
| The lifecycle CLI depended on the complete model checkpoint. Its fixtures use the accepted identity registry and review protocol. This edge delayed a testable workflow until unrelated domain and exchange contracts existed. | Remove the global checkpoint from the five consumer definitions. Retain the actual source, identity, evidence, ledger and archive prerequisites through their producing audits. Run the subset rebuild as models register. Keep full model/backfill acceptance before release approval. |
| Dataset-wide verification waited for every future domain, although its registration checks are what should protect each new domain. | Build coverage for the current registry and enforce coverage as each subsequent model joins. The full checkpoint still exercises all domains together. |
| Scheduling by stage partitioned producers from their first usable workflows. A written prerequisite could disagree with the stage rule. | Group source admission, identity resolution, claims/lineage, review, ingestion, supply and exchange around observable outputs. Group downstream work by domain collection, publication and operation. Stage labels describe the work; the ready task earliest in the required lane takes priority. |
| All 21 audits were optional and collected at the end. Some required only CLEAR tasks, omitting live acceptance, package ingestion, scheduled runs and restore/performance measurements. | Preserve the existing audit IDs and planted cases. Add nine audits at uncovered boundaries. Every agent group ends with an audit of matching optionality and all open members must be its ancestors. Real-instance exchange and calibration close separately from the fixture adapter. |
| External decisions could either stall independent local work or disappear from review. | Keep all 13 human task IDs, scopes, authorizations and negative outcomes. A group can ask for approval after preparing its evidence, then run and audit the authorized outcome. The vocabulary namespace and Drive publication each have a dedicated evidence review. Release preparation consumes required audited outcomes and the existing operator reviews. |
| Bugs, speculative concerns and useful quality work could receive the same vague handoff. | The workflow calls for reproducible evidence, severity, affected consumers, ownership and an acceptance check. A blocker keeps the audit open. An affected consumer explicitly depends on a deferred fix. New product promises return to specification review. |

## Acceptance evidence

The original inventory contained 116 tasks, 103 agent and 13 human. All 116 task IDs survive.
The new inventory has 125 tasks, 112 agent and 13 human. The agent lane has 30 contiguous groups
and 30 closing audits, including five optional extension groups. The first eligible agent task
is `source-catalogue-import`. The human priority remains `decide-vocabulary-uri-namespace`.

The plan checker covers missing or misplaced audits, incomplete run coverage, required/optional
separation, transitive producer handoffs (including paths via human decisions), written order,
unknown IDs and cycles. A closing audit remains schedulable after its last member leaves the
forward plan. The specification registry retains the existing product capability statuses.

A dry scheduling run removed each ready task and its prerequisite references in memory. Order
and dependency validation passed on every remaining graph through all 125 removals. The release
approval reaches all 24 required pre-release audits, including both owner-evidence reviews.
The last required audit checks release migration after approval. The simulated order is retained
under `$DATA_DIR/plan-audit/0034/dry-order.txt`. No human decision or run result was simulated
as product acceptance.

`make ci` passed with 926 tests and 89 local-only tests deselected. `make lint-md` and
`make lint-spec-plan` passed with zero broken links and zero plan or research-register
findings. `git diff --check` passed. This change affects planning and its automated checks.
The local service suite was outside the verification scope.
