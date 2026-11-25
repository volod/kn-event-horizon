# 0045 Partial-update tracking

## Work contract

```markdown
#### partial-update-tracking

Sources send partial records and declare nothing about completeness. Every change must still be
detected per field and traced back to its record version.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: The [registry replay and match writer](current/object-identity.md#replay-and-integrity)
  and the [claim, confirmation and idempotent writer contracts](current/evidence-model.md#claims-and-provenance).
- User-visible outcome: For each mapped record, the engine computes a field-level change set
  (added, changed, unchanged, emptied, or not stated) against the record's previous version. Only
  added, changed, and emptied fields create claims. Unchanged fields record confirmations, and
  omitted fields have no effect. Each record keeps a `last_seen` time, and absence never clears or
  deletes anything.
- Scope boundary: Record keys and version fields from the crawler mapping, version ordering by
  source version or `updated` time and then fetch time, per-field hashes, confirmations, late
  older versions kept as history, weak-key fragments resolved through existing or parent links,
  and change-set lineage (record version, fetch ID, archive record ID, code digest). How a claim
  changes the object belongs to `canonical-fact-selection`. Engine wiring comes in
  `mapping-and-quality-rules`.
  Consume registered source/version/change-set and confirmation contracts; no parallel
  tracker-owned definition of these records is introduced.
- Data and artifact paths: `src/kn/identity/tracking/`, `contracts/core/identity/`,
  `contracts/core/evidence/`, `tests/identity/`.
- Execution path: Write one fixture per row of the specification's change table, plus a record
  that stops appearing and an out-of-order version, before the tracker.
- Acceptance gates: A price-only record leaves parameter claims untouched. An emptied field creates
  a `source_empty` claim and no clearing. An omitted field changes nothing. A record that stops
  appearing keeps its claims, its `last_seen` time stops advancing, and nothing is deleted. An
  identical re-delivery adds a confirmation and no claim. An older version that arrives late does
  not become current.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

Both dependencies were available. The tracker lives in `src/kn/identity/tracking/`: `delivery.py`
(typed `Delivery` and `Statement` inputs, field hashes and version payloads), `changes.py` (pure
planning against a locked journal), `claims.py` (claims and confirmations), `writer.py` (the
PostgreSQL entry point) and `mapping.py` (record keys, versions, updated times, stated fields and
ordering from a reviewed crawler mapping). It consumes the registered `Version`, `ChangeSet`,
`claims` and `claim_confirmations` shapes; no tracker-owned record format was added.

- Baseline per field: each stated field compares with the record's latest claim for that field,
  not with the whole previous version, so a price-only version classifies parameters as
  `not_stated` instead of re-adding them later. `changed` and `emptied` claims name that claim as
  their predecessor.
- First empty statement: the evidence contract requires an `emptied` claim to name a predecessor.
  A field whose first statement is empty therefore has nothing to clear and is `not_stated`; its
  hash stays in the version's field hashes.
- Versions: a source version is unique per record by contract, and a confirmation is keyed by
  claim, version and fetch. A repeat of a recorded version in another fetch, or a fetch without a
  source version whose content equals the current version, is therefore a sighting rather than a
  new version. Without an event `last_seen` could not advance for such a record, so the identity
  payload union gained `record_seen` (`Seen`), and `lifecycle_events.kind` gained the same value.
  `make contract-compile` regenerated the `kn.core.identity` artifacts; table and field counts are
  unchanged. `contracts/core/identity/event.schema.json` was regenerated from the model.
- Ordering: numeric source version, or source updated time, then fetch time, then version text.
  A delivery that orders before the current version is kept as history with no change set. A
  recorded version delivered again with different content is refused.
- Replay integrity: `FieldChange` now refuses hashes inconsistent with its class, change-set
  hashes must equal their version's field hashes, and sightings must cite a known version in a new
  fetch. Existing fixture and scale histories already met these rules.
- Durability: claims and confirmations are validated before the journal append. The same
  delivery retried reuses its journaled version, change set or sighting and recomputes the same
  rows; existing claims of the version are kept, so a rerun after a merge writes nothing new.
- Fix found during implementation: a test that tracked the same delivery sequence again with
  empty evidence tables, as after a rebuild, lost a sighting's confirmations. A retried sighting
  had been judged against the current head instead of the head when it was recorded. State now
  keeps journal positions of versions, change sets and sightings, and planning evaluates baselines
  and heads as of those positions.
- Integration test fix: rebuilding inside the test transaction failed on pending deferred
  evidence foreign keys. The test now checks the evidence constraints by name first; a session-wide
  `SET CONSTRAINTS ALL IMMEDIATE` also affected the rebuild's own inserts and was not kept.

## Acceptance evidence

Status: accepted. Initial `make plan-status`: 117 tasks, 105 agent, 12 human; BLOCKED BY HUMAN=3,
CLEAR=92, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=105, MODEL=12.

| Gate | Evidence |
| --- | --- |
| A price-only record leaves parameter claims untouched | `test_a_price_only_record_leaves_parameter_claims_untouched`; the integration test's current claim view keeps the original package and voltage claims |
| An emptied field creates a `source_empty` claim and no clearing | `test_an_emptied_field_claims_source_empty_and_clears_nothing`: the superseded claim remains stored, a repeated empty statement confirms, and a later value supersedes the empty claim |
| An omitted field changes nothing | `test_an_omitted_field_changes_nothing` and the `not_stated` case of `test_each_change_class_has_its_effect_on_claims` |
| A record that stops appearing keeps its claims, `last_seen` stops advancing, nothing is deleted | `test_a_record_that_stops_appearing_keeps_its_claims`; the integration test checks `source_records.last_seen` for both records |
| An identical re-delivery adds a confirmation and no claim | `test_an_identical_redelivery_confirms_and_adds_no_claim` for fetch and numeric-version ordering; integration `again` delivery |
| An older version that arrives late does not become current | `test_a_late_older_version_is_history_and_never_current`, `test_numeric_source_versions_order_before_fetch_time`; integration `late` delivery |

- Execution path: `tests/identity/tracking_fixtures.py` holds the fixtures, with one case per row
  of the change table plus a record that stops appearing and an out-of-order version.
- `tests/identity/test_tracking.py` (20 tests) also covers first-empty fields, retries, an
  interrupted version without its change set, a weak-key fragment through its parent, refusals,
  reruns after a merge and identical evidence after tracking the deliveries again.
  `tests/identity/test_tracking_inputs.py` (22 tests) covers mapping inputs, delivery and
  statement validation, field-change hash rules and replay checks.
- `tests/integration/test_identity_tracking.py` runs on PostgreSQL. It covers a rolled-back first
  attempt and its retry, current claims through `claims_as_of`, confirmation and change-set
  counts, `last_seen`, deferred reference checks, and identity rows after a schema drop and rebuild.
- The shared development database refused the changed contract set, as designed, and was not
  rebuilt. The runner `$DATA_DIR/identity-tracking/run-20261125/run_acceptance.py` creates and drops
  a disposable database with the normal baseline. The full `tests/integration` run passed 117
  of 117 with zero skipped (`$DATA_DIR/identity-tracking/acceptance-7a71da90/`). It ran before
  the sighting-position fix. After that fix, the tracking, identity, model-baseline and evidence
  integration files passed 34 of 34 (`$DATA_DIR/identity-tracking/acceptance-f0ff11ea/`).
- `make ci`: passed, 1354 tests with 118 integration or heavy tests deselected and run as above.
  The bilingual CLI golden `tests/e2e/fixtures/cli.json` now prints the new `kn.core.identity`
  contract digest.
- `make lint-md`, `git diff --check`: passed.

## Handoff

The task left the plan. `object-lineage-lookup` now requires only `canonical-fact-selection` and
links the tracking section in `Dependencies`. `object-identity-implementation-audit` no longer lists
the task. `mapping-and-quality-rules` links the tracker and its mapping helpers for engine wiring.
The plan preamble no longer names partial-update tracking as remaining core work. Final
`make plan-status`: 116 tasks, 104 agent, 12 human; BLOCKED BY HUMAN=3, CLEAR=91, HUMAN-GATED=9,
RUN NEEDED=13; DELIVERY=104, MODEL=12. Next required agent priority is `canonical-fact-selection`.

`object-identity` remains `planned`: selection, lineage, incremental writes, calibration and the
group audit are open. Claims restored after a rebuild need the raw replay of `rebuild-from-raw`;
tracking writes inherit the cost that `identity-incremental-writes` owns. No commit or push was
made.
