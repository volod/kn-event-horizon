# Engine Skeleton

## Work contract

```markdown
#### engine-skeleton

The core engine must run end to end on a synthetic source before any real source.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Dependencies: The [crawler validator and enablement evidence](current/source-management.md#enablement-evidence),
  [raw archive commit and replay interface](current/raw-archive.md#commit-and-replay), and
  [ingestion state contracts](current/ingestion-engine.md#checkpoint-transaction).
- User-visible outcome: `kn source run` and `kn source replay` process a synthetic fixture source
  served locally. They commit WARC captures and write identity events, claims with evidence linked
  to KN IDs, a checkpoint, and a run summary with a declared status.
- Scope boundary: Lock, run registration, fetch to archive, parse, a minimal mapping, validation,
  load, checkpoint, and status. Fetch safety, full mapping, curated input, and rebuild replay come
  in the next tasks.
  Use the registered run, batch and checkpoint tables and the checkpoint transaction interface.
- Data and artifact paths: `src/kn/engine/`, `domains/fixture/` (test-only),
  `tests/engine/`, `tests/fixtures/fixture/`.
- Execution path: Fixture-first. A test HTTP server serves the synthetic payloads, the adapter
  interface returns records and claims, and the loader is the only writer.
- Acceptance gates: A catalogue candidate and a profile missing its rights decision each
  produce zero requests at the fixture server. A second enabled run is idempotent. An interrupted
  run resumes from the committed checkpoint. A crash after archive finalization and before SQL
  commit reuses the archived batch.
  Replay without network yields the same claims. Russian, Chinese, and unknown-language source
  fixtures ingest without English or Ukrainian translations, retain originals and provenance, and
  use the [shared text selector](current/localization.md#source-data-and-translations) for display.
  `make ci` passes.
- Documentation target: [Ingestion engine](current/ingestion-engine.md).
```

## Implementation and decisions

Added `kn source run` and `kn source replay`, using the deployed source catalogue and reviewed
crawler profile for admission. The initial transport connects only to IPv4 loopback over HTTPS and
reads one bounded JSON response. The fixture adapter and profile live under `domains/fixture/`
and use a synthetic source row in the existing space catalogue domain.

A PostgreSQL session lock spans registration, acquisition and commit for each source and scope.
The stable logical run key lets a retry reuse its finalized WARC response. The loader validates
the snapshot before applying record identities and typed text claims, then commits the loaded
batch, checkpoint and outcome in the same SQL transaction. The identity journal remains
write-ahead. A pending match from that batch completes before any claims are written again.

Replay opens a single named batch with the original profile and code digests. With the same
identity journal, it reproduces the KN IDs and claim provenance. The fixture loader takes
claim and evidence recording times from the archived observation so a replay reproduces every
stored value. The SQL attempt and batch record the actual load.

### Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| ES-01 | major | Interrupting the identity journal during the second record left a pending match. On retry the first record's tracker failed before the loader reached that match. | Ingestion engine. Fixed by resuming the pending match before replaying the records in order. The interruption test reproduced the failure first. |
| ES-02 | minor | The acceptance fixture initially tried to insert a catalogue domain outside the registered enum. The deployment suite also treated the fixture directory as a deployed domain. | Ingestion engine. Fixed by qualifying the synthetic source under `space` in a disposable database and keeping the fixture directory outside deployed-schema checks. Every real package is still checked. |
| ES-03 | minor | The CLI help golden expected only `list` and `validate`. | Source management. Updated the goldens for both new commands. |
| ES-04 | minor | The existing local database started, but a read-only verification reported contract digest drift. Engine fixtures use fresh, disposable databases and the state suite uses a scratch schema. | Local runtime. Preserved the persistent database and ran acceptance against disposable databases. |

## Acceptance evidence

Accepted. The first `make plan-status` counted 109 tasks, with 97 agent and 12 human.

- `source scripts/shared/common.sh && kn_load_env && kn_db_test_env &&
  .venv/bin/python -m pytest tests/engine tests/integration/test_ingestion_state.py`
  passed 27 tests. The JUnit report and log are under
  `$DATA_DIR/engine-skeleton/check-yNvDgPa1/`.
- An enabled profile with a candidate catalogue row, and an enabled catalogue row with missing
  rights evidence, each recorded zero fixture server requests and zero attempts.
- A repeated snapshot added no events, claims or checkpoint. Concurrent commands produced one
  applied snapshot and one `not_modified` result. Interruption before capture, during a later
  record's identity event append, and before SQL commit preserved the committed checkpoint.
  Both post-archive interruptions reused the WARC batch with zero further requests.
- Archive-only replay made zero requests and reproduced all claim and evidence rows after
  rebuilding the disposable database with the same journal. Russian, Chinese and
  unknown-language originals retained their provenance and displayed via the shared selector
  in both interface locales. Malformed and drifted snapshots retained their WARC and left
  no loaded batch or checkpoint.
- `make lint-md lint-spec-plan plan-status` and `git diff --check` passed.
- `make ci` passed with 1,491 tests. The log is in the same evidence directory.

## Handoff

The plan drops from 109 to 108 tasks (97 to 96 agent and 12 human). DELIVERY tasks drop from
100 to 99. The ingestion engine registry links the available runner and storage. The full
ingestion and source management capabilities stay planned. The next required agent task is
`source-status-monitoring`, which reads the run and checkpoint data. The source management
audit consumes this record. General HTTP acquisition, mapping and rebuild replay remain
open in their owning tasks.
