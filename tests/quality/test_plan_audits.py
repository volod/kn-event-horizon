"""Group closure and consumer handoffs are enforced as tasks leave the plan."""

from pathlib import Path

from kn.quality.plan_integrity import integrity_findings
from tests.quality._plan_fixture import audit_block, plan_with, task_block, write_project


def test_group_without_closing_audit_is_rejected(tmp_path: Path) -> None:
    plan = plan_with(task_block()).replace(audit_block("feature", ("build-feature",)), "")
    assert any("end the group" in f for f in integrity_findings(write_project(tmp_path, plan=plan)))


def test_audit_must_wait_for_the_measured_run(tmp_path: Path) -> None:
    plan = plan_with(task_block("run", status="RUN NEEDED")).replace("- Requires: `run`\n", "")
    findings = integrity_findings(write_project(tmp_path, plan=plan))
    assert any("audit must require run" in finding for finding in findings)


def test_cross_lane_consumer_needs_reviewed_producer(tmp_path: Path) -> None:
    approval = task_block("approve", status="HUMAN-GATED") + "\n- Requires: `produce`\n"
    plan = plan_with(task_block("produce"), human_blocks=(approval,))
    consumer = task_block("consume") + "\n- Requires: `approve`\n"
    plan = plan.replace(
        "## Human-Assisted Tasks",
        "### Use -- `use`\n"
        + consumer
        + audit_block("use", ("consume",))
        + "\n## Human-Assisted Tasks",
    )
    root = write_project(tmp_path, plan=plan)
    assert any("require producer audit" in f for f in integrity_findings(root))
    path = root / "docs/impl/plan.md"
    path.write_text(
        plan.replace("Requires: `approve`", "Requires: `approve`, `feature-implementation-audit`")
    )
    assert integrity_findings(root) == []


def test_last_open_audit_can_run_after_members_leave(tmp_path: Path) -> None:
    plan = (
        plan_with(task_block())
        .replace(task_block(), "")
        .replace("- Requires: `build-feature`\n", "")
    )
    assert integrity_findings(write_project(tmp_path, plan=plan)) == []
