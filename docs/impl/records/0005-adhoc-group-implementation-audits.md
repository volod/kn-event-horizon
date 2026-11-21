# 0005 Group Implementation Audit Tasks

## Work contract

Direct request from the owner, with no plan task. Every capability group in the agent lane of the
[forward plan](../plan.md) gets an optional implementation audit task. An audit:

- validates the implementation;
- audits its logic and design scope;
- creates the feature and bug-fix tasks it finds;
- makes sure every finding from the deep dive is documented and either fixed or scheduled;
- confirms the result follows best practices and covers corner and future cases, so that known
  issues do not later force expensive refactoring.

## Implementation and decisions

The shared procedure is a new [implementation audits](../../guide/planning-workflow.md#implementation-audits)
section in the planning workflow guide. It has six checks:

1. implementation validation;
2. specification conformance;
3. design scope, including future cases the specification already names;
4. corner cases;
5. best practices;
6. debt.

Each finding gets a severity, evidence, and one of six dispositions: fixed, scheduled bug,
scheduled feature, specification change, research, or accepted. A `blocker` is never accepted.

The plan gains 23 tasks named `<group>-implementation-audit (optional)`, one at the end of each
agent group. Every audit has the nine required fields. The scope boundary of each task names the
group's focus areas, its execution path names the cases to plant, and its acceptance gates add
group-specific checks to the shared gate. A plan header paragraph links the procedure.

Decisions:

| Decision | Reason |
| --- | --- |
| An audit requires the group's required `CLEAR` tasks only | Slow `RUN NEEDED` runs and human gates would otherwise delay the audit past the point where fixes are cheap. Open runs are reviewed for input readiness, and the dependencies of the affected audits name them. |
| `ai-extraction` audits its optional task and is `RUN NEEDED` | The group has no required task, and its checks rerun model extraction on the `gpu` profile. |
| Audits are optional and nothing requires them | The owner asked for optional tasks. The integrity check also forbids required work that depends on optional work, so audits never block delivery order. |
| Human-lane groups get no audit | The request covers agent groups. Human-lane tasks of the same capability are covered by that capability's agent-group audit. |
| No specification change | Audits are a planning procedure. They do not change any product promise, capability, or registry row. |

## Acceptance evidence

Status: accepted for the documentation change. No production code changed.

- `make lint-spec-plan`: 0 findings, including the research register.
- `make plan-status`: 119 tasks; priority tasks unchanged.
- `make lint-md`: exit 0.
- `make ci`: exit 0.
- `git diff --check`: clean.

## Handoff

Plan counts went from 96 tasks (85 agent, 11 human) to 119 tasks (108 agent, 11 human). Statuses
went from CLEAR 78, RUN NEEDED 7, HUMAN-GATED 9, BLOCKED BY HUMAN 2 to CLEAR 100, RUN NEEDED 8,
HUMAN-GATED 9, BLOCKED BY HUMAN 2. Every agent capability group gains one optional task. No
existing task, prerequisite, or registry row changed. The priority tasks stay
`compose-database-service` and `provide-inventree-instance-access`.
