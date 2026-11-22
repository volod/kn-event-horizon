# OECD Official Product Scheme

## Work contract

```markdown
#### oecd-official-product-scheme

The mixed product vocabulary cannot be presented as an official OECD taxonomy. A separately
verified Figure 9 scheme and explicit crosswalks must preserve existing product references.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Research: yes
- Dependencies: The user-supplied OECD PDF with SHA-256
  `25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083`, and the
  [closed research findings](future-research.md#verify-official-taxonomies----full-official-status-for-mixed-seeds).
- User-visible outcome: A distinct official OECD Figure 9 scheme is verified, and existing product
  concepts retain their IDs and link through reviewed, evidence-backed mappings.
- Scope boundary: Figure 9 categories, source labels and primary parents only. Keep the existing
  mixed scheme normalized; do not promote extensions or invent equivalence for non-chip assets.
  Publication review references are explicit seed evidence, not fabricated claim records.
- Data and artifact paths: `src/kn/semantic/`, `domains/microelectronics/seeds/`,
  `tests/semantic/`, `$DATA_DIR/taxonomy-verification/<run-id>/`, and the task record.
- Execution path: Transcribe and compare Figure 9, add failing fixtures, create the separate scheme,
  author explicit mapping decisions and provenance, then run seed reconciliation and rebuild tests.
- Acceptance gates: All 29 source categories and parent edges match the PDF. Source labels survive
  local disambiguation. Existing product IDs, labels and parents are unchanged. Exact matches,
  broader matches and unmapped non-chip cases have explicit decisions. Unresolved references or
  changed evidence fail closed. `make seed-check`, `make ci` and database integration pass.
  A source mismatch stays unverified and is recorded rather than silently corrected.
- Documentation target: `current/ontology-taxonomy.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

Added `microelectronics.oecd_2024.scheme` with exactly 29 Figure 9 categories, four roots and
25 primary parent links. All source labels and connectors were compared with the supplied PDF
on page 30; page 31 supplies the packaging boundary. The original PDF SHA-256 remains
`25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083`.

The existing mixed `product_v1` scheme and all its 76 concept rows, IDs, codes, labels, definitions
and parents are preserved. It retains normalized origin and unverified official status. The new
scheme is official and verified within the Figure 9 scope. Its KN codes are internal identifiers,
not OECD notations. The two original Others labels are retained as alternatives, with locally
qualified preferred display labels for uniqueness. Both locale slots retain source text pending
Ukrainian terminology review. All terms remain draft.

`domains/microelectronics/seeds/oecd_2024.json` links to the packaged transcription and 76 authored
mapping decisions. The decisions create 69 `concept_mappings`: 29 exact matches, 23 broader
matches and 17 analyst crosswalks. Seven non-chip cases have explicit unmapped reasons and create
no mapping rows. Composite SoC, module, accelerator and other ambiguous groupings use analyst
associations instead of unsupported equivalence. No runtime name matching or ancestor inference
creates a classification, and no local extension enters the official tree.

Mapping IDs use `microelectronics.oecd_2024_crosswalk.<existing-code>`. Every mapping cites the
content-addressed `urn:sha256:<digest>` of the actual packaged review artifact, which includes the
publication URI/checksum, locator, category transcription and mapping reasons. The seed publication
resolver explicitly registers that artifact for `ExternalReferences`; validation does not derive
trusted evidence IDs from mapping rows. No fake entity, claim or evidence-engine rows are created.
New term provenance preserves proposal row locators and adds checked publication/review bindings.
The paper's checksum identifies its bytes; the review checksum identifies the classification
choices, so editing a reason invalidates old mapping evidence until reviewed promotion.

`oecd_reference` owns strict resource validation and evidence resolution; `seed_oecd` owns
projection and exact review reconciliation. Existing generic provenance validation moved into
`seed_provenance` to keep cohesive modules below the size guideline. The builder uses the existing
unlabeled-kind rule for mapping terms, avoiding artificial bilingual mapping names. No contract
migration, dependency, new CLI or network fetcher was added. The normal seed CLI and rebuild hook
consume the new content. General semantic validation still requires explicit known references.

An additional regression exposed that arbitrary publication-provenance fields were previously
accepted despite the mapping's registered evidence. The loader now checks those fields against
the actual reference resource. This closes the gap before DML rather than treating citation text
as independently trustworthy. The five planted citation changes fail as intended.

## Acceptance evidence

Accepted on 2026-11-22. All acceptance gates passed; no unresolved work remains in this task.

| Check | Evidence and result |
| --- | --- |
| Regression first | `tests/semantic/test_oecd.py` initially failed because no official scheme or mappings existed. Five additional provenance cases failed before the citation-binding fix. |
| Publication identity | Recomputed SHA-256 of `.data/f68de895-en.pdf`; it matches the review metadata. The Figure 9 fixture contains 29 categories and 25 edges, with all four source roots and verbatim duplicate source labels. |
| Semantic suite | All 168 semantic tests pass, including independent source transcription, full product-row preservation, mapping types and directions, seven unmapped cases, malformed review data, stale evidence, altered citation bindings and source disagreements. |
| Preservation | Compared the pre-task microelectronics snapshot with the final snapshot: every previous row is still present unchanged. The independent product baseline pins all original concept, term and label rows. |
| Normal entry point | `make seed-check` passed: 1,173 rows with unchanged reconciliation counts (612 accepted, one duplicate, 477 needs_mapping, 83 rejected). Generated official concepts and mappings are reported under their originating proposal rows. |
| Required gate | Final `make ci` passed all checks: 692 tests passed, 64 local tests deselected. Formatting, lint, typing, complexity, shell lint, catalogs, contract drift, documentation links and plan/research integrity all pass. Log: `ci-final.log`. |
| Database runs | Initial and final `make test-integration` runs passed all 64 tests, including 825 terms, 69 mappings, four verified schemes, exact round trips, idempotent loading, two rebuilds and conflict rollback. Final log: `integration-final.log`; 692 unit tests deselected. |
| Coverage | `make coverage` passed: 692 tests, 64 local tests deselected, 93.52% total coverage against the unchanged 90% floor. The three new modules have complete statement and branch coverage. Logs and JSON coverage evidence are archived. |
| Packaging | `UV_CACHE_DIR="$DATA_DIR/cache/uv" UV_OFFLINE=1 make build` passed. The extracted wheel validates outside the repository using only packaged resources: 825 terms, 69 mappings and explicit publication references. |
| Documentation | `make lint-md` and plan/research integrity checks pass. Current-state pages describe source scope, local display labels, mapping meanings, evidence resolution and remaining limitations. |
| Runtime artifacts | `$DATA_DIR/taxonomy-verification/oecd-scheme-2026-11-22/` preserves the pre-task snapshot, publication/mapping review summary, authoring helper, test logs, source/wheel distributions and extracted-wheel verification material. |

No source is enabled or imported as a live feed, no hypothetical example becomes an entity, and
no claim/evidence engine is implied by the seed publication resolver. Database tests run against
the configured local service with transactional fixtures; no service was started, stopped or reset.

## Handoff

Initial counts were 111 total, 99 agent and 12 human (CLEAR=91). Adding this task temporarily made
112 total, 100 agent (CLEAR=92); acceptance returns to 111 total, 99 agent and 12 human. Other
status counts are unchanged. The task and its temporary audit prerequisite were removed from
the forward plan.
The next agent candidate remains `skos-export`.

The affected capability remains `ontology-taxonomy`, still planned because SKOS export is open.
Available content grows from 726 to 825 terms, 491 to 520 concepts, 15 to 16 schemes, and zero to
69 reviewed mappings. Verification states grow from three verified/twelve unverified to four
verified/twelve unverified. The original closed-research decision remains negative for mixed
schemes; its OECD branch now links the shipped separate official scheme and this record.

Final `git diff --check` and `git status --short` were inspected. Changes preserve the existing
uncommitted verification work; no unrelated edits were reverted. All changed source, test and
documentation files are ASCII. Temporary authoring scripts were archived and removed from `/tmp`.

See the [current OECD scheme guide](../current/ontology-taxonomy/oecd.md) for the explicit evidence
API and future-writer boundary. Ukrainian terminology and SKOS export remain with their existing
plan tasks. No commits or pushes were made.
