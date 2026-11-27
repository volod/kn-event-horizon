# 0053 Evidence model implementation audit

## Work contract

```markdown
#### evidence-model-implementation-audit

Claims and canonical selection decide what KN states as true, so an order-dependent or ambiguous
rule would surface only after many sources depend on it.

- Serves: `evidence-model` -- [Evidence model](../design/spec.md#evidence-model)
- Agent status: CLEAR
- Dependencies: The accepted task records of the group, including the
  [review queue record](records/0052-evidence-model-review-queue-cli.md), and the
  [implementation audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Canonical values are shown to be order-independent and explainable. The
  audit record gives every check a result and every finding a disposition. The current-state page
  lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: the rank-first update policy as a total order over claims, independent of
  arrival order; each mode (`priority`, `latest_observed`, `accumulate`, `fixed`); equal-rank
  conflicts; `owner_override` flags; derived verification states; data time used only within one
  source; conditions and units that make claims incomparable; review decisions as `owner_entered`
  claims and their replay; repetition that adds no rank; retraction and correction of a claim. Fixes
  only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/evidence/`, `contracts/core/policies/`,
  `src/kn/evidence/`, `src/kn/review/`, `tests/evidence/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Select
  over every permutation of a planted claim set, replay review decisions after a rebuild, and plant
  equal-rank disagreement, a unit mismatch, and a retracted claim.
- Acceptance gates: Every permutation gives the same canonical values and conflicts. Review
  decisions survive a rebuild. Incomparable conditions never resolve silently. Every finding has a
  severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/evidence-model.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The audit reran the member gates of records 0032, 0044, 0046, 0051 and 0052 on the base tree, then
probed each focus area of the scope boundary with nine probes kept under the evidence directory.
Probe 1 selects over all 5,040 arrival orders of a seven-claim set in each of the four modes. The
set plants same-source revisions, an equal-rank disagreement, a unit mismatch, an owner value and
a retracted claim. On the base tree the canonical content, open review items and members were
already identical in every order, so that gate held before any fix. The probes still found the
defects below. Most let something other than claim content and human decisions decide a value or
a conflict: dates across sources, the order storage returns decisions in, or claim keys. Every fix
started from a failing test (`red.log`, `probe9-before.log`, `red-allow-clear.log`).

The fixes change selection rules only where the specification already states the rule: equal-rank
values that differ beyond tolerance conflict, data time decides only within one source, a model
never picks a winner arbitrarily, an outranking empty claim never clears a value without review,
and `verified` belongs to the reviewed claim version. No contract, enum or stored layout changed.
`select` gained an optional `retired` argument and `history` an optional `superseded` argument
fed by the new `successors(claims)`. The new review reason code `fixed_values_tie` is free text,
like the existing codes.

No deployed contract declares `kn.updatePolicy`, so no stored fact history was computed under the
old rules. A history stored under them would differ from the new projection, and `write` would
refuse it, as for any policy change; the projection is rebuilt, never patched.

## Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| EMA-01 | major | `probe2-before.log`: three first-party sources stated 10, 10.8 and 11.6 kg with tolerance 1. When 10.8 had the newest valid-from date, all three formed one candidate and a value was selected; with either other date order they conflicted. A candidate joined claims that agreed with its first claim only (`candidates.py:90` on the base tree), and agreement within a tolerance is not transitive, so data time across sources decided whether two equal-rank values 1.6 kg apart conflicted. Affects every numeric field with a tolerance. | Evidence model, fixed. A claim joins a candidate only when it agrees with every claim in it (`candidates.py:95`). Test: `test_equal_rank_values_beyond_tolerance_conflict_whatever_their_dates`. |
| EMA-02 | major | `probe3-before.log`: one claim accepted in two review items had its selection time taken from whichever event storage returned last (12:00 or 14:00). `kn.review.facts.applied` reads decisions without an order, and `fixed` settles challengers recorded before that time, so a challenger recorded between the two decisions conflicted or not depending on SQL row order. | Evidence model, fixed. Active decisions apply in recording order, so a claim keeps the time of the latest decision about it (`review/selection.py:34`). Test: `test_a_claim_accepted_in_two_items_settles_the_same_challengers_in_every_order`. |
| EMA-03 | major | `probe4-before.log` (e) and `probe9-before.log`: tracking supersedes per record and field, but the projection groups claims by condition set. A correction that moved a value from 25 C to 85 C left the corrected claim current for 25 C, and a record that emptied the field under another condition set had no effect at all: the 25 C value stayed with no review. This breaks the documented rule that superseded claims are history and lets a retraction disappear. Affects condition-bound observations and lineage readers of facts. | Evidence model, fixed. An emptied claim joins its predecessor's subject (`projection.py:49`), `successors` gives each claim's first successor time whatever its subject (`projection.py:61`), and `history` retires such claims at that time; the review refresh passes it. Tests: `test_a_correction_to_another_condition_set_retires_the_old_value`, `test_an_emptied_field_under_another_condition_set_still_needs_review`. |
| EMA-04 | major | `probe5-before.log` (a): two first-party sources conflicted; when one emptied its field, the other value was selected with no review. A retracted newest revision likewise let the older revision of the same source return silently. An empty claim held its predecessor only when it outranked the leader itself (`planning.py:97` on the base tree), so an equal-rank retraction settled an open conflict. | Evidence model, fixed. Under the default `review` handling an empty claim also holds when the value it retracts still competes with the leader: it differs and the leader does not outrank it (`planning.py:116`). A retraction of an outranked or agreeing value stays quiet, and `allow_clear` keeps letting the retraction take effect; the first fix cleared the field there, which its own regression assertion caught (`red-allow-clear.log`). Test: `test_an_equal_rank_retraction_never_settles_a_conflict_silently`. |
| EMA-05 | minor | `probe5-before.log` (b): a reviewed claim and an owner claim stated one value; the claim key chose the owner claim as the fact's claim, yet the fact was `verified` with criterion `first_eligible`. The specification gives `verified` to the reviewed claim version. | Evidence model, fixed. At equal strength a reviewed claim represents its candidate (`candidates.py:80`), and `verified` requires the represented claim to be reviewed (`modes.py:54`). Test: `test_a_reviewed_claim_represents_the_value_it_verifies`. |
| EMA-06 | minor | `probe1-before.log` and `probe1-after.log`: over 5,040 orders the canonical content is identical in every mode, but the final version's deciding criterion and runner-up take two or three values in `priority` and `latest_observed`, and its outcome rows four. A claim that changes nothing else adds an outcome row and no new version, by design, so these fields describe the version when it opened. The base permutation test excluded them without saying why. | Evidence model, accepted and documented under known limitations with a reopening condition. The permutation test now states the exclusion. `analyst-fact-explanation` gained the dependency that competing values come from current claims through the outcome rows. |
| EMA-07 | major | `probe7-before.log`: one subject's history took 0.9 ms with no decisions, 70 ms with 100 and 741 ms with 1,000 decisions about other claims, because selection replayed at every decision time of the whole log. `kn review decide` refreshes every subject with a declared policy in its transaction, an estimated two hours for 10,000 subjects at that rate. | Evidence model, fixed. `history` replays only when a decision about the subject's own claims changes (`projection.py:153`); 1.8 ms at 1,000 unrelated decisions (`probe7-after.log`). Test: `test_decisions_about_other_claims_replay_nothing`. |
| EMA-08 | major | `probe8-before.log` (a): two sources stated different values of a `fixed` field first at the same instant, and the claim key chose the held, selected value. The specification's negative result forbids an arbitrary winner. | Evidence model, fixed. Values that share the earliest time hold nothing: the fact is `conflict` with a `fixed_value_change` item naming every candidate (`modes.py:147`, `modes.py:159`). Test: `test_equal_first_values_on_a_fixed_field_stay_unresolved`. |
| EMA-09 | major | `probe8-before.log` (b): a held value accepted in one review kept holding after a later review accepted the challenger, and the conflict reopened, because the earliest reviewed value held. The reviewer's latest decision had no effect. | Evidence model, fixed. The most recently accepted value holds and settles claims recorded by its decision; a tie in that time holds nothing. Test: `test_a_challenger_accepted_after_the_held_value_holds_the_fixed_field`. |
| EMA-10 | major | `src/kn/identity/tracking/claims.py:70` builds claims without event, published or valid times, and `delivery.py:72` refuses a second statement for one field. A newer datasheet revision kept as another record therefore conflicts with the older one under `priority`, and a record can claim only one item of an `accumulate` field. Affects `mapping-and-quality-rules` and every source with revisions or set-valued fields. | Object identity, scheduled feature `tracked-claim-times-and-sets`, which `mapping-and-quality-rules` now requires. Listed under known limitations on both current-state pages. |
| EMA-11 | minor | `probe6.log`: the same text in NFC and NFD, or with language tags `en` and `EN`, opens a conflict. Agreement is exact equality. | Evidence model, accepted and documented: the result is a review, never a silent choice. Reopen when a source fixture shows such conflicts in review. |
| EMA-12 | minor | `review/selection.py:43`: a claim rejected in one item stays ineligible after another item accepts it, until the rejection is revoked or superseded. | Evidence model, accepted and documented as the conservative rule for independent targets; reopen if operators report accepted choices without effect. |
| EMA-13 | minor | `current/evidence-model.md` listed per-source dispute rates as not implemented after record 0052 shipped them, and its evidence list omitted records 0051 and 0052. | Evidence model, fixed in the current-state page. |

Units were checked without a finding. Numbers in different normalized units, or without one,
never agree. At equal rank they conflict, a `fixed` field opens review, and an owner value in
kilograms over a first-party value in tonnes is flagged `owner_override`
(`probe4-before.log` (a) to (d)). A higher-ranked value wins by rank whatever the unit of a lower
one, which is the priority rule. Conditions are part of the subject, so claims under different
condition sets never compete.

## Six audit checks

1. **Implementation validation.** The member unit gates (216 tests, `member-unit.xml`) and the
   member PostgreSQL gates (49 tests, `member-local.xml`) pass on the base tree. The current-state
   page matched the commands, interfaces, paths and error codes except EMA-13, now fixed.
2. **Specification conformance.** Each update-policy outcome, eligibility rule, rank class, mode,
   verification state, owner override, empty-claim rule and evaluation item maps to a test in
   `tests/evidence/` or `tests/review/`. The departures found were EMA-01, EMA-04, EMA-05, EMA-08
   and EMA-09, all fixed. Two remain gaps: a curated observation ranks by its own source until
   `curated-source-method`, and tracked claims cannot feed data time or `accumulate` sets until
   `tracked-claim-times-and-sets`. "Why this fact?" stays with `analyst-fact-explanation`. The
   evidence-model evaluation items map to tests: contradictory ownership stays conflicted, times
   stay separate, provenance lookup, no duplicates on rerun, decisions survive rebuild and
   all-dataset human verification. The negative result holds: after EMA-01 and EMA-08 no mode
   chooses between values by claim key or cross-source time. Consumers keep their interfaces:
   tracking and lineage use the unchanged shapes, and the review refresh and lineage fixture pass
   `successors`.
3. **Design scope.** These decisions would be expensive to change later and were kept. The fact
   key covers KN ID, field, condition set and audience, never locale. The fact version key covers
   its explanation columns, so an ignored claim adds a row instead of a version (EMA-06). Review
   item keys cover their sorted candidates. Decision IDs bind the canonical event. The policy
   digest is canonical JSON. Rank overrides are keyed by source and field group. Claim keys
   exclude recording times. The audit's interface additions are optional arguments, so existing
   callers and stored rows are unaffected. New sources extend the rank table, domains declare
   `kn.updatePolicy`, and a new mode needs its vocabulary and contract enum.
4. **Corner cases.** New cases: every arrival order of two planted sets in all four modes (tests)
   and of a seven-claim set (probe 1). Also a retraction recorded before its predecessor,
   tolerance chains, unit mismatches, equal first times, two acceptances of one claim in either
   storage order, a correction and a retraction under another condition set, and decisions about
   other claims. Earlier records and tests cover the rest: duplicate keys collapse, and an empty
   or ineligible set gives no fact. NUL text, credentialed URIs, naive times, future performed
   times and out-of-range decimals are refused. Interrupted, retried and concurrent decision
   writes recover, reruns write nothing new, and a translation never adds a fact. A cycle of
   supersessions, impossible with content keys, still ends in `_home`. Two rebuilds reproduce every
   projected fact, outcome, item and decision row
   (`test_review_decisions_reproduce_canonical_facts_after_two_rebuilds`).
5. **Best practices.** Production code stays typed and passes mypy. The changed modules stay below
   250 lines, and the complexity gate passes after `history` and `_review_times` were split. No
   dependency was added. The new tests are deterministic and network-free, and the code is ASCII.
   The refresh cost is now measured (EMA-07).
6. **Debt.** No parallel rule was added: supersession is still decided only in `select`, and
   holding in `fixed` has one helper. The removed claim-key tie break was the only dead path.
   `test_decisions_about_other_claims_replay_nothing` counts selection calls, an internal; it
   measures the cost defect directly and also asserts identical output. No TODO, skipped test or
   weakened check was introduced.

## Acceptance evidence

Status: accepted on 2026-11-26. Initial `make plan-status`: 111 tasks, 99 agent, 12 human;
BLOCKED BY HUMAN=3, CLEAR=86, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=100, MODEL=11.

The evidence directory is `$DATA_DIR/evidence/audit-WeSzaTLH/`, with the probes under `probes/`.
PostgreSQL ran in its own Compose project `kn-emaudit` on loopback port 15444 with the data
directory `service-data/`. Commands ran from the project root after `source
scripts/shared/common.sh && kn_load_env`, with `KN_TEST_DATABASE_URL` and
`KN_TEST_DATABASE_PASSWORD_FILE` pointing at that service.

| Gate | Run and result |
| --- | --- |
| Member unit gates | `.venv/bin/python -m pytest tests/evidence tests/review` passed 216 tests on the base tree (`member-unit.xml`). |
| Member PostgreSQL gates | `pytest -m "integration or heavy"` over the evidence, verification, review and identity-review modules passed 49 tests on the base tree (`member-local.xml`). |
| Regressions before the fixes | Six tests failed and the corrections module failed to import `successors` (`red.log`). On the base tree the emptied-field scenario left the 25 C value with no review (`probe9-before.log`). |
| Every permutation gives the same canonical values and conflicts | `test_every_arrival_order_gives_identical_canonical_values` covers two five-claim sets in all four modes, comparing the fact, open items and members. Probe 1 gives one canonical state per mode over 5,040 orders before and after the fixes (`probe1-before.log`, `probe1-after.log`). |
| Review decisions survive a rebuild | `test_review_decisions_reproduce_canonical_facts_after_two_rebuilds` compares every projected fact, outcome, item and decision row after two rebuilds, reattachment and refresh. `test_two_rebuilds_reattach_the_original_queue_decision` still passes. |
| Incomparable conditions never resolve silently | Unit mismatches conflict or open review (`probe4-after.log`). Condition sets are separate subjects, and a correction or retraction across them now retires or holds the old value (EMA-03). |
| After the fixes | All probes rerun (`*-after.log`). On the final tree the member PostgreSQL gates and the lineage CLI test passed 51 tests (`member-local-final.xml`). Every local-only test passed, 141 of 141, on the tree before the `allow_clear` refinement of EMA-04, which no database test exercises (`local-after.xml`). `make model-baseline` passed (`$DATA_DIR/model-baseline/check-4CwY4TjF/`). |
| `make ci` | Passed on the final tree: 1,441 tests with 141 local-only tests deselected, and every format, lint, typing, complexity, contract, shell, documentation and spec-plan check (`ci.log`). |

`make lint-md`, `make lint-spec-plan` and `git diff --check` passed. No finding is a `blocker`.
The audit database service was stopped afterwards; its data directory stays with the evidence.

## Handoff

The audit left the plan, and its group heading went with it. `tracked-claim-times-and-sets`
(EMA-10) joined the ingestion-engine group before `mapping-and-quality-rules`, which now requires
it. The plan stays at 111 tasks, 99 agent and 12 human; BLOCKED BY HUMAN=3, CLEAR=86,
HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=100, MODEL=11. Six tasks no longer require this audit:
`curated-source-method`, `rebuild-from-raw`, `interchange-package-export`,
`space-elt-integration-gate`, `analyst-fact-explanation` and `development-model-baseline`.
`analyst-fact-explanation` names EMA-06 in its dependencies. The `evidence-model` capability is
now `shipped`; its remaining gaps are listed under its known limitations and owned by
`curated-source-method` and `tracked-claim-times-and-sets`. The next agent task is
`warc-raw-store`. No commit or push was made.
