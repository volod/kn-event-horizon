# Message Catalog Core

## Work contract

```markdown
#### message-catalog-core

Every operator message must exist in `en` and `uk` from the first CLI command onward.

- Serves: `localization` -- [Localization](../design/spec.md#localization)
- Agent status: CLEAR
- Dependencies: none.
- User-visible outcome: `kn --locale uk info` and `KN_LOCALE=uk` print Ukrainian messages, and
  machine-readable JSON output keeps stable keys.
- Scope boundary: Catalog format and loader, the locale option, CLDR plural and number formatting,
  and the CI key-coverage check. Superset and export localization come in their own tasks.
- Data and artifact paths: `src/kn/i18n/`, `locales/en/`, `locales/uk/`, `src/kn/cli.py`,
  `tests/i18n/`, `pyproject.toml`, `uv.lock`.
- Execution path: Use gettext catalogs through Babel, with keys rather than English source strings
  as identifiers. Add a check that fails on a missing or unused key and on a user-facing literal in
  CLI handlers.
- Acceptance gates: Golden outputs exist in both locales. Plural tests cover the Ukrainian
  categories. The coverage check fails on fixtures with a missing key. `make ci` passes.
- Documentation target: A new `current/localization.md` page listed in the
  [areas index](current.md#areas).
```

The owner additionally requires independent interface and crawled-data languages. Data display
selects the requested language, then English, then the preserved original, with provenance.
This clarifies the localization specification; it does not add a translation service or dashboard.

## Implementation and decisions

The initial tree was clean; the task had no external or manual prerequisites. The localization
specification now distinguishes strict interface catalogs from optional source-data translations.
The core source-text API is included under the owner's explicit clarification. Database projections,
crawlers, dashboards, exports, and inference integration remain with their existing plan tasks.

- Added Babel 2.18.0 to `uv.lock` and the smallest runtime dependency range in `pyproject.toml`.
- Catalogs use stable keys in ASCII JSON with escaped Unicode. Babel compiles decoded strings to
  an in-memory GNU gettext catalog. CLDR category contexts handle Ukrainian fractions without the
  integer-only limitation of traditional gettext plural indexes. No runtime files are written.
- Catalog sources live in the Python package for reliable wheel and sdist inclusion. The root
  `locales` symlink exposes the same files at the specified authoring path, without copies or a
  build-time regeneration step.
- Translator instances own their locale. Missing interface keys and invalid catalogs raise errors;
  they never silently render an English message in a Ukrainian interface.
- CLI success/help/failure output uses catalogs. Operations return stable structured data;
  `--json` keeps machine keys and codes independent of locale. Raw exception strings are not
  operator text and are not exposed through error summaries.
- `TextVariant`, `SourceText`, and `SelectedText` keep original text, language tags, and provenance.
  Selection is requested tag, English, original, without modifying the source or creating facts.
  Tags match case-insensitively and exactly; regional language inference is outside this core.
- The CI catalog gate checks parity, unused and missing keys, message kinds, placeholders, CLDR
  categories, and literals at the CLI boundary. Its deterministic planted cases exercise failures.
  This is an AST boundary check, not a whole-program data-flow analyzer.
- Regression runs caught nested Ukrainian usage prefixes and decimal plural display dropping a
  visible zero. Each failing case was captured before its fix. Locale-parser help interception
  and unknown Babel locale errors also have regression coverage.

## Acceptance evidence

Status: accepted on 2026-11-22. All gates of `message-catalog-core` pass.

| Check | Command or artifact | Result |
| --- | --- | --- |
| Required gate | `make ci` | 253 passed; 36 local-only tests deselected; format, lint, typing, complexity, shell, contracts, links, and plan gates pass |
| Full quality | `UV_OFFLINE=1 UV_CACHE_DIR=/tmp/kn-uv-cache make quality` | 253 passed; 93.62% coverage; Markdown and distribution builds pass |
| Catalog coverage | `make catalog-check` | No findings; planted missing keys in either locale, unused keys, malformed plurals, placeholders, duplicates, and interface literals fail as expected |
| Goldens | `tests/i18n/goldens.json`, exercised by `make ci` | English and Ukrainian identity, root help, and nested help match |
| CLDR and formatting | `tests/i18n/test_core.py`, exercised by `make ci` | 0, 1, 2, 5, 11, 12, 21, 22, negative and fractional counts; exact Decimal display |
| Source text | `tests/i18n/test_core.py`, exercised by `make ci` | Requested, English, original selection; Russian, Chinese, Ukrainian, English, and unknown-language originals retained with provenance |
| Installed entrypoint | `.venv/bin/kn --locale uk info`, `KN_LOCALE=uk .venv/bin/kn --locale en --json info` | Ukrainian human output; explicit English wins over environment; stable JSON keys |
| Distribution isolation | Wheel smoke script below | Packaged catalogs, CLI, CLDR, JSON, and multilingual fallback work outside the source tree |
| Scope review | `git diff --check`, `git status --short`, changed-file ASCII scan | No whitespace errors; only task changes; source, tests, catalogs, and docs remain ASCII |

Runtime evidence is retained under `$DATA_DIR/localization/message-catalog-core-20261122/`:
`ci.log`, `quality.log`, `quality-network-retry.log`, `wheel.log`, and `verify-wheel.py`.
To repeat the wheel smoke check after `make build`, source `scripts/shared/common.sh`, run
`kn_load_env`, then run:

```bash
.venv/bin/python "$DATA_DIR/localization/message-catalog-core-20261122/verify-wheel.py"
```

The script extracts the built wheel into an automatically cleaned temporary directory and verifies
that imports come from it, rather than the checkout. It uses the locked environment's dependencies.
No database service or other persistent process was started. Temporary authoring scripts were
removed. Network-restricted dependency fetching initially failed; the authorized dependency refresh
succeeded, and the quality build retry passed offline using that cache. These are resolved setup
failures, not skipped acceptance gates. Database/heavy tests were not run because the task changes
no database contract or source adapter; the declared gate is `make ci`.

## Handoff

Task counts changed from 116 to 115: agent 105 to 104, human 11 unchanged, CLEAR 97 to 96.
RUN NEEDED remains 8, BLOCKED BY HUMAN 2, HUMAN-GATED 9. The accepted task and its prerequisite
references were removed from the forward plan. `localization` has a current-state link and remains
`planned` because its full bilingual acceptance suite is still open.

Available capability: strict bilingual CLI catalogs and formatting, catalog CI checks, stable
machine output, and an independent lossless source-text selection API. Existing
`evidence-claim-contracts`, `engine-skeleton`, and `dashboards-as-code` acceptance now explicitly
cover multilingual preservation and requested/English/original display. Durable projections and
crawlers are not claimed as implemented. Export and inference integration remain with their
existing tasks. `bilingual-acceptance-suite` and `localization-implementation-audit` retain release
screenshots, terminology review, and broader operator-path acceptance; no gate of this core task
remains open.
