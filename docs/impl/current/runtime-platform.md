# Runtime Platform

This page owns the local Compose stack and its database service. It serves the
[`runtime-platform`](../../design/spec.md#runtime-platform) capability. The stack has one service
so far, PostgreSQL with PostGIS. The [integration test harness](#integration-tests) runs database
tests against it on the development host; GitHub Actions runs no database test. Kestra, Superset,
the proxy, and inference are still in the [forward plan](../plan.md).

## Commands

Each target sources `scripts/shared/common.sh`, runs `kn_load_env`, and calls one `kn_db_*`
helper. The targets refuse to run as root and need Docker Engine with the Compose v2 plugin.

| Command | Behavior |
| --- | --- |
| `make db-up` | Creates the password file and `$DATA_DIR/postgres/` if they are missing, starts the service, waits up to 180 s for healthy, then applies the bootstrap again and prints the host address and the password file path. When the service does not become healthy, it prints the last 30 log lines and a hint about a taken port or a failed first initialization, and exits 1. |
| `make db-down` | Removes the containers and the networks. `$DATA_DIR/postgres/` is kept. |
| `make db-reset` | Runs `db-down`, deletes `$DATA_DIR/postgres/`, then runs `db-up`. The password file and the rest of `$DATA_DIR` are kept. It refuses a `DATA_DIR` that is empty, relative, or `/`. |
| `make db-verify` | Runs the role probe against the running database. It prints `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`, or fails with an error that names the first failed check. |
| `make test-integration` | Runs the tests marked `integration` against the running database. It does not start or stop the database. See [Integration tests](#integration-tests). |
| `make ci-local` | Runs `make ci`, then every local-only test (`integration` or `heavy`) against the running database. See [Where tests run](#where-tests-run). |

Host tools connect to `127.0.0.1:15432` as `postgres` with the password from the password file.
With a host `psql`, the helpers give the configured port and file:

```bash
source scripts/shared/common.sh; kn_load_env
PGPASSWORD="$(cat "$(kn_db_password_file)")" \
  psql -h 127.0.0.1 -p "$(kn_db_host_port)" -U postgres -d kn
```

Without a host `psql`, run
`source scripts/shared/common.sh; kn_load_env; kn_compose exec postgres psql -U postgres -d kn`.
`kn_compose` passes the runtime user ID, the password file path, and the host port to
`docker compose --file deploy/compose.yaml`. `kn_db_psql` runs a non-interactive `psql` as the
superuser in `kn` inside the service.

The host port is `15432` by default, so a PostgreSQL that uses the standard port `5432` on the same
host, such as a system server or another Compose stack, runs beside KN. Set `KN_POSTGRES_HOST_PORT`
in `.env` to change it. Every helper refuses a value that is not a port from 1 to 65535 before
Docker runs. A second checkout on the same host needs its own `COMPOSE_PROJECT_NAME`,
`KN_POSTGRES_HOST_PORT`, and `DATA_DIR`.

## Service

`deploy/compose.yaml` defines project `kn-event-horizon` (override with `COMPOSE_PROJECT_NAME`)
and service `postgres`.

| Item | Value |
| --- | --- |
| Image | `docker.io/postgis/postgis:18-3.7@sha256:fe440a27...`, from `deploy/versions.yaml` |
| Versions | PostgreSQL 18.7, PostGIS 3.7.0, Debian 13, `linux/amd64` only |
| Database | `kn`, UTF8, builtin locale provider with `C.UTF-8` collation |
| Superuser | `postgres`, password from the secret file at `/run/secrets/postgres_password` |
| Data | `$DATA_DIR/postgres/` bound to `/var/lib/postgresql`; the cluster is in `18/docker/` |
| Runtime user | The invoking host user (`KN_UID:KN_GID`), so every file under `$DATA_DIR` stays theirs |
| Hardening | Read-only root file system, tmpfs for `/tmp` and the socket directory, all capabilities dropped, `no-new-privileges`, no Docker socket |
| Host port | `127.0.0.1:15432` (`KN_POSTGRES_HOST_PORT`) to container port 5432; no other host address |
| Networks | `internal`: internal, no IPv6, `gateway_mode_ipv4: isolated`, for traffic between services. `loopback`: not internal, no IPv6, `host_binding_ipv4: 127.0.0.1`, `enable_ip_masquerade: false`; it carries only the published port |
| Health | TCP `pg_isready` to `127.0.0.1` and the role `kn_system_owner` exists |
| Restart | `unless-stopped`, 1 min stop grace period, 256 MB shared memory |

The password file defaults to `$DATA_DIR/secrets/postgres-password`. `make db-up` creates it with
64 random hex characters, mode `0600` in a `0700` directory, and never prints the value. A file
named by `KN_POSTGRES_PASSWORD_FILE` must already exist and be non-empty. The password takes
effect only when an empty volume is initialized. After that, change it with `ALTER ROLE`.

Authentication: TCP connections need a SCRAM password, through the host port and also from inside
the container. Unix socket connections inside the container are trusted, and only
`docker compose exec` reaches them. The host port has no TLS, because it listens on loopback only.

## Schemas and roles

`deploy/postgres/initdb/10-kn-bootstrap.sql` runs once from the image entrypoint on an empty
volume, and `make db-up` applies it again every time. It is idempotent and runs in one
transaction. It replaces the image's own init script, so `kn` has no `topology` schema and the
cluster has no `template_postgis` database.

- PostGIS is installed in schema `public`. `PUBLIC` keeps `USAGE` on `public` but not `CREATE`.
- Schemas: `system`, `semantic`, `identity`, `evidence`, `supply`, `interchange`, `space`,
  `gdelt`, `microelectronics`, and `analytics`. The domain schemas match the packages under
  `domains/`.
- Each schema has three `NOLOGIN` group roles without elevated attributes, and each has
  `CONNECT` on `kn`. `PUBLIC` has no privilege on `kn` and none on the KN schemas.

| Role | Privileges |
| --- | --- |
| `kn_<schema>_owner` | Owns the schema, so it can create, alter, and drop objects in it |
| `kn_<schema>_loader` | `USAGE` on the schema; `SELECT`, `INSERT`, `UPDATE`, `DELETE` on tables; `USAGE`, `SELECT` on sequences. No DDL, `TRUNCATE`, or `TEMPORARY` |
| `kn_<schema>_reader` | `USAGE` on the schema and `SELECT` on tables |

Grants cover the tables and sequences that exist when the bootstrap runs. Default privileges cover
objects that the owner role creates later, so DDL must run under `SET ROLE kn_<schema>_owner`.
An object created by the superuser gets loader and reader grants only on the next bootstrap run,
and it stays owned by the superuser. No role reaches a schema other than its own, and there are no
login roles yet. Login roles join these groups in the tasks that first connect.

## Integration tests

`make test-integration` sources the shared helpers, and `kn_db_test_env` exports two variables
that `tests/integration/harness.py` reads:

| Variable | Value |
| --- | --- |
| `KN_TEST_DATABASE_URL` | `postgresql://postgres@127.0.0.1:<KN_POSTGRES_HOST_PORT>/kn`, a libpq URI without a password. Any libpq connection string or URI works when pytest runs directly |
| `KN_TEST_DATABASE_PASSWORD_FILE` | The superuser password file. A relative path resolves from the project root, and trailing newlines are dropped, as the image entrypoint drops them. Optional when pytest runs directly |

Selection, skips, and failures:

- `tests/conftest.py` marks `integration` every test under `tests/integration/` and every test that
  uses the `integration_database` fixture, directly or through another fixture. `make test` and
  `make coverage`, and so `make ci`, deselect it (see [Where tests run](#where-tests-run)), so the
  unit suite never connects, even when the variables are set.
- Without `KN_TEST_DATABASE_URL`, the integration tests skip with the reason
  `no integration database configured: KN_TEST_DATABASE_URL is not set`. The pytest options include
  `-rfEs`, which prints skip reasons, and `--strict-markers`.
- With the variable set, a missing or empty password file, an invalid connection string, or a
  database that does not answer fails every integration test. The message names the server as
  `user@host:port/database` and gives the `make db-up` hint. No message contains the password.

| Fixture | Scope | Provides |
| --- | --- | --- |
| `integration_database` | session | The checked configuration. `connect(**overrides)` opens a psycopg 3 connection with a 10 s connect timeout and `application_name` `kn-integration-tests`; keyword arguments override libpq parameters |
| `scratch_schemas` | session | `schema(name)` creates `kn_test_<token>_<name>` unless it exists and returns the name. Every schema of the session is dropped with `CASCADE` when the session ends |
| `db_connection` | test | A new connection outside autocommit. It is closed after the test, so work the test does not commit is rolled back |

Scratch schemas: each session draws a random 31-bit token and holds the session-level advisory
lock `(0x4B4E5453, token)` on its own autocommit connection. Before it creates anything, a session
drops every `kn_test_*` schema whose token lock is free, which removes what a killed run left
behind, and it never touches the schemas of a live session. A drop waits at most 10 s for a lock
(`lock_timeout`), so a test that leaves a connection open fails the teardown instead of hanging it,
and the next session drops the rest. Logical names are lowercase identifiers of at most 46
characters. All tests of a session share its schemas, so a test that needs its own uses its own
logical name. The tests connect as `postgres`, so the scratch schemas belong to the superuser. No
product schema is created.

The smoke tests in `tests/integration/test_database.py` check that the server and PostGIS versions
equal the manifest components and that the only extensions are `plpgsql` and `postgis`. They also
check that a TCP login without a password is refused, that a scratch table round-trips a PostGIS
point and Ukrainian text, and that scratch sessions are private and cleaned up.

## Where tests run

GitHub Actions runs only lightweight unit tests: no test there needs a service endpoint, large
memory, or a long run time. Its workflow has the `quality` job alone, which runs `make ci-github`
on Python 3.12 and 3.13, and no job starts a service or a job container.

| Marker | Meaning | Runs in |
| --- | --- | --- |
| none | A lightweight unit test | `make test`, `make coverage`, `make ci`, `make ci-github` (GitHub Actions), `make ci-local` |
| `integration` | Needs the integration database. Set by directory and by fixture use | `make test-integration`, `make ci-local` |
| `heavy` | Needs large memory or a long run time. Set by `@pytest.mark.heavy` | `make ci-local` |

The unit selection is `-m "not integration and not heavy"` and the local-only selection is
`-m "integration or heavy"`. `tests/conftest.py` defines both as `UNIT_SELECTION` and
`LOCAL_SELECTION`, and the `Makefile` as `UNIT_TESTS` and `LOCAL_TESTS`.
`tests/deploy/test_ci_workflow.py` reads the targets with `make -n` and checks that the two
agree, that `make ci-github` runs only the unit selection, and that the workflow runs only
`uv sync` and `make ci-github`. No test is marked `heavy` yet.

A plan gate that names CI for a test that needs a service, large memory, or a long run time is met
by `make ci-local` on the development host.

## Verification

| Check | Command | Expected result |
| --- | --- | --- |
| Compose and manifest rules | `make test` | `tests/deploy/test_compose.py` passes: digest pins match the manifest, only the database publishes one port and only on `127.0.0.1`, only publishing services join `loopback`, the other networks are internal and isolated, unprivileged services, secret files, the volume under `DATA_DIR`, and the schema lists cover `domains/` |
| Shell helpers | `make test` | `tests/scripts/test_common_db.py` passes against a stubbed `docker`, including the default and configured host port, the refused port values, and the test connection |
| Harness without a database | `make test` | `tests/test_integration_harness.py` passes: configuration, deselection of `integration` and `heavy` tests, the skip reason, the failure for an unreachable database without the password, and marking by fixture use |
| GitHub runs unit tests only | `make test` | `tests/deploy/test_ci_workflow.py` passes: no job starts a service or a job container, the workflow runs only `uv sync` and `make ci-github`, and `make -n` shows the unit selection for `ci-github` and the added local-only selection for `ci-local` |
| Integration tests | `make db-up`, then `make test-integration` | `10 passed`; afterwards no `kn_test_*` schema and no advisory lock remain |
| Every test | `make db-up`, then `make ci-local` | the `make ci` checks pass, then `10 passed` for the local-only tests |
| GitHub gate from a fresh copy | In a copy of the tracked and untracked, not ignored files, for 3.12 and 3.13: `uv sync --locked --extra dev --python <version>`, then `make ci-github PYTHON_VERSION=<version>` | both exit 0 without Docker or a database |
| Healthy from empty | `make db-reset` | exits 0 with the container `Healthy` |
| Roles and privileges | `make db-verify` | the `kn roles verified` notice |
| Loopback only | `docker port <container>`; `pg_isready` to the host LAN address and, from a container on the default bridge, to the container addresses and the bridge gateway | `5432/tcp -> 127.0.0.1:15432`; every other probe reports `no response` |
| Password required | `psql -w -h 127.0.0.1 -p 15432 -U postgres -d kn` | `fe_sendauth: no password supplied` |

`deploy/postgres/verify-roles.sql` runs every probe as one transaction and rolls it back. For each
schema the owner creates a table with a PostGIS column. The loader inserts, updates, selects, and
deletes, and is refused `CREATE`, `ALTER`, `TRUNCATE`, and `DROP`. The reader selects and is refused
`INSERT` and `CREATE`. For every pair of schemas the owner, loader, and reader of one are refused in
the other. The probe states its expected schema list itself instead of reading it from the
bootstrap.

The acceptance run, its planted faults, and its evidence are in
[record 0006](../records/0006-runtime-platform-compose-database-service.md). The loopback port and
its parallel-run checks are in [record 0007](../records/0007-adhoc-database-loopback-port.md). The
integration harness and its mutation checks are in
[record 0008](../records/0008-runtime-platform-database-integration-harness.md). The split
between the GitHub unit gate and the local-only tests is in
[record 0009](../records/0009-adhoc-local-only-service-tests.md).

## Durable findings

- After a failed first initialization, the image entrypoint skips init on the next start and the
  server comes up without KN roles. The role check in the healthcheck keeps such a container
  unhealthy, and `make db-up` fails after about 100 s with the SQL error in the log tail. Recover
  with `make db-reset`.
- `pg_isready` reports `no attempt` for a user ID without a passwd entry unless `--username` is
  given. The healthcheck passes it explicitly.
- On Docker Engine 29.9.3, an `internal: true` network still gives the host a bridge address that
  reaches container ports. `gateway_mode_ipv4: isolated` removes it. Engines without bridge
  gateway modes are untested. On such an engine the host could reach the container address,
  still behind SCRAM authentication.
- Docker publishes no port of a container that is attached to internal networks only. On Engine
  29.9.3, `docker run --network <internal> -p 127.0.0.1:15499:5432` starts and records the
  binding, but nothing listens on the host. The database therefore also joins `loopback`.
- On `loopback`, `host_binding_ipv4: 127.0.0.1` binds a port written without an address to
  loopback as well. `docker-proxy` serves the loopback port, so it works without IP masquerade.
- pytest deselects by `-m` in the `pytest_collection_modifyitems` hook of its mark plugin. The
  conftest hook that adds the `integration` marker is `tryfirst`. Without it, a test outside
  `tests/integration/` that uses a database fixture is not deselected; a mutation check confirmed
  this.
- In a `postgis/postgis` container that runs the image's own init script, `make db-verify` still
  passes. Only the smoke test's extension check fails, on `postgis_topology`.
- With psycopg 3, `password=""` and a `passfile` that does not exist make libpq send no password,
  so the refusal check does not depend on `PGPASSWORD` or `~/.pgpass`.
- The builtin `C.UTF-8` collation sorts by code point, so the Ukrainian letters U+0490, U+0404,
  U+0406, and U+0407 (Ghe with upturn, Ie, I, and Yi) sort outside the alphabet. Display order
  uses `COLLATE "uk-UA-x-icu"`, which is available in the image. The builtin collation never
  changes with the C library of a new image digest.

## Known limitations

- The host reaches the container address on `loopback` directly, as on any non-internal bridge.
  That path needs the password like the published port. Containers on other Docker networks and
  other hosts on the LAN got no response.
- `enable_ip_masquerade: false` is meant to block outbound connections from the database
  container. This was not measured, because the development host had no outbound route during
  acceptance.
- Only the superuser logs in, so host tools and the integration tests connect as `postgres` until
  the tasks that first connect add login roles. No pytest test acts as a KN role yet;
  `make db-verify` runs the role probe.
- GitHub Actions runs no database test, so a change that breaks the database or the harness passes
  there. Only `make ci-local` or `make test-integration` on a development host catches it, and the
  local-only tests run on one Python version, the one of `.venv`.
- The image is published for `linux/amd64` only. Another architecture needs a different image,
  recorded in the manifest as a fallback.
- The bootstrap converges what it declares: it re-grants privileges and restores role
  attributes, schema owners, and schema grants. It does not revoke extra table grants or role
  memberships added by hand. `make db-verify` reports those.
- Adding a schema to the bootstrap reaches an existing volume on the next `make db-up`. Removing
  one needs `make db-reset`.
