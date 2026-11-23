"""Validate that the written lanes can be read in dependency and delivery-group order."""

from itertools import groupby

from kn.quality.plan_dependencies import prerequisites
from kn.quality.plan_model import AGENT_SECTION, Task


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


def _group_findings(tasks: list[Task]) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    by_id = {task.identifier: task for task in tasks}
    lane = [task for task in tasks if task.section == AGENT_SECTION]
    optional_seen = False
    for group, items in groupby(lane, key=lambda task: task.group):
        members = list(items)
        audit = members[-1]
        if group in seen:
            findings.append(f"`{group}`: delivery group must be contiguous")
        seen.add(group)
        findings.extend(_audit_findings(group, members, by_id))
        if optional_seen and not audit.optional:
            findings.append(f"`{group}`: agent task order must place required groups first")
        optional_seen |= audit.optional
    return findings


def _audit_findings(group: str, members: list[Task], by_id: dict[str, Task]) -> list[str]:
    findings: list[str] = []
    audit = members[-1]
    if audit.identifier != f"{group}-implementation-audit":
        findings.append(f"`{group}`: end the group with its implementation audit")
    if any(task.optional != audit.optional for task in members):
        findings.append(f"`{group}`: separate required and optional delivery groups")
    missing = {task.identifier for task in members[:-1]} - _ancestors(audit, by_id)
    if missing:
        findings.append(f"`{audit.identifier}`: audit must require {', '.join(sorted(missing))}")
    return findings


def _handoff_findings(tasks: list[Task]) -> list[str]:
    by_id = {task.identifier: task for task in tasks}
    findings: list[str] = []
    for task in tasks:
        if task.section != AGENT_SECTION:
            continue
        ancestors = _ancestors(task, by_id)
        missing = set()
        for identifier in sorted(ancestors):
            producer = by_id[identifier]
            if producer.section != AGENT_SECTION or task.group == producer.group:
                continue
            audit = f"{producer.group}-implementation-audit"
            if audit not in ancestors:
                missing.add(audit)
        findings.extend(
            f"`{task.identifier}`: require producer audit `{audit}`" for audit in sorted(missing)
        )
    return findings


def task_order_findings(tasks: list[Task]) -> list[str]:
    """Check written order, audit coverage and reviewed handoffs across lanes."""
    return _prerequisite_order_findings(tasks) + _group_findings(tasks) + _handoff_findings(tasks)
