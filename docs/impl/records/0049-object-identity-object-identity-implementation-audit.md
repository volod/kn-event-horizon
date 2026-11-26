# 0049 Object identity implementation audit

## Work contract

```markdown
#### object-identity-implementation-audit

Identity is the core model, and KN IDs are stored in counterparts and exports, so a flaw in minting,
lifecycle, or matching is the most expensive kind to fix later.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. `identity-match-calibration`
  stays open and is reviewed for the readiness of its inputs. The [identity resolution
  audit](records/0042-object-identity-identity-resolution-implementation-audit.md) lists the
  accepted matching limitations to recheck, and the [evidence model
  limitations](current/evidence-model.md#known-limitations) name facts stored under a KN ID that
  was later merged. The [lineage lookup](current/object-identity.md#lineage-lookup) and its
  [task record](records/0047-object-identity-object-lineage-lookup.md) trace values to raw records
  and report such facts as gaps. The
  [incremental writes record](records/0048-object-identity-identity-incremental-writes.md) gives
  the PostgreSQL scale, recovery and rebuild parity checks.
- User-visible outcome: Every later group resolves objects through a verified identity registry. The
  audit record gives every check a result and every finding a disposition. The current-state page
  lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: KN ID minting and the identity event log replayed before raw records;
  merge, split, retire, and successor chains, including a merge of merged objects and a split after
  export; resolution of retired IDs; blocking that misses candidates; reproducible match features
  and probabilities; the rule against merging by name alone; change-set classes for absent, emptied,
  and unchanged fields; lineage from any value to its raw record; identity drift on rebuild;
  blocking cost at the target volume. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/identity/`, `src/kn/identity/`, `$DATA_DIR/identity/`,
  `tests/identity/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Rebuild
  twice from the ordered journal and compare KN IDs, links and match records. Reject reordered
  events. Shuffle source fixture order separately and compare resolution decisions. Trace a late
  update and an omitted field through claims, confirmations and the selected fact.
- Acceptance gates: Rebuilds reproduce every KN ID and lifecycle state. A merge followed by a split
  leaves every ID resolvable. Objects that differ in a discriminating attribute never link
  automatically. A late or omitted field preserves history. Every canonical value traces to its
  source record and evidence locator. Every finding has a severity,
  evidence, and a disposition, no `blocker` is accepted, and every fix starts from a failing
  regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The audit reran the member gates of records 0039, 0040 and 0044 to 0048, then probed the focus
areas of the scope boundary on the current tree. Four probes, kept under the evidence directory,
found the defects below. Every fix started from a failing test (`red.log`, `red-lineage.log`).

The owner asked for the specification and plan to be updated where the audit required it. Two
specification sentences changed, and both narrow what the matcher may do:

- A scored auto-link now requires that no discriminating attribute disagrees. The plan's audit gate
  already promised that objects differing in a discriminating attribute never link automatically;
  the specification named only the agreeing attribute.
- The permuted-input evaluation now says what sequential resolution can keep: the same objects and
  decision counts, with only the choice of which of two similar records waits for review changing.

## Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| OIA-01 | major | `probes/probe1.py`: an organization recorded at minute 10, then a record with the same domain observed at minute 0, minted a second object with no candidate, while the reverse order opened review. Views kept only readings at or before the observation instant, so an older observation that arrived late could not see a candidate first read later. Affects every adapter that replays history, prefetched datasets with old observation times, and the recall of `identity-match-calibration`. | Object identity, fixed. A record whose readings all come after the instant contributes its earliest reading (`registry.py` `_latest_readings`). Tests: `test_an_observation_older_than_every_reading_of_a_candidate_still_blocks` and the organization case of `test_every_submission_order_yields_the_same_objects_and_decisions`. |
| OIA-02 | major | `probes/probe2.py` and the red permutation test: when the renamed record with a stable LEI arrived first, the original record, observed earlier, found the LEI interval starting after its instant and went to review as a conflict. The specification fixture "renamed organization with a stable LEI (one object)" therefore failed under permuted input, and the reviewed record never registered its attributes. | Object identity, fixed. An observation earlier than every recorded interval belongs to the earliest holder; an instant between two holders stays a conflict (`registry.py` `holder`). Tests: `test_an_authoritative_key_seen_before_its_first_interval_links_to_its_holder`, `test_an_authoritative_key_seen_between_two_holders_still_needs_review`. |
| OIA-03 | major | `probes/probe1.py`: under a calibrated part profile, a candidate that agreed on manufacturer and MPN but disagreed on GTIN reached probability 0.9954 and linked automatically. The plan gate says such objects never link automatically. All shipped profiles are uncalibrated, so the defect was latent until `identity-match-calibration`. | Object identity, fixed. `_can_link` refuses when a discriminating attribute disagrees (`resolve.py:68`). Specification clarified as above; the calibration task names the veto. Test: `test_a_disagreeing_discriminator_never_links_automatically`. |
| OIA-04 | minor | `current/object-identity.md` said incremental writes remained in the plan after record 0048 accepted them, and its evidence list omitted records 0046 and 0048. | Object identity, fixed in the current-state page. |
| OIA-05 | major | `probes/probe3.py`: a weak-key fragment tracked through its parent's link, then a split of the parent's object. Neither successor's lineage showed the fragment's claim and no gap was reported; the fact projection also leaves it unattributed. The fragment has no link of its own, so the split could not assign it, which breaks the rule that each claim moves to exactly one successor. Affects price-break facts once `mapping-and-quality-rules` tracks fragments. | Object identity. Fixed in part: lineage reports `claim_successor_missing` for an audience that permits every rights statement (`lineage.py:107`, `lineage_records.py:74`); test `test_a_fragment_claim_that_no_split_successor_holds_is_a_gap`. The root cause is a scheduled bug, `fragment-claims-follow-splits`, which `ingestion-engine-implementation-audit` requires. Residual risk is listed under known limitations. |
| OIA-06 | minor | `permutation-probe-after.log`: with uncalibrated profiles, which of two similar records mints and which waits for review depends on arrival order, and a record in review registers no identifiers or attributes, so a later record with the same unregistered key can mint. No order auto-links by name or merges objects. | Object identity, accepted and documented with a reopening condition. `review-queue-cli` now requires that an accepted identity match registers the record's keys and attributes like an automatic link. |
| OIA-07 | minor | `retired-probe.log`: an alias naming a retired object is ignored, so the record mints without review. Retired IDs still resolve to themselves and a re-delivered anchor record goes to review. | Object identity, accepted and documented; reopen when a counterpart import returns retired KN IDs. |

The accepted limitations of the identity resolution audit were rechecked. IDRES-06 (an object
minted without a link sends its anchor record to review after a merge), IDRES-07 (a retried
observation returns its original receipt) and IDRES-08 (leading legal forms) still apply as
written. The evidence-model limitation for facts stored under a merged KN ID still applies, and
lineage still reports such a fact as `fact_subject_superseded`.

## Six audit checks

1. **Implementation validation.** The member unit and PostgreSQL gates reproduce on the base tree
   (`member-unit.xml`, `member-local.xml`), including the 5,000 and 50,000 organization submit
   check. The current-state page now matches the shipped write path and lists records 0046 to 0049.
2. **Specification conformance.** KN IDs are random UUIDv7 values stored before they are returned
   and replayed before raw records. Merged, split and reclassified IDs resolve in one step through
   flattened redirects, including a merge of merged objects and a split after merges
   (`test_resolve_uses_flat_redirects_and_history_follows_successors`), and a split after export
   resolves to both successors and turns an alias into review. Retired IDs stay resolvable.
   Recorded features reproduce score and probability through `verify_match`. Names cannot reach
   the link threshold and name-only records never link. Change-set classes cover absent, emptied
   and unchanged fields. A late version and an omitted field keep the current claims, and the
   selected facts trace through claims, change sets and sightings to archive record IDs
   (`test_lineage_trace.py`). The three matching findings and the fragment gap were the only
   departures found.
3. **Design scope.** The expensive surfaces are unchanged: the KN ID format, the hash-chained v1
   envelope, the ten-table contract, the `submit`, `track` and `lineage` entry points and the error
   codes. The fixes change only decisions computed for new observations, so existing journals,
   recorded matches and rebuilds are unaffected. The new gap kind extends the lineage `gaps` list.
   `fragment-claims-follow-splits` must add fragment lineage as an optional field, following the
   earlier pattern that keeps v1 hashes.
4. **Corner cases.** New cases cover out-of-order observation times, every submission order of
   the specification's identity fixtures, an identifier seen before and between holders, a
   disagreeing discriminator, a late version, an omitted field, a repeated sighting and a fragment
   claim across a split. Earlier audits cover empty, duplicate, malformed, torn and hostile journal
   input, Unicode names and domains, UTC offsets, interruption, retry, concurrency and rebuild
   equality. Record size is bounded upstream by the fetch size limit.
5. **Best practices.** Production code stays typed, the changed modules stay at or below about 250
   lines, and the complexity gate passes after two helper extractions. No dependency was added.
   The new tests are deterministic and network-free. The disagreement outcome is a named
   constant.
6. **Debt.** No parallel rule was added: the discriminator veto lives in the one auto-link gate,
   and identifier holding has one helper. No TODO, skipped test or weakened check was introduced.

## Acceptance evidence

Status: accepted on 2026-11-26. Initial `make plan-status`: 113 tasks, 101 agent, 12 human;
BLOCKED BY HUMAN=3, CLEAR=88, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=101, MODEL=12.

The evidence directory is `$DATA_DIR/identity/audit-fSAN08uP/`, with the probes under `probes/`.
PostgreSQL ran in its own Compose project `kn-oiaudit` on loopback port 15443 with the data
directory `service/`. Commands ran from the project root after `source scripts/shared/common.sh &&
kn_load_env` and, for the database, `kn_db_test_env`.

| Gate | Run and result |
| --- | --- |
| Member unit gates | `.venv/bin/python -m pytest tests/identity tests/evidence` passed 339 tests on the base tree (`member-unit.xml`). |
| Member PostgreSQL gates | `pytest -m "integration or heavy"` passed all 123 local tests on the base tree (`member-local.xml`). Warm submit medians were 16.3 ms at 5,000 and 28.1 ms at 50,000 organizations, a ratio of 1.725 against the 2.0 limit. |
| Regressions before the fixes | Five matching cases failed (`red.log`) and the fragment gap case failed (`red-lineage.log`). |
| Rebuilds reproduce every KN ID and lifecycle state | `test_merge_split_and_name_only_match_reproduce_across_rebuilds`, the incremental-write parity tests and `make model-baseline` fixtures compare every identity row after two rebuilds and a database drop (`local-after.xml`). Reordered events are refused (`test_envelope_rejects_digest_version_predecessor_and_reordering`). |
| A merge followed by a split leaves every ID resolvable | The rebuild test above, `test_resolve_uses_flat_redirects_and_history_follows_successors` and `test_aliases_follow_merge_and_split_redirects`. |
| Objects that differ in a discriminating attribute never link automatically | `test_a_disagreeing_discriminator_never_links_automatically`, after OIA-03. |
| Shuffled source order | `test_every_submission_order_yields_the_same_objects_and_decisions` submits the organization, part and variant fixtures in all orders (120, 2 and 2) and gets the same objects and decision counts. |
| A late or omitted field preserves history | `test_a_late_version_and_an_omitted_field_keep_the_current_claims` and the record 0045 tracking tests. |
| Every canonical value traces to its source record and evidence locator | `test_the_selected_facts_trace_to_their_archives_and_keep_the_late_version` and the record 0047 lineage tests; the one untraceable case is reported as `claim_successor_missing` and scheduled (OIA-05). |
| After the fixes | `make ci` passed 1,435 tests with 123 local-only tests deselected (`ci.log`). The local suite passed all 123 tests (`local-after.xml`); warm medians were 16.8 ms and 29.9 ms, a ratio of 1.777. The bilingual tests passed 104 (`bilingual.log`). |

`make lint-md`, `make lint-spec-plan` and `git diff --check` passed. No finding is a `blocker`.
The audit database service was stopped afterwards; its data directory stays with the evidence.

## Handoff

The audit left the plan and `fragment-claims-follow-splits` joined the ingestion-engine group
before its audit, which now requires it. The plan stays at 113 tasks, 101 agent and 12 human;
BLOCKED BY HUMAN=3, CLEAR=88, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=101, MODEL=12. Fifteen tasks
no longer require this audit. `review-queue-cli` gained the gate that an accepted identity match
registers the record's keys and attributes, and `identity-match-calibration` names the
discriminator veto. Its inputs are not ready: it still waits for `vl-itree-read-acceptance`,
which waits for InvenTree instance access. The next agent task is
`human-verification-projections`. The `object-identity` capability stays `planned` while
calibration and the fragment fix are open. No commit or push was made.
