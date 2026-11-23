# Registered Model Baseline Check

`make model-baseline` provides combined-registry fixture validation for the available governance,
SATCOM, semantic and human verification contracts: 51 tables and 473 fields. It prepares the
integrated
development checkpoint. The complete checkpoint remains open in the [plan](../../plan.md): its 15
remaining
prerequisite model tasks still need identity, claims, dataset-wide human verification projections,
supply, source/run, exchange and canonical domain contracts. Passing this subset does not accept
those missing models, adopt a new shared database baseline or freeze a release.

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
performs two all-schema rebuilds through the normal Alembic path. Each rebuild loads reviewed
vocabulary seeds, imports the reference-closed 168-row real SATCOM mixture as the space loader,
and loads the synthetic semantic fixture as the semantic loader. Reimporting SATCOM must be a
no-op. The fixture supplies decimal weights, condition values, aware timestamps, multilingual
labels, nulls and a translation review reference alongside the reviewed seeds.

All 51 tables must contain representative data. Every typed SATCOM row and original CSV cell must
equal the source fixture, and every semantic field must equal the reviewed seed or native fixture
value. The test reads all columns, ordered by the contract's primary keys, and requires identical
snapshots after the two rebuilds. This includes snapshot identifiers, semantic keys, review
references, original human decision times/actors/IDs and every field of each contract marker.
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
permissions, canonical/source ownership and replay semantics. Their cross-owner checks, durable
all-dataset human decision replay, interchange evolution and explicit shared-database
recovery/backfill evidence remain required before the full checkpoint can leave the plan. Existing
specialized
semantic/SATCOM review fields are not universal human verification stamps.

[Record 0030](../../records/0030-data-contracts-development-model-baseline.md) preserves the
original
work contract, the marker-verification regression and run evidence. Generated contract artifacts
are refreshed when a prerequisite registers a model.

The [shared review protocol](../evidence-model.md) extends this subset with a durable, exact-version
review of a semantic label identified by namespace and locale. The first rebuild records the
fixture decision; the second reuses the same journal and replays the original event. The test
checks the acceptance stamp as well as the stored event and complete marker snapshots. This
fixture coverage does not supply dataset-wide registration and read projections.
