# Source Management Implementation Audit

## Work contract

```markdown
#### source-management-implementation-audit

Every source enters through the catalogue, the crawler schema, and the onboarding workflow, so a gap
there repeats in every source that follows.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Dependencies: The [engine skeleton record](records/0059-ingestion-engine-engine-skeleton.md),
  the [source status record](records/0060-source-management-source-status-monitoring.md), and the
  [implementation audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Every later source is onboarded through verified, enforced declarations. The
  audit record gives every check a result and every finding a disposition. The current-state page
  lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: catalogue states and transitions, with sources disabled by default; crawler
  schema strictness, defaults, and messages; licence, rate-limit, and robots fields that are
  enforced, not advisory; error-code completeness; status freshness, stale and failing thresholds,
  and clock skew; templates that match what the engine needs; new source kinds, such as APIs, bulk
  files, and curated input, without schema changes. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/system/`, `src/kn/sources/`, `domains/<domain>/sources/`,
  `docs/guide/source-onboarding.md`, `docs/guide/templates/`, `tests/sources/`, `docs/impl/plan.md`,
  and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks.
  Validate a crawler file with an unknown key, one without a licence, and a disabled source with a
  schedule, and onboard one fixture source from the templates alone. Interrupt a fixture run before its
  checkpoint, retry it and compare status, history and cursor with an uninterrupted run.
- Acceptance gates: Each invalid crawler file is refused with a stable error code. A
  disabled source cannot run. The templates cover every field the schema requires. Every finding has
  a severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/source-management.md` listed in the [areas
  index](current.md#areas).
```

## Implementation and decisions

The audit reproduced the member gates of records 0035 to 0038, 0059 and 0060 on the base tree,
then probed each focus area through the shipped CLI and the loopback fixture engine. The probe
scripts are kept under `probes/` in the evidence directory. They cover validation of unknown keys,
missing rights, every disabled lifecycle state and unusable schedules
(`validate_probes.py.txt`), malformed input files (`corner/`), unbounded limits at fetch time
(`overflow_probe.py.txt`), an interrupted run compared with an uninterrupted one
(`interrupt_probe.py.txt`), and onboarding the synthetic snapshot source from the new crawler
template (`template_onboarding_probe.py.txt`).

The fixes change no stored format or CLI surface. They add three validation rules under the
existing `E_SOURCE_CONFIG` code: `cronDays`, `cronNeverRuns` and the schema's `maximum`. The
status JSON keeps its fields, and `freshness_threshold_seconds` now reports the default from the
specification. `kn.sources.status.monitoring_policy` derives the thresholds that the CLI and the
operations mart share. `kn.sources.config.schedule.longest_interval_seconds` measures a schedule
over one 400-year Gregorian cycle, in which weekdays and leap years repeat exactly. One pass
keeps only the longest gap between run days, cached per expression, so a consumer that derives
thresholds for every source holds an integer per schedule. The default threshold allows one
missed run.

A schedule may restrict the day of month or the day of week but not both. Vixie cron runs such a
schedule when either field matches, while other implementations require both, so the stale
threshold and a generated flow could disagree. No reviewed profile used both. The timeout bound of
one hour and the retention bound of 36,525 days keep every validated value within the socket and
calendar ranges that the fetch uses. They are generous limits rather than policy.

The new [crawler configuration template](../../guide/templates/source-crawler-config.yaml) is a
candidate HTTP JSON profile with commented alternatives for curated, package, Drive and watch
access, and the fields that enablement adds. A disabled profile keeps its schedule and validates
with its declared state, which the runner then refuses. Pausing a source therefore needs no
schedule edit, and flow generation already has a gate that emits no flow for a disabled source.

### Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| SMA-01 | major | Rebuild loads every catalogue row with `lifecycle_state` typed `Literal["candidate"]` (`seeds.py:55`), and no module writes another state. The engine fixture inserts its `enabled` row with SQL (`tests/engine/conftest.py:134`). The terms reviews, sampling authorizations and enablement approvals each name a catalogue state, and a rejection cannot keep the reason that the specification's negative result requires. `kn source run` requires an `enabled` row (`runner.py:38`). | Source management, scheduled feature `source-lifecycle-registry`, now first in the ingestion engine group. `prefetched-dataset-method` and the ingestion engine audit require it. The terms reviews are documentation-only and come later in written order, so they gain no `Requires` entry. Listed under known limitations. |
| SMA-02 | major | The seed format requires a workbook name, SHA-256, sheet, row and domain cells (`seeds.py:27`, `seeds.py:39`). An enabled profile needs a reviewed catalogue ID (`semantics.py:39`). In `template-onboarding.json`, offline validation refused the enabled synthetic source with `catalogueReference`. The SATCOM package, curated operator disclosures and counterpart instances are not proposal rows. | Source management, scheduled feature `source-lifecycle-registry`. |
| SMA-03 | major | Onboarding step 3 captures an authorized sample into the archive before enablement, but `load_runtime_config` refuses every state except `enabled` (`config/__init__.py:21`). A `sampling_authorized` profile validates with no approver, reference, budget or expiry (`validate-probes.json`). Every source task's steps 3 and 4 depend on a sample. | Source management, scheduled feature `source-sampling-admission`, after `http-fetch-safety`. The ingestion engine audit requires it. |
| SMA-04 | major | The specification gives the schedule's freshness threshold a default of twice the schedule interval. Status fell back to `monitoring.freshness_sla_seconds` instead, so the fixture profile turned stale after 21,600 rather than 14,400 seconds. The status record's CLI test asserted the fallback. | Source management, fixed. `monitoring_policy` doubles the longest gap between scheduled runs (`status.py:61`). Tests: `test_freshness_defaults_to_twice_the_longest_schedule_interval`, `test_longest_interval_spans_the_largest_gap_between_runs` and the updated `test_cli_reads_actual_snapshot_results_without_fetching` (`red-unit.log`, `red-status.log`). |
| SMA-05 | minor | `0 0 30 2 *` never runs, and `0 0 1 * 1` has implementation-specific meaning. Both validated (`validate-probes.json`). A never-running source would stay stale with no failed run. | Source management, fixed. `schedule_problem` refuses them with `cronNeverRuns` and `cronDays` (`schedule.py:93`). Test: `test_unusable_schedules_are_refused`. |
| SMA-06 | minor | A validated `timeout_seconds` of 10^12 or `retention_days` of 10^7 made `kn source run` raise an uncaught `OverflowError` with a traceback and no stable code. Each left attempt 1 unfinished, and the retention case first made one request (`overflow-*.txt`). | Source management, fixed. The schema bounds `timeout_seconds` to 3,600 and both retention fields to 36,525 through one `retentionDays` definition. Tests: two new cases in `test_invalid_shapes_report_exact_paths` (`red-unit-2.log`). |
| SMA-07 | minor | The four templates were Markdown worksheets. The guide drafted the crawler profile from the reference page, which pointed at a test fixture. No template covered the 126 properties that the schema can require outside counterpart profiles. | Source management, fixed. `source-crawler-config.yaml`, linked from onboarding step 1 and the current page. `test_template_is_a_valid_candidate_profile` and `test_template_names_every_property_the_schema_can_require` fail if the schema gains a field the template omits (`red-unit-2.log`). |
| SMA-08 | minor | No module reads `rate_limit` or checks `robots.txt` (`grep` over `src/kn/engine`). The fixture runner makes one request per run, so a second run inside the declared window still fetches. The safety rules require honoring `robots.txt`, and the `http-fetch-safety` gates checked neither. | Ingestion engine, scheduled bug in `http-fetch-safety`. Its execution path and gates now cover a disallowing `robots.txt` and consecutive runs inside the rate window. |
| SMA-09 | minor | Interrupting before commit and resuming left attempt 1 with null counters. The resumed status reported `requests_used` 0 and `bytes_received` 0, while the uninterrupted run reported 1 and 230 for the same single request (`interrupt-finish.json`). A crash that loses the capture refetches, so a run can exceed its budget unseen. | Ingestion engine, scheduled bug in `http-fetch-safety`, whose scope includes budget accounting. |
| SMA-10 | minor | Replay requires an enabled profile and catalogue row. A paused profile's replay is refused with `enabledState` (`test_disabled_profiles_and_catalogue_rows_issue_no_requests`). A rebuild would therefore drop the claims of a paused or retired source. | Ingestion engine, scheduled bug in `rebuild-from-raw`, with a gate for paused and retired sources. |
| SMA-11 | minor | After a development rebuild with the same journal, `kn source run` of a loaded source failed with `E_INPUT` because the tracker found no previous claims (`post-rebuild-run-traceback.txt`). The attempt stayed unfinished, and each retry resumes it. Status shows `unfinished` with zero failures until the stream turns stale. | Ingestion engine, scheduled bug in `rebuild-from-raw`, which replays before a fetch. |
| SMA-12 | minor | `ErrorCode` and `Status` in `outcomes.py` repeat the schema and contract vocabularies. Removing `budget_exhausted` from `ErrorCode` passed the existing contract test (`parity-old-suite-under-mutation.log`). | Ingestion engine, fixed. `test_state_contract.py` now compares both literals with the contract and schema and fails under that mutation (`red-parity-mutation.log`). |
| SMA-13 | minor | `microelectronics:C03` uses GraphQL and three proposal rows mention OAuth. Version 1 has no request body or token exchange. APIs, feeds, bulk files, packages and curated files need no schema change. | Source management, accepted and listed under known limitations. Reopen when such a source is onboarded. An additive optional block keeps existing profiles valid. |
| SMA-14 | minor | Status evaluates only the stale and consecutive-failure thresholds. Without `alert_thresholds.consecutive_failures`, `failing` stays false, and an unfinished attempt is not counted as a failure (`interrupt-*.json`). | Source management, accepted and listed. The stream still turns stale. Reopen when the operations mart defines alerting on the other declared thresholds. |
| SMA-15 | minor | Profiles in all six disabled states validate with their schedule and report their state (`validate-probes.json`). | Source management, accepted by design and listed. The runner refuses each before any request, and `kestra-flow-generation` gates flows on enablement. Reopen if flow generation needs validation to refuse the schedule. |

## Six audit checks

1. **Implementation validation.** The member gates reproduce on the base tree. 195 source,
   engine, ingestion-state and fixture-sanitization tests passed (`baseline.xml`). The
   integration suite had two cluster-wide `ALTER ROLE` races, caused by audit probes running
   beside it, and the identity submit ratio that record 0058 already reported (ISC-04). The
   serial rerun is under acceptance evidence. The CLI paths in record 0038 return the same codes
   and rules. The current page described the old stale fallback (SMA-04) and the test fixture as
   a starting point (SMA-07), both now corrected. Its commands, interfaces, paths and nine error
   codes otherwise matched.
2. **Specification conformance.** The four evaluation items of
   [source management](../../design/spec.md#source-management) map to `test_catalogue.py`,
   `test_config_enablement.py`, `test_config.py` and the status tests. Each crawler block,
   access method, rights field and approval field has a schema rule and a test. The departures
   were the freshness default (SMA-04, fixed), lifecycle transitions and registration (SMA-01,
   SMA-02), sampling (SMA-03) and `robots.txt` (SMA-08), each scheduled. Nothing exists outside
   the boundary: no crawler, discovery, or enablement from a catalogue row. The engine consumes
   `load_runtime_config`, `source_enabled` and `retry_class_for`. Status consumes
   `load_status_config`, the operations mart can use `monitoring_policy` with
   `read_source_status`, and flow generation reads validated profiles.
3. **Design scope.** These decisions would be expensive to change and were kept. Source IDs are
   `<domain>:<native-id>` or `<domain>:row-<n>`. The schema is `urn:kn:sources:crawler-config:1`
   with closed objects, so an optional field is additive. Diagnostics use `E_SOURCE_CONFIG`, a
   JSON Pointer and a rule name. The vocabulary has nine error codes, four retry classes and six
   run statuses, now parity-tested. Status rows sit under `source_status`. Parsers live under
   `kn.domains.<domain>`. New access methods, counterpart adapters and locales extend enums or
   optional properties. A new domain needs a catalogue contract enum value and seed fields, both
   additive in development. The reviewed seed format becomes versioned data migrations at
   release. A source outside the proposals needs `source-lifecycle-registry` (SMA-02).
4. **Corner cases.** Empty files, a list root, a byte-order mark, invalid UTF-8, an 8 MiB + 1
   byte file and 200 levels of nesting are refused with stable rules (`corner/results.txt`).
   Duplicate keys, aliases, control characters, duplicate list entries and conflicting error
   conditions have tests. The new schedule tests cover weekday, month-end and leap-day gaps,
   Sunday as 0 or 7, and schedules that never run. Interrupting before capture or before commit
   and resuming gives the uninterrupted run's state, checkpoint revision, cursor token and claims.
   Only the attempt number, and SMA-09's request counters, differ (`interrupt-*.json`). Clock
   skew, future confirmations, read-only reader access in another database time zone and the
   exact freshness boundary are tested in `test_status*.py`. Concurrent runs and replay
   idempotency are covered by `test_snapshot.py`. Bilingual labels are required, and source text
   keeps its language. Rebuild reproduces the catalogue, and two rebuilds list identically.
5. **Best practices.** Production code stays typed and passes mypy, Ruff and the complexity gate.
   `schedule.py` has 127 lines and `status.py` 222. The bounds and cycle length are named
   constants or schema definitions. Validation stays offline and value-free, and the template
   holds no credential, only environment-variable names. No dependency was added. Every new test
   is deterministic and network-free, and the template and schedule tests run in `make ci`.
6. **Debt.** `valid_cron` was replaced by `schedule_problem`, which shares one parser with the
   interval measurement. The duplicated outcome literals now have parity tests (SMA-12).
   `monitoring.freshness_sla_seconds` and three alert thresholds are declared for the operations
   mart and not read by status (SMA-14). No TODO, skipped test or weakened check was added.

## Acceptance evidence

Status: accepted on 2026-11-27, with ISC-04 still open under `performance-gate`. Initial
`make plan-status`: 107 tasks, 95 agent, 12 human; BLOCKED BY HUMAN=3, CLEAR=82, HUMAN-GATED=9,
RUN NEEDED=13; DELIVERY=98, MODEL=9.

The evidence directory is `$DATA_DIR/source-management-implementation-audit/check-1yriivNy/`.
Commands ran from the project root after `source scripts/shared/common.sh && kn_load_env`. The
database ran under its own Compose project `kn-smia`, loopback port 15532 and a fresh data
directory under the evidence directory, with `kn_db_test_env` for the tests.

| Gate | Run and result |
| --- | --- |
| Each invalid crawler file is refused with a stable error code | An unknown top-level key and an unknown key in `access` exit 1 with `E_SOURCE_CONFIG` and `additionalProperties` at `$` and `$/access`. An enabled profile without a licence exits 1 at `$/rights/licence` with `required`. Never-running and both-day schedules now exit 1 with `cronNeverRuns` and `cronDays`, and unbounded limits with `maximum`. Six malformed files are refused with `type`, `required`, `syntax`, `size` or `depth` (`validate-probes.json`, `corner/results.txt`). |
| A disabled source cannot run | `test_disabled_profiles_and_catalogue_rows_issue_no_requests` refuses `paused`, `retired`, `approved` and `sampling_authorized` profiles for run and replay with `enabledState`, and `paused`, `retired` and `rejected` catalogue rows with `catalogueState`. The fixture server counts zero requests and no attempt is registered. The existing admission test covers a `candidate` row and a missing rights decision. |
| The templates cover every field the schema requires | The template validates as a candidate and names all 126 properties the schema can require outside counterpart profiles. Removing a commented key fails the test. The synthetic snapshot source was onboarded from the template alone: the filled candidate validated, and uncommenting its enablement lines gave a profile that ran with `success`, 3 records, 3 claims and 1 request (`template-onboarding.json`). |
| Interruption compared with an uninterrupted run | Same state, freshness, checkpoint revision, cursor token and claim values for both interruption points. The history keeps the unfinished first attempt (`interrupt-archived_snapshot.json`, `interrupt-finish.json`, SMA-09). |
| Findings | 15 findings with severity, evidence and disposition. No `blocker` was found. Each fix started from a failing test or a reproduced failure: `red-unit.log`, `red-unit-2.log`, `red-status.log`, `red-parity-mutation.log`, `validate-probes.json` and `overflow-*.txt`. |
| Regression and integration suites | After the fixes, the source, engine, ingestion-state and fixture-sanitization tests passed 216 of 216 (`final-sources-engine.xml`). The serial integration suite passed 169 of 170 (`integration-after.xml`). The one failure is `test_postgresql_submit_cost_stays_flat` at a ratio of 2.175 against 2.0. With every source change stashed, it failed alone at 2.274 (`write-scale-base-tree.log`). That is the pre-existing ISC-04 of [record 0058](0058-ingestion-engine-ingestion-state-contracts.md), whose diagnosis belongs to `performance-gate`. Two rebuilds listed 119 candidates byte for byte, 65 microelectronics, 37 space and 17 GDELT, all `candidate`, and `kn db verify` passed (`source-list-*.json`). `make seed-check` reconciled 1,173 proposal rows. A wheel built offline and extracted outside the checkout loaded the bounded schema, validated the template and refused a never-running schedule (`wheel-smoke.log`). |
| `make ci` | Passed on the final tree with the scheduled tasks in the plan: 1,512 tests with 171 local-only tests deselected, and every catalog, contract, format, lint, typing, complexity, shell, fixture, documentation and spec-plan check (`ci.log`). |

## Handoff

The audit and its group heading left the plan. `source-lifecycle-registry` (SMA-01, SMA-02) opens
the ingestion engine group, and `source-sampling-admission` (SMA-03) follows `http-fetch-safety`.
`prefetched-dataset-method` requires the registry, and the ingestion engine audit requires both.
`http-fetch-safety` gained the robots, rate-window and interrupted-request checks (SMA-08,
SMA-09). `rebuild-from-raw` gained the paused-source replay and post-rebuild run checks (SMA-10,
SMA-11). `http-fetch-safety`, `capture-retention-enforcement`, `gdelt-domain-contracts`,
`kestra-flow-generation`, `space-elt-integration-gate` and the integrated model baseline no longer
require this audit.

The plan moves from 107 to 108 tasks, from 95 to 96 agent tasks, from 82 to 83 CLEAR and from 98
to 99 DELIVERY tasks. The 12 human, 9 MODEL, 3 BLOCKED BY HUMAN, 9 HUMAN-GATED and 13 RUN NEEDED
tasks are unchanged. The `source-management` capability stays `planned` while the two scheduled
features remain open. The next agent task is `source-lifecycle-registry`. No commit or push was
made.
