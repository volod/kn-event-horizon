# Development Rebuild Mode

## Work contract

```markdown
#### development-rebuild-mode

Development keeps an explicit disposable rebuild alongside normal in-place migrations.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: The accepted [contract compiler](current/data-contracts/compiler.md).
- User-visible outcome: `kn db rebuild` drops and recreates the KN schemas from generated DDL and
  loads the reviewed seeds. It refuses to run in an environment marked as released.
- Scope boundary: Schema drop and recreate, the seed-load hook, grants, and the released-environment
  guard. Raw replay and decision replay come in `rebuild-from-raw`. Vendor databases are never
  touched.
- Data and artifact paths: `src/kn/db/`, `src/kn/cli.py`, `tests/integration/`.
- Execution path: Rebuild in one transaction per schema group, then verify catalog objects against
  the compiled contracts.
- Acceptance gates: A rebuild from empty creates every compiled object. A second rebuild is
  identical. The loader role cannot run DDL. The released guard refuses.
- Documentation target: `current/data-contracts.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Rebuild now regenerates all ten KN schemas as one atomic group under the existing platform
advisory lock. It executes PostgreSQL DDL generated in memory from the bundled contract, initializes
the same installed-contract marker as the editable Alembic baseline, and stamps Alembic head.
Normal upgrades keep their existing migration path. The bundle currently deploys 32 SATCOM tables
in `space`; the other schemas are empty until their storage contracts are implemented.

The explicit development guard runs before engine creation and again inside the rebuild function.
The Python function requires a caller-owned transaction and adds a savepoint, so failed DDL, seeds
or verification restore every schema even when the caller catches the error. Shared platform
policy recreates roles, schema ownership and default grants. Seed callbacks run as schema loader
roles, with no DDL privileges, through an explicit ordered registry. The registry is empty until
`seed-vocabulary-import` and `source-catalogue-import` deliver reviewed content. No proposal or
source package is loaded automatically.

This deliberately replaces the old SATCOM-only behavior: obsolete tables anywhere inside a KN
schema are removed. Reflection never follows foreign keys into external schemas. Tables drop
without cascade, and empty schemas drop with `RESTRICT`. External dependents and unsupported
non-table objects refuse safely instead of being cascaded away. Separate databases and durable
files remain untouched. Views, functions and standalone sequences that block the empty-schema drop
must be removed or migrated explicitly. Raw, identity and decision replay remain with their
respective planned tasks.

A planted missing check constraint initially passed existing Alembic structural verification.
Added compiled-catalog checks for exact table sets, primary key names and columns, check constraint
names, and table and column comments. Missing checks, renamed primary keys and missing comments
now refuse and roll back. Arbitrary check-expression equivalence remains outside verification,
as documented in the [current rebuild reference](../current/data-contracts/rebuild.md).

## Acceptance evidence

Status: accepted. All task acceptance gates passed.

- Initial `make plan-status`: 113 tasks, 102 agent, 11 human; 94 CLEAR, 8 RUN NEEDED,
  2 BLOCKED BY HUMAN, 9 HUMAN-GATED.
- `make db-up`: passed; started local PostGIS for acceptance without resetting its volume.
- `.venv/bin/python -m pytest tests/contracts/test_governance.py -q`: the new pre-engine guard and
  transaction regressions first failed against the old implementation. After implementation, the
  targeted governance, platform and operation suites passed all 22 tests.
- `make test-integration`: first passed 43 tests covering empty rebuild, repeatability, obsolete
  tables, seed hooks, real loader DDL refusal, rollback and external dependency refusal. A later
  missing-generated-check regression failed because no exception was raised, then passed after
  catalog verification was extended.
- `make ci-local`: passed; 431 unit tests and 49 local integration tests. Checks include formatting,
  lint, typing, complexity, shell lint, catalog and artifact drift, documentation links, and
  spec-plan integrity. An initial complexity finding in the new verifier was fixed at its source
  by extracting the per-table catalog check.
- `tests/integration/test_rebuild.py`: real PostGIS rebuild from no KN schemas; identical catalog
  and deterministic seed rows after two rebuilds; loader CREATE, ALTER and DROP refused; Python
  seed failures, SQL seed failures and damaged generated objects restore the original schemas;
  obsolete KN tables are removed; external tables and dependencies are preserved; unsupported
  views refuse without partial schema loss. All destructive probes roll back.
- `tests/integration/test_rebuild_cli.py`: the normal JSON CLI rebuilt and committed twice in a
  newly created temporary database. Both catalogs matched. Released mode then refused and kept a
  sentinel row. The temporary database was removed in teardown.
- Final `make ci`: passed with 431 unit tests on the updated implementation and plan.
- `make lint-md` and `git diff --check`: passed after current docs and plan updates.
- `make quality`: checks, 431 unit tests, 91.58% coverage (90% required), and Markdown lint
  passed. The build step first failed on a read-only uv cache; a writable-cache retry could not
  resolve PyPI inside the sandbox. `make build` then passed with sandbox escalation and the
  existing cache, producing both source and wheel distributions. No check was weakened.
- `make db-verify`: passed on the original database after the destructive probes rolled back.
  Cleanup inspection found zero scratch schemas and zero temporary rebuild databases.
  `make db-down` stopped the service started for this task and retained the database volume.
- Final CI log, machine-readable acceptance summary and copied distributions are preserved under
  `$DATA_DIR/rebuild-mode/acceptance-3MNcS9Im/`.

## Handoff

`development-rebuild-mode` leaves the plan, and its ID is removed from downstream `Requires`
fields. Seed import tasks and the optional data-contracts audit link the current rebuild hook.
The capability registry changes `data-contracts` from `planned` to `shipped`. No new task is added.
`data-contracts-implementation-audit` remains optional and open; reviewed seed content, identity
replay and `rebuild-from-raw` remain in their existing tasks.

Final `make plan-status`: 112 tasks, 101 agent, 11 human; 93 CLEAR, 8 RUN NEEDED,
2 BLOCKED BY HUMAN, 9 HUMAN-GATED. The next required agent task is `semantic-model-contracts`.
