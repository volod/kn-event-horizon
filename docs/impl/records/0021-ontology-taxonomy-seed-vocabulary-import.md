# Seed Vocabulary Import

## Work contract

```markdown
#### seed-vocabulary-import

The converted workbook proposals must become reviewed seed data with a row-by-row reconciliation.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: The [semantic meta-model](current/ontology-taxonomy.md), the
  [reviewed seed hook](current/data-contracts/rebuild.md#reviewed-seed-hook) and
  the proposal JSON under `domains/<domain>/seeds/proposals/`, documented in
  [domains/README.md](../../domains/README.md).
- User-visible outcome: Every rebuild loads reviewed space, GDELT, and microelectronics ontology and
  taxonomy seeds with deterministic identifiers. A reconciliation report classifies every proposal
  row.
- Scope boundary: Namespacing (including the `S*` and `APP.*` collisions), relation-direction
  normalization with inverse labels, and structural parents for the ESA GPT nodes. The pilot's
  missing space classes are added as `kb_extension`. Examples and templates become fixtures. All
  schemes stay unverified. The source catalogue comes in `source-catalogue-import`.
- Data and artifact paths: `domains/<domain>/seeds/`, `src/kn/semantic/seeds.py`,
  `$DATA_DIR/seed-import/<run-id>/` for the reconciliation report, `tests/semantic/`.
- Execution path: Write a deterministic import from the proposals into reviewed seed files, and
  have a maintainer review the diff of those files. The rebuild hook then loads the reviewed files.
- Acceptance gates: Every proposal row is `accepted`, `duplicate`, `needs_mapping`, or `rejected`
  with a reason. Identifiers are identical across two runs. No example row becomes an entity. Every
  file records its provenance (file, SHA-256, sheet, row).
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The task began with a clean worktree and available dependencies. Initial plan counts were 113
(total), 101 (agent), and 12 (human).

The importer stages reviewed snapshots and an all-row reconciliation; it never promotes proposals
at rebuild time. Reviewed domain paths link to packaged resources so a wheel and a source checkout
use identical bytes. The explicit rebuild hook runs validated bulk DML as the semantic loader role.
It refuses stored-content drift within a savepoint. No dependency or contract change was needed.

The [current seed reference](../current/ontology-taxonomy/seeds.md) documents the review process,
identifiers, normalization, local classes, origins and remaining mappings. Content review checked
all row classifications, the generated IDs and hierarchy, domain collisions, inverse directions,
fixture boundaries, origin assignments, provenance and packaged byte identity. The import produces
726 terms: 88 classes, 132 relation types, 15 schemes and 491 concepts. The 12 additional space
classes are explicit local import decisions, not claims that those rows existed in the workbook.

All terms are draft and every scheme remains unverified. Mixed ESA GPT, OECD-derived product and
application trees are normalized schemes, preserving row-level origins without representing local
extensions as official. Ukrainian locale slots explicitly retain source spelling pending the
separate terminology review. Source catalogue imports, publication verification, SKOS export and
executable policies are outside this task.

Implementation runs exposed and fixed these issues:

- ESA technology rows without subdomain codes initially failed conversion. They now contribute
  only their domain concept; regression coverage excludes artificial null-code leaves.
- Template formulas needed to survive fixture extraction. Their source text and cached values
  are preserved without evaluation.
- Unknown sheets must remain pending, and missing native codes must fail. The importer now uses
  explicit class sheets and strict text fields rather than treating any first sheet as ontology.
- The first database suite passed 61 tests but failed three repeat-rebuild cases with PostgreSQL
  pending deferred trigger events. The loader now checks only semantic foreign keys and restores
  their deferred mode. The repository's typed `SetConstraints` SQLAlchemy construct quotes every
  identifier; tests also cover hostile names. The full repeat-rebuild suite then passed.
- Row-by-row DML was replaced with homogeneous bulk inserts and per-dataset conflict checks.
  Seed failures roll back their savepoint; the enclosing rebuild still restores all KN schemas.
- English and Ukrainian root help changed for the new command. Golden updates are limited to the
  command list, wrapped usage and added help entry; other expectations remain unchanged.

## Acceptance evidence

Status: accepted. All task acceptance gates pass.

| Gate | Evidence |
| --- | --- |
| Every proposal row classified with a reason | All five workbooks yield 1,173 rows: 612 accepted, one duplicate, 477 needing mapping and 83 rejected. README notes account for 56 rejections; the other 27 are example/template fixtures. |
| Deterministic identifiers and files | Two checked import runs have byte-identical seed, fixture and reconciliation files; IDs also match with proposal input order reversed. |
| Examples do not become entities | All 27 example/template rows are fixture-only. The reviewed snapshot has no entity tags; the database checks the tag table remains empty. |
| Durable provenance | Every term and fixture has source JSON filename and digest, workbook filename and digest, sheet and original row. Missing or malformed provenance refuses. |
| Invalid semantics refuse | Regression fixtures cover cycles, missing parents, duplicate labels, ID collisions, relation endpoints, changed proposal manifests and invalid reviewed envelopes. |
| Rebuild hook | Two rebuilds have identical stored content. Idempotent loading, conflict rollback and the existing role, registry, interruption and failure-path suites pass. |
| Packaging | The sdist and wheel build. All three wheel resources are byte-identical to the reviewed domain paths; an isolated process loads 726 terms outside the checkout. |

Commands and results:

- `make seed-import` and `make seed-check`: pass. These write reports under
  `$DATA_DIR/seed-import/<run-id>/` and compare reviewed seeds and the committed example fixture.
- `KN_ENVIRONMENT=development make db-rebuild`: pass on the running local service. The service
  initially had contract digest drift, so an ordinary `make db-up` upgrade refused as designed.
- `make satcom-import db-verify`: pass after the development rebuild. SATCOM import
  `7ec6001f0d41b91f287003ba00c893c08a96ba69ad0979d7fb1707ded6b0c7dd` is restored from the supplied
  package and archived under `$DATA_DIR/satcom-import/`.
- `make test-integration`: 64 passed after the trigger fix, including the new exact-content,
  repeat-rebuild, idempotency and stored-conflict regression.
- `make ci-local`: pass on the final implementation: 630 unit tests and 64 local integration
  tests. This includes the required `make ci` checks; no required gate was skipped.
- `make lint-md`: pass. Documentation links and spec-plan integrity have zero findings.
- After `source scripts/shared/common.sh && kn_load_env`,
  `UV_CACHE_DIR="$DATA_DIR/cache/uv" make build`: pass. The inherited home cache was read-only;
  using DATA_DIR and permitting access to the declared build backend resolved the environmental
  build failure without changing dependencies or checks.

Additional evidence is preserved under
`$DATA_DIR/seed-import/verification-24debc25837d4b60a1410826f8c340cb/`:

- `verification.json` records both checked import report paths, identical SHA-256 digests of every
  emitted file, wheel digest and isolated wheel-load counts.
- `verify.py` reproduces that file and wheel comparison from the project root with the loaded
  environment and the project's Python interpreter.
- `database.json` and `verify_database.py` preserve a read-only exact comparison of every seeded
  dataset after SATCOM restoration: 726 terms, 15 unverified schemes, zero entity tags, and the
  expected pilot import ID. The sorted term-ID SHA-256 is
  `acb4bdd67c2224a5a2631f10df1ffdf3ec63f5e502f1a10573789274d0604fdb`.

Final `git diff --check`, ASCII checks, documentation links and plan integrity pass. The broader
optional coverage gate (`make quality`) was not run; Markdown lint and package build were run
separately. The existing database service remains running, and temporary helper scripts were
removed after preserving their evidence under DATA_DIR.

## Handoff

The plan removes this task and its prerequisite references: 113 to 112 total tasks, 101 to 100
agent tasks, 12 human tasks unchanged, and CLEAR tasks 93 to 92. The ontology-taxonomy capability
remains planned because publication verification and SKOS export are still open.

The 477 pending rows are preserved with reasons, not silently discarded. Their existing owner
tasks now name the remaining mapping work: `vendor-information-coverage`, `supply-model-contracts`,
`microelectronics-domain-contracts`, `gdelt-domain-contracts`, `gdelt-source-dictionaries`,
`source-catalogue-import` and `space-domain-contracts`. The source and dictionary tasks retain
all collection authorization gates. No source was enabled or fetched by this import.
