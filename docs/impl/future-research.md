# Closed Research Register

This register records research questions that were investigated to a decision and then stopped,
with the conditions that would make each worth reopening. Check it before opening a research task.
It is not a backlog or a changelog. Open work belongs in the [forward plan](plan.md), available
behavior in [current-state documentation](current.md), and measurements in
[task records](records/README.md). Each section links that evidence instead of restating it.

Every `##` section below this header is one closed question and follows these rules:

1. **Heading.** The task id the question carried in the plan, in backticks, then ` -- ` and the
   question in a few words. The id is no longer an open task.
2. **Question.** What was asked, in operator terms.
3. **Answer.** The decision, usually "no" or "not at this scale", what was measured, and what
   closed it. Link the task record and current-state pages that hold the evidence.
4. **Reopening condition.** What would have to be true, not merely attempted, for the question to
   be worth reopening. State a number or a change in the world, never more effort. When the
   condition waits on an authorization or an input nobody has yet, an open plan task can own the
   reopening path. Name it on a `- Reopening task:` line.
5. **Do not re-run.** Each direction already shown not to work, with a one-line reason it is closed
   by measurement rather than by budget, so a reopening does not repeat it.

```markdown
## `task-id` -- the question in a few words

### Question

### Answer

### Reopening condition

- Reopening task: `open-task-id`

### Do not re-run

- A dead direction -- the measurement that closed it.
```

The [planning workflow](../guide/planning-workflow.md#closed-research) covers adding, reopening,
and removing sections. `make lint-spec-plan` checks section structure and task references.

No closed questions yet.
