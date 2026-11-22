# Record 0007: database loopback port

## Work contract

Direct request on 2026-11-21, after `compose-database-service` was accepted in
[record 0006](0006-runtime-platform-compose-database-service.md): use a non-standard PostgreSQL
port by default, so that the KN database and the `vl-itree` stack can run in parallel on the
same host.

Neither stack published a host port, so the two could already run side by side. The owner chose
to publish the KN database on `127.0.0.1:15432`, with the port configurable, so that host tools
and host-run tests can connect. This changes the [runtime platform](../../design/spec.md#runtime-platform)
promise "no database port is published". The specification section, its registry row, and the
dependent plan tasks are amended in the same change.

Scope: the Compose service and networks, the shell helpers, `.env.example`, tests, the
specification and plan wording, and the current-state page. No login roles, TLS, or new Make
targets.

## Implementation and decisions

The [runtime platform page](../current/runtime-platform.md) describes the delivered behavior.
Files: `deploy/compose.yaml`, `scripts/shared/common.sh` (`kn_db_host_port`, and port handling in
`kn_compose` and `kn_db_up`), `.env.example`, `README.md`, `tests/deploy/test_compose.py`,
`tests/scripts/test_common_db.py`, the specification section and registry row, and the plan
tasks `database-integration-harness` and `operations-hardening-implementation-audit`.

| Decision | Reason |
| --- | --- |
| Host port `15432`, set by `KN_POSTGRES_HOST_PORT` | Non-standard, so a PostgreSQL on `5432` keeps its port. It is below the Linux ephemeral range (32768-60999), so an outgoing connection cannot hold it. |
| The server inside the container stays on `5432` | Each container has its own network namespace, so the inside port never collides. The healthcheck, the image defaults, and other services on `internal` keep the standard port. |
| Published on `127.0.0.1` only, with no address setting | Loopback is the promise. A LAN address would need TLS and a separate decision. |
| A second network, `loopback`, joined only by publishing services | Measured: Docker publishes no port of a container that is attached to internal networks only. `internal` stays internal and isolated for traffic between services. |
| `host_binding_ipv4: 127.0.0.1` on `loopback` | A port added later without an address still binds to loopback only. Measured with `-p 15499:5432`. |
| `enable_ip_masquerade: false` on `loopback` | The database needs no outbound traffic. Without source NAT, replies from outside cannot return. Measured: the loopback port still works, because `docker-proxy` serves it. |
| The port is checked in `kn_compose` and `kn_db_up` | Compose interpolates the whole file for every command, so `db-down` needs a valid port too. `kn_db_up` checks it before it creates a password file or volume. |
| The failure hint names the port | A taken port fails before the container starts, with Docker's `port is already allocated`. The former hint named only `make db-reset`. |
| `make db-up` prints the address and the password file path | Host tools need both. The password itself is never printed. |
| No TLS on the loopback port | Loopback traffic does not leave the host. The security audit gate now requires TLS beyond loopback and authentication everywhere. |
| No opt-out of the published port | Not requested. A later task can add one if a host must not expose even loopback. |

## Acceptance evidence

Status: accepted on 2026-11-21, Docker Engine 29.9.3, Compose v5.7.1, Linux x86_64.

The acceptance script and its full log are kept in
`$DATA_DIR/acceptance/database-loopback-port-20261121/` (`acceptance.sh`, `acceptance.log`). It ran
the default project on the existing `.data` volume. The second-checkout and port-conflict cases
used throwaway `DATA_DIR`s and Compose projects. Client checks ran `psql` and `pg_isready` from the
pinned image, in the host network namespace for host-side probes.

Pre-change probes, throwaway containers and networks:

| Probe | Result |
| --- | --- |
| `-p 127.0.0.1:15499:5432` on an `internal`, isolated network | `PortBindings` recorded, `Ports` `null`, `docker port` empty, host connect refused |
| Plain bridge with `host_binding_ipv4: 127.0.0.1`, `-p 15498:5432` | bound to `127.0.0.1:15498`; loopback accepting; LAN address `no response` |
| The same with `enable_ip_masquerade: false` | the same; loopback served by `docker-proxy` |
| Outbound TCP from either container | timed out, but it also timed out from the host network namespace, so egress blocking is not measured |

Gates on the change:

| Gate | Evidence | Result |
| --- | --- | --- |
| Default port | `make db-up`, then `docker port` | healthy; `5432/tcp -> 127.0.0.1:15432`; it printed `Database kn is on 127.0.0.1:15432` and the password file path |
| Networks | `docker network inspect` | `loopback`: internal `false`, masquerade `false`, host binding `127.0.0.1`. `internal`: internal `true`, gateway mode `isolated` |
| Host connects with a password | `psql -h 127.0.0.1 -p 15432` | `kn`, server 18.7, PostGIS 3.7.0 |
| Password required | `psql -w`; a wrong password | `fe_sendauth: no password supplied`; `password authentication failed for user "postgres"` |
| Loopback only | `pg_isready` to the host LAN address `:15432`; from a default-bridge container to both container addresses `:5432` and to `172.17.0.1:15432` | all `no response`, exit 2 |
| Parallel with a standard-port PostgreSQL | A throwaway PostgreSQL published on `127.0.0.1:5432`, started beside KN | both accepting; KN `healthy` |
| Taken port | `KN_POSTGRES_HOST_PORT=5432 make db-up` in a scratch project while `5432` was taken | exit 2; `Bind for 127.0.0.1:5432 failed: port is already allocated` and the new hint |
| Second checkout | Project `kn-accept-second`, empty `DATA_DIR`, port `15433`, beside the default | healthy from empty; `make db-verify` passed; both ports answered |
| Invalid port | `KN_POSTGRES_HOST_PORT=5432x make db-up` | exit 2; `must be a port from 1 to 65535, got '5432x'`; no Docker call |
| Roles and data | `make db-verify`; a probe row through `make db-down` and `make db-up` | `kn roles verified: 10 schemas, 30 roles, postgis 3.7.0`; the row read back, then was dropped |
| Clean-up | `make db-down`; `docker ps -a`, `docker network ls` | no KN or probe containers or networks remain; the stack is stopped as before |

Unit tests: the suite grew from 87 to 106 tests, and three existing tests were extended. A
mutation check reverted each of these, one at a time, and
each made at least one test fail: the `host_ip`, the `loopback` network on the service, the host
binding option, the masquerade option, the `15432` default, the port check in `kn_compose`, and
the strict port pattern.

Other checks: `make ci` exit 0 with 106 tests. `make quality` exit 0 after one Markdown line was
wrapped. `git diff --check` clean. The changed files are ASCII only.

## Handoff

Plan counts before and after: 118 tasks (107 agent, 11 human); statuses BLOCKED BY HUMAN 2,
CLEAR 99, HUMAN-GATED 9, RUN NEEDED 8. No task was added or removed. Priority agent task
`database-integration-harness`; priority human task unchanged.

Specification change: the [runtime platform](../../design/spec.md#runtime-platform) section now
promises a loopback-only database port with a password instead of no published port, and its
evaluation and registry row say the same. `runtime-platform` stays `planned`.

Dependent tasks:

- `database-integration-harness`: the `Dependencies` field says that host-run tests connect over
  TCP to `127.0.0.1` at `KN_POSTGRES_HOST_PORT`. The harness still needs a login role or the
  superuser password file.
- `operations-hardening-implementation-audit`: the scope and gate now require TLS and
  authentication beyond loopback, and authentication on loopback endpoints.
- `runtime-platform-implementation-audit`: its scope now names the loopback-only port and the
  unmeasured outbound traffic from the database container. It should rerun `acceptance.sh` and
  measure egress on a host with an outbound route.
