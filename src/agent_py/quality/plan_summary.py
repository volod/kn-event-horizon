"""Summarize the forward plan and identify the highest-priority work in each lane."""

import argparse
import logging
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from agent_py.quality.plan_dependencies import prerequisites
from agent_py.quality.plan_integrity import PLAN_DOC, integrity_findings
from agent_py.quality.plan_model import (
    AGENT_SECTION,
    HUMAN_SECTION,
    Task,
    read_tasks,
)
from agent_py.quality.project_root import discover_project_root

_LOG = logging.getLogger(__name__)


INVALID_PLAN_MESSAGE = "plan is invalid; run make lint-spec-plan"


def _lane_priority(tasks: list[Task], section: str) -> str:
    lane_tasks = [task for task in tasks if task.section == section]
    candidates = (task for task in lane_tasks if not prerequisites(task))
    # Validated document order preserves registry order between tasks of equal priority.
    task = min(candidates, key=lambda task: task.optional, default=None)
    if task is None:
        return "all waiting on prerequisites" if lane_tasks else "none"
    optional = " (optional)" if task.optional else ""
    return f"{task.identifier}{optional} [{task.group}]"


def summary_lines(project_root: Path) -> list[str]:
    """Render lane counts and priority among tasks without open task prerequisites after validating the plan."""
    if integrity_findings(project_root):
        return [INVALID_PLAN_MESSAGE]

    tasks = read_tasks(project_root / PLAN_DOC)
    status_counts = Counter(task.agent_status for task in tasks)
    lines = [
        f"tasks: {len(tasks)}",
        f"agent lane: {sum(task.section == AGENT_SECTION for task in tasks)}",
        f"human lane: {sum(task.section == HUMAN_SECTION for task in tasks)}",
    ]
    if status_counts:
        rendered = ", ".join(
            f"{status}={count}" for status, count in sorted(status_counts.items()) if status
        )
        lines.append(f"statuses: {rendered}")
    lines.append(f"priority agent task: {_lane_priority(tasks, AGENT_SECTION)}")
    lines.append(f"priority human task: {_lane_priority(tasks, HUMAN_SECTION)}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    """Print plan status for maintainers and agents."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="summarize the forward implementation plan")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else discover_project_root()
    lines = summary_lines(root)
    for line in lines:
        _LOG.info("%s", line)
    return 1 if lines == [INVALID_PLAN_MESSAGE] else 0


if __name__ == "__main__":
    raise SystemExit(main())
