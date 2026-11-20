# 0001 Personalize Template Project

## Work contract

Original task from the [forward plan](../plan.md), copied before editing:

```markdown
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
```

## Implementation and decisions

Status: accepted.

Resolved identity:

- Repository `volod/kn-event-horizon` from `origin`; description "A domain knowledge aggregator"
  from the GitHub repository metadata (`gh` was not installed, so the public GitHub API was read).
- The owner chose the display name `KN Event Horizon`, the import package `kn`, and the commands
  `kn` and `kn-plan`. These match the operator CLI `kn` named in the draft design package under
  `docs/design/Knowledge_Awareness_Platform_Codex_Package/`, which was untracked owner work at the
  time. That package was read but left unchanged and is not linked from tracked docs.
- Distribution `kn-event-horizon`, built as `kn_event_horizon-0.1.0`.

Changes:

- Moved `src/agent_py/` to `src/kn/` and updated imports, tests, `DISTRIBUTION_NAME`, the CLI
  `prog`, module docstrings, mypy `files`, coverage `source`, Make targets, and both
  `[project.scripts]` entries.
- `pyproject.toml`: name, description, keywords, and repository URLs now point to the GitHub
  repository instead of the `example.com` placeholders.
- The starter shell prefix `apy_` became `kn_` in `scripts/shared/common.sh`, the Makefile,
  `AGENTS.md`, the README, and the development guide.
- The README describes the project and its own setup; the template setup instructions were removed.
- The spec title, purpose (previously starter text), source paths, project-identity section, and
  registry row now describe the project. Its scope, evaluation, and planning rules are unchanged.
- Added [product core](../current/product-core.md), linked from the
  [areas index](../current.md#areas). The development guide's starter identity section now
  links there.
- Retired the template-only `test_repository_plan_starts_with_template_personalization`. It was
  replaced by `test_repository_plan_is_valid_and_schedulable`, which still covers the repository
  plan without pinning its contents. `tests/test_cli.py` now asserts `(kn)` instead of the trivially
  true substring `kn`.

## Acceptance evidence

Status: accepted.

| Gate | Command | Result |
| --- | --- | --- |
| Lockfile | `make lock`, `make bootstrap` | `agent-python-project` removed, `kn-event-horizon 0.1.0` installed |
| Installed import | `make doctor` | `kn-event-horizon` |
| Installed CLI | `make run` | `kn-event-horizon 0.1.0 (kn)` |
| Renamed plan command | `.venv/bin/kn-plan` | plan summary printed; no `agent-py*` scripts remain in `.venv/bin` |
| Build | `make build` | `kn_event_horizon-0.1.0.tar.gz` and `kn_event_horizon-0.1.0-py3-none-any.whl` |
| Required gate | `make ci` on the final tree | pass: format, lint, mypy, complexity, shell, 0 broken links, 0 spec-plan and register findings, 59 tests |
| Coverage | `make coverage` | 96.90% (floor 90%) |
| Markdown | `pymarkdown scan` over tracked and new Markdown | pass |
| Description | README first line and `pyproject.toml` | both "A domain knowledge aggregator" |
| Starter-name audit | grep for `agent_py`, `agent-py`, `agent python`, `apy_`, `example.com`, `OWNER/REPO` | no active references; remaining hits are this record and the external-link fixture in `tests/quality/test_doc_links.py` |

`make quality` fails at `lint-md` only because `pymarkdown scan -r docs` also reads the untracked
draft design package, which reports 119 style findings. Every tracked file passes. Fixing or
excluding that package is up to its owner.

Initial `make plan-status`:

```text
tasks: 1
agent lane: 1
human lane: 0
statuses: CLEAR=1
priority agent task: personalize-template-project [project-identity]
priority human task: none
```

Final `make plan-status`:

```text
tasks: 0
agent lane: 0
human lane: 0
priority agent task: none
priority human task: none
```

## Handoff

Task counts went from 1 (agent 1, human 0) to 0. `project-identity` stays `shipped`, and its
registry row now links [product core](../current/product-core.md). No other tasks had `Requires`
on this task. Next: bring the knowledge-aggregation design into the specification as registered
capabilities with evaluations, then plan its tasks.
