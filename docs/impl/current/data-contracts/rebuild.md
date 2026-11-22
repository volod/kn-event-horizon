# Development Rebuild

`kn db rebuild` and `make db-rebuild` recreate all ten KN schemas declared in
`src/kn/contracts/resources/platform.json`. Set `KN_ENVIRONMENT=development` explicitly. Every other
value, including `released` or an unset value, refuses before opening a database connection. The
Python function checks again before any database work. Normal `kn db upgrade` continues to apply
reviewed Alembic migrations in place.

```bash
make db-up
KN_ENVIRONMENT=development make db-rebuild
make db-verify
make satcom-import
```

All tables inside KN schemas are disposable, including obsolete tables absent from the current
contract. This replaces the earlier SATCOM-only rebuild that kept unmanaged tables inside `space`.
Separate databases, schemas outside the KN list, PostGIS in `public`, and files under `DATA_DIR`
are preserved. A rebuild clears imported SATCOM rows; restore them explicitly with the import
command. Raw archive replay, identity event replay and decision replay remain planned.

## Execution and transaction boundary

`src/kn/db/rebuild.py` loads the bundled contract and generates its PostgreSQL DDL in memory using
`kn.contracts.ddl.postgresql_ddl`. It never executes an artifact supplied through `generated/` or
an archived source SQL file. The current bundle contains 32 SATCOM tables in `space`; the other nine
schemas have no contracted datasets yet. Future storage contracts must be added explicitly to the
deployment set together with their verification.

The caller owns the transaction. A nested transaction groups all KN schemas, because cross-schema
references and the migration marker must stay consistent. The shared platform advisory lock
serializes bootstrap, upgrade and rebuild. Rebuild reflects only KN tables without following
foreign keys outside them, drops the tables without cascade, then drops the empty schemas with
`RESTRICT`. It recreates schemas and grants through the shared Python policy, executes generated
DDL as the schema owner, initializes the installed-contract marker, and stamps Alembic head.
It then loads reviewed seeds and verifies the database before returning.

External dependencies refuse instead of being cascaded away. Non-table schema objects that the
compiler does not manage, such as views, functions or standalone sequences, also refuse if they
prevent an empty-schema drop. A refusal restores the previous schemas. Remove or migrate such
objects explicitly before retrying. A failed DDL statement, seed loader or catalog check rolls back
the complete group even when the caller catches the exception. No migration runs outside the
caller's transaction.

## Reviewed seed hook

`src/kn/db/seeds.py` owns the ordered `REVIEWED_SEED_LOADERS` registry. Each entry supplies a KN
schema and a deterministic callable accepting the rebuild connection. The hook runs the callable
as that schema's loader role, with DML privileges only, and then resets the role. Loaders must use
the supplied transaction and must not commit independently. An exception aborts the rebuild.

The registry is currently empty: ontology vocabulary and source catalogue review are separate plan
tasks. Proposals are never loaded automatically, and SATCOM source imports are not seed data. Those
tasks will register loaders for their reviewed files; this task supplies and tests the hook.

## Verification

After the rebuild, the existing governance checks verify Alembic head, contract digest, table and
column types, nullability, foreign keys, indexes, role attributes, schema isolation and table and
sequence grants. `verify_compiled_catalog` additionally checks the exact compiled table set,
primary key names and columns, check constraint names, and table and column comments. It does not
prove equivalence of arbitrary manually edited check expressions.

`tests/integration/test_rebuild.py` starts from empty KN schemas, rebuilds twice, compares catalog
structure and deterministic seed rows, and exercises real loader DDL refusals. It plants missing
checks, altered primary key names, missing comments, seed exceptions and SQL errors, obsolete
tables, external dependencies and unsupported views. Destructive probes roll back and leave the
original database in place. Run `make test-integration` against local PostGIS, or `make ci-local`
for both the required CI gate and local-only tests.

[Task record 0016](../../records/0016-data-contracts-development-rebuild-mode.md) preserves acceptance
evidence and the plan transition.
