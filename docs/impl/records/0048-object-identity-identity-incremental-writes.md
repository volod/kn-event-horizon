# Identity incremental writes

## Work contract

```markdown
#### identity-incremental-writes

Each identity write rereads and validates the whole journal and rewrites every identity table, so
one submit slows as the registry grows and a large source ingests in quadratic time.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: Finding IDRES-05 and its measurements in the
  [identity resolution audit](records/0042-object-identity-identity-resolution-implementation-audit.md#findings).
- User-visible outcome: A source adapter submits observations at a cost that stays flat as the
  registry grows. Each write appends its events and updates only the rows they change, and a
  rebuild still reproduces every row.
- Scope boundary: Reuse of the validated journal state under the writer lock, incremental SQL
  projection of new events and their ownership changes, and indexed candidate and attribute
  lookup. Event formats, match decisions, recovery and rebuild semantics stay unchanged. Profile
  values and calibration are out of scope.
- Data and artifact paths: `src/kn/identity/`, `tests/identity/`, `tests/integration/`,
  `$DATA_DIR/identity/`.
- Execution path: Extend the replay growth check to journal-backed submits and PostgreSQL
  projection, measure the current curve, then change the writer.
- Acceptance gates: On a synthetic organization registry, one PostgreSQL submit at 50,000 objects
  costs at most twice as much as at 5,000 objects. Rows after incremental writes equal the rows of
  a rebuild after dropping the database. Interrupted, retried and concurrent writes keep their
  current recovery results. `make ci` and the local integration suite pass.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

- A reused `Journal` retains a validated replay state under its file lock. The cache is keyed by
  file device, inode, size and nanosecond modification and change times. File changes outside
  the instance trigger full validation. A rejected batch restores its original in-memory prefix,
  and an interrupted append invalidates both the lock's state and the cache until reopen.
- The same replay transitions identify the objects, source records, holdings and redirect sets to
  update. The writer appends journal events before SQL projection and closes old links before it
  inserts replacements. It tracks a pending suffix again after SQL rollback. Explicit replay
  validates the entire SQL event prefix and replaces the disposable state.
- Alembic revision `0002_identity_checkpoint` adds a transactional validation checkpoint and a
  trigger that invalidates it on SQL update, delete or truncate of event rows. The event sequence
  index checks for extra SQL history before append. The migration can run on an existing database
  without a rebuild.
- Matching narrows lookup by active owner, authoritative key, source record, aliases and
  normalized historical blocking values. It still checks each complete blocking key against
  the latest readings at the observation instant for each source record. Retries verify the
  original match's follow-ups by querying the source record and identifier keys, then checking
  their event sequences.
- Reviewed lifecycle writes validate the transition before fsyncing the decision and then the
  identity event. Existing reviewed bindings keep their journal and SQL checks.

## Acceptance evidence

Accepted. Runtime logs are under `$DATA_DIR/identity/incremental-writes-vaTH9b7T/`.

- The original writer failed the synthetic PostgreSQL growth check. Warm medians across five
  distinct submits were 2.957 s at 5,000 organizations and 35.110 s at 50,000, a ratio of 11.873
  (`scale-before.log`). Each registry was seeded by journal replay. Timing starts at the
  adapter's `submit` call inside a caller-owned transaction and includes journal fsync and SQL.
- The first implementation run measured 20.842 ms and 31.071 ms, a ratio of 1.491
  (`scale-after.log`). The final implementation measured 18.660 ms and 28.960 ms, a ratio
  of 1.552 against the 2.0 limit (`integration-final.log`). Cold submits took 1.150 s and
  11.055 s respectively, including full journal validation and the initial blocking index.
- The caught append interruption regression failed before the fix and passed with the final
  journal tests (`interruption-red.log`, `interruption-green.log`). The replay growth check and
  typed DDL checks passed (`replay-growth.log`).
- `make db-upgrade` advanced the isolated pinned PostGIS database from `0001_baseline` to
  `0002_identity_checkpoint` and verified the database (`db-upgrade.log`).
- `make ci` passed 1,425 tests with 123 integration or heavy tests deselected (`ci-final.log`).
  `PYTEST_ADDOPTS=--capture=tee-sys make test-integration` passed all 122 local PostgreSQL tests
  (`integration-final.log`). The suite compared every registered identity row after committed
  incremental writes and two rebuilds following database drops. It also verified ownership
  changes, unaffected rows, divergent SQL history, rollback, partial appends, retries and
  concurrent writers.
- `make lint-md lint-doc-links lint-spec-plan` and `git diff --check` passed. The isolated PostGIS
  container, networks and scratch database volume were removed.

## Handoff

The plan went from 114 to 113 tasks, with agent tasks down from 102 to 101 and 12 human tasks.
DELIVERY went from 102 to 101 with 12 MODEL tasks. The object identity implementation audit is
the next agent task and links to this record. The `object-identity` capability remains planned
while that audit and identity match calibration are open.
