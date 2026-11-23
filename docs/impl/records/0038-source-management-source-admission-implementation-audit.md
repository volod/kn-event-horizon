# Source Admission Implementation Audit

## Work contract

```markdown
#### source-admission-implementation-audit

Verify the source keys and onboarding handoff against its specification and the next consumer.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Dependencies: The [catalogue import record](records/0035-source-management-source-catalogue-import.md),
  the [crawler configuration record](records/0036-source-management-crawler-config-schema.md),
  the [source onboarding record](records/0037-source-management-source-onboarding-workflow.md),
  and the [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Run onboarding with a disabled catalogue entry and a configuration missing its
  rights decision. Check that neither can schedule a fetch.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: [Current-state areas](current.md#areas).
```

## Implementation and decisions

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| ADMISSION-01 | major | Three enabled HTTP profiles passed with raw redistribution broader than the export review. Archive and export consumers would receive contradictory instructions. | Source management, fixed. `test_raw_redistribution_cannot_exceed_reviewed_rights` covers forbidden, private and restricted policies. |
| ADMISSION-02 | major | A passing case masked a nested suite with a failure counter, or an unnamed case outside its suite. Both reports passed enablement. | Source management, fixed. `test_incomplete_and_failed_reports_refuse_enablement` now checks both structures against the pytest report layout. |
| ADMISSION-03 | minor | `kn source validate` exits 0 for a valid candidate. The first fetch consumer previously had only a successful run and replay in its plan gates. | Ingestion engine, quality improvement assigned to [engine-skeleton](../plan.md#engine-skeleton). Its fixture server must count zero requests for a candidate or missing rights. |

## Six audit checks

1. **Implementation validation.** Reproduced the catalogue, configuration and onboarding gates
   below through the shipped CLI, database rebuild and CI entry points. Only synthetic profiles
   were marked enabled. No source owner decision or external collection was needed.
2. **Specification conformance.** `tests/sources/test_catalogue.py` reconciles every proposal cell
   and locator. The crawler schema and `test_config.py` cover all declared blocks, five profiles
   and all nine error codes with their retry classes. Enablement tests enforce review, fixtures
   and report evidence. The guide covers all seven onboarding steps and links the four templates.
   The status evaluation in the specification belongs to
   [source-status-monitoring](../plan.md#source-status-monitoring).
3. **Design scope.** Qualified native or worksheet IDs survive reordering and feed ranking and
   evidence references. The ODCS baseline deploys catalogue data separately from versioned,
   reviewed YAML. New sources reuse the profiles and domain parser namespace. The semantic
   validator owns cross-field rights checks. CLI clients can use the state and stable error path
   in either locale. The archive-first pagination decision in record 0036 still applies.
4. **Corner cases.** Seed and config tests cover empty, duplicate, incomplete and malformed
   inputs. The shared document loader bounds size and depth and refuses aliases. Evidence tests
   exercise missing and empty files, symlinks, invalid XML, skipped cases and inconsistent
   totals. Audit probes reversed the GDELT seed order, rejected an 8 MiB + 1 byte report and
   compared eight concurrent read-only validations. Bilingual listing preserves proposal text.
   Cron is UTC and review timestamps require an offset. Admission compares no wall clocks.
   Database integration checks cover retry, conflicting seeds, transactional rollback and an
   interrupted rebuild with a concurrent reader. Fetch interruption belongs to the engine.
5. **Best practices.** Validation uses local files, the pinned schema and bounded report reads.
   Reader-role listing, safe error paths and redacted fixture diagnostics were exercised.
   Format, typing, lint and complexity gates cover the fixes. No dependency was added.
6. **Debt.** Checked the source modules, fixture scanner and corresponding tests for skips,
   TODOs and duplicate policy logic. The general redistribution check now also serves adapter
   profiles. Human review still establishes the revision a test report covers and whether
   fixtures may be redistributed. The first runtime consumer owns ADMISSION-03.

## Acceptance evidence

Status: accepted on 2026-11-23.

Evidence directory: `$DATA_DIR/source-admission/check-tIUiqrok/`. Run commands from the project
root with the repository virtual environment. The database run used its own Compose project,
loopback port and fresh data directory.

| Gate | Run and result |
| --- | --- |
| Catalogue and rebuild (0035) | `make db-up`, then `KN_ENVIRONMENT=development make db-rebuild` and `make db-verify` twice. Captured `kn --json --locale en source list` and the `uk` equivalent from CLI stderr. The empty listing became 119 unique unverified candidates (37 space, 65 microelectronics, 17 GDELT). All four JSON listings were byte-identical. Both localized listings had 119 rows. |
| Database ownership and replay (0035) | `make test-integration` passed 92 tests. `make model-baseline` reproduced the same 62-table fixture snapshot twice. `database.log` includes Compose teardown. `make seed-check` reconciled 1,173 proposal rows. |
| Configuration and packaging (0035, 0036) | Built wheel and sdist with offline `uv build` after `kn_load_env`. The extracted wheel loaded all six registered contracts and 119 candidates outside the checkout import path. `smoke.py` checked the CLI from both the checkout and extracted wheel, all five profiles and the invalid label in both locales. |
| Admission boundary (0036, 0037) | `kn --json source run space:row-4` exited 2 with `E_ARGUMENTS`. The candidate validated as `candidate`. Validation accepted an enabled synthetic copy referencing the actual passing pytest report. Removing only the rights decision or approval reference returned 1 with `E_SOURCE_CONFIG` at `$/rights/permission` or `$/approval/reference`. Neither negative path reached fetch or scheduling. See `smoke.log`. |
| Fixture review (0037) | With a temporary synthetic Authorization header in a test fixture, `make ci` exited 2 at `fixture-check`. The diagnostic identified the file and rule without the planted value. Removed the fixture and verified the clean scan of 21 files. See `negative-ci.log`. |
| Regressions | Five cases failed before the fixes (`red.log`). Afterward, `.venv/bin/python -m pytest tests/sources tests/quality/test_fixture_sanitization.py --junitxml <run>/suite.xml` passed all 163 cases. `corners.py` records the additional size, order and concurrency probes. |

`make ci` passed with 1,089 tests. All 92 tests deselected by that gate passed in the
separate integration run. `make lint-md` and `git diff --check` passed. The disposable
PostGIS volume and credentials were removed after teardown.

## Handoff

The audit leaves the plan with 121 tasks (122 before), 108 agent tasks (109 before) and
13 human tasks. DELIVERY falls from 108 to 107 and MODEL stays at 14. The next ready agent task
is `object-lifecycle-operations`. Evidence claims, ingestion state, the engine and the three
domain terms reviews can consume the audited handoff subject to their other dependencies.
The source-management capability stays planned until its run-status work passes.
