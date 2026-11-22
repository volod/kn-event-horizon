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
| `make db-up` | Creates the password file and `$DATA_DIR/postgres/` if they are missing, starts the service, waits up to 180 s for server readiness, then runs Python platform governance, Alembic upgrade, contract and privilege verification, and prints the host address and the password file path. When the service does not become healthy, it prints the last 30 log lines and a hint about a taken port or a failed first initialization, and exits 1. |
| `make db-down` | Removes the containers and the networks. `$DATA_DIR/postgres/` is kept. |
| `make db-reset` | Runs `db-down`, deletes `$DATA_DIR/postgres/`, then runs `db-up`. The password file and the rest of `$DATA_DIR` are kept. It refuses a `DATA_DIR` that is empty, relative, or `/`, and refuses `KN_ENVIRONMENT=released`. |
| `make db-upgrade` | Applies Python platform policy and the Alembic head, then verifies the installed contract. |
| `make db-rebuild` | Recreates only contract-managed space projections when `KN_ENVIRONMENT=development`; archived packages remain available for backfill. |
| `make db-verify` | Runs the Python role, contract and structure probes against the running database. It prints `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`, or fails with an error that names the first failed check. |
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
| Outbound traffic | None. TCP to outside addresses times out, because `loopback` has no source NAT. `dns: [127.0.0.1]` makes Docker's embedded resolver forward unknown names to the container's own loopback, so external names do not resolve, while service names on the stack networks still do |
| Health | TCP `pg_isready` to `127.0.0.1`; `make db-up` subsequently requires successful governance and verification |
| Restart | `unless-stopped`, 1 min stop grace period, 256 MB shared memory |

The password file defaults to `$DATA_DIR/secrets/postgres-password`. `make db-up` creates it with
64 random hex characters, mode `0600` in a `0700` directory, and never prints the value. A file
named by `KN_POSTGRES_PASSWORD_FILE` must already exist and be non-empty. The password takes
effect only when an empty volume is initialized. After that, change it with `ALTER ROLE`.

Authentication: TCP connections need a SCRAM password, through the host port and also from inside
the container. Unix socket connections inside the container are trusted, and only
`docker compose exec` reaches them. The host port has no TLS, because it listens on loopback only.

## Schemas and roles

`src/kn/db/platform.py` reads the schema and role policy from
`src/kn/contracts/resources/platform.json`. `make db-up` starts the server, then invokes
`kn db upgrade` through the host virtual environment. The mounted init directory contains only
`.gitkeep`, replacing the image's own init SQL so `kn` has no `topology` schema or
`template_postgis` database. Deployment has no SQL files.

The Python platform policy, Alembic upgrade and verification run in one transaction. The policy
first takes transaction-level advisory lock `(0x4B4E4253, 0)`; concurrent deployments serialize.
Failures return nonzero and roll back governance changes; server readiness alone is not successful
deployment. Retry `make db-upgrade` after correcting the error. Contract digest drift during
development needs an explicit guarded rebuild and source backfill, described under
[data contracts](data-contracts.md#development-baseline-and-release-evolution).

- PostGIS is installed in schema `public`, and every run updates it to the version of the image
  (`ALTER EXTENSION postgis UPDATE`). `PUBLIC` keeps `USAGE` on `public` but not `CREATE`.
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

`IntegrationDatabase` keeps the password out of its representation, so the arguments that pytest
prints for a failing test never show it.

The smoke tests in `tests/integration/test_database.py` check that the server version, the PostGIS
library, and the installed PostGIS extension equal the manifest components, and that the only
extensions are `plpgsql` and `postgis`. They also check that a TCP login without a password is
refused, that a scratch table round-trips a PostGIS point and Ukrainian text, and that scratch
sessions are private and cleaned up.

`tests/integration/test_roles.py` acts as each KN role in one transaction per test that is always
rolled back, with probe names that carry a random suffix, so parallel runs never collide. For every
schema the owner creates a table, the loader inserts and deletes through the default privileges,
and the reader selects. The loader is refused `CREATE` and `TRUNCATE`, the reader `INSERT` and
`CREATE`, and every role `CREATE` in `public`, temporary tables, and any access to the next schema
of the list. A temporary login in `kn_system_reader` cannot `SET ROLE` to the superuser or to any
other KN role. The test fails when a probe object outlives its transaction.

`tests/integration/test_bootstrap.py` applies the Python platform policy as `make db-up` does: four concurrent
SQLAlchemy connections run it three times each, and the installed PostGIS version afterwards equals the
image's default version and the manifest. The tests change nothing on a database that
`make db-up` started, because the platform policy converges to its declared state.

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
| Compose and manifest rules | `make test` | `tests/deploy/test_compose.py` passes: digest pins match the manifest, only the database publishes one port and only on `127.0.0.1`, only publishing services join `loopback`, the other networks are internal and isolated, the database resolves no external name, unprivileged services, secret files, the volume under `DATA_DIR`, and the schema lists cover `domains/` |
| `DATA_DIR` in make | `make test` | `tests/deploy/test_make_data_dir.py` passes: in a copy of the project, `make -n` gives the pytest cache below the `DATA_DIR` of `.env` or the environment, as one argument when the path contains a space |
| Shell helpers | `make test` | `tests/scripts/test_common_db.py` passes against a stubbed `docker`, including the default and configured host port, the refused port values, and the test connection |
| Harness without a database | `make test` | `tests/test_integration_harness.py` passes: configuration, deselection of `integration` and `heavy` tests, the skip reason, the failure for an unreachable database without the password, and marking by fixture use |
| GitHub runs unit tests only | `make test` | `tests/deploy/test_ci_workflow.py` passes: no job starts a service or a job container, the workflow runs only `uv sync` and `make ci-github`, and `make -n` shows the unit selection for `ci-github` and the added local-only selection for `ci-local` |
| Integration tests | `make db-up`, then `make test-integration` | `36 passed`; afterwards no `kn_test_*` schema and no advisory lock remain |
| Every test | `make db-up`, then `make ci-local` | the `make ci` checks pass, then `36 passed` for the local-only tests |
| GitHub gate from a fresh copy | In a copy of the tracked and untracked, not ignored files, for 3.12 and 3.13: `uv sync --locked --extra dev --python <version>`, then `make ci-github PYTHON_VERSION=<version>` | both exit 0 without Docker or a database |
| Healthy from empty | `make db-reset` | exits 0 with the container `Healthy` |
| Roles and privileges | `make db-verify` | the `kn roles verified` notice |
| Loopback only | `docker port <container>`; `pg_isready` to the host LAN address and, from a container on the default bridge, to the container addresses and the bridge gateway | `5432/tcp -> 127.0.0.1:15432`; every other probe reports `no response` |
| Password required | `psql -w -h 127.0.0.1 -p 15432 -U postgres -d kn` | `fe_sendauth: no password supplied` |
| No outbound traffic | In the container: `timeout 5 bash -c 'exec 3<>/dev/tcp/1.1.1.1/53'` and `getent hosts one.one.one.one` | both fail, while a container on the default bridge connects and resolves |

`src/kn/db/verification.py` checks declared role access to every schema, database CONNECT and
TEMPORARY privileges, CREATE denial in `public`, and table/sequence default grants. Probe tables
are created as each schema's owner in a savepoint that is always rolled back. It also compares the
installed PostgreSQL structure with contract-generated metadata. The integration role tests retain
actual allowed and refused operations. `governance.py` additionally checks safe role attributes,
schema ownership, the Alembic head and installed contract digest.

The acceptance run, its planted faults, and its evidence are in
[record 0006](../records/0006-runtime-platform-compose-database-service.md). The loopback port and
its parallel-run checks are in [record 0007](../records/0007-adhoc-database-loopback-port.md). The
integration harness and its mutation checks are in
[record 0008](../records/0008-runtime-platform-database-integration-harness.md). The split
between the GitHub unit gate and the local-only tests is in
[record 0009](../records/0009-adhoc-local-only-service-tests.md). The implementation audit, its
findings, and its measurements are in
[record 0010](../records/0010-runtime-platform-runtime-platform-implementation-audit.md).

## Image updates

Change the tag, the digest, the component versions, and the pin date in `deploy/versions.yaml` and
the image reference in `deploy/compose.yaml` together; `make test` checks that they agree.

- Same PostgreSQL major: `make db-up` recreates the container on the existing volume, and the
  bootstrap updates the installed PostGIS extension to the new library. The smoke test fails while
  the installed version differs from the manifest.
- New PostgreSQL major: the cluster lives in `$DATA_DIR/postgres/<major>/docker/`. The entrypoint of
  an 18 or later image refuses to start when it finds a cluster of another major, so `make db-up`
  fails after its 180 s wait with that error in the log tail. In the
  [development phase](../../design/spec.md#development-and-release-phases) the path is
  `make db-reset` and a rebuild; see [Known limitations](#known-limitations).

## Durable findings

- Governance now runs after TCP server readiness. A failed policy or migration rolls back and
  makes `make db-up` fail; the running server can still be healthy. Retry `make db-upgrade` after
  fixing the cause. Readiness is not permission to load an unverified schema.
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
- The image entrypoint looks for a `PG_VERSION` file in `/var/lib/postgresql/*/docker` and exits
  with `there appears to be PostgreSQL data in: /var/lib/postgresql/18/docker` when the cluster
  belongs to another major. Measured by starting the pinned image with `PG_MAJOR=19` on an 18
  volume. It creates an empty `19/` directory before it exits.
- After an image update within one major, the library is new at once, but `pg_extension` keeps the
  old PostGIS version until `ALTER EXTENSION postgis UPDATE`. `postgis_lib_version()` alone does
  not show the drift.
- Concurrent `GRANT` and `ALTER DEFAULT PRIVILEGES` on the same objects fail with
  `tuple concurrently updated`. Two `make db-up` at once failed in 5 of 5 rounds before the
  bootstrap took its advisory lock.
- Docker's embedded resolver at `127.0.0.11` forwards unknown names to the host's resolvers for a
  container on a non-internal network, even without source NAT. With `dns: [127.0.0.1]` it forwards
  them to the container's own loopback, where nothing answers, and it still answers service names.
- `SET ROLE` is checked against the session user, not the current role, so a superuser session
  that runs `SET ROLE kn_x_reader` can still `SET ROLE postgres`. A test of role escalation acts
  as a login role through `SET SESSION AUTHORIZATION`.
- pytest prints the arguments of a failing test with `repr()`. A dataclass field with a secret
  needs `repr=False`.
- A killed server process restarts under `restart: unless-stopped` and is healthy again after
  about 3 s of crash recovery. Docker does not restart a container that is only unhealthy.
- A service restart during a test fails that test with `AdminShutdown` at once, and the teardown
  of `scratch_schemas` reports the same error. The next session drops the schemas left behind.
- The builtin `C.UTF-8` collation sorts by code point, so the Ukrainian letters U+0490, U+0404,
  U+0406, and U+0407 (Ghe with upturn, Ie, I, and Yi) sort outside the alphabet. Display order
  uses `COLLATE "uk-UA-x-icu"`, which is available in the image. The builtin collation never
  changes with the C library of a new image digest.

## Known limitations

- The host reaches the container address on `loopback` directly, as on any non-internal bridge.
  That path needs the password like the published port. Containers on other Docker networks and
  other hosts on the LAN got no response.
- Outbound traffic was measured on one host with a default route (record 0010): TCP to an outside
  address times out and external names do not resolve. Whether packets leave the host with their
  private source address was not measured, only that no reply returns. No firewall rule blocks
  egress, because Compose cannot set one; the
  [operations hardening](../../design/spec.md#operations-hardening) audit owns outbound network
  limits.
- Only the superuser logs in, so host tools and the integration tests connect as `postgres` until
  the tasks that first connect add login roles. The role tests act as the KN group roles through
  `SET ROLE` and as a temporary login, inside rolled-back transactions.
- A new PostgreSQL major has no upgrade path that keeps data: the entrypoint refuses the old
  cluster, and the development phase runs `make db-reset` and a rebuild from the durable inputs.
  Kept on purpose, because the database is a reproducible projection of those inputs before
  [release migration mode](../../design/spec.md#development-and-release-phases). It reopens when a
  release is approved: then a major upgrade needs `pg_upgrade --link`, which the single mount at
  `/var/lib/postgresql` allows, or a dump and restore, with its own task.
- GitHub Actions runs no database test, so a change that breaks the database or the harness passes
  there. Only `make ci-local` or `make test-integration` on a development host catches it, and the
  local-only tests run on one Python version, the one of `.venv`.
- The image is published for `linux/amd64` only. Another architecture needs a different image,
  recorded in the manifest as a fallback.
- The bootstrap converges what it declares: it re-grants privileges and restores role
  attributes, schema owners, and schema grants. It does not revoke extra table grants or role
  memberships added by hand. `make db-verify` reports privilege violations visible to its probes;
  it does not audit the complete role membership graph.
- Adding a schema to the bootstrap reaches an existing volume on the next `make db-up`. Removing
  one needs `make db-reset`.

The Python governance replacement, development baseline and initial space dataset are documented
in [data contracts](data-contracts.md) and
[record 0011](../records/0011-data-contracts-satcom-schema-governance.md).
