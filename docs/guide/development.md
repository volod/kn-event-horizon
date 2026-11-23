# Development Guide

This guide describes the tooling, documentation checks, and agent adapters that came with the
project template. The project's own product behavior is indexed
under [current implementation](../impl/current.md).

## Setup

The development host needs the commands that `deploy/versions.yaml` lists under
`host_prerequisites`: Git, Make, uv, Docker Engine with the Compose v2 plugin, and a Java 21 or
newer runtime. On Ubuntu, Java is `openjdk-21-jre-headless`. Then run:

```bash
make bootstrap
make doctor
make run
```

`make bootstrap` (alias `make venv`) syncs `.venv` from `uv.lock` with the development extra,
then checks every prerequisite and fails with one message per missing command or too-old version
and its install hint; it never installs system packages. It also installs each archive listed under
`downloaded_tools`, today Apache Jena 6.3.0, into `DATA_DIR/tools/`, only when the download matches
the pinned SHA-512. A marker file records that checksum, and a directory without it is never
reused. `make doctor` repeats the checks without installing anything. GitHub Actions installs with
`uv sync` and runs only the unit gate, so it needs neither Docker nor Java.

To move Jena to a new release, verify the new archive against the release manager's key in
`https://downloads.apache.org/jena/KEYS` and its `.sha512` file, then change `version`, `archive`,
`sha512`, `install_dir` and `pinned` together and run `make bootstrap`.

The lockfile is committed. After changing dependencies in `pyproject.toml`, run `make lock` and
include the resulting `uv.lock` change.

## Quality workflows

`make ci` is the required fast gate. GitHub Actions runs its explicit alias, `make ci-github`, on
Python 3.12 and 3.13 after `uv sync --locked --extra dev`. It checks formatting, Ruff rules, mypy,
complexity, shell scripts, documentation links, specification and plan integrity, message catalogs,
and tests. `make catalog-check` checks interface key coverage and CLI literals; see
[localization](../impl/current/localization.md#verification).
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
placement, lane statuses, required metadata, human-lane registry order, and forward-only language.
`plan_dependencies.py` checks open task references across both lanes for unknown IDs, cycles, and
required work that depends on optional work. `plan_order.py` rejects prerequisites placed after
their same-lane dependents, including ancestors reached through the other lane. Each agent group
must end with an audit covering all open members. Cross-group consumers must wait for the producer audit.

`make plan-status` and `kn-plan` count tasks by lane, status and stage. They first filter
open prerequisites, then select required before optional work in written order. Contributors
verify external inputs and authorization. The [contract workflow](schema-first-development.md)
describes the per-group fixture and integrated release checks.

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

Run `make contract-check` to validate the bundled open contracts and compare the committed
`generated/contracts/` output byte for byte, and `make contract-compile` to refresh that output
(schemas, DDL, Pydantic models and dbt sources) after a contract or generator change. Review and
commit the `generated/` diff with the change.
The SATCOM example belongs to the existing space domain: `make satcom-validate` checks the
owner-provided package and `make satcom-import` archives and imports it into the governed database.

Development edits contract version `1.0.0` and one Alembic baseline in place. If a definition
changes, explicitly set `KN_ENVIRONMENT=development`, run `make db-rebuild`, and backfill with
`make satcom-import`. Rebuild recreates all KN schemas and removes obsolete KN tables; external
dependencies refuse atomically. See the [rebuild reference](../impl/current/data-contracts/rebuild.md)
for the reviewed seed hook and boundaries. `make seed-import` stages vocabulary changes for review;
`make seed-check` checks them against the packaged files and fixtures. See the
[seed reference](../impl/current/ontology-taxonomy/seeds.md). Released environments refuse rebuild.
First release
freezes the baseline;
later schema changes use reviewed Python Alembic revisions and separate contract versions.
See [data contracts](../impl/current/data-contracts.md) for preservation rules and current limits.

## Bilingual acceptance workflow

Run `make test-bilingual` for the delivered CLI, catalogs, multilingual selection, and lossless
source archive/import checks. Each run writes evidence under `$DATA_DIR/e2e/bilingual-<run-id>/`.
Run `make bilingual-acceptance` for the full release gate; it fails while any operator surface lacks
acceptance evidence, even if the available checks pass. See
[localization coverage](../impl/current/localization.md#bilingual-acceptance) for artifacts and
remaining paths. Both targets honor `.env` and `DATA_DIR` using the normal Make resolution.

Review expected output changes in `tests/e2e/fixtures/cli.json`; do not automatically regenerate
goldens to hide a regression. Keep fixture files and reports ASCII with escaped Unicode. Source
text decodes to Unicode and its original bytes must remain intact in archives. Missing data
translations exercise fallback; missing interface keys must still fail the catalog gate.
