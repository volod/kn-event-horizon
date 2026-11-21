# Runtime Platform

This page owns the local Compose stack and its database service. It serves the
[`runtime-platform`](../../design/spec.md#runtime-platform) capability. The stack has one service
so far, PostgreSQL with PostGIS. The integration test harness, Kestra, Superset, the proxy, and
inference are still in the [forward plan](../plan.md).

## Commands

Each target sources `scripts/shared/common.sh`, runs `kn_load_env`, and calls one `kn_db_*`
helper. The targets refuse to run as root and need Docker Engine with the Compose v2 plugin.

| Command | Behavior |
| --- | --- |
| `make db-up` | Creates the password file and `$DATA_DIR/postgres/` if they are missing, starts the service, waits up to 180 s for healthy, then applies the bootstrap again. When the service does not become healthy, it prints the last 30 log lines and exits 1. |
| `make db-down` | Removes the containers and the network. `$DATA_DIR/postgres/` is kept. |
| `make db-reset` | Runs `db-down`, deletes `$DATA_DIR/postgres/`, then runs `db-up`. The password file and the rest of `$DATA_DIR` are kept. It refuses a `DATA_DIR` that is empty, relative, or `/`. |
| `make db-verify` | Runs the role probe against the running database. It prints `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`, or fails with an error that names the first failed check. |

For an interactive session, run
`source scripts/shared/common.sh; kn_load_env; kn_compose exec postgres psql -U postgres -d kn`.
`kn_compose` passes the runtime user ID and the password file path to
`docker compose --file deploy/compose.yaml`. `kn_db_psql` runs a non-interactive `psql` as the
superuser in `kn`.

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
| Network | `internal`: internal, no IPv6, `gateway_mode_ipv4: isolated`; no published port |
| Health | TCP `pg_isready` to `127.0.0.1` and the role `kn_system_owner` exists |
| Restart | `unless-stopped`, 1 min stop grace period, 256 MB shared memory |

The password file defaults to `$DATA_DIR/secrets/postgres-password`. `make db-up` creates it with
64 random hex characters, mode `0600` in a `0700` directory, and never prints the value. A file
named by `KN_POSTGRES_PASSWORD_FILE` must already exist and be non-empty. The password takes
effect only when an empty volume is initialized. After that, change it with `ALTER ROLE`.

Authentication: TCP connections need a SCRAM password, also from inside the container. Unix
socket connections inside the container are trusted, and only `docker compose exec` reaches them.

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

## Verification

| Check | Command | Expected result |
| --- | --- | --- |
| Compose and manifest rules | `make test` | `tests/deploy/test_compose.py` passes: digest pins match the manifest, no ports, internal isolated networks, unprivileged services, secret files, the volume under `DATA_DIR`, and the schema lists cover `domains/` |
| Shell helpers | `make test` | `tests/scripts/test_common_db.py` passes against a stubbed `docker` |
| Healthy from empty | `make db-reset` | exits 0 with the container `Healthy` |
| Roles and privileges | `make db-verify` | the `kn roles verified` notice |
| No reachable port | `docker port <container>` and a TCP connect from the host to the container address | no binding; the connection fails |

`deploy/postgres/verify-roles.sql` runs every probe as one transaction and rolls it back. For each
schema the owner creates a table with a PostGIS column. The loader inserts, updates, selects, and
deletes, and is refused `CREATE`, `ALTER`, `TRUNCATE`, and `DROP`. The reader selects and is refused
`INSERT` and `CREATE`. For every pair of schemas the owner, loader, and reader of one are refused in
the other. The probe states its expected schema list itself instead of reading it from the
bootstrap.

The acceptance run, its planted faults, and its evidence are in
[record 0006](../records/0006-runtime-platform-compose-database-service.md).

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
- The builtin `C.UTF-8` collation sorts by code point, so the Ukrainian letters U+0490, U+0404,
  U+0406, and U+0407 (Ghe with upturn, Ie, I, and Yi) sort outside the alphabet. Display order
  uses `COLLATE "uk-UA-x-icu"`, which is available in the image. The builtin collation never
  changes with the C library of a new image digest.

## Known limitations

- The image is published for `linux/amd64` only. Another architecture needs a different image,
  recorded in the manifest as a fallback.
- The bootstrap converges what it declares: it re-grants privileges and restores role
  attributes, schema owners, and schema grants. It does not revoke extra table grants or role
  memberships added by hand. `make db-verify` reports those.
- Adding a schema to the bootstrap reaches an existing volume on the next `make db-up`. Removing
  one needs `make db-reset`.
