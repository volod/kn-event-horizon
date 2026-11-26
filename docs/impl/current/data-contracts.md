# Data Contracts and Space Example Import

The space domain has an initial SATCOM source dataset: owner-supplied, prefetched files from a real
space source, kept as the first data integration example. More prefetched datasets will follow
through a shared path (`prefetched-dataset-method` in the [plan](../plan.md)); today the adapter is
SATCOM-specific. SATCOM is a subset of space, not a domain, service, or PostgreSQL schema of its
own. This implementation supplies the first bounded profile
of the [data contracts capability](../../design/spec.md#data-contracts). The remaining ontology content,
matching, interchange and raw replay work stays in the [plan](../plan.md).

## One definition for each model

`src/kn/contracts/resources/satcom/1.0.0.json` is the ODCS source of truth for the example dataset.
It declares `domain: space` and storage schema `space`. It contains all 28 CSV tables and three
bookkeeping tables: `satcom_imports`, `satcom_files`, and `satcom_rows`. The bundled resources ship
in the wheel, so validation and deployment do not need network access.

## Deployment set

`src/kn/contracts/resources/registry.json` is the reviewed list of deployed storage contracts, in
deployment order, with paths relative to the registry and an optional reference catalog per entry:

```json
{
  "contracts": [
    {"path": "system/1.0.0.json"},
    {"path": "system/source-catalogue/1.0.0.json"},
    {"path": "satcom/1.0.0.json"},
    {"path": "semantic/1.0.0.json"},
    {"path": "evidence/1.0.0.json"},
    {"path": "identity/1.0.0.json", "references": "identity/references.json"}
  ]
}
```

The identity entry deploys the [identity registry and replay model](object-identity.md).
The semantic entry deploys the [ontology meta-model](ontology-taxonomy.md), with no content import.
The first entry is the governance contract `kn.system.governance`. Its table
`system.installed_contracts` is the installed-contract marker: one row per registered contract with
version, digest, storage schema and table names. The next entry deploys the
[source catalogue](source-management.md) beside it. `kn.contracts.registry.registered_contracts()`
loads and validates every entry without touching a database. It refuses a file outside the registry
directory, a registry that does not start with the governance contract, a repeated contract ID, a
field ID used by two contracts, and a table, primary key or index name used twice in one schema.
Several contracts can share a schema; the SATCOM dataset and later prefetched datasets share
`space`. The loader refuses a `kn.storageSchema` outside the ten platform schemas before it resolves
any reference, and `kn db upgrade|verify|rebuild` load the registry before opening a connection.

`kn db upgrade` and `kn db rebuild` create every registered contract as its schema owner through the
Alembic baseline and record each marker row. `kn db verify`, every upgrade and rebuild, and every
import check that the marker rows equal the registry (no missing, extra or drifted contract), that
the structure of every registered table matches its contract, and that every table in a KN schema
belongs to a registered contract or is one of the internal tables, `system.alembic_version` and
`identity.projection_checkpoint`. Partitions count with their parent. To register a contract, add
its file and entry, run `make contract-compile`, and rebuild the development database.

Contracts refer to each other only by stable field IDs, which the registry keeps unique, and by KN
IDs that the owning engines check. SQL foreign keys stay within one contract. A cross-schema
foreign key would need `REFERENCES` grants and `USAGE` on another schema for its owner role, which
the least-privilege policy refuses and verifies, and it would couple the drop and migration order of
contracts. A capability whose integrity rule needs database-enforced references across schemas
amends this decision together with the grants it needs.

The official ODCS 3.1.0 JSON Schema is vendored with upstream and local checksums in `pins.json`.
The local copy only escapes non-ASCII characters as JSON escapes. Both standard and extension
schema checksums are mandatory and verified offline on every lint and compile.

## Contract lint and toolchain

`kn contract lint <file.yaml>` validates YAML or JSON against ODCS 3.1.0 and the closed schemas for
every `kn.*` family in the specification. Omitting the file validates every registered contract.
Lint checks types, required members, allowed locations, duplicate extensions and unknown names.
It does not resolve ontology, policy, vocabulary, mapping or dataset references. The
[toolchain reference](data-contracts/toolchain.md) lists extension shapes, diagnostics, parser
limits, and the pinned external tool's verification command.

The compiler accepts supplied JSON or YAML contracts and resolves local reference catalogs before
producing SQLAlchemy metadata, generated PostgreSQL DDL, strict Pydantic models, JSON Schema, Avro,
Elasticsearch mappings, dbt sources and contract documentation. The
[compiler reference](data-contracts/compiler.md) describes the supported profile, reference catalog,
PostGIS and partition templates, output paths, and exact-byte drift checks.

`make contract-check` validates every registered contract and compares the committed
`generated/contracts/<contract-id>/` of each (SATCOM: 100 artifacts plus a manifest, including
physical mappings and generated DDL) byte for byte with a fresh compile; a directory of an
unregistered contract is drift. `make contract-compile` refreshes them. `kn contract compile` with a
source defaults to `generated/contracts/<contract-id>/`, and `--output <directory>` selects another
destination. Without a source, `--output <root>` receives one directory per registered contract.
Normal upgrades and the explicit development rebuild both run the Alembic baseline over the
contracts' SQLAlchemy metadata. No SQL text reaches the database:
schema objects come from SQLAlchemy metadata, and the platform policy from typed statements.

## Human verification metadata

The [shared human verification protocol](evidence-model.md) adds a registered decision-log contract
and typed record/field targets, UTC/null semantics, authenticated reviewer context, durable history
and transactional application. With the [evidence contracts](evidence-model.md#evidence-contracts),
the registry defines 73 tables and 707 fields. Every table declares coverage for its record and
fields. The registry validates this at registration, and
[the shared read projection](evidence-model.md#current-verification-reads) exposes the current
metadata with audience filtering.

SATCOM `verification_status` is imported source data; semantic `verification_state`, publication
`reviewed_on` dates and label `review_reference` values retain their specialized meanings. None
sets a universal human verification time. Existing data is not backfilled as human-verified from
those values. The [model review](../records/0028-adhoc-human-verification-model-review.md) records
why authority, exact time and version binding are required.

## Development baseline and release evolution

The [contract workflow](../../guide/schema-first-development.md) pairs each contract with its
first consumer. `make model-baseline` checks the registered subset and preserves evidence.
The [baseline reference](data-contracts/model-baseline.md) describes its current coverage.
The full integrated check and its audit remain release prerequisites.

Development keeps contract version `1.0.0` and an editable Python Alembic baseline,
`0001_baseline`, that creates every registered contract. Revision `0002_identity_checkpoint`
adds the internal identity prefix checkpoint and its invalidation trigger to existing and fresh
identity deployments. A contract edit changes its digest. Refresh the committed `generated/`
output after reviewing it. Normal `make db-upgrade` verifies the
installed digest and structure; it does not silently alter an existing projection to match edited
development definitions.

For a development model edit:

1. Edit the `1.0.0` contract, baseline if needed, and regression fixtures.
2. Run `make contract-compile`, review the `generated/` diff, and run `make ci`.
3. Set `KN_ENVIRONMENT=development` and run `make db-rebuild`.
4. Run `make satcom-import` to restore the example dataset from the source package.

Rebuild now recreates all ten KN schemas, removes obsolete KN tables, loads registered reviewed
seeds and verifies the compiled catalog. It preserves external schemas and durable files. External
dependencies and unsupported non-table objects refuse without cascade. The
[development rebuild reference](data-contracts/rebuild.md) describes its transaction boundary,
seed hook, safeguards and tests. Without explicit development mode, including when
`KN_ENVIRONMENT=released`, rebuild fails before database access.

At first release, freeze the baseline and contract `1.0.0`. Subsequent releases add contract
snapshots and Python Alembic revisions. `evolution.py` supplies conservative diff validation and
additive operations for new tables and nullable fields. It refuses removals, renames, type,
identity, nullability, enum, reference and precision changes, and new constrained fields that need
backfill. Changes to table metadata or reference definitions and new fields with semantic
extensions require reviewed migrations instead of silently losing new compiler behavior.
Additive evolution adds new fields with their comments, applies changed table and field
descriptions, and updates the contract's row in `system.installed_contracts`. A revision calls this
helper
with reviewed old and new contracts; deployment never autogenerates or applies arbitrary drift.
Destructive downgrades are refused. The full-model release gate remains `release-migration-mode`.

## Source preservation and import

`make satcom-validate` reads `$DATA_DIR/satcom_enriched_package` without writing. `make satcom-import`
validates, archives, checks the installed contract, and imports it into `space`. `kn space satcom
validate|import <directory>` accepts another package in the same source format. Make loads `.env`
and resolves `DATA_DIR` from the project root through the shared shell helpers.

The adapter reads exactly the 28 contracted CSV files and their ordered headers. It rejects
missing or extra CSV files, malformed row widths, duplicate primary keys, broken references,
required blanks, invalid calendar dates, enum errors, non-finite or excessive decimals, malformed
booleans, and out-of-range integers. Missing numeric values remain null; zero and false survive.
Partial dates retain their original precision. Source labels and quotations remain Unicode data;
JSON artifacts and fixtures use ASCII escapes without changing those values.

All CSV fields are preserved, including provenance quotes and locators, original and normalized
values, qualifier/ranges, canonical selection flags and rules, formula text and input claim IDs,
mass and throughput bases, verification states, aliases, contextual observations, and gaps with
missing reasons. No unit, reference or semicolon-separated source expression is silently rewritten.
Source verification labels are preserved assertions, not a new verification of public websites.

Each snapshot is identified by a SHA-256 over ordered relative file names, lengths and content
hashes. Every domain row adds `import_id` to its source primary key, and references include it.
Different source snapshots coexist, including conflicting assertions; identical bytes are a no-op.
The same snapshot under a different contract digest is refused until an explicit development replay
or reviewed migration. The import manifest records contract version, digest and adapter profile.

Before the database transaction, every supplied file is copied byte-for-byte into
`$DATA_DIR/satcom-import/<digest>/package/`, with a manifest beside it. This includes the workbook,
PDF, dictionaries, validation report and original reference `schema.sql`. That supplied SQL file is
archived evidence only; the application never reads it as executable schema. The adapter executes
no source formulas or SQL. Existing archives are verified, and tampering is refused. Symlinks in
source packages are refused. A failed database load leaves the archive available for retry.

`satcom_files` records every file hash and length; `satcom_rows` preserves every original CSV cell
as canonical JSON, including empty strings and lexical decimals. A single database transaction
loads the typed projection, raw rows and import manifest. Deferred constraints roll everything back
on failure. An import lock serializes identical snapshots. The archive has its own atomic staging
and retry behavior.

## Observed package and limitations

The supplied package has 12,755 rows, 5,392 claims, 1,590 gaps, 807 source entity IDs, and 618 source
records across 28 tables. The workbook has 36 sheets, 28 reference tables, 18,230 formulas and seven
native charts. Independent OOXML extraction found matching CSV headers and source values after
Excel date decoding and allowance for ten binary floating-point representation differences.
The original workbook remains the authority for formula, chart and layout preservation; formulas
are not recalculated or promoted into typed facts by this import.

These are source projections, not canonical KN UUID entities, reviewed ontology seeds, or complete
space-domain models. Regulatory versus deployed status, planned versus observed counts, launch
scenario conditions, finance bases, and terminal mass boundaries remain explicit source fields.
Canonical identity matching, rights review and source onboarding remain required before publication
or exchange. The importer does not fetch URLs or treat a local file as permission to crawl them.

The compiler supports flat scalar models and bounded WKT/PostGIS geometry templates. PostgreSQL
numeric bounds hold this dataset exactly; oversized new values fail and keep their original input
file available.
Structural drift checking covers tables, columns, types including PostGIS geometry, nullability,
comments and references through Alembic; it does not prove equivalence of arbitrary manually
altered check expressions. The pinned standard and implemented ODCS profile remain bounded;
ontology content, runtime semantic policies and interchange compilation remain separately planned.

Known limitations, with what would reopen them:

- The prefetched-dataset path is SATCOM-specific: its own commands (`kn space satcom`), bookkeeping
  tables, archive directory (`$DATA_DIR/satcom-import/`), and a `kn.sourceProfile` fixed to
  `satcom-csv/1`, and rebuild does not restore it. `prefetched-dataset-method` in the
  [plan](../plan.md) generalizes it before the next dataset.
- Registered contracts are package resources under `src/kn/contracts/resources/`, so source
  installations and wheels deploy the same bytes. The specification's `contracts/core/` and
  `domains/<domain>/contracts/` layout applies once contracts outside the package are deployed;
  the registry then needs a reviewed path rule for them.
- `load_contract()` without a path still loads the SATCOM contract for the SATCOM adapter and its
  tests. Deployment code no longer relies on it; `prefetched-dataset-method` removes the default.
- The digest covers the source document as written. Reordering tables or `customProperties`
  entries changes the digest and `contract.json`, though every other artifact is byte-identical
  after masking the digest, so a reorder costs a development rebuild or a release version bump.
  This is kept so that the digest names exactly the reviewed text. Reopen it if reorders cause
  review churn or when contracts are assembled from several files.
- A development database created before the registry has revision `0001_satcom` and no
  `system.installed_contracts`, so `make db-up` and `make db-verify` fail until
  `KN_ENVIRONMENT=development make db-rebuild` and `make satcom-import` restore it.

## Verification

- `make ci`: required quality gates, digest drift check and deterministic unit tests.
- `make test-integration`: exact real-mixture PostgreSQL round trips, deferred-constraint rollback,
  additive release-style evolution, concurrent platform bootstrap and existing role isolation.
- `make db-verify`: Alembic head, installed contract digest, structural drift, role attributes,
  schema isolation, table/sequence default privileges and PostGIS. Probe tables are rolled back.
- `make model-baseline`: compile all registered contracts, rebuild and replay combined fixtures
  twice, and compare every stored value and complete marker. This covers the registered subset;
  the remaining shared/domain models and the integrated checkpoint remain open acceptance work.
- `tests/domains/space/satcom/real_sample.json`: 168 reference-closed rows selected from the owner
  package. Tests mix snapshots and plant missing references, duplicate keys, bad dates, enums and
  numeric values.
- `tests/contracts/test_contracts.py`: deterministic exports, invalid contracts, PostgreSQL DDL
  compilation, independent fastavro schema parsing and exact decimal/date/null round trips.
- `tests/contracts/test_physical.py`, `test_type_mapping.py`, `test_diagnostics.py` and
  `test_generated.py`: derived names, value ranges, located refusals and the committed output.
- `tests/contracts/test_statements.py`: typed platform statements, and no SQL string in production
  code.
- `tests/contracts/test_lint.py` and `test_document.py`: every extension family, invalid fixtures,
  schema tampering, compiler refusal of lint-only metadata, and safe YAML/JSON failure paths.
- `make contract-toolchain-check`: isolated pinned external linter and export probe, separate from
  runtime dependencies and the deterministic network-free CI suite.

The analysis, real import evidence and remaining scope are in
[record 0011](../records/0011-data-contracts-satcom-schema-governance.md).
The pinned lint toolchain and external export boundary are recorded in
[record 0014](../records/0014-data-contracts-contract-toolchain-pin.md).

The full compiler templates, offline reference resolution and drift acceptance are in
[record 0015](../records/0015-data-contracts-contract-compiler.md).

The all-schema rebuild and reviewed-seed hook are in
[record 0016](../records/0016-data-contracts-development-rebuild-mode.md).

The implementation audit of the group, its findings and their dispositions are in
[record 0017](../records/0017-data-contracts-data-contracts-implementation-audit.md).
