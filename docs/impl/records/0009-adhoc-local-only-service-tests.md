# Record 0009: local-only service tests

## Work contract

Direct request, 2026-11-21, after [record 0008](0008-runtime-platform-database-integration-harness.md)
was accepted in the same uncommitted change:

> please split test for local run and for github environment. in github environment should be
> runned only lightweight unit tests that does not requires service endpoint or memory and time
> resources

Scope: GitHub Actions runs only lightweight unit tests. Tests that need a service endpoint, large
memory, or a long run time run only on the development host. The specification, the plan, the
project rules, and the current-state pages state the same split.

## Implementation and decisions

The [where tests run section](../current/runtime-platform.md#where-tests-run) of the runtime
platform page describes the delivered behavior.

| Decision | Reason |
| --- | --- |
| The `integration` job and its service container left `.github/workflows/ci.yml`; the workflow is the committed one again, with the `quality` job alone | GitHub runs no test that needs a service endpoint. The workflow stays as it was before record 0008. |
| `kn_db_prepare_container`, `kn_db_set_password`, `KN_DB_BOOTSTRAP_HOST_SQL`, and the `KN_DB_CONTAINER` branch of `kn_db_psql` were removed with their tests | Only the CI service container used them, so they would be dead code. `tests/scripts/test_common_db.py` is the committed file again plus the `kn_db_test_env` tests; `tests/scripts/_db_shell.py` and `tests/scripts/test_common_db_integration.py` are gone. The `deploy/versions.yaml` comment is the committed one again. |
| A registered `heavy` marker beside `integration` | The request also excludes tests that need large memory or a long run time. Under `--strict-markers` an unregistered marker fails, so later tasks can mark such tests without changing the gates. No test is marked `heavy` yet. |
| `make test`, `make coverage`, and so `make ci` and `make ci-github` select `not integration and not heavy` | One selection for the GitHub set, also used locally, so a test that passes `make ci` passes on GitHub. |
| `make ci-local` runs `make ci`, then `integration or heavy` against the database from `make db-up` | One local entry point for every test. `make test-integration` stays for the database tests alone. Both share the `LOCAL_PYTEST` recipe of the `Makefile`. |
| `make ci` stays the required gate and needs no Docker | Plan tasks require `make ci` to pass without Docker, for example `inventree-test-service`. |
| The selections are defined in `tests/conftest.py` and the `Makefile`, and `tests/deploy/test_ci_workflow.py` reads the targets with `make -n` | The test checks that the two definitions agree and what the targets actually run, not the Makefile text. |
| A plan gate that names CI for a test that needs a service, large memory, or a long run time is met by `make ci-local` | The user said earlier that "passes in CI" means the local tests. `AGENTS.md`, the development guide, and the runtime platform page state it. |

Specification and plan changes:

- [Runtime platform](../../design/spec.md#runtime-platform): integration tests run on the
  development host and GitHub Actions runs no database test. The evaluation and the registry row
  say "on the development host" instead of "in CI".
- [Reproducible environment](../../design/spec.md#reproducible-environment): GitHub Actions runs
  only lightweight unit tests, and the rest runs through `make ci-local`.
- [Ingestion engine](../../design/spec.md#ingestion-engine), TDD growth rule: `make ci-local`,
  not CI, runs every source fixture suite and the full rebuild.
- `rebuild-from-raw`: its scope and gate name `make ci-local` for the rebuild, and `make ci` stays
  green without a database.
- `runtime-platform-implementation-audit`: the focus "CI parity with local runs" became the split
  between the GitHub unit gate and the local-only tests.

Other plan gates that name CI, such as checksum, key-coverage, drift, and version-bump checks, are
lightweight unit checks and were not changed.

## Acceptance evidence

Status: accepted, 2026-11-21. Docker Engine 29.9.3, Compose v5.7.1, Linux x86_64, Python 3.12.3
and 3.13.18. Scripts and logs are in `$DATA_DIR/acceptance/adhoc-local-only-service-tests-20261121/`:
`gates.sh` with `gates.log`, `mutations.sh` with `mutations.log`, and the logs they name.

| Gate | Evidence | Result |
| --- | --- | --- |
| GitHub runs only lightweight unit tests | Fresh copy of the tracked and untracked, not ignored files; for 3.12 and 3.13, `uv sync --locked --extra dev --python <version>`, then `make ci-github PYTHON_VERSION=<version>` | exit 0 each, `129 passed, 10 deselected`, without Docker or a database |
| The unit set needs no service, memory, or time | `make test` under `/usr/bin/time`, and `--durations=5`, with the database stopped | `129 passed, 10 deselected`; wall 1.52 s, peak RSS 49232 KB; the slowest test 0.20 s, a pytest subprocess on a socket directory without a socket |
| `make ci` without a database | database stopped | exit 0; `129 passed, 10 deselected` |
| Coverage floor | `make coverage` | 96.76 % against the 90 % floor |
| Every test locally | `make db-up`, then `make ci-local` | exit 0; `129 passed, 10 deselected`, then `10 passed, 129 deselected`; afterwards no `kn_test_*` schema and 0 advisory locks |
| Database tests alone | `make test-integration` | `10 passed, 129 deselected` |
| Local gate without a database | `make ci-local` with the database stopped | exit 2 after the unit tests passed; `cannot connect to the integration database postgres@127.0.0.1:15432/kn` with the `make db-up` hint |

Mutation checks. Each fault was applied alone, the named test failed, and the file was restored:

| Fault | Failing test |
| --- | --- |
| A `services` block in the workflow | `test_no_github_job_starts_a_service_or_a_job_container` |
| A workflow step `make test-integration`, or `make ci-local` instead of `make ci-github` | `test_github_jobs_run_only_the_locked_install_and_the_github_gate` |
| `UNIT_TESTS` without `not heavy`, or `make ci` depending on `test-integration` | `test_the_github_gate_runs_only_the_lightweight_unit_tests` |
| `make ci-local` running `-m integration` only | `test_the_local_gate_adds_the_local_only_tests` |
| `UNIT_SELECTION` without `not heavy`, or the `heavy` marker not registered | `test_unit_runs_deselect_a_heavy_test` |

Other checks: `make quality` exit 0, `make quality-report` lists no file over 250 lines,
`git diff --check` is clean, and the changed files are ASCII only. The unit suite went from 133 to
129 tests: 13 tests of the CI container and its workflow left, and 4 `kn_db_test_env` cases, 4
workflow guards, and the `heavy` deselection test were added.

## Handoff

Plan counts before and after: 117 tasks (106 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR
98, HUMAN-GATED 9, RUN NEEDED 8. No task was added or removed, and no registry status changed.
Capabilities affected: `runtime-platform` (shipped), `reproducible-environment` (shipped), and
`ingestion-engine` (planned), by the specification text above.

Notes for later tasks:

- A test that needs a service endpoint uses the `integration_database` fixture or lives under
  `tests/integration/`. A test that needs large memory or a long run time carries
  `@pytest.mark.heavy`. Both stay out of GitHub Actions without further changes.
- A task that adds a GitHub Actions job or step must update `tests/deploy/test_ci_workflow.py`, which
  allows only `uv sync` and `make ci-github`.
