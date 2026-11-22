# Data Contracts and Space Example Import

The space domain has an initial SATCOM source dataset: owner-supplied, prefetched files from a real
space source, kept as the first data integration example. More prefetched datasets will follow
through a shared path (`prefetched-dataset-method` in the [plan](../plan.md)); today the adapter is
SATCOM-specific. SATCOM is a subset of space, not a domain, service, or PostgreSQL schema of its
own. This implementation supplies the first bounded profile
of the [data contracts capability](../../design/spec.md#data-contracts). The remaining ontology,
identity, interchange and raw replay work stays in the [plan](../plan.md).

## One definition for each model

`src/kn/contracts/resources/satcom/1.0.0.json` is the ODCS source of truth for the example dataset.
It declares `domain: space` and storage schema `space`. It contains all 28 CSV tables and four
bookkeeping tables: `satcom_contract`, `satcom_imports`, `satcom_files`, and `satcom_rows`.
The bundled resources ship in the wheel, so validation and deployment do not need network access.

The official ODCS 3.1.0 JSON Schema is vendored with upstream and local checksums in `pins.json`.
The local copy only escapes non-ASCII characters as JSON escapes. Both standard and extension
schema checksums are mandatory and verified offline on every lint and compile.

## Contract lint and toolchain

`kn contract lint <file.yaml>` validates YAML or JSON against ODCS 3.1.0 and the closed schemas for
every `kn.*` family in the specification. Omitting the file validates the bundled SATCOM contract.
Lint checks types, required members, allowed locations, duplicate extensions and unknown names.
It does not resolve ontology, policy, vocabulary, mapping or dataset references. The
[toolchain reference](data-contracts/toolchain.md) lists extension shapes, diagnostics, parser
limits, and the pinned external tool's verification command.

The compiler accepts supplied JSON or YAML contracts and resolves local reference catalogs before
producing SQLAlchemy metadata, generated PostgreSQL DDL, strict Pydantic models, JSON Schema, Avro,
Elasticsearch mappings, dbt sources and contract documentation. The
[compiler reference](data-contracts/compiler.md) describes the supported profile, reference catalog,
PostGIS and partition templates, output paths, and exact-byte drift checks.

`make contract-check` validates the bundled contract and compares the committed
`generated/contracts/kn.space.satcom/` (103 artifacts plus a manifest, including physical mappings
and generated DDL) byte for byte with a fresh compile. `make contract-compile` refreshes that
directory. `kn contract compile` defaults to `generated/contracts/<contract-id>/`; `--output
<directory>` selects another destination. Normal upgrades and the explicit development rebuild both
run the Alembic baseline over the contract's SQLAlchemy metadata. No SQL text reaches the database:
schema objects come from SQLAlchemy metadata, and the platform policy from typed statements.

## Development baseline and release evolution

Development keeps contract version `1.0.0` and one Python Alembic baseline, `0001_satcom`, editable
in place. A contract edit changes its digest. Refresh the artifact digest manifest after reviewing
exports. Normal `make db-upgrade` verifies the installed digest and structure; it does not silently
alter an existing projection to match edited development definitions.

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
descriptions, and updates the installed contract marker. A revision calls this helper
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
- One storage contract is deployed. Upgrade, rebuild, verification and the installed-contract
  marker (`space.satcom_contract`) know only the bundled SATCOM contract, `kn.storageSchema` is not
  checked against the platform schemas at compile time, and cross-contract SQL references are
  refused. `storage-contract-registry` in the [plan](../plan.md) owns this before the first second
  contract.
- The digest covers the source document as written. Reordering tables or `customProperties`
  entries changes the digest and `contract.json`, though every other artifact is byte-identical
  after masking the digest, so a reorder costs a development rebuild or a release version bump.
  This is kept so that the digest names exactly the reviewed text. Reopen it if reorders cause
  review churn or when contracts are assembled from several files.
- A development database created before the audit keeps its old single-column foreign key names
  (`fk_<table>_import_id_`) until the next `make db-rebuild`. Structural verification compares
  references by columns, so `make db-verify` passes; the compiled-catalog check of a rebuild
  compares names.

## Verification

- `make ci`: required quality gates, digest drift check and deterministic unit tests.
- `make test-integration`: exact real-mixture PostgreSQL round trips, deferred-constraint rollback,
  additive release-style evolution, concurrent platform bootstrap and existing role isolation.
- `make db-verify`: Alembic head, installed contract digest, structural drift, role attributes,
  schema isolation, table/sequence default privileges and PostGIS. Probe tables are rolled back.
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
