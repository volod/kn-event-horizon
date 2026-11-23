# Planning Workflow Guide

The documentation lifecycle keeps product intent, future work, and available behavior separate.

## Choose the work contract

- For a named plan task, read the owning specification and current-state page, verify its
  prerequisites, and open a [task record](../impl/records/README.md) before implementation.
- For an ordinary fix or maintenance request, use the request and the existing specification as
  the contract. Create a record when the work needs a durable handoff.
- Before opening a research task, check the
  [closed-research register](../impl/future-research.md). A closed question reopens only when its
  reopening condition holds. See [Closed research](#closed-research).
- For a new capability, define the operator problem, boundary, evaluation, and valid negative
  result in the [specification](../design/spec.md#extending-this-specification). Register the
  capability and plan its work before editing production code. Amend the owning section when
  changing an existing product promise.

Review findings against the work contract. Fix in-scope findings, attach concrete follow-up to
the owning open task or create one, and route new capabilities through the specification. Include
observed behavior, impact, and an acceptance check when scheduling an unfixed bug.

## Task lanes

Use **Agent Implementation Tasks** when an agent can reach acceptance using repository fixtures,
deterministic tools, or an authorized non-interactive run:

- `CLEAR`: code, tests, and docs can finish locally.
- `RUN NEEDED`: implementation is deterministic, but acceptance includes a declared heavier run.

Use **Human-Assisted Tasks** when acceptance itself needs a person or authority unavailable to an
agent:

- `BLOCKED BY HUMAN`: an agent can prepare support, but a human-provided artifact gates completion.
- `HUMAN-GATED`: the outcome is human judgment, authorization, private access, or spend approval.

Add `Research: yes` when the path is uncertain and a well-supported negative result is acceptable.
Research tasks still need scope and acceptance criteria. A negative result, including "not at this
scale", leaves the plan as a section in the [closed-research register](../impl/future-research.md)
that states what would reopen the question.

## Prerequisites and scheduling

Use the optional `Requires` field for open tasks that must leave the plan before work can start.
List backticked task IDs separated by commas. IDs can refer to either lane. The integrity check
rejects missing IDs, cycles, and required tasks that depend on optional work.
Within each lane, prerequisites must appear before their dependents, including an ancestor
reached through the other lane. Cross-lane gates keep their own lane and remain blocking.

```markdown
- Requires: `prepare-fixtures`, `approve-inputs`
```

Use the required `Dependencies` field for external inputs, manual prerequisites, or evidence
needed at acceptance. Use `none.` when there is no additional prerequisite. A human-lane task
should name the specific input, decision, or authorization required and what an agent can prepare.

Long prerequisite lists can continue on the next line with two spaces of indentation.

`make plan-status` skips tasks with an open `Requires` entry, then lists priority in each lane.
Check the `Dependencies` field and the task's acceptance gates before starting.

Tasks can label contracts and fixture-based storage work `Execution stage: MODEL`. Other work
defaults to DELIVERY. These labels describe the work for reporting. Dependencies and the order
of delivery groups determine when it can start.

## Task shape

Task ids are stable lowercase slugs. A task heading may end with `(optional)`. Use this structure:

```markdown
### Delivery group name -- `group-id`

#### stable-task-id

Describe the unresolved operator problem in present or future tense.

- Serves: `capability-id` -- [Specification section](../design/spec.md#section)
- Agent status: CLEAR
- Execution stage: DELIVERY
- Dependencies: none.
- User-visible outcome: State what becomes possible or trustworthy.
- Scope boundary: State what is in scope and explicitly out of scope.
- Data and artifact paths: Name repository-relative or `$DATA_DIR` locations.
- Execution path: Name modules, fixtures, commands, and any declared run.
- Acceptance gates: State deterministic checks and the negative-result rule.
- Documentation target: [Current-state area](../impl/current.md#areas).
```

The plan integrity gate requires every field. Human-lane tasks use a human-lane status. Optional
agent work follows all required agent work; within the human lane it follows required work for
the same capability.

## Ordering

The agent lane consists of contiguous delivery groups. Name the group for an observable outcome,
place prerequisites before dependents, and keep the specification owner in each task's `Serves`
field. A group may cross capability boundaries. Keep required groups first. Human tasks retain
their capability headings and explicit approvals. Scan past a blocked task to find independent
ready work. MODEL and DELIVERY can occur in either order when dependencies permit it.

End each group with `<group-id>-implementation-audit`. Its prerequisites cover every open member,
including measured runs, directly or through another member. A consumer in another agent group
requires the producing audit, directly or transitively. Name any human decisions separately.
Keep a human approval that enables the group's own run inside that dependency path. Split fixture
delivery and external acceptance when one can be audited independently. Once only the audit
remains, keep its heading and run it against accepted records.

## Implementation audits

Each required group has a required closing audit. An optional extension has an audit with the
same optional status and must pass it to claim acceptance of that extension. Compare the group
with the owning spec sections, the actual normal entry point and named downstream consumers.
Reproduce the member acceptance gates, including measured results and required human evidence.
For human decisions and one-time external writes, verify the recorded approval, receipts and
read-back evidence. Repeat a live operation only within its authorization. Document remaining
uncertainties, supported limits and conditions for re-evaluation.

Record findings when discovered during implementation as well as during the audit. For each,
give a stable ID, severity, evidence, affected consumer, owner and disposition. Fix in-scope
defects with a failing regression. Give deferred bugs, specified features and quality
improvements a forward task with a concrete acceptance check and link its ID from the finding.
Route new product promises through specification review. Insert prerequisite fixes before the audit and
add their IDs to its `Requires`. A blocker keeps the audit open. For nonblocking follow-ups,
gate affected consumers where necessary and document the residual risk. A clean audit records
commands, results and the boundaries actually checked.

The record gives each check a result:

1. **Implementation validation.** Every acceptance gate of the group's accepted tasks reproduces on
   the current tree from the commands in their records. The current-state page matches the actual
   commands, interfaces, paths, and error codes.
2. **Specification conformance.** Each promise, integrity rule, boundary, and evaluation item of
   the owning specification section maps to code and a test, or is listed as a gap. No behavior
   exists outside the boundary. Contracts and interfaces that other groups consume match what
   those groups expect.
3. **Design scope.** Each decision that would be expensive to change later is listed with its
   reason: identifiers, contract and file layouts, CLI and error-code surfaces, extension points,
   and the seams that later groups use. Changes that the specification already names, such as new
   sources, domains, counterparts, releases, locales, scale targets, and release migration mode,
   fit by extension without a breaking change.
4. **Corner cases.** Empty, missing, duplicate, out-of-order, partial, oversized, malformed, and
   hostile input; time zones and clock skew; Unicode and bilingual text; interruption, retry, and
   concurrent runs; rerun idempotency; and a rebuild from durable inputs with identical results.
   Each case has a test or a recorded reason why it cannot occur.
5. **Best practices.** The [project rules](../../AGENTS.md) and the practices of the group's
   tools: typing, cohesive modules, named constants, logging, secret handling, ASCII, pinned
   dependencies, deterministic network-free tests, failure-path coverage, least privilege, input
   validation, observability, and declared performance budgets.
6. **Debt.** Parallel implementations of one rule, dead code, skipped or weakened checks, open
   `TODO` notes, and tests that assert internals instead of behavior.

Each finding gets an ID, a severity (`blocker`, `major`, or `minor`), evidence (a file and line, a
command and its output, or a failing test), and one disposition:

| Disposition | Rule |
| --- | --- |
| Fixed | An in-scope defect is fixed in the audit, starting from a failing regression test. |
| Scheduled bug | A defect too large for the audit becomes a plan task in the owning group, with observed behavior, impact, and an acceptance check. |
| Scheduled feature | A missing behavior that the specification already promises becomes a plan task with its operator problem. Tasks that need it gain a `Requires` entry. |
| Specification change | A change to a product promise follows [Choose the work contract](#choose-the-work-contract) before any task is planned. |
| Quality improvement | Schedule a measurable reliability, maintainability or verification improvement with an owner and acceptance check. |
| Research | An uncertain path becomes a task with `Research: yes`. |
| Accepted | A risk kept on purpose is listed under known limitations on the current-state page, with its reason and what would reopen it. |

A `blocker` is never accepted. An audit fixes defects and schedules the rest; it does not add
features or refactor without a finding. A finding owned by another group is scheduled in that
group. Record the before and after task counts like any other plan change.

## Record file naming

Name each task record `NNNN-<group>-<task-id>.md`. Use the next unused four-digit sequence
from the [records index](../impl/records/README.md), starting at `0001`. For planned work, use
the capability ID as `<group>` and the plan task ID as `<task-id>`. For ad hoc work, use
`adhoc` as `<group>` and a descriptive lowercase slug as `<task-id>`.

Copy the [record template](../impl/records/template.md), add the new file to the index in
sequence order, and advance the next unused sequence in the same change. Keep each assigned
number for the life of its record. The index (`README.md`) and `template.md` are unnumbered.

## Completion transition

Before reporting completion:

1. Capture the initial counts with `make plan-status` before editing the plan.
2. Run the declared acceptance checks. Record exact commands, results, and any outstanding gate.
   A declared research negative can satisfy acceptance when the evidence supports it.
3. Update current-state docs with interfaces, locations, verification methods, and durable findings.
4. For a research task that closes negative, add its section to the
   [closed-research register](../impl/future-research.md) in the same change that removes the task
   from the plan, and link the section from the record. A task that reopened a closed question
   rewrites or removes that section as described in [Closed research](#closed-research).
5. Remove the accepted task and its ID from downstream `Requires` fields. Add links to current
   facts in `Dependencies` where useful. Mark a newly available capability `shipped` and link its current
   documentation.
6. Run `make ci` on the resulting tree, including documentation links and spec-plan integrity.
   Capture the final counts and close the record when all gates pass.
7. Review the diff and report verification, count changes, affected capabilities, and open gates.

Keep routine run evidence in the record and durable implementation facts in current state.

## Closed research

The [closed-research register](../impl/future-research.md) keeps questions that stopped with a
decision. Its header defines the section shape. A section links the evidence in its record and
current-state pages rather than restating it, and its reopening condition is something a
measurement or an outside change can satisfy.

To reopen a closed question once its condition holds, open a task with a new id; the closed id stays
on the register heading. Link the register section from its `Dependencies` and keep the listed dead
directions out of its scope. When that
task is accepted, update the register in the same change so it never contradicts current state:

- if the task ships the behavior, remove the section and point links to it at the new record;
  `make lint-doc-links` lists any that remain;
- if the task closes negative again, rewrite the section under its original heading so existing
  links resolve, link the new record from the answer, and add the newly closed directions.

A `- Reopening task:` line names the open plan task that owns a reopening path, usually a
human-lane task waiting for an authorization or input. When that task leaves the plan,
`make lint-spec-plan` fails until the section names the follow-up research task or is rewritten.
