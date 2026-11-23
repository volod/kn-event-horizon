"""Validate that the written lanes can be read in dependency and execution-stage order."""

from kn.quality.plan_dependencies import prerequisites
from kn.quality.plan_model import AGENT_SECTION, MODEL_STAGE, Task


def _ancestors(task: Task, by_id: dict[str, Task]) -> set[str]:
    pending = prerequisites(task)
    seen: set[str] = set()
    while pending:
        identifier = pending.pop()
        if identifier in seen or identifier not in by_id:
            continue
        seen.add(identifier)
        pending.extend(prerequisites(by_id[identifier]))
    return seen


def _prerequisite_order_findings(tasks: list[Task]) -> list[str]:
    positions = {task.identifier: index for index, task in enumerate(tasks)}
    by_id = {task.identifier: task for task in tasks}
    return [
        f"`{task.identifier}`: place prerequisite `{identifier}` before its dependent "
        f"in '{task.section}'"
        for task in tasks
        for identifier in sorted(_ancestors(task, by_id))
        if by_id[identifier].section == task.section
        and positions[identifier] > positions[task.identifier]
    ]


def _stage_order_findings(tasks: list[Task]) -> list[str]:
    findings: list[str] = []
    previous = (False, False)
    for task in tasks:
        if task.section != AGENT_SECTION:
            continue
        rank = (task.optional, task.execution_stage != MODEL_STAGE)
        if rank < previous:
            findings.append(
                f"`{task.identifier}`: agent task order must put required before optional "
                "and MODEL before DELIVERY within each class"
            )
        previous = max(previous, rank)
    return findings


def task_order_findings(tasks: list[Task]) -> list[str]:
    """Check same-lane ancestors through either lane, then schema-first agent ordering."""
    return _prerequisite_order_findings(tasks) + _stage_order_findings(tasks)
