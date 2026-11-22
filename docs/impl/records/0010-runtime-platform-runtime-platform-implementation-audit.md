# Record 0010: runtime-platform-implementation-audit

## Work contract

Original plan task, copied before implementation:

```markdown
#### runtime-platform-implementation-audit (optional)

The database service and test harness carry every later group, so defects in pinning, roles, or test
isolation are cheapest to fix before contracts compile against them.

- Serves: `runtime-platform` -- [Runtime platform](../design/spec.md#runtime-platform)
- Agent status: CLEAR
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. Docker Engine with Compose v2.
- User-visible outcome: Later groups build on a verified database service and test harness. The
  audit record gives every check a result and every finding a disposition. The current-state page
  lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: image pins by tag and digest and the path to a new PostgreSQL or PostGIS
  major; role and default privileges for schemas that later groups add; healthcheck and restart
  behavior; volume ownership and `DATA_DIR` handling; secrets kept out of Compose files and logs;
  test database isolation, parallel runs, and cleanup; the split between the GitHub unit gate and
  the local-only tests; the loopback-only database port and outbound traffic from the database
  container, which [record 0007](records/0007-adhoc-database-loopback-port.md) could not measure.
  Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/`, `tests/integration/`, `tests/conftest.py`,
  `.github/workflows/ci.yml`, `Makefile`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Start
  from empty volumes, probe each role with one granted and one refused operation, run the
  integration suite twice in parallel, and restart the service during a test.
- Acceptance gates: A role acting outside its grants is refused by a test. Parallel and repeated
  integration runs leave no shared state. Every finding has a severity, evidence, and a disposition,
  no `blocker` is accepted, and every fix starts from a failing regression test. `make ci` passes
  with the scheduled tasks in the plan.
- Documentation target: `current/runtime-platform.md` listed in the [areas index](current.md#areas).
```

Prerequisites: the task has no `Requires` entry. The group's required tasks were accepted in
[record 0006](0006-runtime-platform-compose-database-service.md) and
[record 0008](0008-runtime-platform-database-integration-harness.md), with the ad hoc changes of
[record 0007](0007-adhoc-database-loopback-port.md) and
[record 0009](0009-adhoc-local-only-service-tests.md). Docker Engine 29.9.3 with Compose v5.7.1 is
installed on the development host. The host now has a default route, so outbound traffic from the
database container can be measured.

## Implementation and decisions

The audit worked through the six [implementation audit](../../guide/planning-workflow.md#implementation-audits)
checks against the [runtime platform](../../design/spec.md#runtime-platform) section and the
records of the group. The [runtime platform page](../current/runtime-platform.md) describes the
resulting behavior, its [image updates](../current/runtime-platform.md#image-updates), and its
known limitations.

### Findings

| ID | Severity | Check | Finding and evidence | Disposition |
| --- | --- | --- | --- | --- |
| RP-01 | major | 5 | A failing test that takes `integration_database` prints the superuser password: pytest shows test arguments with `repr()`, and the dataclass field was in it. A planted failing test against the scratch database printed `integration_database = IntegrationDatabase(conninfo='postgresql://postgres@127.0.0.1:15441/kn', password='<the password>')`. | Fixed: `field(repr=False)` in `tests/integration/harness.py`. Regression test `test_a_failing_test_prints_its_database_argument_without_the_password`. |
| RP-02 | major | 3 | An image update within one PostgreSQL major leaves the installed PostGIS extension at its old version, because the bootstrap only ran `CREATE EXTENSION IF NOT EXISTS`. The smoke test checked `postgis_lib_version()`, which is new at once. Simulated by setting the catalog version to `3.6.0` and running `make db-up`: installed `3.6.0`, default `3.7.0`, library `3.7.0`, `make db-up` exit 0. | Fixed: the bootstrap runs `ALTER EXTENSION postgis UPDATE`. Regression tests: the smoke test compares the installed version with the manifest, and `test_the_bootstrap_brings_postgis_to_the_version_of_the_image`. After the fix the same database read `3.7.0` after `make db-up`. |
| RP-03 | minor | 4 | Two concurrent bootstrap runs fail. Two `make db-up` at once: one exited 2 with `ERROR: tuple concurrently updated` at line 90 in 5 of 5 rounds. The single transaction left nothing partial. | Fixed: the bootstrap takes the transaction-level advisory lock `(0x4B4E4253, 0)` first. Regression test `test_concurrent_bootstrap_runs_all_succeed` (four connections, three rounds). After the fix, 5 of 5 rounds of two `make db-up` exited 0 and 0. |
| RP-04 | minor | 2 | The database container resolves external names. TCP egress is blocked (below), but Docker's embedded resolver forwards unknown names from a container on the non-internal `loopback` network: `getent hosts one.one.one.one` answered inside the database container. | Fixed: `dns: [127.0.0.1]` on the service. A throwaway container on `loopback` with `--dns 127.0.0.1` failed external names and still resolved `postgres` and the container name. Regression test `test_the_database_resolves_no_external_name`; the recreated container fails the lookup. |
| RP-05 | minor | 4 | A `DATA_DIR` that contains a space breaks `make test`, `make coverage`, `make test-integration`, `make ci`, and `make ci-local`: `-o cache_dir=$(DATA_ROOT)/cache/pytest` was unquoted. `make test-integration` with `DATA_DIR=".../audit data"` failed with `ERROR: file or directory not found: data/cache/pytest`. The database targets themselves worked with the space. | Fixed: the option is quoted. Regression test `test_a_data_dir_with_a_space_is_one_pytest_cache_path` for `test` and `test-integration`. Afterwards `make test-integration` passed with the space. |
| RP-06 | minor | 2, 6 | The `Makefile` resolved `DATA_DIR` by its own rule and ignored `.env`, so the database volume followed `.env` while the pytest, Ruff, and mypy caches stayed in `./.data`. With `.env` holding `DATA_DIR=<scratch>/envdir`, `make -n test` gave `cache_dir=<root>/.data/cache/pytest`. The [reproducible environment](../../design/spec.md#reproducible-environment) section promises that tool caches follow `DATA_DIR`. | Fixed here, although `reproducible-environment` owns the rule: the same `Makefile` line feeds this group's `test-integration` and `ci-local`, RP-05 changed it, and `reproducible-environment` has no open group in the plan. `DATA_ROOT` now comes from `kn_load_env`, the one rule of the shell helpers. Regression test `test_make_reads_data_dir_from_dot_env_like_the_shell_helpers`. |
| RP-07 | minor | 2 | No pytest test acted as a KN role. Roles were proven only by `make db-verify`, and the task gate asks for a test (record 0008 left it to this audit). | Fixed: `tests/integration/test_roles.py`, 22 tests. Seven planted privilege faults each failed at least one of them (below). |
| RP-08 | minor | 3 | A new PostgreSQL major has no data-keeping path. The image entrypoint refuses a cluster of another major. The pinned image started with `PG_MAJOR=19` and `PGDATA=/var/lib/postgresql/19/docker` on the 18 volume exited 1 with `there appears to be PostgreSQL data in: /var/lib/postgresql/18/docker`. So the failure is loud, not an empty database, but the only recovery is `make db-reset`. | Accepted: listed under known limitations with its reason (the database is a reproducible projection in the development phase) and its reopening condition (release approval; then `pg_upgrade --link` or dump and restore with its own task). The procedure is under [image updates](../current/runtime-platform.md#image-updates). |

No `blocker` was found. No task was scheduled, so the plan gains no task.

Observations that are not findings:

- The killed server process (SIGKILL from the host) restarted under `unless-stopped`: `restarting`
  after 1 s, `healthy` after 3 s, crash recovery in the log, the probe row intact. Docker does not
  restart a container that is only unhealthy; `make db-up` then waits and fails with the log tail.
  Recorded as a durable finding.
- `docker restart` during a test failed that test at once with `AdminShutdown` and the
  `scratch_schemas` teardown with the same error. The run ended after 2 s. Its four scratch schemas
  remained, and the next `make test-integration` dropped them.
- The GitHub workflow names actions by major tag and `ubuntu-latest`. These are undeclared tools
  under the [reproducible environment](../../design/spec.md#reproducible-environment) boundary, and
  the workflow runs with `contents: read` and no secret. Not a runtime platform promise.
- A configured `KN_POSTGRES_PASSWORD_FILE` is used with the mode its owner gave it. The generated
  default file is `0600` in a `0700` directory.

### Check results

1. **Implementation validation.** Passed. Rerun from an empty `DATA_DIR` in project `kn-audit` on
   port `15441`, with a space in the path: healthy after 3 s, `make db-verify` passed, the probe
   row survived `docker restart` and `db-down`/`db-up`, `5432/tcp -> 127.0.0.1:15441`, network
   options as documented, every file owned by UID 1000, volume and secret directory `0700`,
   password file `0600`, and no occurrence of the password in `docker logs`, `docker inspect`, or
   `docker compose config`. The loopback-only probes of record 0007 gave `no response` for the
   host LAN address, both container addresses from the default bridge, and the bridge gateway, and
   a login without a password was refused. The current-state page matched the commands, paths, and
   messages. It now also lists the new tests, the advisory lock, the PostGIS update, the DNS
   setting, and the image update path.
2. **Specification conformance.** Each promise maps to code and a test: digest pins
   (`test_every_manifest_image_is_the_pinned_image_of_its_service`), schemas and roles
   (`test_bootstrap_and_probe_cover_core_schemas_and_every_domain_package`, `test_roles.py`,
   `make db-verify`), volumes under `DATA_DIR` (`test_database_volume_lives_under_data_dir...`,
   `test_make_data_dir.py`), healthchecks and internal networks (`test_compose.py`), the
   loopback-only configurable port (`test_compose.py`, `tests/scripts/test_common_db.py`), a
   password for every TCP login (`test_a_tcp_login_without_a_password_is_refused`), secrets from
   files (`test_passwords_come_only_from_secret_files`), integration tests on the development host
   and none on GitHub (`test_ci_workflow.py`). Gaps found: RP-04, RP-06, RP-07. The manifest lists
   only the image; schema and tool entries arrive with `contract-toolchain-pin`, which names
   `deploy/versions.yaml`. Later services are owned by their groups. Nothing outside the boundary
   exists.
3. **Design scope.** Expensive to change later: the builtin `C.UTF-8` collation (needs a new
   cluster), the `$DATA_DIR/postgres/<major>/docker` layout that allows `pg_upgrade --link`, the
   schema and role names `kn_<schema>_{owner,loader,reader}` and the default privileges for the
   owner role, the advisory lock keys `0x4B4E5453` (scratch sessions) and `0x4B4E4253`
   (bootstrap), the `KN_TEST_DATABASE_URL` and `KN_TEST_DATABASE_PASSWORD_FILE` variables, and the
   `integration` and `heavy` markers. A new schema is one array entry in the bootstrap and the probe,
   and reaches an existing volume on the next `make db-up`; the role tests then cover it
   automatically. New services join `internal`; only a publishing service joins `loopback`, which
   `test_compose.py` enforces. Findings: RP-02, RP-08.
4. **Corner cases.** Empty volume, restart, crash, `db-down`/`db-up`, concurrent `db-up` (RP-03),
   a space in `DATA_DIR` (RP-05), `.env` versus environment (RP-06), a restart during a test, a
   killed test run (record 0008), parallel and repeated runs, a stale extension (RP-02), and an
   image of another major (RP-08) were exercised. Unicode text round-trips in the smoke test.
   Time zones and clock skew do not apply: the group stores no times.
5. **Best practices.** Least privilege, refusing root, read-only root file system, dropped
   capabilities, digest pins, deterministic network-free unit tests, and failure-path coverage
   hold. Finding: RP-01. The new tests are typed, ASCII, and below 250 lines per file.
6. **Debt.** The `make -n` reading of the workflow test moved to `tests/deploy/make_dry_run.py` and
   the bootstrap array parser to `tests/deploy/bootstrap_sql.py`, so the new tests reuse them
   instead of copying them. RP-06 removed the second `DATA_DIR` rule. No `TODO`, skipped check, or
   dead code was found.

## Acceptance evidence

Status: accepted on 2026-11-21. Docker Engine 29.9.3, Compose v5.7.1, Linux x86_64, Python 3.12.3
and 3.13.18. The host had a default route.

Scripts and logs are in `$DATA_DIR/acceptance/runtime-platform-implementation-audit-20261121/`:
`validation.sh` and `validation.log` (scratch project, egress, image bump, PostGIS drift, concurrent
`db-up`, restart during a test, loopback probes), `role-mutations.sh` and `role-mutations.log`,
`parallel.sh` and `parallel.log` with the two fingerprints, `restart-probe.py` and
`restart-during-test.log`, `unit-regressions-before.log` and `unit-regressions-after.log`,
`integration-regressions-before.log`, `github-gate.sh` and `github-gate.log`, `ci.log`,
`ci-local.log`, `quality.log`, and the two `plan-status` logs.

| Gate | Evidence | Result |
| --- | --- | --- |
| A role acting outside its grants is refused by a test | `tests/integration/test_roles.py` | 22 passed. Each planted fault failed at least one test, and the database passed again after each revert: `CREATE` on `space` for its loader, `kn_gdelt_reader` granted to `kn_space_reader`, the default `INSERT` for the `supply` loader revoked, `TEMPORARY` for `kn_system_reader`, `CREATE` on `public` for `kn_analytics_owner`, `LOGIN` for `kn_system_owner`, and `kn_system_owner` granted to `kn_system_reader` |
| Parallel and repeated integration runs leave no shared state | `parallel.sh`: two rounds of two `make test-integration` at once on the default project, with a catalog fingerprint before and after | 4 runs, each `34 passed, 135 deselected`. Roles, memberships, schemas with ACLs, default privileges, relation count, database ACL, and extension versions are equal; 0 scratch schemas, 0 advisory locks, and 0 other sessions before and after |
| Every finding has a severity, evidence, and a disposition; no accepted `blocker` | The findings table | 2 major and 6 minor; 7 fixed and 1 accepted; no `blocker` |
| Every fix starts from a failing regression test | `unit-regressions-before.log`, `integration-regressions-before.log` | Before the fixes, the five new unit tests failed (RP-01, RP-04, RP-05 twice, RP-06), and against the scratch database the concurrent bootstrap test, the PostGIS bootstrap test, and the smoke test failed (RP-02, RP-03). After the fixes all passed |
| `make ci` passes with the scheduled tasks in the plan | `make ci` | exit 0; `135 passed, 34 deselected`; 0 spec-plan findings. No task was scheduled |

Further checks:

| Check | Result |
| --- | --- |
| `make ci-local` with the database up | exit 0; `135 passed, 34 deselected`, then `34 passed, 135 deselected`; afterwards 0 scratch schemas and 0 advisory locks |
| GitHub gate from a fresh copy, 3.12 and 3.13 | `uv sync --locked`, then `make ci-github`: exit 0 each, `135 passed, 34 deselected`, caches in the copy's `.data/cache` |
| `make quality` | exit 0; coverage 96.76 % against the 90 % floor; package built |
| `make db-verify` on the default project | `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0` |
| Egress from the database container | TCP `1.1.1.1:53` and `:443` time out (exit 124); a default-bridge container and the host connect to `:53` (`:443` timed out everywhere on this network). DNS: see RP-04 |
| `make help` time with the `DATA_DIR` lookup | 0.02 s |
| `git diff --check`, ASCII, `make quality-report` | clean; ASCII only; no file over 250 lines |

The unit suite grew from 129 to 135 tests and the local-only suite from 10 to 34.

## Handoff

Plan counts before: 117 tasks (106 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 98,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `message-catalog-core`; priority human task
`provide-inventree-instance-access`.

Plan counts after: 116 tasks (105 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 97,
HUMAN-GATED 9, RUN NEEDED 8. Priority tasks unchanged.

Completion changes: `runtime-platform-implementation-audit` left the plan, and with it the
`runtime-platform` group, which has no open task. No `Requires` field named it. `runtime-platform`
stays `shipped`; `reproducible-environment` stays `shipped` and now meets its promise that tool
caches follow `DATA_DIR`. Capabilities affected: `runtime-platform` and `reproducible-environment`.
No specification text changed.

Notes for later tasks:

- `operations-hardening-implementation-audit` owns outbound network limits. Without a firewall
  rule, whether packets leave the host without source NAT is unmeasured; only replies are known
  not to return.
- A task that adds a KN schema adds it to the arrays in the bootstrap and in
  `deploy/postgres/verify-roles.sql`; `test_compose.py` and `test_roles.py` then cover it.
- A service that needs outside names or addresses must not copy the database's `dns` setting or
  join `loopback` for egress; it needs its own network decision.
