# Record 0008: database-integration-harness

## Work contract

Original plan task, copied before implementation:

```markdown
#### database-integration-harness

Tests that touch SQL need one repeatable database fixture locally and in CI.

- Serves: `runtime-platform` -- [Runtime platform](../design/spec.md#runtime-platform)
- Agent status: CLEAR
- Dependencies: The pinned PostGIS image from the version manifest and the local service in
  [runtime platform](current/runtime-platform.md). The service publishes its port on `127.0.0.1`
  only (`KN_POSTGRES_HOST_PORT`, default `15432`), so host-run tests connect over TCP with a
  password.
- User-visible outcome: `make test-integration` runs database tests against the Compose service,
  and GitHub Actions runs them against a PostGIS service container.
- Scope boundary: A pytest marker, a fixture that creates and drops a scratch schema set per
  session, and the CI job. No product schemas yet.
- Data and artifact paths: `tests/integration/`, `tests/conftest.py`, `.github/workflows/ci.yml`,
  `Makefile`, `pyproject.toml`, `uv.lock`.
- Execution path: Add psycopg 3 as the justified dependency. Unit tests stay network-free and
  database-free, and integration tests skip with a clear reason when no database is configured.
- Acceptance gates: An integration smoke test passes locally and in CI. `make ci` stays green with
  and without a database. Coverage still meets its floor.
- Documentation target: `current/runtime-platform.md` listed in the
  [areas index](current.md#areas).
```

Prerequisites: the task has no `Requires` entry. `compose-database-service` was accepted in
[record 0006](0006-runtime-platform-compose-database-service.md), and the loopback port in
[record 0007](0007-adhoc-database-loopback-port.md). Docker Engine 29.9.3 with Compose v5.7.1 is
installed on the development host. The host has no `psql` and no `libpq`.

## Implementation and decisions

Later change: [record 0009](0009-adhoc-local-only-service-tests.md) removed the GitHub Actions
`integration` job, the CI container helpers, and their tests at the user's request. Database tests
run only on the development host. The CI rows below describe what this task accepted.

The [integration tests section](../current/runtime-platform.md#integration-tests) of the runtime
platform page describes the delivered behavior. Files: `tests/conftest.py`,
`tests/integration/harness.py`, `tests/integration/test_database.py`, the `integration` job in
`.github/workflows/ci.yml`, the `test-integration` target and the `-m "not integration"` filter
of `test` and `coverage` in the `Makefile`, the pytest options and the psycopg dependency in
`pyproject.toml`, `uv.lock`, the `kn_db_test_env`, `kn_db_set_password`, and
`kn_db_prepare_container` helpers and the `KN_DB_CONTAINER` branch of `kn_db_psql` in
`scripts/shared/common.sh`, and the tests `tests/test_integration_harness.py`,
`tests/deploy/test_ci_workflow.py`, and `tests/scripts/test_common_db_integration.py`.

| Decision | Reason |
| --- | --- |
| `psycopg[binary]>=3.3,<4` in the `dev` extra | Only tests use it. The binary wheel bundles libpq 18, and the host has no libpq. The lock gained `psycopg` 3.3.9, `psycopg-binary` 3.3.9, and `tzdata`, which carries a Windows-only marker. The task that first adds `src/kn/db/` moves it to the runtime dependencies. |
| Configuration through `KN_TEST_DATABASE_URL` and a password file | An explicit KN variable, so a `PGHOST` in a developer shell never selects a database. The password is not in the URL, the environment, or a command line. The shell derives the URL and the file from the same helpers as `make db-up`, so the port and password-path rules exist once. |
| `make test` and `make coverage` deselect `integration`; the marker comes from the directory and from fixture use | The unit suite never connects, whatever the environment holds, and a database test outside `tests/integration/` cannot slip into it. Pytest run directly skips the integration tests with a reason. |
| A configured database that does not answer fails instead of skipping | A broken CI database must not pass by skipping. |
| `make test-integration` does not start the database | Two parallel runs would otherwise apply the bootstrap concurrently. The service lifecycle stays with `make db-up` and `make db-down`, and CI uses the same target. |
| Scratch schemas created on request, isolated by a token and an advisory lock | Each test names the schemas it needs, and later tasks can request the KN schema names. Parallel runs never share a schema, and the next session drops what a killed run left behind. The two-key lock space cannot collide with bigint locks of product code. |
| `lock_timeout` of 10 s on the scratch connection | A test that leaves a connection open makes the teardown fail, not hang. |
| A GitHub Actions service container, with an empty init directory | The plan and the specification name a service container. The empty directory keeps the image's init script out, so the CI database holds what the local one holds. The smoke test checks the extension list; without the directory it fails (measured below). |
| An initialization-only password that the prepare step replaces | A service container's environment cannot take a value that is computed during the job. No committed value authenticates a test, and the new password reaches `psql` on standard input only. |
| `kn_db_psql` honors `KN_DB_CONTAINER` | `kn_db_verify` runs unchanged against the CI container, so there is one way to run `psql`. `kn_db_up` keeps its in-container bootstrap path. |
| The role probe runs in the prepare step, not in pytest | It is a `psql` script. A pytest test that acts as each role belongs to `runtime-platform-implementation-audit`, whose gate names it. |
| The smoke test compares versions and extensions with the manifest | It proves that the tests run on the pinned image and catches a CI database that diverges from the Compose one. |
| The integration job runs on Python 3.12 only | The database behavior does not depend on the Python minor version. The `quality` matrix still covers 3.13. |
| `-rfEs --strict-markers` in the pytest options | Skip reasons are printed, and a misspelled marker fails. |
| Stub helpers of `tests/scripts/test_common_db.py` moved to `tests/scripts/_db_shell.py` | The new helper tests need them, and one file would have passed the 250-line guideline. The move only renames. |

Scope note: the task listed no `scripts/`, `tests/scripts/`, or `tests/deploy/` paths. The helpers
follow the rule that shared shell behavior lives in `scripts/shared/common.sh`, and their tests
follow the rule that behavior changes carry tests. The manifest comment in `deploy/versions.yaml`,
the `README.md` command table, and one sentence of the development guide name the new CI job.

## Acceptance evidence

Status: accepted, 2026-11-21. Docker Engine 29.9.3, Compose v5.7.1, Linux x86_64, Python 3.12.3
and 3.13.18.

Gate reading: the user decided that "passes in CI" means that the jobs of the CI workflow pass on
the development host. A GitHub Actions run is not part of acceptance; the user reports a failure
there with its context. An earlier version of this record kept the task open for that run.

The scripts and logs are kept in `$DATA_DIR/acceptance/database-integration-harness-20261121/`:
`acceptance.sh` with `acceptance.log` and the final rerun `acceptance-rerun.log`,
`ci-rehearsal.sh` and `ci-rehearsal.log`, `ci-simulation.sh` and `ci-simulation.log`,
`ci-simulation-without-empty-initdb.log`, `parallel-1.log` and `parallel-2.log`, the `make ci`
logs with and without the database, and `quality.log`. The rerun repeated every result of the
first run below.

| Gate | Evidence | Result |
| --- | --- | --- |
| Smoke test passes locally | `make db-up`, then `make test-integration` | `10 passed`; afterwards no `kn_test_*` schema and 0 advisory locks |
| Smoke test passes in CI | `ci-rehearsal.sh` copies the tracked and untracked, not ignored files to a fresh directory, as a checkout of the change holds them. Per `quality` matrix version it runs `uv sync --locked --extra dev --python <version>` and `make ci-github PYTHON_VERSION=<version>`. For `integration` it starts a container from the workflow's image, environment, initdb arguments, port `127.0.0.1:15432`, empty init directory, and health options, then runs `kn_db_prepare_container` with `KN_DB_CONTAINER` and `make test-integration` | `quality` 3.12 and 3.13: exit 0, `133 passed, 10 deselected` each. `integration`: `healthy`; the prepare step created the password file and printed `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`; `10 passed, 133 deselected`. The earlier `ci-simulation.sh` run also showed that the initialization-only password is refused after the prepare step |
| `make ci` with a database | Compose database running | exit 0; 133 passed, 10 deselected |
| `make ci` without a database | after `make db-down` | exit 0; 133 passed, 10 deselected |
| Coverage floor | `make coverage` without a database | 96.76 % against the 90 % floor |
| Skip with a clear reason | `pytest tests/integration` without the variables | exit 0; `10 skipped`, each with `no integration database configured: KN_TEST_DATABASE_URL is not set. ...` |

Further checks:

| Check | Result |
| --- | --- |
| `make test-integration` with the database stopped | exit 2; 10 errors with `cannot connect to the integration database postgres@127.0.0.1:15432/kn (... Connection refused ...)` and the `make db-up` hint |
| Two `make test-integration` runs in parallel | both `10 passed`; no scratch schema or lock remained |
| A run killed with `SIGKILL` after it created `kn_test_54305582_killed` | the schema remained and no lock was held; the next `make test-integration` passed and dropped it |
| `make test` with both variables exported | 133 passed, 10 deselected |
| CI simulation without the empty init directory | the prepare step and the role probe passed; the smoke test failed on the extension list (`postgis_topology`); 1 failed, 9 passed |

Mutation checks. Each change was applied alone, and the named test failed. The file was then
restored.

| Change | Failing test |
| --- | --- |
| Marker by fixture use removed | `test_a_test_elsewhere_that_uses_the_database_is_an_integration_test` |
| Marker hook `trylast` instead of `tryfirst` | the same |
| Skip replaced by an error | `test_integration_tests_skip_with_a_reason_without_a_database` |
| Trailing newline of the password file kept | `test_a_missing_or_empty_password_file_is_refused[\n]` |
| Invalid URL quoted in the message | `test_an_invalid_url_is_refused_without_quoting_it` |
| Description returns the connection string | `test_the_description_names_the_server_without_the_password` |
| Single quotes of the password not doubled | `test_set_password_doubles_single_quotes_and_keeps_the_password_out_of_arguments` |
| `KN_DB_CONTAINER` branch of `kn_db_psql` removed | `test_prepare_container_stops_when_the_password_cannot_be_set` |
| Container guard of `kn_db_prepare_container` removed | `test_prepare_container_requires_a_container` |
| Prepare continues after a failed password step | `test_prepare_container_stops_when_the_password_cannot_be_set` |
| Empty init directory, loopback address, or `--auth-host` removed from the workflow | the matching test in `tests/deploy/test_ci_workflow.py` |
| Orphan sweep removed, or a token used without its lock (integration) | `test_a_new_session_drops_the_schemas_of_a_session_that_holds_no_lock` |
| Drop at close removed (integration) | `test_scratch_schemas_are_private_to_their_session_and_dropped_when_it_closes` |
| Name length check removed (integration) | `test_a_scratch_schema_name_must_be_a_short_lowercase_identifier[xxx...]` |

Other checks: `make quality` exit 0. `git diff --check` clean. The changed files are ASCII only.
`make quality-report` lists no file over 250 lines. The unit suite grew from 106 to 133 tests,
and 10 integration tests were added.

## Handoff

Plan counts before: 118 tasks (107 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 99,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `database-integration-harness`; priority human
task `provide-inventree-instance-access`.

Plan counts after: 117 tasks (106 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 98,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `message-catalog-core`; priority human task
unchanged.

Completion changes: `database-integration-harness` left the plan and the `Requires` fields of
`runtime-platform-implementation-audit` (whose `Requires` line went) and `contract-compiler`, whose
`Dependencies` now link the harness. `runtime-platform` is `shipped` in the registry with a link to
the runtime platform page; its only open task is the optional audit. The runtime platform page
lists the CI rehearsal under verification, and its known limitations name the three runner
behaviors that a host rehearsal cannot observe: a service port with a host address, the bind of a
missing host directory, and `job.services.postgres.id`. Final `make ci`: exit 0,
`133 passed, 10 deselected`, 0 broken links.

The CI job and these runner behaviors no longer apply: record 0009 removed the job, and GitHub
Actions runs only the lightweight unit tests.

Notes for later tasks:

- `contract-compiler` and `development-rebuild-mode` can request scratch schemas named after the
  KN schemas, for example `scratch_schemas.schema("identity")`. Generated DDL that names its schema
  needs a schema mapping or a `search_path` to apply there.
- Tests that need KN role behavior can `SET ROLE` to a `kn_<schema>_*` group, because the harness
  connects as the superuser.
- `runtime-platform-implementation-audit` can reuse `acceptance.sh` for its parallel-run and
  cleanup checks. Restarting the service during a test was not tried.
