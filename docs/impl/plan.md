# Agent Python Project Implementation Plan

Forward-only: this file describes work that remains. Available behavior and durable results belong
in [current-state documentation](current.md). Product behavior and evaluation belong in the
[specification](../design/spec.md). Research questions that stopped, with what would reopen them,
belong in the [closed-research register](future-research.md).

Every task serves a capability from the
[capability registry](../design/spec.md#capability-registry). Capability groups follow registry
order in both lanes. Prefer required work whose start prerequisites are satisfied.

Task fields, statuses, ordering, and the capability-gap lifecycle are defined in the
[planning workflow](../guide/planning-workflow.md). Run `make plan-status` to view lane counts and
the highest-priority candidate in each lane after filtering open task prerequisites. Check its
external and manual dependencies before starting.

## Agent Implementation Tasks

### Project identity -- `project-identity`

#### personalize-template-project

Personalize a new GitHub repository created from this template before starting product work.

- Serves: `project-identity` -- [Project identity](../design/spec.md#project-identity)
- Agent status: CLEAR
- Dependencies: A checkout of the new repository and a project name and short description. Use
  the owner's explicit choices and project-specific details already in the spec or README. Treat
  starter placeholders as missing. Identify the new repository and its slug from `origin` and
  fill gaps from its GitHub metadata, available on the repository page or via
  `gh repo view OWNER/REPO --json name,description,url`. A repository slug and a display name can
  differ. Ask the owner only for details that remain missing or ambiguous.
- User-visible outcome: The README describes the new project, and the installed package and
  commands use its identity.
- Scope boundary: Update starter names, URLs and links, setup examples, and repository layout.
  Replace the template setup instructions in the README with the project's own setup. Keep existing
  product requirements, planning rules, and quality gates. This task covers identity and packaging.
- Data and artifact paths: `src/agent_py/`, `tests/`, `pyproject.toml`, `uv.lock`, `Makefile`,
  `README.md`, `AGENTS.md`, `docs/`, and any other tracked scripts or configuration with
  project-specific references. Use the
  [record file naming rules](../guide/planning-workflow.md#record-file-naming)
  to name and index the task record under `docs/impl/records/`.
- Execution path: Capture the initial `make plan-status` counts and open a task record before
  editing. Use the resolved project name to choose a valid distribution name, a non-keyword Python
  import name, and CLI names for both entry points. Move `src/agent_py/` and update imports,
  metadata, tests, coverage and mypy settings, Make targets, agent instructions, and docs. Use the
  actual repository URL for repository links and update links to moved paths and renamed headings.
  Use the resolved description for the README and package metadata, and use it for the spec purpose
  if the spec still contains starter text. Regenerate the lockfile with `make lock` and install
  with `make bootstrap`.
- Acceptance gates: Audit tracked files for starter names and URLs. Replace active references and
  preserve historical evidence in task records. Verify the installed import and CLI with
  `make doctor` and `make run`, run the renamed plan command, and pass `make build`. Verify the
  README and package metadata agree on the project description. Document the resulting identity in
  a new `current/product-core.md` page linked from the [areas index](current.md#areas), point the
  `project-identity` registry row at it, and replace the
  [starter identity](../guide/development.md#starter-identity) section of the development guide
  with a link to it. Follow the
  [completion workflow](../guide/planning-workflow.md#completion-transition) to record the evidence
  and plan counts. When removing this task, retire the template-only assertion in
  `tests/quality/test_plan_summary.py` that expects it as the first task, then run `make ci` on the
  resulting tree. If the identity remains unresolved, identify the missing input and leave the task
  open.
- Documentation target: A new `current/product-core.md` page listed in the
  [areas index](current.md#areas).

## Human-Assisted Tasks

No open human-gated tasks. Add work here when acceptance requires human judgment, authorization,
private access, or spending authority.
