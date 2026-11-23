# Vocabulary Text Integrity

Reviewed vocabulary text retains its actual language. The current proposals supply English:
all 756 named-term preferred labels, 24 namespace labels and two alternatives are stored as `en`.
There are no reviewed Ukrainian vocabulary translations yet. The earlier 782 copied `uk` rows
are removed; missing translation uses the [shared text selector](../localization.md#source-data-and-translations).
The 825 term IDs, all English labels, concept codes, hierarchy and mappings are unchanged.

## Definitions and provenance

`semantic.terms.definition` is nullable in the editable development contract `1.0.0`. An absent
definition is null or omitted, and the SKOS exporter emits no `skos:definition` for it. All 520
concept definitions are absent because their proposals supply category labels and metadata,
not definitions. Genuine class, relation and scheme prose remains intact. Namespace definitions
remain required. Supplied definitions that parse as JSON fail with `semantic.definition`, including
localized definitions; blank strings already fail semantic row validation.

Each term's seed provenance retains the original proposal `values`, `formulas_not_evaluated`,
`source_language: en`, source file and checksum, workbook identity, sheet and row. These columns
also remain in the reconciliation and original proposals. They are never dumped into a definition.
The reviewed files and packaged resources are the same linked files, as described under
[seed provenance](seeds.md#review-boundary-and-provenance).

The storage contract also adds nullable `review_reference` and `reviewed_identical` fields to
`labels`, `namespace_labels` and `alternative_labels`. The normal compiler regenerates their
schemas, models and DDL. Existing development databases need the normal explicit
[rebuild and backfill](../data-contracts/rebuild.md); upgrades refuse installed-contract drift.
No release migration or automatic rewrite of stored labels is introduced.

## Label and review rules

A named term or namespace requires at least one preferred label in its source language; ingestion
does not require translations. Preferred-label uniqueness, one row per case-insensitive language
tag, alternative-label constraints and inverse relation labels remain enforced. The validator
does not guess a language from spelling or script.

Packaged proposal-derived seeds require their English preferred labels. Every derived non-English
label requires a nonempty `review_reference`, naming its durable terminology review. English and
Ukrainian text may be identical only when the Ukrainian row also has `reviewed_identical: true`.
This rule compares English preferred and alternative labels for the same term, or English labels
for the same namespace. A true identity marker with different text or no review is rejected with
`semantic.translation`. A review reference records a human decision; it does not perform or infer
the translation. `review-ukrainian-terminology` owns writing and approving those translations.

`kn.semantic.text.select_label(snapshot, term_id, requested)` returns the shared `SelectedText`
value: exact selected text, actual language, source/review provenance, originality and fallback.
It uses `kn.i18n.data.select_text`: requested language, then English, then the original. Current
proposal content has an English original. Other snapshots can carry originals in other languages;
an unreviewed source row takes precedence over derived review rows when identifying the original.
The helper never creates or mutates a label. Source provenance is a stable
`semantic.labels:<term-id>:<language>` row reference; reviewed text retains `review_reference`.

## SKOS and interfaces

The [SKOS export](skos.md) preserves every real preferred and alternative label with its original
language tag. It emits no synthetic `@uk` literal for missing Ukrainian text. For each described
named term or scheme it also emits two named `kn:LabelSelection` resources, one for `en` and one
for `uk`. These carry the requested and selected languages, exact selected text with its actual
tag, provenance, originality and fallback. Thus a Ukrainian display choice selects `"..."@en`
with `fallback true` when the translation is absent.

The command reports `fallbacks_en` and `fallbacks_uk` in JSON and in both human interface locales.
Counts cover all described labels, including mapped counterpart concepts and schemes. Both choices
are always in the file, so changing interface locale preserves identical Turtle bytes and keeps
source data independent of the interface language.

## Publication comparisons and verification

All 16 publication reviews have new content digests because copied labels were removed. Each
review's `text_revision` records its previous digest, the [task record](../../records/0027-ontology-taxonomy-vocabulary-text-integrity.md),
the cleanup reason and `comparison_unchanged: true`. English comparison text, category coverage,
findings, origin, publication edition/URI/checksum and verification result remain unchanged:
four schemes or subsets verified, twelve unverified. No new publication verification is claimed.
Later label edits still invalidate the content digest and require review before loading.

- `make seed-check`: byte-identical staging of all 1,173 proposal rows and reviewed seed files.
- `tests/semantic/test_text*.py`: all 16 schemes, absence of false `uk` copies and JSON definitions,
  retained original columns, reviewed identical labels, missing translations, other source
  languages, shared selection, unchanged publication comparisons and new review digests.
- `make ci`: those regressions, both interface locales, contract generation and strict independent
  RDF parsing with Oxigraph, plus the normal quality gates.
- `make test-integration`: nullable definitions, review-reference columns, exact reviewed seeds,
  repeated rebuilds, idempotency and conflict rollback in PostgreSQL.
- `make skos-reference-check`: Apache Jena RIOT validates every fresh export without warnings.

Acceptance commands and retained evidence are in
[record 0027](../../records/0027-ontology-taxonomy-vocabulary-text-integrity.md).
