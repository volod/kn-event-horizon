"""The written agent lane follows dependencies and the schema-first execution stages."""

from pathlib import Path

import pytest

from kn.quality.plan_integrity import integrity_findings
from tests.quality._plan_fixture import plan_with, task_block, write_project


def _requires(block: str, identifier: str) -> str:
    return block.replace(
        "- Dependencies: none.", f"- Requires: `{identifier}`\n- Dependencies: none."
    )


def test_a_later_agent_prerequisite_is_rejected(tmp_path: Path) -> None:
    dependent = _requires(task_block("dependent"), "foundation")
    plan = plan_with(dependent, task_block("foundation"))
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any(
        "dependent" in item and "foundation" in item and "before" in item for item in findings
    )


def test_prerequisite_order_crosses_capability_groups(tmp_path: Path) -> None:
    dependent = _requires(task_block("dependent", capability="foundation"), "model")
    plan = plan_with(task_block("model")).replace(
        "### Feature", f"### Foundation -- `foundation`\n\n{dependent}\n### Feature", 1
    )
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any("dependent" in item and "model" in item and "before" in item for item in findings)


def test_agent_prerequisite_through_a_human_gate_must_also_come_first(tmp_path: Path) -> None:
    dependent = _requires(task_block("dependent"), "approval")
    approval = _requires(task_block("approval", status="HUMAN-GATED"), "prepare")
    plan = plan_with(dependent, task_block("prepare"), human_blocks=(approval,))
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any("dependent" in item and "prepare" in item and "before" in item for item in findings)


@pytest.mark.parametrize("optional", [False, True])
def test_model_after_delivery_in_the_same_class_is_rejected(tmp_path: Path, optional: bool) -> None:
    delivery = task_block("delivery", optional=optional)
    model = task_block("model", optional=optional).replace(
        "- Dependencies: none.", "- Execution stage: MODEL\n- Dependencies: none."
    )
    findings = integrity_findings(write_project(tmp_path, plan=plan_with(delivery, model)))
    assert any("agent task order" in item and "MODEL" in item for item in findings)


def test_required_work_after_another_capability_optional_task_is_rejected(tmp_path: Path) -> None:
    optional = task_block("optional", capability="foundation", optional=True)
    plan = plan_with(task_block()).replace(
        "### Feature", f"### Foundation -- `foundation`\n\n{optional}\n### Feature", 1
    )
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any("agent task order" in item and "required" in item for item in findings)


def test_human_gates_stay_in_their_lane_without_becoming_agent_authorization(
    tmp_path: Path,
) -> None:
    dependent = _requires(task_block("dependent"), "approval")
    human = task_block("approval", status="HUMAN-GATED")
    root = write_project(tmp_path, plan=plan_with(dependent, human_blocks=(human,)))
    assert integrity_findings(root) == []


def test_human_capability_groups_still_follow_the_registry(tmp_path: Path) -> None:
    human = task_block("approval", status="HUMAN-GATED")
    earlier = task_block("foundation-approval", capability="foundation", status="HUMAN-GATED")
    plan = plan_with(task_block(), human_blocks=(human,))
    plan += f"\n### Foundation -- `foundation`\n\n{earlier}"
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any("Human-Assisted Tasks" in item and "registry order" in item for item in findings)
