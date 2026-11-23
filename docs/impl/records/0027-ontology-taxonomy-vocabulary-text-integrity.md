# Vocabulary Text Integrity

## Work contract

```markdown
#### vocabulary-text-integrity

Every Ukrainian label of the reviewed seeds is a copy of the English proposal text, and every
concept definition is a JSON dump of proposal columns. The database and SKOS therefore present
untranslated text as Ukrainian and spreadsheet metadata as definitions.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: Findings ON-04 and ON-05 of the
  [ontology audit](records/0025-ontology-taxonomy-ontology-taxonomy-implementation-audit.md#findings),
  the [localization data rules](../design/spec.md#localization), and the shared
  [text selector](current/localization.md#source-data-and-translations).
- User-visible outcome: Seed labels carry the language of their text: proposal labels are `en`,
  and a `uk` label exists only as a reviewed translation. Interfaces and the SKOS export fall back
  from `uk` to `en` and report the fallback. A concept definition is a definition or absent; the
  proposal columns stay in provenance and the reconciliation.
- Scope boundary: The label rule of the semantic validator (a named term needs one preferred label,
  English for proposal content), the seed import, nullable definitions if the contract needs them,
  the SKOS mapping, and new content digests for the publication reviews with a recorded statement
  that the comparisons are unchanged. Writing translations is `review-ukrainian-terminology`.
- Data and artifact paths: `src/kn/semantic/`, `src/kn/contracts/resources/semantic/`,
  `src/kn/semantic/resources/`, `domains/<domain>/seeds/`, `generated/contracts/`,
  `tests/semantic/`.
- Execution path: Write failing tests first: no `uk` label equals its `en` label unless a review
  marks the text as identical in both languages, no definition parses as JSON, and the SKOS export
  of every scheme has no `@uk` copy. Then change the import, the validator and the export, and
  rerun `make seed-check`.
- Acceptance gates: The tests pass for all 16 schemes. The reviewed seeds and SKOS output contain
  only real `uk` labels. Every publication review keeps its comparison result under its new
  digest. `make ci` passes.
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).

```

## Implementation and decisions

- Removed 782 unreviewed Ukrainian copies: 756 preferred term labels, 24 namespace labels and two
  OECD alternatives. The reviewed proposals retain only their real English source labels. No
  translation was authored; `review-ukrainian-terminology` remains responsible for that work.
- Named terms and namespaces now need at least one preferred label in its source language, while
  packaged proposal content still requires its English original. All existing uniqueness,
  language-tag, inverse-label, hierarchy and mapping rules remain intact.
- Added nullable `review_reference` and `reviewed_identical` fields to all three label tables.
  Derived seed labels require review references. Identical English/Ukrainian preferred or
  alternative text additionally requires an explicit reviewed identity marker; markers on
  different text or without a review fail. Language is never inferred from spelling.
- Made `semantic.terms.definition` nullable in the development `1.0.0` contract and regenerated
  the normal contract artifacts. All 520 concept definitions are now absent because their
  proposals supply no prose definition. Existing class, relation, namespace and scheme prose
  remains. JSON definitions fail with `semantic.definition`; absent definitions emit no SKOS
  definition. Original columns, formulas, source language and locators remain in provenance and
  reconciliation. The archive fixture for the original product vocabulary stays unchanged;
  tests compare its structural and English content with the explicitly authorized cleanup.
- Added `kn.semantic.text.select_label` as an adapter to the existing immutable `SourceText` and
  `select_text` policy. It preserves exact text, language and source/review reference and returns
  explicit originality and fallback without manufacturing or mutating label rows.
- SKOS retains only real language-tagged labels. Named display-choice resources record selections
  for both `en` and `uk`, with actual language, text, provenance, originality and fallback. Human
  and JSON CLI results report `fallbacks_en` and `fallbacks_uk`, including described counterparts.
  Both choices are in each file, preserving identical Turtle bytes across interface locales.
- All 16 publication reviews have new label-content digests. Each typed `text_revision` records
  the prior digest, this record, the cleanup reason and `comparison_unchanged: true`. Every
  comparison, finding, scope, verification reason/state, origin and publication reference remains
  exactly unchanged, as checked against the pre-change fixture. All term IDs, English labels,
  codes, statuses, parents and mappings remain unchanged. Four schemes/subsets remain verified;
  twelve remain unverified. No publication was fetched or re-certified.
- A broader regression exposed an initial loophole: an alternative `uk` label could copy the
  English preferred label without an identity review. The regression failed first and now passes
  after comparing both preferred and alternative English labels for each term.
- Updated only the semantic contract digest in the CLI goldens. Interface catalogs
  still require both interface languages; the SKOS success message adds localized fallback counts.

## Acceptance evidence

Status: accepted. All declared gates passed.

1. Initial working tree: clean. `make plan-status`: 112 tasks, 99 agent, 13 human;
   CLEAR=90, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10. The task had no open `Requires`;
   its audit findings, specification and existing text selector were available locally.
2. `.venv/bin/python -m pytest tests/semantic/test_text_integrity.py`: five failures before
   implementation, proving copied language tags, JSON definitions, mandatory translations and
   missing explicit identity review. The later cross-preferred/alternative regression also failed
   before its fix. Missing translations, real reviewed translations, other source languages,
   Unicode, nullable definitions, JSON primitives and deep JSON now have regression coverage.
3. `make contract-compile format typecheck`: passed. Development contract digest:
   `5dfdbc18f4452ba7dca18fc5e11738d7b27a75593b38664e3b6c920aab83a760`.
   No dependency changed. `make complexity-gate catalog-check`: passed without weakening limits.
4. `make seed-check`: passed; all 1,173 proposal rows reconcile with unchanged outcomes and
   byte-identical reviewed content. Retained report:
   `$DATA_DIR/seed-import/22b3b726f8df46749f59cb56273d82b6/reconciliation.json`.
5. Intermediate semantic/subprocess suite: 271 passed; an intermediate full `make ci` after the
   final text-validator fix: 815 passed, 64 integration tests deselected, all other gates passed.
6. `make test-integration`: 64 passed, 815 deselected. The first sandboxed attempt failed to
   connect to loopback; the approved run with local-service access passed. The two updated
   semantic tests were then rerun through the configured database environment: two passed.
   PostgreSQL stores null definitions and review references, loads only English seed labels,
   and reproduces all reviewed content through repeated transactional rebuilds and idempotent
   loading. The shared database service was already running; none was started for this task.
7. Live acceptance from the project root, after shared environment loading:

   ```bash
   export KN_TEXT_EVIDENCE="$DATA_DIR/vocabulary-text-integrity/20261122T200612Z"
   .venv/bin/python "$KN_TEXT_EVIDENCE/verify.py"
   ```

   All 32 real CLI exports passed: 16 schemes, each in `en` and `uk`. RDFLib and strict Oxigraph
   parse every artifact. None contains a false `@uk` copy or a JSON definition. Every Ukrainian
   display choice reports selected language `en`, provenance and fallback; English has no
   fallback. Corresponding locale exports have identical hashes. A comparison with the Git
   baseline confirms all 825 term identities, 520 concepts, English labels, hierarchy and
   mappings are preserved, with exactly 782 copied `uk` rows removed. `summary.json` beside the
   script records each path, hash, triple count and fallback counts. `reviews-before.json`
   retains the prior publication reviews.
8. `make skos-reference-check`: all 16 fresh exports passed pinned Apache Jena RIOT without
   warnings. Summary: `$DATA_DIR/skos-reference/07d69a389b274385ad285ff42311eae6/summary.json`.
   The initial sandbox run could not resolve Java's local host name; the approved host run
   passed. No network publication fetch occurred.
9. `make lint-md lint-spec-plan`: passed, including documentation links and plan integrity.
10. Final command, after shared environment loading:
    `UV_CACHE_DIR="$DATA_DIR/cache/uv" UV_OFFLINE=1 make ci build`: passed. CI reports 815 tests
    passed and 64 integration tests deselected; the separate integration run passed all 64.
    All formatting, lint, typing, complexity, shell, catalogs, contract drift, documentation and
    plan/research checks passed. The source and wheel distributions built offline with the
    writable cache. Full output is in `ci-build.log` beside the live acceptance summary.
11. Wheel smoke check: extracted the built wheel under the evidence directory, selected that
    package through `PYTHONPATH`, and ran the actual Ukrainian CLI outside the repository.
    Its OECD export is verified, has 29 selected concepts, zero English fallbacks, 100 Ukrainian
    label fallbacks across selected and counterpart descriptions, and no false `@uk` literal.
    The parsed receipt and imported package path are retained in `wheel.json`.
12. `git diff --check`, an ASCII scan of all changed/added files, and final scope review passed.
    The two semantic integration tests also passed after their fixture/assertion helpers were
    extracted to keep the unchanged complexity limit. No required acceptance gate was skipped.

## Handoff

The accepted task removes one required agent task: 112 to 111 total, 99 to 98 agent, 13 human
unchanged; CLEAR=90 to 89, RUN NEEDED=9, BLOCKED BY HUMAN=3, HUMAN-GATED=10 unchanged.
`review-ukrainian-terminology` no longer requires this task and links the available review fields.
Ontology-taxonomy remains planned because `decide-vocabulary-uri-namespace` still requires the
owner's decision. That URI decision and the optional publication drift check remain open; neither
is part of this text cleanup. No new task was needed.

Existing development databases must use the documented explicit rebuild/backfill to adopt the
changed baseline; no automatic destructive update was run. This task has no unresolved acceptance
gate. Coverage and the full release bilingual gate were not required or run for this task.

## Requested development database rebuild

Completed on 2026-11-23 at 06:55 UTC after the owner explicitly requested the rebuild.
The earlier implementation handoff above describes the state before this operational follow-up.

- Started the existing local PostgreSQL service, which had stopped; its existing data volume and
  password file were retained. No database reset was used.
- Saved a private PostgreSQL custom-format recovery dump and verified its archive listing before
  changing any schema. Before/after counts, scripts, logs, dump and verification summary are under
  `$DATA_DIR/db-rebuild/20261122T202930Z/`. The initial filename collision and later approval-service
  interruption occurred before any database mutation; resuming completed the backup successfully.
- Ran `KN_ENVIRONMENT=development make db-rebuild`, `make satcom-import`, and `make db-verify`;
  all passed. The development setting was scoped to the rebuild command, without editing `.env`.
- The live database now has semantic contract digest
  `5dfdbc18f4452ba7dca18fc5e11738d7b27a75593b38664e3b6c920aab83a760`. All 18 semantic tables
  exactly match the reviewed snapshot: 825 terms, 520 concepts, 69 mappings, zero copied `uk`
  preferred labels, and all 520 concept definitions absent.
- Re-imported the same SATCOM snapshot. All 31 space-table counts match the pre-rebuild state,
  and all 12,755 archived raw rows match the durable source cells exactly. External schema names
  are unchanged. PostgreSQL remains running and healthy.
- This follow-up changed runtime state and this acceptance record only. The implementation's
  prior CI result remains unchanged; documentation and diff checks were repeated.
