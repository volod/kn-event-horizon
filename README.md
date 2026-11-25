# KN Event Horizon

A domain knowledge aggregator. KN Event Horizon is intended to collect evidence about industrial
and technology domains from public or legitimately licensed sources, normalize it into domain
knowledge models, and keep the provenance and history of each fact. Product capabilities enter
through the [specification](docs/design/spec.md) before they are planned and built.

The repository currently provides the typed `kn` package and its `kn` command, a local PostgreSQL
and PostGIS service, a locked development environment, and shared rules for planning,
implementation, and verification.

## Setup

With Git, Make, uv, Docker Engine with Compose v2, and Java 21 or newer installed (the
[development guide](docs/guide/development.md#setup) lists them):

```bash
git clone https://github.com/volod/kn-event-horizon.git
cd kn-event-horizon
make bootstrap
make doctor
make run
make plan-status
```

`make run` calls `kn info`, which reports the installed distribution, version, and import package.
`make plan-status` (or `kn-plan`) counts open work and shows the next task in each lane.

## Daily commands

| Command | Purpose |
| --- | --- |
| `make help` | List supported workflows |
| `make bootstrap` | Create or update the locked development environment |
| `make run` | Run `kn info` |
| `make test` | Run the lightweight unit tests, the set that GitHub Actions runs |
| `make test-integration` | Run the database integration tests locally against the database from `make db-up` |
| `make coverage` | Run tests with the coverage gate |
| `make format` | Apply Ruff formatting |
| `make ci` | Run required local and CI checks |
| `make ci-local` | Run `make ci`, every local-only test (database and heavy tests), and `make skos-reference-check`; start `make db-up` first |
| `make skos-reference-tools` | Install the pinned Java 21 runtime and Apache Jena that `make skos-reference-check` runs |
| `make skos-reference-check` | Validate every SKOS export with the pinned Apache Jena RIOT |
| `make quality` | Run CI checks, coverage, Markdown lint, and package build |
| `make db-up` | Start the local PostgreSQL and PostGIS service on `127.0.0.1:15432` and wait until it is healthy |
| `make db-down` | Stop the database service and keep its data |
| `make db-reset` | Delete the local database volume and start from empty |
| `make db-verify` | Probe the database schemas, roles, and privileges |
| `make plan-status` | Count tasks and show lane priorities after checking open-task prerequisites |
| `make lint-spec-plan` | Check the capability registry, plan, and closed-research register |
| `make lint-doc-links` | Check relative Markdown files and anchors |
| `make quality-report` | Report files over the soft size limit |

Use Make targets for repeatable workflows. Direct `uv` debugging should first source
`scripts/shared/common.sh` and run `kn_load_env` so cache and link behavior follows `.env`.

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
src/kn/                    production package and kn CLI
tests/                     unit, governance, and database integration tests
domains/                   domain packages; seeds/proposals/ holds the converted workbooks
deploy/                    Compose stack, service configuration, and the version manifest
docs/design/               product specification and domain design pages
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
