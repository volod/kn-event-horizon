# CLI Golden Tests and Localization Scope

## Work contract

Fix the GitHub CLI golden test failures. Keep bilingual interface requirements on dashboards and
maps and retain original language metadata and optional English or Ukrainian translations for
text facts.

## Implementation and decisions

- Both reported failures came from argparse moving the synopsis ellipsis between lines. The
  successful-help normalization did not cover standalone usage errors, and the in-process test
  compared help verbatim. Both comparisons now ignore synopsis continuation wrapping.
- Help, statuses, confirmations and diagnostics use the English CLI catalog. The CLI ignores
  the former `KN_LOCALE` environment variable and rejects `--locale` with `E_ARGUMENTS`.
  The position of `--json` and existing machine result formats are preserved.
- Catalog parity applies to dashboard and map strings. English CLI keys are checked for usage and
  placeholders without requiring Ukrainian entries. Tests exercise Ukrainian plurals and
  formatting with representative dashboard strings.
- The existing evidence model stores original text and language on the claim and optional
  translations with separate provenance. Display tests exercise both languages and original
  fallback, including exact text and provenance preservation.
- The localization release gate covers dashboards and maps. The plan names the space, GDELT, and
  microelectronics dashboard audits as prerequisites.

## Acceptance evidence

- The standalone usage wrapping and English-only environment regressions both failed before the
  fix.
- The initial CI runs caught a contract fixture that used `cli.contract_help` as a bilingual display
  key. The fixture now uses a bilingual satellite label and a separate test checks that an
  English-only CLI key is refused.
- `make ci` on Python 3.12 and `make ci-github` on Python 3.13 each passed all required checks and
  1,409 tests. Each run deselected 123 local-only tests.
- All seven tests from `test_identity_database.py`, `test_identity_lifecycle.py`, and
  `test_lineage_cli.py` passed against a disposable PostGIS service.
- `make test-bilingual` passed 87 checks. `make bilingual-acceptance` passed those same checks and
  exited nonzero because the five dashboard and map release gates are open. Both manifests
  identify the open gates.
- `make lint-md` and `git diff --check` passed.

CI logs are under `$DATA_DIR/ci/cli-localization-EHfNt1PC/`. The available and strict release manifests
are under `$DATA_DIR/e2e/bilingual-2PijCjHa/` and `$DATA_DIR/e2e/bilingual-8JuKSaAE/`.

## Handoff

The plan contains 113 tasks before and after this change. Localization remains planned.
The [open acceptance record](0013-localization-bilingual-acceptance-suite.md) tracks dashboard and
map browser evidence.
