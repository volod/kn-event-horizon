# Ingestion State Contracts

## Work contract

```markdown
#### ingestion-state-contracts

Run status, checkpoints and source health need stable storage definitions before the engine and
monitoring workflows begin writing them.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The run, cursor, archive and monitoring fields in the specification and the
  [standard source error codes](current/source-management.md#error-codes-and-pagination).
  Fixtures can supply source IDs, archive IDs and claim keys without executing a crawler.
- User-visible outcome: Registered contracts define run attempts/status/error history, source
  checkpoints, committed batch/archive references, configuration/code versions and health metrics.
- Scope boundary: Schemas, keys, enums, time semantics, human-verification coverage and
  transactional checkpoint constraints. Runtime fetching, scheduling and status CLI stay later.
- Data and artifact paths: `contracts/core/system/`, `src/kn/contracts/resources/`,
  `src/kn/engine/`, `tests/engine/`, `tests/integration/`.
- Execution path: Compile the contracts and load interrupted, retried and committed fixture runs;
  test transaction rollback and checkpoint references without HTTP or an engine implementation.
- Acceptance gates: Duplicate attempt/batch keys are refused or idempotent as declared. A failed
  transaction cannot advance a checkpoint. Status/error/time fields needed by source monitoring
  are present, preserve history and share the approved error vocabulary. Rebuild reproduces the
  fixture state. `make ci` and integration checks pass.
- Documentation target: A new `current/ingestion-engine.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Registered `kn.system.ingestion_state` in the development `1.0.0` baseline. It adds four
tables and 47 fields in `system`, with generated artifacts and external human verification
coverage. Attempts share a logical run ID across retries. Attempt outcomes, ordered error
occurrences and committed batches remain separately addressable. Archive references use the
existing archive batch key and distinguish the application run from the capture run.

Checkpoint history uses increasing revisions within each source, scope and cursor namespace.
The revision records the loaded batch it covers. PostgreSQL rejects duplicate attempt and batch
keys, duplicate application of an archive batch within one stream, duplicate advances for one
batch, and cross-stream or missing references. The writer checks the expected revision and
rejects backward time watermarks. It leaves transaction ownership with the caller so a claim
write, loaded batch and checkpoint can all roll back together. Source-specific ordering and
the choice to advance only a contiguous processed prefix belong to the loader.

### Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| ISC-01 | minor | Initial `make ci` reported an unreachable return from a dynamic-column `RETURNING` result in the checkpoint writer. The engine loader depends on a typed revision return. | Ingestion engine. Fixed with a boolean `RETURNING` marker and the already calculated revision. |
| ISC-02 | minor | Fixture review found that a compressed WARC object length was being used as run response bytes. Monitoring fixtures need source entity bytes per attempt. | Ingestion engine. Fixed by reading retained capture metadata on each rebuild, assigning the payload length to the fetching attempt and zero source bytes to its archive reuse. |
| ISC-03 | minor | Adding the registered owner exposed five registry collision tests that unpacked the old set by position. The registry gate could no longer exercise its collision checks. | Data contracts. Fixed by selecting SATCOM by contract ID and retaining the full registry in each collision test. |
| ISC-04 | major | The existing PostgreSQL identity submit benchmark exceeded its 2.0 warm median ratio. It measured 2.805 in the full local run, 2.418 in isolation, and 2.359 in isolation from unchanged Git HEAD `bc8588a` on the same host. Affected consumer is the identity writer at scale. | Operations hardening. Scheduled diagnosis and reproduction under [`performance-gate`](../plan.md#performance-gate). |

## Acceptance evidence

Accepted. The first `make plan-status` counted 110 tasks, with 98 agent and 12 human.
`make contract-compile` compiled the development registry before the database checks.

- The initial schema parity tests failed because the registered ingestion model was absent.
  They now compare the persisted error and cursor vocabularies with the crawler schema and
  check the terminal outcomes, timed observations and health fields.
- `source scripts/shared/common.sh && kn_load_env && kn_db_test_env &&
  .venv/bin/python -m pytest tests/integration/test_ingestion_state.py` passed 15 tests.
  It refused duplicate and invalid rows and absent or cross-stream checkpoint references.
  It also forced a deferred foreign-key commit failure after writing a claim, batch and
  checkpoint. The claim and advance rolled back. The retry read the same archived capture and
  committed once. A synchronized pair of writers verified that only one could advance a revision.
- `make model-baseline` passed. Two rebuilds restored the interrupted and retried attempts, a
  later `not_modified` run, error history, archive reference and checkpoint from fixture inputs.
  The two snapshots under `$DATA_DIR/model-baseline/check-vpgYuBu0/fixtures/` were byte-identical
  with SHA-256 `ebaf2e99af22e2f36bc528114ab589d620c77d2e79884d5f7d0d910c628c9f8a`.
- `make ci` passed within the final `make ci-local` run, with 1,489 unit tests passed.
  The local phase passed 155 tests, including all 15 ingestion-state tests, and failed only the
  identity benchmark in ISC-04. The separate `make skos-reference-check` passed Apache Jena
  RIOT validation. Every ingestion-state acceptance check ran and passed.
- Reran the benchmark with `.venv/bin/python -m pytest -s
  tests/integration/test_identity_write_scale.py` after loading the integration environment.
  Then ran the same test from a temporary export of Git HEAD with the same dependencies and
  database. Logs for both and the full CI run are under
  `$DATA_DIR/ingestion-state/check-Haeqpbgy/`.
- `make lint-md lint-spec-plan plan-status` and `git diff --check` passed after the plan transition.

## Handoff

The plan drops from 110 to 109 tasks (98 to 97 agent, 12 human). MODEL tasks drop from 10 to
9. The registry links the available storage while the ingestion engine capability stays planned.
The next required agent task is `engine-skeleton`. It consumes the checkpoint transaction
interface. `source-status-monitoring` consumes the run and health records. The integrated
development baseline now covers ingestion state. Its remaining model owners and release gates
stay open.
