# Record 0006: compose-database-service

## Work contract

Original plan task, copied before implementation:

```markdown
#### compose-database-service

The core engine needs a pinned, local PostgreSQL with PostGIS before any contract can be compiled
or loaded.

- Serves: `runtime-platform` -- [Runtime platform](../design/spec.md#runtime-platform)
- Agent status: CLEAR
- Dependencies: Docker Engine with Compose v2 on the development host. Choose the newest PostgreSQL
  major that has an official PostGIS image at pin time.
- User-visible outcome: `make db-up`, `make db-down`, and `make db-reset` manage a healthy local
  database `kn` with its schemas and roles. The data survives restarts.
- Scope boundary: The PostgreSQL and PostGIS service, role bootstrap (owner, loader, and reader per
  schema), `.env.example` entries without secrets, and the version manifest. Kestra, Superset, the
  proxy, and inference come in their own tasks.
- Data and artifact paths: `deploy/compose.yaml`, `deploy/postgres/`, `deploy/versions.yaml`,
  `.env.example`, `Makefile`, the `$DATA_DIR/postgres/` volume, and a numbered task record.
- Execution path: Pin the image by tag and digest. Add a healthcheck, an internal network, a
  non-root runtime where the image allows it, and an initialization script for schemas and roles.
  Add Make targets that source `scripts/shared/common.sh`.
- Acceptance gates: Starting from empty volumes reaches healthy. A restart preserves a probe row. No
  port is published to the host network. The roles exist with the declared privileges. `make ci`
  passes.
- Documentation target: A new `current/runtime-platform.md` page listed in the
  [areas index](current.md#areas).
```

Prerequisites: the task has no `Requires` entry. Docker Engine 29.9.3 with Compose v5.7.1 (the
Compose v2 plugin line) is installed on the development host.

## Implementation and decisions

The [runtime platform page](../current/runtime-platform.md) describes the delivered behavior.
Files: `deploy/compose.yaml`, `deploy/versions.yaml`, `deploy/postgres/initdb/10-kn-bootstrap.sql`,
`deploy/postgres/verify-roles.sql`, the `kn_db_*` and `kn_compose` helpers in
`scripts/shared/common.sh`, four Make targets, `.env.example`, and the tests
`tests/deploy/test_compose.py` and `tests/scripts/test_common_db.py`.

| Decision | Reason |
| --- | --- |
| `postgis/postgis:18-3.7` pinned by index digest | On 2026-11-21, PostgreSQL 19 had only `19rc2-3.7` images, so 18 is the newest major with a stable PostGIS image. PostGIS 3.7.0 is the newest stable minor, and the `18-3.7` build of 2026-11-16 carries PostgreSQL 18.7. `18-3.6` was last rebuilt on 2026-10-26. |
| Run as the invoking host user, refuse root | The image supports an arbitrary UID through `nss_wrapper`. Files under `$DATA_DIR` stay owned by the developer, `db-reset` needs no `sudo`, and the `0600` secret file stays readable only by that user. Running as root would need capabilities for the entrypoint's `gosu` step. |
| Read-only root file system, all capabilities dropped | The server writes only to the data volume, `/tmp`, and the socket directory, so the rest can be read-only. |
| `gateway_mode_ipv4: isolated` on the internal network | Measured: with only `internal: true`, the host connected to the container address on port 5432. With the option, the bridge has no host address and the connection fails. |
| Builtin `C.UTF-8` locale provider | Collation must not change when a new image digest brings a new C library, because rebuilds must reproduce results. Ukrainian display order uses the ICU `uk-UA-x-icu` collation explicitly. This cannot be changed without a new cluster, so it is set now. |
| `--auth-host=scram-sha-256` | The image default trusts TCP from `127.0.0.1` inside the container. With this option, every TCP login needs the password. |
| Replace the image's init directory | The image script also creates `postgis_topology` and a `template_postgis` database, which no specification names. The bootstrap installs only `postgis`. |
| One idempotent bootstrap transaction, applied at init and on every `db-up` | A failure leaves no partial bootstrap. The rebuild task can rerun the same file after it recreates schemas, and new schemas reach existing volumes. |
| Healthcheck requires a bootstrap role | Measured: after a failed first initialization, the restarted container skipped init and was reported healthy without roles. |
| Random password generated at the default location | No default password exists, and a fresh checkout needs no manual secret step. A configured `KN_POSTGRES_PASSWORD_FILE` must exist, so a typo does not silently create a new secret. |
| Group roles only, no login roles | Which login joins which loader groups depends on the engine and service tasks. Adding logins now would add secrets that no consumer uses. |
| `TEMPORARY` revoked from `PUBLIC` | Least privilege. A loader that needs temporary staging tables gets a grant in its own task. |
| `make db-verify` added | The acceptance gate "roles exist with the declared privileges" needed a repeatable probe for the harness and the audit. It changes nothing, because it rolls back. |
| `pyyaml` declared as a development dependency | The Compose tests parse YAML. It was already locked as a transitive dependency, so the lock gained two lines and no new package. |

Scope note: the task listed no `scripts/` or `tests/` paths. The shell helpers follow the rule
that shared shell behavior lives in `scripts/shared/common.sh`, and the tests follow the rule that
behavior changes carry tests. `kn_load_env` now resolves `DATA_DIR` through the new
`kn_resolve_path`, with the same result.

## Acceptance evidence

Status: accepted on 2026-11-21, Docker Engine 29.9.3, Compose v5.7.1, Linux x86_64.

The acceptance script and its full log are kept in
`$DATA_DIR/acceptance/compose-database-service-20261121/` (`acceptance.sh`, `acceptance.log`).
It ran with the default `DATA_DIR=.data`, starting with `.data/postgres` absent.

| Gate | Evidence | Result |
| --- | --- | --- |
| Empty volume reaches healthy | `make db-up` with `.data/postgres` absent | exit 0 after 2 s, health `healthy`; server 18.7, PostGIS 3.7.0, locale `b/C.UTF-8` |
| Restart preserves a probe row | Owner creates `system.kn_acceptance_probe`, the loader inserts a row, then `docker compose restart`, then `make db-down` and `make db-up` | the row reads back after both; it was then dropped |
| No published port | `docker inspect` and `docker port` | `PortBindings={}`, `5432/tcp: null`, `docker port` empty |
| Not reachable from outside the network | TCP connect from the host to `172.18.0.1:5432`; `pg_isready` from a container on the default bridge | both fail (`no response`, exit 2) |
| Roles with the declared privileges | `make db-verify` | `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`; 30 `kn_*` roles, all `NOLOGIN`; each schema owned by its `kn_<schema>_owner` |
| Non-root runtime | `/proc/1/status` in the container | UID 1000, `CapEff 0`, read-only root file system |
| Password required over TCP | `psql -h 127.0.0.1` without a password in the container; a wrong password from a peer container | `no password supplied`; `password authentication failed` |
| `make ci` | full gate | exit 0; 87 tests passed |

Probe sensitivity. Each planted fault made `make db-verify` fail. Each fault was reverted
afterwards and the clean probe passed again. Scratch `DATA_DIR`, project `kn-scratch`:

| Planted fault | Failure reported |
| --- | --- |
| `GRANT CREATE ON SCHEMA space TO kn_space_loader` | `expected kn_space_loader to be refused: CREATE TABLE space.kn_verify_refused` |
| `GRANT kn_gdelt_loader TO kn_space_loader` | cross-schema insert expected to be refused |
| `ALTER ROLE kn_system_reader LOGIN` | `role kn_system_reader is missing or has login or elevated attributes` |
| `GRANT TEMPORARY ON DATABASE kn TO PUBLIC` | `PUBLIC keeps CONNECT, TEMPORARY, or public CREATE` |
| Analytics reader default privilege revoked | reader `SELECT` expected to be allowed |
| `ALTER SCHEMA supply OWNER TO postgres` | `schema supply is missing or not owned by kn_supply_owner` |

After the first fault, rerunning `make db-up` left the extra schema grant in place. The bootstrap
now revokes schema privileges from the loader and reader before it grants `USAGE`. A rerun then
converged, and the probe passed.

Failure paths, scratch `DATA_DIR`:

| Path | Result |
| --- | --- |
| Init script fails on an empty volume (override with a failing statement) | Before the healthcheck fix: restarted, skipped init, reported healthy with no roles. After: `unhealthy`, `make db-up` exit 1 after 102 s, the log tail shows the SQL error and the `make db-reset` hint. No partial role remained, because the bootstrap is one transaction. |
| `make db-down` on a fresh `DATA_DIR` with no volume or secret | exit 0; creates nothing |
| Configured password file missing; default password file empty | exit 1, `missing or empty`; nothing is created |
| `make db-reset` on a 72 MB volume holding a probe table | exit 0 in 2.4 s; the table is gone, the password file is kept, the probe passes |

Unit tests: 22 new tests. A mutation check confirmed that each of these breaks fails at least
one test: a published port, a manifest digest drift, the removed gateway mode, a literal
password, a schema dropped from the bootstrap, the removed reset guard, and the removed root
refusal. The tests now run with their working directory in `tmp_path`. During the mutation
check, the removed reset guard let a relative `DATA_DIR` create `relative/data/` in the checkout.
That directory was deleted.

Other checks: `make lint-md` exit 0. `make quality` exit 0. `git diff --check` clean. The new
documentation is ASCII only.

## Handoff

Plan counts before: 119 tasks (108 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 100,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `compose-database-service`.

Plan counts after: 118 tasks (107 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 99,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `database-integration-harness`; priority human
task unchanged.

Dependency changes: `compose-database-service` left the `Requires` fields of
`database-integration-harness`, `runtime-platform-implementation-audit`,
`inventree-test-service`, `kestra-service`, and `superset-service`. The harness `Dependencies`
field now links the runtime platform page. The service publishes no port, so the harness must
reach it from a container on the Compose network or through a mounted socket. It can run
`deploy/postgres/verify-roles.sql` as its role test. `runtime-platform` stays `planned` in the
registry, because the harness and the audit are open.

Later change, 2026-11-21: [record 0007](0007-adhoc-database-loopback-port.md) publishes the
database on `127.0.0.1:15432` at the owner's request, so the harness connects over TCP from the
host. The no-published-port evidence above describes the service as accepted in this record.

Notes for later tasks:

- The rebuild task (`development-rebuild-mode`) should run DDL under
  `SET ROLE kn_<schema>_owner`, so default privileges apply, and rerun the bootstrap after it
  recreates schemas.
- Cross-schema foreign keys need `USAGE` and `REFERENCES` grants between owner roles. None exist
  yet.
