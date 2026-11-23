# Dependency-Ordered Implementation Plan

## Work contract

Reorder agent implementation tasks so every prerequisite can be implemented before its dependent.
Make the written plan follow the schema-first execution order rather than relying on a scheduler
to compensate for capability-group ordering. Preserve every task, dependency and acceptance gate.

## Implementation and decisions

The old plan placed `development-model-baseline` first despite its 16 open prerequisites.
Capability grouping in registry order took precedence in the written plan, while the summary
silently selected a different task. Initial inspection found 14 direct same-lane dependency
inversions. This change makes the written agent lane follow executable dependency order.

- Reordered all 105 agent tasks with a topological traversal of the complete dependency graph,
  including human tasks, then kept tasks in their declared lanes. Among ready tasks, required
  work precedes optional work, MODEL precedes DELIVERY, registry order chooses between owners,
  and the previous task order resolves remaining ties.
- All 17 required agent MODEL tasks now appear first. `human-verification-contracts` is first,
  and `development-model-baseline` is seventeenth, after all 16 of its prerequisites. Required
  DELIVERY tasks follow, then optional work. Capability headings recur when execution returns
  to an owner; every task still sits under the capability matching its `Serves` field.
- Preserved every task body, field, dependency, optional flag, execution stage and acceptance
  gate. The 13-task human lane is byte-identical to the previous plan. Moving an agent task
  does not satisfy its human or external prerequisites, so these gates still block execution.
- Added `plan_order.py` to the integrity gate. It rejects a same-lane prerequisite appearing
  after its dependent, including an ancestor reached through the other lane. Traversal is
  bounded even for cycles or unknown IDs, which the existing dependency checker still rejects.
  It also rejects agent required/optional and MODEL/DELIVERY order inversions.
- Replaced agent registry-group ordering with the dependency/stage checks. Human registry
  ordering, ownership checks, required fields, valid statuses/stages, cycle detection and
  optional-work dependency checks remain enforced. Updated stage/summary fixtures to use the
  new physical order and added a regression preserving human registry ordering.
- Updated the specification's integrity rules, plan introduction, planning workflow,
  schema-first guide and development-check documentation. The summary's scheduling policy is
  unchanged; validated agent document order now agrees with its priority classes.

## Acceptance evidence

Status: accepted. Evidence is retained under
`$DATA_DIR/plan-review/dependency-order-72o4bjix/`.

| Check | Result |
| --- | --- |
| Regression tests against the old checker | Six new cases failed and one human-lane preservation case passed before implementation |
| Focused planning suite | 95 passed; `focused.log` |
| Complete task preservation and ordering | `verify_order.py` passed; `verification.json` proves all 118 task bodies and parsed metadata are unchanged, the human lane is unchanged, and both dependency and agent-class inversions are zero |
| Baseline placement | Position 1 before, position 17 after; its 16 prerequisites occupy the preceding required MODEL prefix |
| Formatting, lint, typing and complexity | `make format typecheck complexity-gate` passed |
| Documentation and plan checks | `make lint-md lint-spec-plan plan-status` passed with zero broken links or integrity findings |
| Required CI | `make ci` passed: 833 tests, 67 local-only tests deselected; `ci.log` retains the complete output |

Reproduce the order audit from the project root after loading the environment:

```bash
source scripts/shared/common.sh
kn_load_env
.venv/bin/python "$DATA_DIR/plan-review/dependency-order-72o4bjix/verify_order.py" \
  "$DATA_DIR/plan-review/dependency-order-72o4bjix"
```

`before-plan.md`, `before.json` and `after-order.json` preserve the original plan, initial
inversions and the reordered model sequence. No database behavior changes in this request;
`make ci-local` is not repeated for this planning change. The prior baseline implementation's
67-test database run remains recorded in [record 0030](0030-data-contracts-development-model-baseline.md).
The final ASCII scan and `git diff --check` passed; no temporary service was started for this work.

## Handoff

Before and after: 118 tasks, 105 agent, 13 human; statuses BLOCKED BY HUMAN=3, CLEAR=96,
HUMAN-GATED=10, RUN NEEDED=9; stages MODEL=18, DELIVERY=100. No task is accepted or removed,
and no capability status changes. Affected capability: `documentation-integrity`; the reordered
plan still serves all its original capabilities.

Start with `human-verification-contracts`, then follow the written agent sequence while checking
human/external inputs. The baseline work from record 0030 remains open until the preceding model
owners and the combined acceptance pass. Previous implementation work and all pre-existing
working-tree changes are preserved.
