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
command. The rebuild replays identity events, loads reviewed seeds, then restores human
verification for exact targets already present. SATCOM targets can stay pending until the import
restores their snapshot. See the [replay reports](../evidence-model.md#durable-history-and-conflicts).
Raw archive replay remains planned.

## Execution and transaction boundary

`src/kn/db/rebuild.py` drops the KN schemas and then runs the normal `kn db upgrade` path:
`alembic upgrade head`, whose environment converges the platform policy, and the editable baseline
`0001_baseline`. The baseline creates every contract of the
[deployment set](../data-contracts.md#deployment-set) from its SQLAlchemy metadata as its schema
owner, in registry order, and records one row per contract in `system.installed_contracts`. A
rebuild and an upgrade of an empty database therefore use one mechanism. Revision
`0002_identity_checkpoint` installs the internal identity checkpoint and its invalidation trigger
through typed DDL. The generated `postgresql/schema.sql` is a review artifact. Archived source
`schema.sql` files are never used for deployment. The current set holds governance and source catalogue
tables in `system`, 31 SATCOM tables in `space`, 18 semantic tables in `semantic`, 12 tables in
`evidence` including the human decision log, and ten [identity tables](../object-identity.md).
The other five schemas have no contracted datasets.
`rebuild()` and `upgrade()` accept another validated set, which the integration tests use for
fixture contracts in `space` and `semantic`.

The caller owns the transaction. A nested transaction groups all KN schemas, because cross-schema
references and the migration marker must stay consistent. The shared platform advisory lock
serializes bootstrap, upgrade and rebuild. Rebuild reflects only KN tables without following
foreign keys outside them, drops the tables without cascade, then drops the empty schemas with
SQLAlchemy `DropSchema`, which PostgreSQL applies as `RESTRICT`. The drop also removes the
migration-owned checkpoint function. Identity replay, reviewed seeds, human verification replay
and catalog verification all run inside the rebuild transaction. The CLI writes a private report
for verification targets after commit.

External dependencies refuse instead of being cascaded away. Non-table schema objects that the
compiler does not manage, such as views, functions or standalone sequences, also refuse if they
prevent an empty-schema drop. A refusal restores the previous schemas. Remove or migrate such
objects explicitly before retrying. A failed revision, seed loader or catalog check rolls back
the complete group even when the caller catches the exception. A rebuild process that is killed
midway leaves the previous committed schemas in use: readers keep the old catalog and wait for the
dropped tables' locks, and the server rolls the transaction back when it notices the lost client.

Without `KN_ENVIRONMENT=development`, the command reports
`E_INPUT: rebuild requires KN_ENVIRONMENT=development; ...` in the selected locale.

## Reviewed seed hook

`src/kn/db/seeds.py` owns the ordered `REVIEWED_SEED_LOADERS` registry. Each entry supplies a KN
schema and a deterministic callable accepting the rebuild connection. The hook runs the callable as
that schema's loader role (`SET LOCAL ROLE`), with DML privileges only, and then resets the role.
Loaders must use the supplied transaction and must not commit independently. An exception aborts the
rebuild.

The registry loads the [reviewed source catalogue](../source-management.md) as the system
loader and the [reviewed semantic vocabulary](../ontology-taxonomy/seeds.md) as the semantic
loader. Both use packaged files. Proposal workbooks remain offline inputs. Restore SATCOM
source data with the separate import command.

## Verification

After the rebuild, the existing governance checks verify Alembic head, contract digest, table and
column types, nullability, foreign keys, indexes, role attributes, schema isolation and table and
sequence grants. Marker verification compares every stored field: contract ID, version, digest,
storage schema and the exact managed-table list, using the same definition as marker creation.
`verify_compiled_catalog` additionally checks the exact compiled table set,
primary key names and columns, check constraint and foreign key names, and table and column
comments. Structural verification also compares PostGIS geometry types and SRIDs, which Alembic
reflects as an unknown type. It does not
prove equivalence of arbitrary manually edited check expressions.

`tests/integration/test_registry.py` rebuilds twice with fixture contracts beside SATCOM, checks the
marker rows and tables of every contract, and plants a missing table, a drifted or missing marker
row, and unregistered tables in `space` and in a schema without contracts; verification refuses
each. `tests/integration/test_rebuild.py` starts from empty KN schemas, rebuilds twice, compares
catalog structure and deterministic seed rows, and exercises real loader DDL refusals. After the
baseline it plants a dropped check, a renamed primary key or foreign key, and a missing comment, and
it plants seed exceptions and SQL errors, obsolete tables, external dependencies and unsupported
views. It also records every SQL string the rebuild sends and finds no `CREATE TABLE`.
`tests/integration/test_rebuild_interrupt.py` kills a rebuild process while it holds the dropped
schemas and checks that the catalog, a sentinel row and verification are unchanged. Destructive
probes roll back and leave the original database in place. Run `make test-integration` against local
PostGIS, or `make ci-local` for both the required CI gate and local-only tests.
The [combined fixture check](model-baseline.md) rebuilds the complete registered set twice with
the source catalogue, real SATCOM, semantic rows, identity history and human decision fixtures; its
full-model checkpoint remains open.

[Task record 0016](../../records/0016-data-contracts-development-rebuild-mode.md) preserves acceptance
evidence and the plan transition, and the group audit in
[record 0017](../../records/0017-data-contracts-data-contracts-implementation-audit.md) replaced the
executed DDL string with the Alembic path.
