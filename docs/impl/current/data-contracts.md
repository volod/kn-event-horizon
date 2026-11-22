# Data Contracts and Space Example Import

The space domain has an initial SATCOM source dataset. SATCOM is a subset of space, not a domain,
service, or PostgreSQL schema of its own. This implementation supplies the first bounded profile
of the [data contracts capability](../../design/spec.md#data-contracts). The remaining ontology,
identity, interchange, PostGIS and broader compiler work stays in the [plan](../plan.md).

## One definition for each model

`src/kn/contracts/resources/satcom/1.0.0.json` is the ODCS source of truth for the example dataset.
It declares `domain: space` and storage schema `space`. It contains all 28 CSV tables and four
bookkeeping tables: `satcom_contract`, `satcom_imports`, `satcom_files`, and `satcom_rows`.
The bundled resources ship in the wheel, so validation and deployment do not need network access.

The official ODCS 3.1.0 JSON Schema is vendored with upstream and local checksums in `pins.json`.
The local copy only escapes non-ASCII characters as JSON escapes. Validation checks this checksum,
the official standard, the supported profile, names, stable field IDs, and references. Unsupported
ODCS features, unknown or misplaced extensions, repeated extensions, missing metadata, and
incompatible reference types fail instead of disappearing from an export.

The implemented `kn.*` extensions are `storageSchema`, `sourceProfile`, `csv`, `fieldId`,
`foreignKey` (ordered source and target columns), `enum`, `partialDate`, `precision`, and `scale`.
Their closed schemas live in `loader.py`; supported ODCS keys live in `profile.py`. The wider
extension families in the specification remain planned and are refused by this bounded profile.

`model.py` supplies immutable typed models. The same fields compile into:

| Consumer | Representation |
| --- | --- |
| PostgreSQL | SQLAlchemy metadata; exact `NUMERIC(38,18)`, big integers, dates, text, booleans, required fields, composite keys, enum checks, and initially deferred composite foreign keys |
| Elasticsearch | Strict mappings with date and numeric inference disabled; exact decimals are keyword strings, partial dates are keyword strings, full dates use `strict_date` |
| Avro | Records, nullable unions with null defaults, `long`, dates, and standard decimal logical types with precision 38 and scale 18 |
| JSON Schema | Closed objects, required fields, enums, dates, partial-date syntax and decimal strings for portable JSON |

Elasticsearch mappings describe fields; JSON Schema and the importer enforce required values and
allowed enums before indexing. Decimal keyword fields preserve precision but do not support numeric
range aggregation. No Elasticsearch service or Avro transport is deployed.

`make contract-check` validates and compares artifact digests with the reviewed manifest.
`make ci` includes this gate. The PostgreSQL descriptor is generated from SQLAlchemy metadata,
including column types, nullability, keys and checks, so physical mapping drift also fails CI.
`make contract-compile` writes 96 portable artifacts, a PostgreSQL metadata descriptor and a digest
manifest under `$DATA_DIR/contract/current/`. `kn contract compile --output <directory>` supports a selected
runtime directory. SQLAlchemy metadata is consumed directly by Alembic; no SQL script is authored
or executed by deployment.

## Development baseline and release evolution

Development keeps contract version `1.0.0` and one Python Alembic baseline, `0001_satcom`, editable
in place. A contract edit changes its digest. Refresh the artifact digest manifest after reviewing
exports. Normal `make db-upgrade` verifies the installed digest and structure; it does not silently
alter an existing projection to match edited development definitions.

For a development model edit:

1. Edit the `1.0.0` contract, baseline if needed, and regression fixtures.
2. Refresh the reviewed artifact manifest and run `make ci`.
3. Set `KN_ENVIRONMENT=development` and run `make db-rebuild`.
4. Run `make satcom-import` to restore the example dataset from the source package.

Rebuild drops only tables listed in the current or previously installed contract manifest. It
keeps other space tables, the other domain schemas, and package archives. Reflection does not
follow foreign keys into unmanaged tables. A dependency from an unmanaged table can refuse the
rebuild rather than being cascaded away. The rebuild and baseline application share one
transaction and advisory lock. Without explicit development mode, including when
`KN_ENVIRONMENT=released`, rebuild fails before database access.

At first release, freeze the baseline and contract `1.0.0`. Subsequent releases add contract
snapshots and Python Alembic revisions. `evolution.py` supplies conservative diff validation and
additive operations for new tables and nullable fields. It refuses removals, renames, type,
identity, nullability, enum, reference and precision changes, and new constrained fields that need
backfill. Additive evolution updates the installed contract marker. A revision calls this helper
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

The compiler currently supports flat scalar models. PostgreSQL numeric bounds are chosen to hold
this dataset exactly; oversized new values fail and keep their original input file available.
Structural drift checking covers tables, columns, types, nullability and references through
Alembic; it does not prove equivalence of arbitrary manually altered check expressions. The pinned
standard and implemented extension subset are deliberately narrower than the future full compiler.

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

The analysis, real import evidence and remaining scope are in
[record 0011](../records/0011-data-contracts-satcom-schema-governance.md).
