# Source Status Monitoring

## Work contract

```markdown
#### source-status-monitoring

Operators need per-source health and freshness without opening Kestra.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Dependencies: The [fixture runner](current/ingestion-engine.md#run-and-replay-a-snapshot)
  and [run history and health fields](current/ingestion-engine.md#run-history-and-health).
- User-visible outcome: `kn source status` shows the last success and attempt,
  state, stale flag, counts, bytes, budget use, cursor lag, and last error code, and feeds the
  operations mart.
  Read the registered run and checkpoint tables.
- Scope boundary: Status computation from run records and the CLI. Dashboards come in
  `space-dashboard-bundles`.
- Data and artifact paths: `src/kn/sources/status.py`, `tests/sources/`.
- Execution path: Compute status from fixture runs covering every run status and error code.
- Acceptance gates: Stale detection follows the configured threshold. Every error code renders.
  Golden outputs cover English text and stable JSON.
- Documentation target: `current/source-management.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Added the read-only `kn source status PROFILE` command and `read_source_status` projection.
A single PostgreSQL query scopes the catalogue, run history, errors, and checkpoint to the
selected stream. The command defaults to the runner's `default` scope and `live` namespace.
The [current-state page](../current/source-management.md#source-health-and-freshness) documents the
stable result fields, reader role, and threshold rules.

The optional schedule threshold overrides the declared monitoring SLA. A successful or
unchanged fetch confirms freshness, while replay can appear as the latest attempt or success.
The latest checkpoint revision supplies its time watermark when applicable. Staleness uses
the exact age and lag reports whole seconds. Negative ages clamp to zero.

### Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| STATUS-01 | minor | The catalogue checker rejected a conditional message key for the boolean flags. | Source management. Fixed by resolving both message keys explicitly. |
| STATUS-02 | minor | `make db-up` started a healthy PostGIS container, then returned `E_INPUT` during the persistent database upgrade. The connection probe and disposable fixture rebuilds succeeded. | Local runtime. Preserved the persistent database and used the disposable databases and scratch schema for verification. |
| STATUS-03 | minor | The complexity gate flagged the expanded CLI integration case. | Source management. Split stream selection and unknown-source handling into their own case. |
| STATUS-04 | minor | Overlapping fixture invocations raced on the cluster-wide `ALTER ROLE` during database setup. | Verification. Retried the integration suite as a single invocation. |

## Acceptance evidence

Accepted. The first `make plan-status` counted 108 tasks, with 96 agent and 12 human. Records 0058 and
0059 establish the ingestion state and fixture runner prerequisites.

- `source scripts/shared/common.sh && kn_load_env && kn_db_test_env &&
  .venv/bin/python -m pytest tests/sources tests/engine tests/integration/test_ingestion_state.py`
  passed 166 tests in a single invocation. The log and JUnit report are
  `serial-fixtures.log` and `serial-results.xml` under
  `$DATA_DIR/source-status-monitoring/check-epExBkHO/`.
- The operator CLI read a successful loopback HTTPS snapshot, an unchanged snapshot, and a
  skipped archive replay. Status issued zero additional HTTPS requests. The fixture data
  covered all six terminal outcomes, unfinished and never-run states, and all nine error codes.
  Exact English and JSON goldens passed. The reader-role test used a read-only transaction in
  a different database time zone and checked the exact freshness boundary.
- Fixture checks also covered isolated scopes and namespaces, a retry with clock skew,
  watermark lag by revision, null versus measured zero, and unknown source rejection.
- `make lint-md lint-spec-plan` and `git diff --check` passed.
- `make ci` passed with 1,492 lightweight tests and 170 local-only tests deselected. The
  `ci.log` is in the same evidence directory.

## Handoff

Plan counts move from 108 to 107 tasks, from 96 to 95 agent tasks, and from 99 to 98 DELIVERY
tasks. The 12 human and nine MODEL tasks are unchanged. The source management audit is next and
consumes this record. The registry links the available status command under source management,
whose audit remains open. `space-analytics-marts` owns materialization and checks the operations
mart against the source status projection before and after replay.
