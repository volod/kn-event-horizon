from pathlib import Path

import pytest

from kn.quality.research_register import main, register_findings
from tests.quality._plan_fixture import plan_with, task_block, write_project

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HEADER = """# Closed Research Register

Every `##` section below this header is one closed question.

```markdown
## `example-task` -- a fenced example is not a section

### Question

- Reopening task: `not-an-open-task`
```

"""
EMPTY_REGISTER = HEADER + "No closed questions yet.\n"


def closed_section(
    identifier: str = "probe-standard", *, reopening: str = "`build-feature`"
) -> str:
    return f"""## `{identifier}` -- does the standard publish a conformance contract

### Question

Can the product claim conformance from public material alone?

### Answer

No. The survey implemented on 2026-01-01 found no normative schema. The record holds the evidence.

```text
remaining units = target / cost per unit
```

### Reopening condition

A published normative schema with an applicable license.

- Reopening task: {reopening}

### Instead

Extra subsections are allowed between the required parts.

### Do not re-run

- Inferring a schema from announcement prose -- the prose names no fields.
"""


VALID_REGISTER = HEADER + closed_section()


def write_register(root: Path, register: str, *, plan: str | None = None) -> Path:
    write_project(root, plan=plan)
    (root / "docs/impl/future-research.md").write_text(register, encoding="utf-8")
    return root


def test_repository_register_agrees_with_the_plan() -> None:
    assert register_findings(PROJECT_ROOT) == []


def test_an_empty_register_with_fenced_examples_passes(tmp_path: Path) -> None:
    assert register_findings(write_register(tmp_path, EMPTY_REGISTER)) == []


def test_a_complete_section_passes_and_may_record_history(tmp_path: Path) -> None:
    assert register_findings(write_register(tmp_path, VALID_REGISTER)) == []


def test_a_human_lane_task_can_own_the_reopening_path(tmp_path: Path) -> None:
    approval = task_block(identifier="approve-input", status="HUMAN-GATED")
    plan = plan_with(task_block(), human_blocks=(approval,))
    register = HEADER + closed_section(reopening="`approve-input`, `build-feature`")

    assert register_findings(write_register(tmp_path, register, plan=plan)) == []


def test_part_headings_are_matched_without_case(tmp_path: Path) -> None:
    register = VALID_REGISTER.replace("### Reopening condition", "### Reopening Condition")

    assert register_findings(write_register(tmp_path, register)) == []


def _swap_question_and_answer(register: str) -> str:
    return (
        register.replace("### Question", "### SWAP")
        .replace("### Answer", "### Question")
        .replace("### SWAP", "### Answer")
    )


@pytest.mark.parametrize(
    ("register", "expected"),
    [
        (
            VALID_REGISTER.replace("## `probe-standard`", "## probe-standard"),
            "section heading must read",
        ),
        (
            VALID_REGISTER.replace(" -- does the standard publish a conformance contract", ""),
            "section heading must read",
        ),
        (HEADER + closed_section("build-feature"), "still an open task"),
        (VALID_REGISTER.replace("### Answer\n", ""), "needs `###` parts"),
        (VALID_REGISTER.replace("### Do not re-run", "### Do not retry"), "needs `###` parts"),
        (_swap_question_and_answer(VALID_REGISTER), "needs `###` parts"),
        (
            VALID_REGISTER.replace(
                "Can the product claim conformance from public material alone?\n", ""
            ),
            "part 'Question' is empty",
        ),
        (HEADER + closed_section(reopening="`missing-task`"), "`missing-task` is not an open"),
        (HEADER + closed_section(reopening="build-feature"), "comma-separated backticked"),
        (HEADER + closed_section(reopening=""), "comma-separated backticked"),
        (VALID_REGISTER + "\n" + closed_section(), "listed twice"),
    ],
)
def test_refused_register_shapes_are_named(tmp_path: Path, register: str, expected: str) -> None:
    findings = register_findings(write_register(tmp_path, register))

    assert any(expected in finding for finding in findings), findings


def test_findings_name_the_section_line(tmp_path: Path) -> None:
    register = HEADER + closed_section("build-feature")
    heading = "## `build-feature` -- does the standard publish a conformance contract"
    line = register.splitlines().index(heading) + 1

    findings = register_findings(write_register(tmp_path, register))

    assert findings == [
        f"docs/impl/future-research.md:{line}: `build-feature`: still an open task "
        "in docs/impl/plan.md; close it or remove the section"
    ]


def test_missing_register_is_reported(tmp_path: Path) -> None:
    write_project(tmp_path)

    assert register_findings(tmp_path) == [
        "missing required document: docs/impl/future-research.md"
    ]


def test_main_exit_status_follows_findings(tmp_path: Path) -> None:
    valid = write_register(tmp_path / "valid", VALID_REGISTER)
    invalid = write_register(tmp_path / "invalid", HEADER + closed_section("build-feature"))

    assert main(["--root", str(valid)]) == 0
    assert main(["--root", str(invalid)]) == 1
