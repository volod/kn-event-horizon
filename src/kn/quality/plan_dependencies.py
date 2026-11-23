"""Validate open-task prerequisites and identify tasks blocked by them."""

import re
from graphlib import CycleError, TopologicalSorter

from kn.quality.plan_model import MODEL_STAGE, Task

_TASK_ID = re.compile(r"`([a-z0-9][a-z0-9-]*)`")


def prerequisites(task: Task) -> list[str]:
    """Return the open task IDs explicitly required before a task can start."""
    return _TASK_ID.findall(task.fields.get("requires", ""))


def _task_findings(task: Task, tasks_by_id: dict[str, Task]) -> list[str]:
    where = f"`{task.identifier}`"
    findings: list[str] = []
    if "requires" in task.fields and not re.fullmatch(
        rf"{_TASK_ID.pattern}(?:,\s*{_TASK_ID.pattern})*", task.fields["requires"]
    ):
        findings.append(f"{where}: Requires must list comma-separated backticked task IDs")
    for identifier in prerequisites(task):
        prerequisite = tasks_by_id.get(identifier)
        if prerequisite is None:
            findings.append(f"{where}: requires unknown open task `{identifier}`")
        elif prerequisite.optional and not task.optional:
            findings.append(f"{where}: required work depends on optional task `{identifier}`")
        elif task.execution_stage == MODEL_STAGE and prerequisite.execution_stage != MODEL_STAGE:
            findings.append(
                f"{where}: MODEL task requires DELIVERY task `{identifier}`; split the runtime work first"
            )
    return findings


def dependency_findings(tasks: list[Task]) -> list[str]:
    """Check prerequisite syntax, targets, and cycles across both lanes."""
    tasks_by_id = {task.identifier: task for task in tasks}
    findings = [finding for task in tasks for finding in _task_findings(task, tasks_by_id)]
    sorter = TopologicalSorter({task.identifier: prerequisites(task) for task in tasks})
    try:
        sorter.prepare()
    except CycleError as error:
        findings.append("task dependency cycle: " + " -> ".join(error.args[1]))
    return findings
