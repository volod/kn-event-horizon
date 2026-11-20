# Agent Python Project

A GitHub template for Python projects that use coding agents. It includes a typed starter package,
an `agent-py` command, a locked development environment, and shared rules for planning,
implementation, and verification.

## Start a project from this template

On GitHub, choose **Use this template** and then **Create a new repository**. Enter the new
repository name and a short project description, then click **Create repository from template**.
[GitHub template instructions](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)

With Git, Make, and uv installed, substitute your new repository's owner and name below.

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
make bootstrap
make plan-status
```

### Give your agent the first task

Open your coding agent in the new checkout and give it this prompt to start
[`personalize-template-project`](docs/impl/plan.md#personalize-template-project).

> Read `AGENTS.md` and complete `personalize-template-project` from `docs/impl/plan.md` before
> starting product work. Resolve the project name and description from the existing spec or the
> new GitHub repository's metadata.
> Ask me for any missing details or conflicting choices. Rename the starter package, commands, and
> their references, then verify the result and close the task through its record.

The task covers the distribution, imports, CLI entry points, lockfile, tests, tooling, and active
documentation links. The agent updates the README for the new project and checks the installed
package and commands.

## Daily commands

| Command | Purpose |
| --- | --- |
| `make help` | List supported workflows |
| `make bootstrap` | Create or update the locked development environment |
| `make run` | Run the starter CLI |
| `make test` | Run the unit test suite |
| `make coverage` | Run tests with the coverage gate |
| `make format` | Apply Ruff formatting |
| `make ci` | Run required local and CI checks |
| `make quality` | Run CI checks, coverage, Markdown lint, and package build |
| `make plan-status` | Count tasks and show lane priorities after checking open-task prerequisites |
| `make lint-spec-plan` | Check the capability registry, plan, and closed-research register |
| `make lint-doc-links` | Check relative Markdown files and anchors |
| `make quality-report` | Report files over the soft size limit |

Use Make targets for repeatable workflows. Direct `uv` debugging should first source
`scripts/shared/common.sh` and run `apy_load_env` so cache and link behavior follows `.env`.

## Documentation model

| What you need | Where to look |
| --- | --- |
| Product intent, capability boundaries, and evaluation | [Specification](docs/design/spec.md) |
| Remaining work, ordered by capability | [Forward plan](docs/impl/plan.md) |
| Available behavior and how to verify it | [Current implementation](docs/impl/current.md) |
| Original task contracts, decisions, and acceptance evidence | [Task records](docs/impl/records/README.md) |
| Research questions already closed, and what would reopen them | [Closed-research register](docs/impl/future-research.md) |

Define new capabilities and their evaluation in the specification before adding plan tasks.
For planned work, check the prerequisites and open a record with the original task before editing.
At acceptance, capture the check results and before and after plan counts in that record, update
the owning current-state page, and remove the accepted task from the forward plan. Update the
capability registry and any dependent tasks as needed. [Planning workflow](docs/guide/planning-workflow.md)

## Agent support

Keep shared rules for starting work, editing code, and verifying changes in the root policy.
Codex and Cursor read it directly. [AGENTS.md](AGENTS.md)

Claude Code imports the root policy, and Gemini's entry file directs contributors to it.
Keep these files focused on their integration. [CLAUDE.md](CLAUDE.md), [GEMINI.md](GEMINI.md),
[Agent integration details](docs/guide/development.md#agent-instructions)

## Layout

```text
src/agent_py/              production package
tests/                     unit and governance tests
docs/design/               product specification
docs/impl/plan.md          forward-only work
docs/impl/current/         delivered behavior
docs/impl/records/         task contracts and acceptance evidence
docs/guide/                contributor workflows
scripts/shared/            shared shell environment helpers
.github/workflows/         required CI
```

Runtime output belongs under `$DATA_DIR/<method>/<run-id>/`, which defaults to `.data/` and is
ignored by Git.

## License

MIT. See [LICENSE](LICENSE).
