# Reviewed Vocabulary Seeds

`make seed-import` stages deterministic vocabulary snapshots, fixtures, and a reconciliation of all
five converted workbooks under `$DATA_DIR/seed-import/<run-id>/`. It never overwrites reviewed
content. `make seed-check` repeats that conversion and compares it byte for byte with the reviewed
files and fixture. Both targets resolve `.env` and `DATA_DIR` through the normal shell helper.

```bash
make seed-import
make seed-check
KN_ENVIRONMENT=development make db-rebuild
make satcom-import
```

The equivalent CLI is `kn vocabulary import-proposals [--check] [--data-dir PATH]`, run from inside
the repository. It supports the existing `--locale en|uk` and `--json` options. Its structured result
contains `status`, `rows`, `counts`, and `report`. Errors use `E_INPUT` or `E_CONTRACT`, as on the
other commands. Direct CLI callers supply `DATA_DIR` or `--data-dir`; Make also loads `.env`.
Each run writes `space.json`, `gdelt.json`, `microelectronics.json`, `fixtures.json`, and
`reconciliation.json`. Only the run-directory name changes across identical runs.

## Review boundary and provenance

The reviewed files are `domains/<domain>/seeds/semantic.json`. These are links to the packaged
`src/kn/semantic/resources/<domain>.json` files, so source installations and wheels load the same
bytes. Each envelope contains a format version, domain, contracted `snapshot`, and `provenance`
keyed by term ID. Every term has source JSON filename and SHA-256, original workbook filename and
SHA-256, sheet, original spreadsheet row, and origin. These checksums identify the supplied
proposal conversion, not an independently verified official publication.
Provenance also retains `source_language`, original `values`, and `formulas_not_evaluated`;
proposal columns are never used as definitions. See [text integrity](text.md).

`kn.semantic.proposals` checks the manifest's sheet set, digests, row counts, source identity, and
unique row locators. `seed_ontology` and `seed_vocabulary` contain the explicit import decisions;
`seed_model` builds the snapshots. `kn.semantic.seeds.reconcile()` validates the complete combined
model before writing any artifact. Unrecognized sheets remain `needs_mapping`; missing native
codes fail rather than being fabricated. Codes derived from uncoded labels are stable textual
codes, never row numbers.

Each reconciliation also lists, per domain under `changes`, the term IDs that were `added`,
`changed`, or `removed` relative to the packaged reviewed seeds that rebuilds load, and the CLI's
JSON result repeats them. A removed proposal row therefore never drops a term ID unnoticed;
retire a concept in use as `deprecated` or `replaced` instead of deleting it. `stale_reviews` names
each scheme whose content changed after its publication review, with the reviewed and the new
content digest. Staging continues with that scheme `unverified` and a reason that asks for a new
comparison; it never keeps the old verification. The packaged loader and `make seed-check` still
refuse the change until the review records the new comparison and digest. `lifecycle` holds the
[lifecycle report](../ontology-taxonomy.md#lifecycle-report) of the combined content.

Review staged files against `domains/<domain>/seeds/semantic.json` before promoting a change to
`src/kn/semantic/resources/`. Promote the staged `fixtures.json` to
`tests/semantic/fixtures/proposal_examples.json` at the same time. Reconciliation lists every input
row, its original values and unevaluated formulas, its resulting term IDs, and a reason for its
`accepted`, `duplicate`, `needs_mapping`, or `rejected` status. Inspect it alongside the seed diff.
A proposal edit does not change the next rebuild until its reviewed files are updated.

## Available content and decisions

| Domain | Entity classes | Relation types | Schemes | Concepts | Total terms |
| --- | --- | --- | --- | --- | --- |
| Space | 33 | 32 | 5 | 231 | 301 |
| GDELT | 28 | 42 | 5 | 110 | 185 |
| Microelectronics | 27 | 58 | 6 | 179 | 339 |

The reconciliation covers 1,173 rows: 612 accepted, one duplicate, 477 needing mapping, and 83
rejected. Rejected rows comprise 56 explanatory note rows and 27 example/template rows. The latter
are retained in the fixture, including the energy template's unevaluated formulas. No entity, claim,
observation, or entity tag is created from an example.

- Service codes use separate `space.services`, `gdelt.services`, and `microelectronics.services`
  namespaces. Application tags also remain domain-qualified. CAMEO codes retain leading zeroes.
- The ESA GPT proposal is a `kb_normalized` tree with four structural segment parents. Nodes retain
  their original codes and their proposal origin in provenance. Preferred labels include their
  segment to distinguish repeated names. Official-looking rows do not turn this mixed tree into
  an official scheme.
- The OECD-derived product tree and mixed microelectronics application vocabulary are also
  `kb_normalized`; local engineering extensions never become official. The two `Others` labels in
  the product tree include their codes. ESA technology domains become parents, and rows without a
  subdomain create no artificial `None` leaf.
- The [separate OECD Figure 9 scheme](oecd.md) adds 29 verified categories and 69 reviewed product
  mappings, while all existing product references and the mixed tree stay unchanged. Seven
  non-chip categories have explicit unmapped reasons. Mapping evidence resolves to the packaged
  publication-review artifact through an explicit caller registry.
- Relations have explicit endpoint pairs. A named combined class is resolved before splitting a
  slash-separated union. `member_of_constellation` becomes `contains_spacecraft` in the reverse
  direction; `variant_of` shares `has_mpn` and accounts for the duplicate row. `operates` has the
  inverse label `operated_by`. Other inverses use explicit names or `inverse of <relation>`.
  Cardinalities are normalized; an unspecified cardinality stays unconstrained `many_to_many`.
  Native extracted relations require `extracted` evidence; other relations require `primary`.
  Original evidence instructions and error guards remain in the seed or reconciliation.
- Space adds 12 explicit `kb_extension` classes, including model/configuration, evidence claim,
  financial/deployment observation, opportunity and compatibility concepts needed by the pilot,
  plus generic asset/system/network/material/software endpoints. Their definitions are local
  import decisions, anchored to the proposal ontology; no pilot data rows become seed entities.

All 16 schemes have [publication or local-vocabulary reviews](verification.md): four schemes or
scoped subsets are `verified` and twelve schemes are `unverified` with reasons. All terms remain `draft`.
Only English source labels are stored. Ukrainian terminology review remains pending; missing
translations use the shared selector and are reported as fallback, without manufacturing `uk`
rows. The [text reference](text.md) describes nullable definitions and translation review fields.

## Unmapped rows and ownership

The 477 pending rows remain available in the reconciliation and the original proposals:

- 188 source, coverage, watchlist and ingestion rows belong to `source-catalogue-import` and later
  source onboarding. No source is enabled by this import.
- 195 attribute dictionary rows need the class, type, unit and condition decisions owned by
  `vendor-information-coverage` and `supply-model-contracts`.
- 31 observation-schema, comparison-profile and rubric rows need typed conditions and attributes
  in `microelectronics-domain-contracts`; prose is not an executable comparison policy.
- 61 GDELT actor/geography, GCAM, field and ingestion-order rows need dictionary or domain-contract
  mapping in `gdelt-source-dictionaries` and `gdelt-domain-contracts`.
- Two space relations need mapping: regulatory `Activity` is not a defined entity class, and an
  EUSPA segment is a concept rather than a class. `space-domain-contracts` owns that distinction.

## Rebuild and verification

The explicit registry in `kn.db.seeds` calls `kn.semantic.seed_loader` as `kn_semantic_loader`,
within the rebuild transaction. It validates the envelopes, term provenance and full snapshot before
DML. Bulk inserts are idempotent; conflicting stored content refuses and rolls back the seed
savepoint rather than being overwritten. Semantic foreign-key checks are completed and returned to
deferred mode before returning, so a second rebuild in the same transaction can drop the seeded
tables. The loader does not read proposals, instantiate fixtures, fetch publications, or commit.

- `make seed-check`: deterministic conversion, checked-in seed/fixture comparison, row reconciliation.
- `make ci`: semantic integrity and conversion failures, all-row accounting, identifier stability
  under reordered proposals, inverse direction, fixture isolation, both CLI locales and error paths.
- `make test-integration`: exact content after two rebuilds, idempotent seed loading, stored-content
  conflict rollback, existing registry, privilege and rebuild failure paths.
- `make build`: packages the seed snapshots, verification and publication-review resources.

[Task record 0021](../../records/0021-ontology-taxonomy-seed-vocabulary-import.md) records acceptance
evidence. [Publication verification](verification.md) and [SKOS export](skos.md) are available;
executable pending policies remain open.
