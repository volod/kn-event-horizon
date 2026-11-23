from pathlib import Path

from kn.quality.plan_summary import main, summary_lines
from tests.quality._plan_fixture import SPEC, audit_block, plan_with, task_block, write_project

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_repository_plan_is_valid_and_schedulable() -> None:
    lines = summary_lines(PROJECT_ROOT)

    assert lines[0].startswith("tasks: ")
    assert any(line.startswith("priority agent task: ") for line in lines)


def test_summary_counts_statuses_and_selects_required_work(tmp_path: Path) -> None:
    optional = task_block(identifier="optional-first", optional=True)
    required = task_block(identifier="required-next")
    plan = plan_with(required).replace(
        "## Human-Assisted Tasks",
        "### Extension -- `extension`\n\n"
        + optional
        + audit_block("extension", ("optional-first",), True)
        + "\n## Human-Assisted Tasks",
    )
    root = write_project(tmp_path, plan=plan)

    lines = summary_lines(root)

    assert "tasks: 4" in lines
    assert "statuses: CLEAR=4" in lines
    assert "priority agent task: required-next [feature]" in lines


def test_invalid_plan_summary_refuses_to_schedule(tmp_path: Path) -> None:
    root = write_project(tmp_path, plan=plan_with())

    assert summary_lines(root) == ["plan is invalid; run make lint-spec-plan"]
    assert main(["--root", str(root)]) == 1


def test_required_work_precedes_optional_work_across_capabilities(tmp_path: Path) -> None:
    optional = task_block(identifier="refine-foundation", capability="foundation", optional=True)
    plan = plan_with(task_block()).replace(
        "## Human-Assisted Tasks",
        f"### Foundation -- `foundation`\n\n{optional}\n"
        + audit_block("foundation", ("refine-foundation",), True)
        + "\n## Human-Assisted Tasks",
        1,
    )
    root = write_project(tmp_path, spec=SPEC, plan=plan)

    assert "priority agent task: build-feature [feature]" in summary_lines(root)


def test_priority_skips_task_waiting_on_other_lane(tmp_path: Path) -> None:
    waiting = task_block().replace(
        "- Dependencies: none.", "- Dependencies: none.\n- Requires: `review-feature`"
    )
    next_task = task_block(identifier="prepare-fixtures")
    review = task_block(identifier="review-feature", status="HUMAN-GATED")
    root = write_project(tmp_path, plan=plan_with(waiting, next_task, human_blocks=(review,)))

    assert "priority agent task: prepare-fixtures [feature]" in summary_lines(root)
    assert "priority human task: review-feature [feature]" in summary_lines(root)


def test_priority_reports_lane_blocked_by_open_prerequisite(tmp_path: Path) -> None:
    waiting = task_block().replace(
        "- Dependencies: none.", "- Dependencies: none.\n- Requires: `review-feature`"
    )
    review = task_block(identifier="review-feature", status="HUMAN-GATED")
    root = write_project(tmp_path, plan=plan_with(waiting, human_blocks=(review,)))

    assert "priority agent task: all waiting on prerequisites" in summary_lines(root)
