# Registered Model Baseline Check

`make model-baseline` provides combined-registry fixture validation for governance, the source
catalogue, SATCOM, semantic, human verification, identity and evidence contracts. These define 73
tables and 707 fields. The full checkpoint in the [plan](../../plan.md) also requires supply,
ingestion run, exchange and canonical domain fixtures. Each delivery group
extends the subset check. The integrated result and its audit gate release approval.

## Run and evidence

```bash
make db-up
make model-baseline
```

The target loads `.env` and resolves `DATA_DIR` through the shared shell helpers. Each invocation
creates `$DATA_DIR/model-baseline/check-XXXXXXXX/`, with a JUnit `results.xml` and pytest fixtures
under `fixtures/`. The test's directory contains `compiled/<contract-id>/` and `rebuild-1.json` and
`rebuild-2.json`. JSON uses ASCII escapes and tagged decimal, date and timestamp values. These
artifacts preserve source text and exact typed values, including nulls, zero and false.

The integration harness supplies a development-mode, caller-owned transaction. Both rebuilds,
seed loads and imports roll back at test teardown, preserving the shared database. No live fetch
or runtime engine runs, and no source SQL or formula executes. Deferred fixture references are
checked explicitly before the next rebuild; the test does not alter unrelated constraint timing.
The check also runs as part of `make test-integration` and `make ci-local`.

## Coverage

`tests/integration/test_model_baseline.py` compiles and checks the entire registered set, then
performs two all-schema rebuilds through the normal Alembic path. Each rebuild loads the
reviewed source catalogue and vocabulary seeds, imports the reference-closed 168-row real SATCOM
mixture as the space loader, and loads the synthetic semantic fixture as the semantic loader.
The evidence loader writes one consistent row of every evidence table. Reimporting SATCOM and
rewriting the evidence rows must be no-ops. The fixture supplies decimal weights, condition values,
aware timestamps, multilingual labels, nulls and a translation review reference alongside the
reviewed seeds.

All 73 tables must contain representative data. Every typed SATCOM row and original CSV cell must
equal the source fixture, and every semantic field must equal the reviewed seed or native fixture
value. All 119 catalogue rows must equal the reviewed seeds. The test reads every column and
orders rows by the contract's primary keys. The two rebuilds must yield identical snapshots,
including snapshot identifiers, semantic keys, review references, original human decision
times/actors/IDs and every field of each contract marker.
Database governance and role verification run after each replay. SATCOM tables retain their
snapshot meaning and existing
field IDs; no canonical space table is introduced by this check.

## Extending the checkpoint

`FIXTURE_OWNERS` explicitly names contracts with fixture replay. A newly registered owner fails
this suite until it supplies representative fixture data and assertions. Add its replay under
the owning loader role, resolve its deferred references, and compare it with independently
authored expected data. The table snapshot automatically includes every registered column;
empty-table and fixture-owner checks prevent silent coverage gaps.

The owning model tasks must first establish shared keys, measurements, seed references, coverage,
permissions, canonical/source ownership and replay semantics. Their cross-owner checks,
interchange evolution and explicit shared-database
recovery/backfill evidence remain required before the full checkpoint can leave the plan. Existing
specialized
semantic/SATCOM review fields are not universal human verification stamps.

[Record 0030](../../records/0030-data-contracts-development-model-baseline.md) preserves the
original
work contract, the marker-verification regression and run evidence. Generated contract artifacts
are refreshed when a prerequisite registers a model.

The [shared review projection](../evidence-model.md#current-verification-reads) is checked for
one representative row and every field of each table. The fixture writes decisions for semantic
labels, a mapping, a SATCOM terminal field and a decision-log row before the two measured rebuilds.
Each rebuild restores the original events and stamps from the same journal after the required
inputs arrive. The test retains intermediate and final replay reports in the fixture directory's
`human-verification/` subdirectory. Alternate locales, an edited label and a new SATCOM snapshot
expose null stamps. The source fixture and archived files are compared byte for byte.

The [identity fixture](../object-identity.md) seeds the durable journal before either rebuild.
Identity replay precedes SATCOM import; all lifecycle events, record versions, match features,
change sets, ownership and flattened redirects survive the two complete snapshots.
