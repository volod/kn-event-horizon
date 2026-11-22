# SATCOM schema governance

## Work contract

```markdown
#### satcom-schema-governance

The supplied SATCOM package needs a lossless initial import and one model definition for engines.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: The owner-provided `.data/satcom_enriched_package` and official ODCS schema.
- User-visible outcome: SATCOM records import without losing evidence, and Python governance
  replaces deployment SQL scripts.
- Scope boundary: All supplied CSV fields, immutable package archive, strict validation,
  SQLAlchemy/Alembic, Elasticsearch and Avro outputs; no new search service or identity matching.
- Data and artifact paths: `src/kn/contracts/`, `src/kn/db/`, `src/kn/satcom/`, `tests/`,
  `$DATA_DIR/satcom-import/`, and `$DATA_DIR/contract/`.
- Execution path: Inspect CSV and XLSX, compile contracts, validate and import the real package,
  exercise mixed fixtures and migrations, route Make deployment through Python.
- Acceptance gates: Deterministic compile; malformed data and breaking evolution refused;
  atomic idempotent import; raw and typed round trips; `make ci` and database integration tests.
- Documentation target: `current/data-contracts.md` listed in the [areas index](current.md#areas).

```

## Implementation and decisions

Owner clarification: keep contract version `1.0.0` and one editable Alembic baseline during
development. Rebuild disposable data instead of creating provisional version chains. Freeze at
first release, then evolve through versioned migrations. Remove handwritten SQL deployment files.

The source adapter lives under `src/kn/domains/space/satcom/`; SATCOM is an example dataset,
not a new domain. The CLI is `kn space satcom validate|import`.

## Acceptance evidence

Accepted after the final gates below. Initial plan: 116 tasks (105 agent, 11 human). One scoped
implementation task was opened before code edits, taking the plan to 117; acceptance removes it,
returning to 116 (105 agent, 11 human). Runtime platform, initial data contracts and space source
preservation are affected. Full data-contract and space-ELT capabilities remain planned.

- `make ci`: all checks pass, including contract digest drift and 189 unit tests; 36 local-only
  integration tests are deselected.
- `make test-integration`: 36 passed. This covers concurrent bootstrap, existing role isolation,
  exact typed real-mixture round trips, deferred-constraint rollback, additive evolution and an
  explicit development rebuild that preserves unmanaged tables and rolls back test changes.
- `make quality`: passed all checks, coverage, Markdown lint and package builds.
- `make coverage`: 93.41 percent against the unchanged 90 percent floor. Unit tests remain
  network-free.
- `make lint-md`: passed, including relative documentation links.
- `make build`: source distribution and wheel built; wheel inspection confirms all ODCS, contract,
  compiler, Alembic and space adapter resources are packaged, with no separate SATCOM domain.
- `make db-up`, `make db-upgrade`, `KN_ENVIRONMENT=development make db-rebuild`,
  `make db-verify`, `make satcom-import`: exercised against the local PostGIS service. Repeated
  import reports already imported. The source package stays immutable.
- Every typed value in all 12,755 rows and every original CSV cell round-trips against PostgreSQL.
  The snapshot is `7ec6001f0d41b91f287003ba00c893c08a96ba69ad0979d7fb1707ded6b0c7dd`.
- Independent OOXML extraction checks all 28 CSV headers and source table values. The 36-sheet
  workbook keeps 18,230 formulas and seven charts. Date serial conversion and ten binary float
  representation differences explain the raw representation differences; there are no remaining
  source value differences. Recalculation and visual layout were not changed or revalidated.
- Runtime evidence: `$DATA_DIR/satcom-analysis/2026-11-22/structure.json` and
  `database-roundtrip.json`; raw package archive under `$DATA_DIR/satcom-import/<snapshot>/`.
  Generated portable schemas and the PostgreSQL metadata descriptor are under
  `$DATA_DIR/contract/current/`; reviewed digests cover all engine outputs.
- `git diff --check`: clean. No commit or push was made. The service started for validation is
  stopped after acceptance; PostgreSQL data, raw archives and runtime evidence are retained.

## Durable findings

The old implementation had schema/role bootstrap only and no dataset ingestion or domain model.
It could not yet preserve the source records. The supplied SQL described a useful reference
projection, but was not used as deployment code. The new ODCS contract preserves its fields,
constraints and descriptions, improves floating-point values to exact decimals, and adds snapshot
keys and immutable raw evidence. Partial dates remain partial. Source model names and registry
IDs are not automatically canonical KN identities.

A regression check exposed that structural comparison initially treated an unmanaged space table
as drift. It now limits reflection to contract-owned tables. Rebuild reflection also disables
following foreign keys into unmanaged tables, preserving the requested boundary.

Development edits version `1.0.0` and one baseline in place. No provisional version chain was
created. The `1.1.0` evolution exists only as a transient test model; first release must freeze
the baseline before separate released versions and revisions are introduced.

## Handoff

`contract-toolchain-pin` and `contract-compiler` retain broader ODCS extension, ontology, PostGIS,
Pydantic and dbt gates. `development-rebuild-mode` retains full-platform seed/replay work beyond
this dataset. `space-domain-contracts` now explicitly consumes the preserved real mixture for
canonical modeling. Identity, rights review, source onboarding and the remaining domain pipeline
retain their original gates. `release-migration-mode` verifies and freezes the full release;
it no longer selects a different migration framework. No new external service was introduced.

## Task sections

- [x] Analyze all supplied CSV tables and workbook structure; document preservation gaps.
- [x] Define the `1.0.0` ODCS model and deterministic multi-engine compiler.
- [x] Validate and archive real source data; implement atomic snapshot import and mixed fixtures.
- [x] Replace deployment SQL with Python governance, development rebuild, and release evolution.
- [x] Run unit, database, real-package and CI gates; record remaining acceptance work.
