# Localization

The message catalog core serves the [localization capability](../../design/spec.md#localization).
Interface text and crawled text have independent language rules. The core is available; dashboard,
export, and complete operator-path acceptance remain in the [forward plan](../plan.md).

## Operator interface

```bash
kn --locale uk info
KN_LOCALE=uk kn info
kn --locale uk space satcom --help
kn --locale uk --json info
make catalog-check
```

The explicit `--locale` overrides `KN_LOCALE`; the default is `en`. `main()` accepts the global
`--locale` and `--json` options before or after a subcommand. Locale selection happens before help
rendering. Each invocation uses its own `Translator`, without changing process-global gettext
state. Unsupported interface locales fail with `E_LOCALE` and exit status 2.
Malformed global options use the last parsed locale, or `KN_LOCALE` before any explicit selection,
for both usage and error text. If that locale is invalid, the diagnostic uses English. JSON argument
errors keep the same keys and codes even when the locale option itself is malformed.

CLI help, success messages, and error summaries use the catalog. Command names, flags, IDs,
versions, hashes, paths, and JSON keys remain stable. Operator output uses the `kn.operator` logger
and stderr, with help on stdout. Domain and quality-tool engineering logs stay English.
Operations return structured data; the CLI owns its presentation.

`--json` emits ASCII JSON with unchanged keys and codes across locales. For example, `info` returns
`distribution`, `package`, and `version`. SATCOM validation returns the original manifest fields
`import_id`, `tables`, and `files`; normal text output summarizes its table count. Imports return
`import_id`, `status` (`imported` or `already_imported`), and `archive`. Database operations return
`status: verified`; contract operations return `contract_id`, `version`, and `digest`.

Errors use `E_ARGUMENTS` or `E_LOCALE` (status 2), and `E_DATABASE`, `E_CONTRACT`, or `E_INPUT`
(status 1). JSON errors have the shape `{"error": {"code": "E_INPUT"}}`. Human argument errors
show localized usage and refer to `--help`. Domain error summaries give a localized action without
exposing arbitrary exception strings or connection credentials.

## Catalogs and formatting

`locales/` exposes `src/kn/i18n/locales/` through a repository symlink. The
[English](../../../locales/en/messages.json) and [Ukrainian](../../../locales/uk/messages.json)
catalogs are the same files, packaged into both source and wheel distributions. Resource loading uses
`importlib.resources`, independent of the working directory or source checkout.

Each `<locale>/messages.json` is an ASCII JSON object with escaped Unicode. At runtime JSON decodes
to Unicode, Babel builds a GNU MO catalog in memory, and Python's `GNUTranslations` renders the
messages. This keeps one editable source and meets the repository's ASCII rule without requiring
binary MO files in Git. See Babel's [MO support](https://babel.pocoo.org/en/latest/api/messages/mofile.html).

- Stable keys such as `cli.info` identify messages; English sentences are never identifiers.
- Singular values are nonempty strings with named placeholders such as `{version}`.
- Plural values map every CLDR category for that locale to a nonempty string with `{count}`.
  English has `one` and `other`; Ukrainian has `one`, `few`, `many`, and `other`.
- `Translator.text(key, **values)` renders a singular message.
  `Translator.plural(key, count, **values)` selects a CLDR category and formats the count.
  Gettext contexts store categories so fractional counts retain CLDR's `other` behavior.
- `Translator.number(int_or_decimal)` uses locale separators without truncating precision and
  retains Decimal fraction digits, including trailing zeros. Displayed counts therefore agree
  with their plural category. See Babel's [number formatting](https://babel.pocoo.org/en/latest/numbers.html)
  and [CLDR plural API](https://babel.pocoo.org/en/latest/api/core.html#babel.core.Locale.plural_form).

Missing interface keys, mismatched placeholders, and wrong singular/plural calls raise errors.
There is no silent English fallback for missing interface translations. An additional Babel locale
can use the same key set in another resource directory; no loader branch is needed. CLI help
currently advertises the supported `en` and `uk` pair. Date and unit presentation and additional
operator surfaces remain in their owning plan tasks.

## Source data and translations

`kn.i18n.data` provides immutable values for later ingestion, analytics, and export integration:

- `TextVariant(text, language, provenance)` keeps exact text and a durable source-record, review,
  or model/prompt reference. Language tags are compared case-insensitively; they are not inferred
  from text. Use `und` when the source language is unknown. Tags are checked for BCP-47 shape,
  without restricting source languages to the interface locales or Babel's locale list.
- `SourceText(original, translations=())` always retains the original variant, even without any
  English or Ukrainian text. A translation must be nonblank and carry provenance. Duplicate
  language tags, including a translation in the original's language, are rejected as ambiguous.
- `select_text(source_text, requested)` returns `SelectedText` with the selected `variant`,
  `is_original`, and `fallback`. The variant carries the displayed language and provenance.

Selection uses an exact, case-insensitive tag match: requested language, then `en`, then the
unchanged original. An original in the requested language participates before the English fallback.
No automatic translation or regional-tag inference occurs. Different regional variants need
explicit tags; `en-US` is not silently relabeled `en`.

| Requested | Original | Available translations | Selected |
| --- | --- | --- | --- |
| `uk` | `zh` | `uk`, `en` | `uk` translation |
| `uk` | `ru` | `en` | `en` translation, fallback |
| `uk` | `zh` | none | `zh` original, fallback |
| `en` | `ru` | `uk` | `ru` original, fallback |
| `uk` | `uk` | `en` | `uk` original |

Selection changes no fact, original text, tag, or provenance. A missing translation never makes
source text an unused interface key or a catalog coverage failure. The existing SATCOM archive and
raw cells remain lossless. Durable multilingual projections belong to `evidence-claim-contracts`
and `engine-skeleton`; dashboards and exports must apply the same selection policy when built.
The optional inference task may propose derived translations with provenance.

## Verification

`make catalog-check`, included in `make ci`, validates both required catalogs, any additional
catalogs, key parity, nonempty text, duplicate keys, CLDR categories, and placeholder parity.
It scans production `text` and `plural` calls for literal keys and matching message kinds, and
rejects missing or unused keys. The CLI boundary check catches literal help, descriptions, titles,
logging output, and direct error/print/write output. Keep translated calls explicit at these
boundaries; this AST check is not a general Python data-flow analyzer.

`tests/i18n/` contains bilingual CLI goldens, plural and number cases, locale precedence, nested
help and failure paths, planted catalog/literal failures, and multilingual source-text preservation
and fallback cases. See [record 0012](../records/0012-localization-message-catalog-core.md) for run
commands, packaging evidence, and the accepted core task contract.

## Bilingual acceptance

```bash
make test-bilingual
make bilingual-acceptance
```

`make test-bilingual` runs `tests/e2e/` and `tests/i18n/`, without a service or network, and writes
ASCII JSON evidence under a unique `$DATA_DIR/e2e/bilingual-<run-id>/` directory. `.env`, relative
paths, and paths containing spaces use the shared Make environment rules. The same tests also run
in `make ci`; ordinary CI runs keep their artifacts in pytest's temporary directory.

- `en/cli/` and `uk/cli/` contain actual subprocess exit codes, stdout, and stderr. The committed
  [CLI goldens](../../../tests/e2e/fixtures/cli.json) cover identity, every delivered help surface,
  contract checks, argument/input/configuration failures, and stable JSON diagnostics. Only the
  installed project version is normalized for golden comparison. Package validation and contract
  compilation also run against real fixture inputs; compiled artifact hashes are checked.
- `en/data-selection.json` and `uk/data-selection.json` contain original variants, all translations,
  and selected text with language, provenance, originality, and fallback metadata. The
  [source-text fixtures](../../../tests/e2e/fixtures/source-text.json) cover English, Ukrainian,
  Russian, Chinese, Arabic, unknown language, case-insensitive tags, and regional tags. Translation
  subsets and ordering, exact whitespace and combining characters, unrelated translations, and
  later translation without replacing the original have independent checks.
- `source-preservation.json` records a source-only multilingual archive/import/replay check.
  Real SATCOM source rows and attached messages retain their original text, language, and provenance.
  Archive bytes and raw CSV cells round-trip exactly; typed missing values retain the existing
  contract's null semantics. This check uses SQLite for the portable projection, not PostgreSQL
  service acceptance or a live crawler.
- `machine-parity.json` confirms identical machine output across interface locales.
  `manifest.json` records test exit status, selected and passing tests, available scope, untested
  paths, the Kestra waiver, and explicit release blockers with their owning plan tasks.

`make bilingual-acceptance` runs those checks and additionally fails if release blockers remain,
even when every available test passes. A planted passing-subset test verifies this behavior with
and without persistent artifacts. A passing `make test-bilingual` or `make ci` is therefore only
evidence for available paths. The acceptance command currently exits nonzero because dashboards,
filters, maps, review queue, source status, lineage, InvenTree plans/reports, export README,
date/unit/missing-value presentation, and browser screenshots still need their implementations.
No screenshot or Cyrillic font-rendering acceptance is claimed. There is no browser dependency
until a real browser surface can be tested; no other delivered English-only operator screen was
found. Ukrainian terminology review also remains open.

Interface key coverage stays strict in both locales. A Chinese or Russian source message displayed
through the data fallback policy is valid content, not an untranslated interface label. The
dashboard language must change controls and formatting independently of whether any data
translation exists. Future dashboard and export acceptance must exercise the same source fixtures
through their real projections and the shared selector, preserving the original for later
translation. See the open [acceptance record](../records/0013-localization-bilingual-acceptance-suite.md)
for evidence and remaining prerequisites.
