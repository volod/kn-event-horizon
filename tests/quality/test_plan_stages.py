"""Schema foundations are scheduled early without bypassing prerequisites or required work."""

from pathlib import Path

import pytest

from kn.quality.plan_integrity import integrity_findings
from kn.quality.plan_summary import summary_lines
from tests.quality._plan_fixture import plan_with, task_block, write_project


def staged(
    identifier: str, stage: str = "MODEL", *, optional: bool = False, status: str = "CLEAR"
) -> str:
    return task_block(identifier, optional=optional, status=status).replace(
        "- Dependencies: none.", f"- Execution stage: {stage}\n- Dependencies: none."
    )


def test_model_precedes_earlier_delivery_task(tmp_path: Path) -> None:
    root = write_project(tmp_path, plan=plan_with(task_block("build-ui"), staged("model")))
    assert "priority agent task: model [feature]" in summary_lines(root)


def test_model_priority_crosses_capability_groups(tmp_path: Path) -> None:
    plan = plan_with(staged("model"))
    earlier = task_block("earlier-workflow", capability="foundation")
    plan = plan.replace(
        "### Feature", f"### Foundation -- `foundation`\n\n{earlier}\n### Feature", 1
    )
    root = write_project(tmp_path, plan=plan)
    assert "priority agent task: model [feature]" in summary_lines(root)


def test_prerequisite_filter_runs_before_stage_priority(tmp_path: Path) -> None:
    waiting = staged("dependent-model").replace(
        "- Dependencies: none.", "- Requires: `base-model`\n- Dependencies: none."
    )
    root = write_project(tmp_path, plan=plan_with(task_block("ui"), waiting, staged("base-model")))
    assert "priority agent task: base-model [feature]" in summary_lines(root)


def test_optional_model_never_delays_required_delivery(tmp_path: Path) -> None:
    root = write_project(
        tmp_path, plan=plan_with(task_block("required-ui"), staged("optional-model", optional=True))
    )
    assert "priority agent task: required-ui [feature]" in summary_lines(root)


@pytest.mark.parametrize("stage", ["FAST", "MODEL DELIVERY", ""])
def test_invalid_execution_stage_is_rejected(tmp_path: Path, stage: str) -> None:
    root = write_project(tmp_path, plan=plan_with(staged("model", stage)))
    assert any("execution stage" in finding.lower() for finding in integrity_findings(root))


def test_model_cannot_hide_a_delivery_prerequisite(tmp_path: Path) -> None:
    model = staged("model").replace(
        "- Dependencies: none.", "- Requires: `engine`\n- Dependencies: none."
    )
    root = write_project(tmp_path, plan=plan_with(model, task_block("engine")))
    assert any("MODEL" in finding and "DELIVERY" in finding for finding in integrity_findings(root))


def test_human_model_prerequisite_is_preserved(tmp_path: Path) -> None:
    model = staged("model").replace(
        "- Dependencies: none.", "- Requires: `owner-choice`\n- Dependencies: none."
    )
    human = staged("owner-choice", status="HUMAN-GATED")
    root = write_project(tmp_path, plan=plan_with(model, human_blocks=(human,)))
    assert integrity_findings(root) == []
    lines = summary_lines(root)
    assert "priority agent task: all waiting on prerequisites" in lines
    assert "priority human task: owner-choice [feature]" in lines
