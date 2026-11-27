# Localization

English CLI presentation, message catalog validation, and language-tagged text are available.
Bilingual dashboards and maps remain in the [forward plan](../plan.md). See the
[localization specification](../../design/spec.md#localization) for the interface and data rules.

## Command-line interface

```bash
kn info
kn space satcom --help
kn --json info
make catalog-check
```

Help, statuses, confirmations, and diagnostics use English. The global `--json` option is
accepted before or after a subcommand. The former `--locale` option now returns `E_ARGUMENTS`
and exit status 2. The CLI ignores the former `KN_LOCALE` environment variable.

Human argument errors show usage on stdout and a diagnostic on stderr. Help goes to stdout
and command results use the `kn.operator` logger on stderr. JSON errors use stable codes,
for example `{"error": {"code": "E_INPUT"}}`. Domain error summaries omit arbitrary exception
strings and connection credentials.

## Catalogs and formatting

`locales/` exposes `src/kn/i18n/locales/` through a repository symlink. The
[English](../../../locales/en/messages.json) and [Ukrainian](../../../locales/uk/messages.json)
catalogs are packaged into both source and wheel distributions. Resource loading uses
`importlib.resources`. The English catalog contains the `cli.*` messages. Dashboard and map
messages will have matching keys in both catalogs. The Ukrainian catalog is currently empty.

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
A missing dashboard or map translation fails catalog validation. Date and unit presentation
remain in the dashboard plan tasks.

## Source data and translations

`kn.i18n.data` provides immutable language-tagged text values:

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
raw cells remain lossless. The evidence model stores
[text translations](evidence-model.md#multilingual-text) beside the original text claim and
applies this selector. The [fixture engine](ingestion-engine.md#run-and-replay-a-snapshot)
ingests Russian, Chinese, and unknown-language originals. Dashboards and exports use the same
selection policy for fact text.
The optional inference task may propose derived translations with provenance.

[Vocabulary text integrity](ontology-taxonomy/text.md) applies this selector to reviewed semantic
labels and SKOS display choices. Proposal labels retain `en`; missing Ukrainian vocabulary text
selects English with its real tag, source/review provenance and explicit fallback. Export results
report fallback counts for both supported display locales. Genuine reviewed translations can be
selected without changing the original label or weakening interface-catalog coverage.

## Verification

`make catalog-check`, included in `make ci`, validates both catalogs, CLDR categories,
placeholders, and key usage. Missing dashboard or map keys fail in either language, and
`cli.*` keys belong to English. The command also checks that CLI presentation uses catalog keys.

The CLI goldens normalize continuation line breaks in argparse usage synopses for both successful
help and argument errors. The assertions retain the help body, diagnostic text, and exit status.
See the [CLI scope change record](../records/0050-adhoc-cli-localization-scope.md) for the regression
and verification.

## Bilingual acceptance

```bash
make test-bilingual
make bilingual-acceptance
```

Both targets write ASCII JSON evidence under a unique `$DATA_DIR/e2e/bilingual-<run-id>/`
directory. The tests also run in `make ci`, where pytest stores artifacts in its temporary directory.

- `cli/` contains English help, errors and command outputs. The
  [CLI goldens](../../../tests/e2e/fixtures/cli.json) retain the subprocess exit codes, stdout,
  and stderr. Package validation and contract compilation use real fixture inputs.
- `en/data-selection.json` and `uk/data-selection.json` record the original, available
  translations, and selected text with its language, provenance, originality, and fallback.
- `source-preservation.json` records the lossless SATCOM source archive and SQLite projection.
- `manifest.json` records the selected and passing tests and the open release gates.

`make bilingual-acceptance` also requires browser evidence for dashboards, filters and maps in
both languages, including dates, units, and missing-value labels. These gates remain open.
The [acceptance record](../records/0013-localization-bilingual-acceptance-suite.md) tracks the
remaining work.
