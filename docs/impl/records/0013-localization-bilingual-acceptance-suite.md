# Bilingual Acceptance Suite

## Work contract

```markdown
#### bilingual-acceptance-suite

Release needs one end-to-end proof that every operator path works in both locales.

- Serves: `localization` -- [Localization](../design/spec.md#localization)
- Agent status: CLEAR
- Requires: `obsidian-space-profile`, `microelectronics-comparison-dashboards`,
  `inventree-write-export`
- Dependencies: A browser automation tool justified as a development dependency.
- User-visible outcome: One command produces screenshots and golden outputs for the CLI, the review
  queue, source status, lineage, InvenTree plans and reports, the dashboards with filters and the
  map, and the export README, in both locales.
- Scope boundary: Verification and fixing of missing translations. The Kestra UI is excluded under
  the approved waiver.
- Data and artifact paths: `tests/e2e/`, `$DATA_DIR/e2e/<run-id>/` for screenshots, and
  `locales/`.
- Execution path: Script the browser paths against fixture data, and compare key coverage and
  rendered Cyrillic, dates, numbers, and missing-value labels.
- Acceptance gates: Both locales pass with no untranslated critical string. Any remaining
  English-only operator screen is listed as a release blocker.
- Documentation target: `current/localization.md` listed in the [areas index](current.md#areas).
```

The owner requests implementation, execution, fixes, and documentation, with independent
interface and source-data languages. Display uses requested language, English, then original;
source originals and provenance must survive when English and Ukrainian translations are absent.

## Implementation and decisions

Initial tree: clean. Prerequisites `obsidian-space-profile`,
`microelectronics-comparison-dashboards`, and `inventree-write-export` are still open.
The requested work starts the deterministic CLI and multilingual-data portion ahead of those
prerequisites. Missing operator surfaces remain release acceptance blockers; fixture-only browser
pages would not prove that the real product works. No browser dependency is justified until
a product browser surface exists.

- Added real subprocess CLI goldens for 21 paths in each locale, without substituting domain
  operations. The suite covers all delivered help surfaces, identity, contract lint/check/compile,
  package validation, missing input/configuration, locale precedence, and machine output.
- Added 12 source-text scenarios in both locales plus all English/Ukrainian translation subsets
  and orders for seven original-language tags. Exact text, language tags, provenance, whitespace,
  combining characters, originality, and fallback metadata survive selection and JSON round trips.
  An unrelated translation cannot replace an unavailable requested/English variant; later English
  translation retains the durable original. Missing interface keys still raise errors.
- Exercised the existing SATCOM archive and SQLite projection with source-only Chinese, Russian,
  Arabic, and unknown-language messages. Archives and raw cells round-trip exactly; typed rows
  retain original titles, tags, and source references. Identical replay imports no second snapshot.
  These are portable projection checks, not PostgreSQL service or live crawler acceptance.
- Added `make test-bilingual` for available paths and `make bilingual-acceptance` for release
  enforcement. Both write ASCII JSON evidence under a unique `$DATA_DIR/e2e/` run directory.
  The manifest lists selected/passing tests and blockers instead of claiming that a passing subset
  proves unavailable screens. The release command fails with or without artifact persistence while
  blockers remain. Running both Make targets together still executes the release check.
- Updated current localization and development documentation. The forward task retains all three
  prerequisites and its full screenshot gates. The audit wording now agrees with strict interface
  key rejection and independent source-text fallback. No dependency or storage contract changed.

Findings fixed during execution:

| Finding | Evidence before fix | Disposition |
| --- | --- | --- |
| Early global argument errors switched a Ukrainian interface to English | `.venv/bin/python -m pytest -q tests/e2e/test_cli.py -k malformed_locale --tb=short`: two failing cases; `kn --locale uk info --locale` emitted English usage/error | Fixed in `parse_interface_options`; it uses argparse's partially populated namespace for locale-aware diagnostics, including the usage formatter. JSON keys/codes stay unchanged. |
| Make dry-run test parsing rejected a continued pytest command | Initial `make ci`: the two new bilingual path-with-spaces cases failed with `No escaped character` | Fixed the shared test parser to join shell continuations; all seven DATA_DIR/Make checks pass. |
| A subset target used as a cached prerequisite could bypass a second release target | Multi-target dry-run regression requires two commands and a mandatory release flag on the second | Separate target recipes share one command definition; no target-specific flag dependency remains. |
| Artifact reports omitted sibling i18n results | A 96-test run listed only 32 passing tests; expanded passing-subset regression failed on the omitted sibling case | Register the result collector as a global pytest plugin. The regression verifies both directories and preserves the failing release status. |

The first available-suite run also exposed two incorrect new test assumptions: contract compilation
emits JSON metadata rather than SQL files, and empty optional typed cells become null. The tests
now validate compiled artifact digests and the existing typed/null contract while independently
checking exact raw cells. Production storage behavior was preserved.

## Acceptance evidence

Status: open on 2026-11-22. Available checks pass; the full release gate is intentionally unmet.

| Check | Command or artifact | Result |
| --- | --- | --- |
| Available bilingual paths | `make test-bilingual` | 96 passed; CLI, source selection, archive/import/replay, catalogs, plurals, and number formatting |
| Full release gate | `make bilingual-acceptance` | 96 available checks pass; pytest exits 1 and Make exits 2 because release blockers remain |
| Required gate | `make ci` | 288 passed, 36 local-only tests deselected; catalogs, contract artifacts, formatting, lint, typing, complexity, shell, links, and spec-plan checks pass |
| Quality | `UV_OFFLINE=1 UV_CACHE_DIR=/tmp/kn-uv-cache make quality` | 287 passed, 36 local-only tests deselected, 93.34% coverage; Markdown, links, and wheel/sdist builds passed before the final Make/reporting regressions were added |
| Reporting regression | `.venv/bin/python -m pytest tests/e2e/test_release_gate.py -q --tb=short` | 2 passed after reproducing the missing sibling-result failure |
| Make path and release gating | `.venv/bin/python -m pytest tests/deploy/test_make_data_dir.py -q --tb=short` | 7 passed, including paths containing spaces and combined subset/release targets |
| Scope review | `git diff --check`, changed-file ASCII scan | No whitespace errors; all changed files ASCII |

Logs are retained under `$DATA_DIR/e2e/implementation-20261122/`: `ci-initial.log` for the resolved
dry-run parsing failure, `ci.log` for the final required gate, `quality.log`, and `release-gate.log`.
Final release-run artifacts are under `$DATA_DIR/e2e/bilingual-LGTI2ATS/`: 96 selected and passing
tests, `test_exit_code: 0`, eight blocker groups, and `release_ready: false`. Every selected test
appears in the passing-test list. Earlier run directories retain the initial harness failures and
intermediate reporting evidence; the final directory is the current reference.

No database service, browser, or persistent process was started. Database/heavy tests and browser
screenshots were not run: this change does not modify the database contract or provide the missing
operator screens. A browser tool, fonts, deployed fixture projections, dates/units/missing-value
labels, and screenshot baselines remain prerequisites for full acceptance.

## Handoff

Before/after counts are unchanged: 115 tasks; agent 104, human 11; CLEAR 96, RUN NEEDED 8,
HUMAN-GATED 9, BLOCKED BY HUMAN 2. No task was removed, registry status changed, or dependency
waived. `localization` remains planned with a current-state link.

Keep `bilingual-acceptance-suite` open. Complete `obsidian-space-profile`,
`microelectronics-comparison-dashboards`, and `inventree-write-export`, including their transitive
review/source/lineage/dashboard prerequisites. Then add real browser and export acceptance using
the committed multilingual fixtures and shared selector, replace each blocker with actual evidence,
and run `make bilingual-acceptance` and `make ci`. The human terminology review and optional
localization audit remain downstream. Available capability affected: localization verification and
early CLI diagnostics; no dashboards or translation service are claimed as delivered.

The owner subsequently requested natural implementation sequencing. The remaining localization
group now follows microelectronics dashboards, the last group containing a direct prerequisite.
The capability registry and human-assisted lane use the same order. Task text, prerequisites,
statuses, and counts are unchanged.
