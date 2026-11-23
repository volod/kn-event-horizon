from pathlib import Path

SPEC = """# Design

## Capability Registry

| # | Capability | Status | How it is evaluated | Implementation |
| --- | --- | --- | --- | --- |
| 1 | `foundation` | shipped | Fresh setup passes | [Foundation](../impl/current.md) |
| 2 | `feature` | planned | Fixture behavior passes | - |
"""


def task_block(
    identifier: str = "build-feature",
    *,
    capability: str = "feature",
    status: str = "CLEAR",
    optional: bool = False,
) -> str:
    suffix = " (optional)" if optional else ""
    return f"""#### {identifier}{suffix}

Describe future product behavior.

- Serves: `{capability}` -- [Feature](../design/spec.md#feature)
- Agent status: {status}
- Dependencies: none.
- User-visible outcome: A user can exercise the feature.
- Scope boundary: The fixture path only; deployment is outside scope.
- Data and artifact paths: `tests/fixtures/` only.
- Execution path: Add a module and deterministic tests.
- Acceptance gates: `make ci` passes or the negative result is recorded.
- Documentation target: [Current state](current.md).
"""


def audit_block(group: str, members: tuple[str, ...], optional: bool = False) -> str:
    block = task_block(f"{group}-implementation-audit", optional=optional)
    if members:
        ids = ", ".join(f"`{identifier}`" for identifier in members)
        block = block.replace("- Dependencies:", f"- Requires: {ids}\n- Dependencies:")
    return block


def plan_with(*blocks: str, human_blocks: tuple[str, ...] = ()) -> str:
    agent_content = "\n".join(blocks) if blocks else "No open agent tasks."
    if blocks:
        ids = tuple(block.split()[1] for block in blocks)
        agent_content += "\n" + audit_block(
            "feature", ids, "(optional)" in blocks[0].splitlines()[0]
        )
    human_content = "\n".join(human_blocks) if human_blocks else "No open human tasks."
    return f"""# Plan

## Agent Implementation Tasks

### Feature -- `feature`

{agent_content}

## Human-Assisted Tasks

### Feature -- `feature`

{human_content}
"""


def write_project(root: Path, *, spec: str = SPEC, plan: str | None = None) -> Path:
    (root / "docs/design").mkdir(parents=True)
    (root / "docs/impl").mkdir(parents=True)
    (root / "docs/design/spec.md").write_text(spec, encoding="utf-8")
    resolved_plan = plan if plan is not None else plan_with(task_block())
    (root / "docs/impl/plan.md").write_text(resolved_plan, encoding="utf-8")
    return root
