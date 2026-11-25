# 0042 Identity Resolution Implementation Audit

## Work contract

```markdown
#### identity-resolution-implementation-audit

Verify the identity lifecycle and matching handoff against its specification and the next consumer.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: The [lifecycle acceptance record](records/0039-object-identity-object-lifecycle-operations.md),
  the [matching acceptance record](records/0040-object-identity-identity-match-engine.md),
  and the [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Replay a merge followed by a split and submit a name-only match. Compare IDs and
  decisions across rebuilds and check the review boundary.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Findings

Every fix started from a failing test. `red.log` and `red-integration.log` record the failures
before the change; the second ran the new PostgreSQL tests against an unmodified worktree of the
base commit.

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| IDRES-01 | major | `probe2.py`: after a torn match batch, `LockedJournal.append` accepted a retirement and `lifecycle.submit` would do the same. The match retry then refused as a diverged suffix and every new match refused as pending, which stopped matching for good. Affects every source adapter and `kn identity` operators. | Identity resolution, fixed. `State.pending_match()` gates every non-match append and registry mint. Lifecycle refuses before it writes a review decision, and the CLI refuses before its prompt. Tests: `test_pending_match_refuses_other_journal_writes_until_its_retry`, `test_lifecycle_refuses_before_review_while_a_match_batch_is_pending`. |
| IDRES-02 | major | `probe1.py`: scoring used one latest reading per field per object. After a reviewed merge of A into B, a new record with A's recorded domain minted a third object. A second source linked through the same LEI hid the first source's domain, and two same-instant names from different records erased the field. Affects adapters (duplicate objects), `review-queue-cli` (missed candidates) and `identity-match-calibration` (recall). | Identity resolution, fixed. Matcher attributes name their source record in an optional field, so earlier v1 hashes are unchanged. Each candidate scores one view per contributing record and keeps the best. Tests: the three view cases in `test_match_registry.py` and `test_merge_split_and_name_only_match_reproduce_across_rebuilds`. |
| IDRES-03 | major | `probe4.py`: an alias naming a merged KN ID was dropped, and the record minted a new object. Affects counterpart adapters that carry stored KN IDs, which the specification keeps resolvable. | Identity resolution, fixed. Aliases follow redirects to active successors of the profile's class. Unknown alias IDs stay ignored. Test: `test_aliases_follow_merge_and_split_redirects`. |
| IDRES-04 | major | `scale-before.log`: one submit took 1.204 s at 1,000 organizations, four times the 500-record cost. A 2,000-record ingest did not finish within 600 s. `cProfile` put 97% of a submit in replay scans of all objects (anchor uniqueness) and all holdings (active links). The growth test measured a 15.4x ratio for 4x more history. Affects every adapter. | Identity resolution, fixed. Replay indexes anchors, record links, identifier intervals, record versions, change sets and match requests. Projection maps decision references once. After: 0.110 s at 1,000 records. The `heavy` `test_replay_and_projection_cost_grows_linearly_with_history` keeps the ratio below 8. |
| IDRES-05 | major | `scale-after.log`: each write still parses, validates and replays the whole journal and rewrites every identity table. One submit took 0.028 s at 250 records and 0.280 s at 2,000. A sequential 4,000-record ingest did not finish within 900 s. Affects high-volume sources reached through `mapping-and-quality-rules` and the space, vendor and GDELT groups. | Object identity, quality improvement scheduled as [`identity-incremental-writes`](../plan.md#identity-incremental-writes). `object-identity-implementation-audit` requires it, and every real-data consumer requires that audit. |
| IDRES-06 | minor | Code review of `_exact`: an object minted without a link, which only a reclassification successor is today, sends its re-delivered anchor record to review after a merge instead of following the redirect. | Identity resolution, accepted. Listed under [known limitations](../current/object-identity.md#known-limitations) with its reopening condition. |
| IDRES-07 | minor | A retried observation returns its original receipt, whose KN ID can since have been merged. The old ID stays resolvable. | Identity resolution, accepted and documented: adapters resolve the receipt before storing the ID outside KN. |
| IDRES-08 | minor | `legal-name-v1` keeps a leading Ukrainian legal form, while trailing English and German forms are removed. Names never discriminate, so only review recall can drop. | Identity resolution, accepted with the calibration reopening condition on the current-state page. |

## Six audit checks

1. **Implementation validation.** The member gates below reproduce on the current tree from the
   commands in records 0039 and 0040. The current-state page now matches the actual write order,
   refusal codes, per-record views, alias redirects and tests.
2. **Specification conformance.** IDs are random UUIDv7 values minted once per source anchor,
   never derived from labels and never reused. Lifecycle states, terminal redirects resolved in
   one step, cross-class refusal and reviewed decisions map to `transitions.py`,
   `lifecycle.py` and their tests. Resolution order, the calibrated, threshold, margin and
   discriminating gates, the review-only default and the name-only link rule map to `resolve.py`
   and `profiles.py`. Organizations may block on a name, so a name-only record opens review and
   never links. Partial-update tracking, lineage and calibration remain open plan tasks. The
   matcher never merges by itself: a shared authoritative identifier goes to review.
3. **Design scope.** The expensive surfaces are the KN ID format, the hash-chained v1 envelope,
   the ten-table ODCS contract, the `E_INPUT`, `E_IDENTITY_AUTH` and `E_DATABASE` codes, and the
   `submit` adapter entry point. The attribute record follows the earlier optional trace pattern,
   so existing journals keep their hashes. New classes add a profile file. Calibration changes
   profile values only. Incremental writes can replace the projection without changing events.
4. **Corner cases.** Existing tests cover empty and duplicate inputs, missing values, malformed
   and torn journals, symlinks, out-of-order identifier intervals, reordered events,
   interruptions, retries, concurrent writers and rebuild equality. The audit added duplicate
   observation inputs, retries across UTC offsets, Cyrillic legal names, IDN domains and journal
   appends during an incomplete batch. Oversized graded strings and numbers already compare as
   `invalid`. Naive timestamps refuse.
5. **Best practices.** Production code stays typed, under 250 lines per file and inside the
   complexity gate. The audit added no dependency. Tests stay network-free and deterministic,
   except the timing ratio, which is `heavy` and runs only locally. Reviewer identity still comes
   from the operator boundary, not source data.
6. **Debt.** Three copies of the anchor scan and a second pending-batch loop now share the
   replay indexes and `pending_match`. No TODO, skip or weakened check exists in the group. The
   diverged-retry test now writes its suffix directly, as a journal from before IDRES-01 could
   hold it. `tests/identity/test_matching.py` was already 258 lines, so new cases went into
   `test_match_registry.py`.

## Acceptance evidence

Status: accepted on 2026-11-25.

The evidence directory is `$DATA_DIR/identity-resolution/audit-5NZX5gl3/`. PostgreSQL ran in its
own Compose project `kn-idaudit` on loopback port 15442 with the data directory `service/`. Commands
ran from the project root after `source scripts/shared/common.sh && kn_load_env` and, for the
database, `kn_db_test_env`.

| Gate | Run and result |
| --- | --- |
| Member unit gates (0039, 0040) | `.venv/bin/python -m pytest tests/identity` passed all 107 tests on the base tree. |
| Member PostgreSQL gates | The record 0039 command over `tests/integration/test_identity*.py`, `test_human_verification.py`, `test_rebuild*.py` and `test_model_baseline.py` passed 43 tests (`member-postgres.xml`). |
| Regressions before the fix | Six new unit cases failed (`red.log`). The two new PostgreSQL cases failed against the base commit: the name-only record minted and the lifecycle write went through (`red-integration.log`). |
| Audit execution path | `test_merge_split_and_name_only_match_reproduce_across_rebuilds` mints four organizations, merges one and splits the survivor through reviewed decisions. A name-only record then opens review on the successor that holds its evidence, with no link or object, and stays review under a calibrated profile. Re-delivery and the LEI follow the split assignment. Two rebuilds and a rebuild after dropping the schema reproduce every identity row, both decision IDs and resolution. |
| After the fixes | `tests/identity` passed 116 tests, including the `heavy` growth check (`identity-unit.xml`). The PostgreSQL command above passed 45 tests (`postgres-after.xml`). `make test-bilingual` passed 102 tests (`bilingual-Ozaoqqil/`). |
| Scale | `probe3.py` timings before and after are in `scale-before.log` and `scale-after.log`. |

`make ci` passed with 1,172 tests and 102 local-only tests deselected (`ci-final.log`). Against
the audit database, `make test-integration` passed all 101 integration tests
(`integration-all.log`). `make lint-md` and `git diff --check` passed. `make bootstrap` reported
that Java 21 and Apache Jena are missing on this host. That affects only the SKOS reference check,
which is outside this group. The audit database service was stopped and its volume removed after
the runs.

## Handoff

The plan stays at 118 tasks, 106 agent tasks and 12 human tasks. The audit leaves the plan and
`identity-incremental-writes` joins the object-identity group. DELIVERY stays at 105 and MODEL at
13. `partial-update-tracking`, `canonical-fact-selection`, `review-queue-cli` and `engine-skeleton`
no longer require this audit. The next ready agent task is `evidence-claim-contracts`. The
object-identity capability stays planned while partial updates, lineage and calibration remain
open.
