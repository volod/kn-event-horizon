# Development Guide

This guide describes the tooling, documentation checks, and agent adapters that came with the
project template. The project's own product behavior is indexed
under [current implementation](../impl/current.md).

## Setup

Install Git, Make, and uv, then run:

```bash
make bootstrap
make doctor
make run
```

The lockfile is committed. After changing dependencies in `pyproject.toml`, run `make lock` and
include the resulting `uv.lock` change.

## Quality workflows

`make ci` is the required fast gate. GitHub Actions runs its explicit alias, `make ci-github`, on
Python 3.12 and 3.13 after `uv sync --locked --extra dev`. It checks formatting, Ruff rules, mypy,
complexity, shell scripts, documentation links, specification and plan integrity, and tests.
GitHub Actions runs only lightweight unit tests: no test there needs a service endpoint, large
memory, or a long run time. Tests that do carry the `integration` or `heavy` marker and run only on
the development host, through `make test-integration` or `make ci-local`, which runs `make ci` and
then every local-only test against the database from `make db-up`. A plan gate that names CI for
such a test is met by `make ci-local`. See
[where tests run](../impl/current/runtime-platform.md#where-tests-run).

`make quality` adds branch coverage, Markdown style, and source/wheel builds. Run it before release
or after changing project infrastructure. `make quality-report` reports files over the 250-line soft
limit without turning cohesion into a numeric failure.

## Direct uv commands

Make targets are the stable workflow. For one-off dependency debugging:

```bash
source scripts/shared/common.sh
kn_load_env
uv <command>
```

This resolves `DATA_DIR`, moves supported tool caches with it, and avoids cross-filesystem link
warnings.

## Runtime artifacts

Write generated data under `$DATA_DIR/<method>/<run-id>/`. Use a stable method name and a unique run
id. Keep fixtures under `tests/` only when they are small, deterministic, safe to publish, and
required for CI.

`.env.example` declares `DATA_DIR=.data`, and relative values resolve against the project root.
A `DATA_DIR` in `.env` wins over the environment. The `Makefile` resolves it through `kn_load_env`,
so Ruff, mypy, pytest, and complexipy caches stay below the same root as the database volume, also
when the path contains spaces. `.gitignore` excludes runtime
artifacts, local environments, secrets, caches, and root build outputs without hiding same-named
source subpackages.

## Project identity

The distribution, import package, and commands are described in
[product core](../impl/current/product-core.md).

## Documentation checks

`plan_model.py` reads the capability registry and task metadata. `plan_integrity.py` checks group
placement, lane statuses, required metadata, registry order, and forward-only language.
`plan_dependencies.py` checks open task references across both lanes for unknown IDs, cycles, and
required work that depends on optional work.

`make plan-status` and `kn-plan` use `plan_summary.py`. They count work and surface lane
priority after filtering tasks whose explicit prerequisites are still open. Contributors verify
manual prerequisites before taking a task.

`make lint-spec-plan` also runs `research_register.py` over the
[closed-research register](../impl/future-research.md). It reports, with the register line:

- a `##` heading that is not a backticked task id followed by ` -- ` and the question;
- a section whose id is still an open task in the plan, or appears twice;
- a missing, repeated, out-of-order, or empty `Question`, `Answer`, `Reopening condition`, or
  `Do not re-run` part. Part headings match without case, and extra `###` subsections are allowed;
- a `- Reopening task:` line that is not a list of backticked IDs, or that names a task not open in
  either plan lane. When the owning task leaves the plan, the check fails until the section is
  updated.

Fenced examples are ignored, so the register header can show the section shape. The plan's
forward-language check does not read the register, which records history by design, and
`make plan-status` does not read it either. Reviewers judge whether a reopening condition is a
number or a change in the world.

`make lint-doc-links` uses `doc_links.py` to validate relative links and heading anchors before a
Git commit is required. Fixtures in `tests/quality/` exercise the failure cases of every check,
including invalid task graphs, cross-lane scheduling, and refused register shapes, rather than only
asserting that the repository passes.

## Agent instructions

[AGENTS.md](../../AGENTS.md) contains shared rules and points agents to the relevant workflow.
Use repository checks to enforce testable rules and keep detailed procedures in this guide.

- Codex discovers the root policy and supports discovery of narrower instructions along the
  working-directory path. [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Claude Code expands the `@AGENTS.md` import in [CLAUDE.md](../../CLAUDE.md).
  Use `/memory` to inspect loaded instructions. [Claude Code memory](https://code.claude.com/docs/en/memory)
- Cursor Agent uses the root policy directly. Projects copied from the template can add scoped
  project rules for directory-specific guidance. [Cursor rules](https://cursor.com/docs/rules)
- [GEMINI.md](../../GEMINI.md) routes Gemini contributors to the shared policy.

## Contract and space example workflow

Run `make contract-check` to validate the bundled open contracts and artifact digests, and
`make contract-compile` to inspect generated schemas under `$DATA_DIR/contract/current/`.
The SATCOM example belongs to the existing space domain: `make satcom-validate` checks the
owner-provided package and `make satcom-import` archives and imports it into the governed database.

Development edits contract version `1.0.0` and one Alembic baseline in place. If a definition
changes, explicitly set `KN_ENVIRONMENT=development`, run `make db-rebuild`, and backfill with
`make satcom-import`. Released environments refuse rebuild. First release freezes the baseline;
later schema changes use reviewed Python Alembic revisions and separate contract versions.
See [data contracts](../impl/current/data-contracts.md) for preservation rules and current limits.
