# Official Taxonomy Verification

## Work contract

```markdown
#### verify-official-taxonomies

Concepts that name an official standard cannot be shown as official until checked against the
publication.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Research: yes
- Dependencies: Public access to the ESA GPT, ESA Technology Tree v4.1 (STM-277), NASA 2024
  Technology Taxonomy, EUSPA EU Space Market Report 2026, ECS SRIA 2026, OECD "Chips, nodes and
  wafers", and GDELT lookup publications.
- User-visible outcome: Each scheme records a verified edition, URI, and checksum, or stays
  `unverified` with a stated reason, and interfaces label it accordingly.
- Scope boundary: Documentation reading and comparison only. No full-dictionary import for GDELT,
  which is source work in `gdelt-source-dictionaries`.
- Data and artifact paths: `domains/<domain>/seeds/verification.json`, `tests/semantic/`, and the
  task record.
- Execution path: Compare codes and labels with each official document, and record mismatches and
  missing leaves.
- Acceptance gates: Every scheme has a verification state with evidence. A mismatch keeps the
  concept unverified rather than changing it silently. A negative result (publication
  inaccessible) is valid when recorded.
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Compared primary publications against the reviewed schemes. Fifteen scheme decisions are packaged
and linked as `domains/<domain>/seeds/verification.json`. At initial acceptance, eight downloadable
primary publications had byte checksums; OECD Figure 9 was inspected through the web reader after
its official PDF endpoint returned HTTP 403. The follow-up below records the subsequently supplied
OECD PDF and its checksum. Retrieval receipts, publication bodies, extracted text, comparison
helpers, rendered pages and a decision summary remain under
`$DATA_DIR/taxonomy-verification/official-2026-11-22/`.

Three subsets verify: ESA's 133 abbreviated TD/TS nodes, EUSPA's 16 segment labels and 43 GKG
codes. Twelve schemes remain unverified with specific reasons. NASA TX17, CAMEO 20 and ECS 2.3
retain the supplied labels despite publication differences. GPT, OECD-derived products and the
mixed ECS application tree retain normalized origins; six local schemes claim no official edition.
GCAM's codebook was decoded and its three concrete proposal examples checked without importing a
scheme or full dictionary. Missing lower levels and source inconsistencies are recorded explicitly.
See the [durable review decisions](../current/ontology-taxonomy/verification.md).

Minimal offline wiring projects the reviewed decisions into the existing seed staging and loader
paths. Strict report validation requires one review per scheme, unchanged origin and a checksum of
IDs, codes, statuses, hierarchy and all label rows. Unsupported verified claims, stale content,
missing review files and stored metadata drift fail before database writes. No publication fetcher,
dictionary importer, new CLI surface or dependency was added. Verification is a scoped manual
comparison, not automatic certification or Ukrainian terminology review.

An initial content digest included proposal-row definitions. The existing reordered-proposals
regression exposed that structural parents inherit their first contributing row. Those definitions
are provenance, not official definitions, so the digest now binds the compared codes, labels and
hierarchy while excluding proposal prose. Reordering passes without weakening content-change
checks. The first CI attempt also identified excessive complexity in the review loop; validation
and metadata projection now have separate cohesive functions.

## Acceptance evidence

Accepted on 2026-11-22. All declared gates are satisfied, including the allowed partial negative
result recorded in the [closed-research register](../future-research.md#verify-official-taxonomies----full-official-status-for-mixed-seeds).

| Check | Evidence and result |
| --- | --- |
| Prerequisites and initial count | `make plan-status`: 112 tasks, 100 agent, 12 human; CLEAR=92, RUN NEEDED=8, BLOCKED BY HUMAN=3, HUMAN-GATED=9. No open task prerequisites. Public publications were checked directly. |
| Regression first | `.venv/bin/python -m pytest tests/semantic/test_verification.py -q` initially failed: no verified metadata and no review manifests. |
| Publication comparison | Public HTTPS bodies downloaded with Python `urllib.request`; SHA-256 computed over original bytes. All report publication hashes were checked against archived bodies. ESA table extraction reproduced 26 domains and 107 subdomains with zero label differences. |
| Independent source fixtures | `tests/semantic/fixtures/official_comparisons.json` preserves only 239 selected rows from six publications. Offline comparisons reproduce exactly the NASA, CAMEO and ECS label mismatches. No full GDELT dictionary is imported. |
| Failure paths | `tests/semantic/test_verification_failures.py` rejects changed labels in either locale, codes, statuses, parents, additions/removals, malformed or incomplete reviews, unsupported verified claims and packaged metadata drift. Rejected reviews leave input unchanged. |
| Normal entry point | `make seed-check` passed: 1,173 reconciled rows, 612 accepted, one duplicate, 477 needs_mapping and 83 rejected. Both locale CLI paths and machine output pass in CI. Latest staged evidence: `seed-import/06eaa91959234e9bb3713dad5ba87df4/` under DATA_DIR. |
| Required gate | `make ci` passed: format, lint, typing, complexity, shell lint, catalogs, contract drift, documentation links, plan integrity and research register; 654 tests passed, 64 local tests deselected. |
| Database loader | `make test-integration` passed: 64 tests, 654 deselected, including exact reviewed content after two rebuilds, idempotency and conflict rollback. The sandbox initially denied the loopback connection; the authorized rerun passed against the configured service. No database service was started or stopped. |
| Coverage | `make coverage` passed: 654 tests, 93.21% total coverage against the unchanged 90% floor; publication verification module has complete coverage. |
| Documentation | `make lint-md` passed, including link checks. The new review page is linked from the owning current-state page and seed reference. |
| Packaging | `make build` passed with `UV_CACHE_DIR` under DATA_DIR and public build-requirement access. An extracted wheel loaded 726 terms outside the source package and returned exactly 3 verified and 12 unverified schemes. Wheel and source distribution copies are preserved in the evidence directory's `dist/`. |
| Preservation | Compared against HEAD: all 726 IDs, 491 concept rows, preferred labels and all scheme origins are unchanged. Only scheme metadata and the generic scheme description changed. |
| Final review | `git diff --check` passed. Changes are limited to review artifacts, their seed integration, regression tests, current documentation, the research decision and plan bookkeeping. |

The initial sandbox build could not use the default uv cache and then could not resolve the build
requirement over the restricted network. A DATA_DIR cache and authorized public dependency fetch
resolved both; no check was disabled. The original OECD HTTP 403 was an accepted access limitation;
the user-supplied PDF resolved it in the follow-up below. Ukrainian terminology, deeper leaves
and complete GDELT
dictionaries remain outside this task's acceptance scope.

## Handoff

Task counts changed from 112 to 111 total, 100 to 99 agent, and 12 to 12 human. CLEAR changed from
92 to 91; all other status counts are unchanged. `verify-official-taxonomies` left the plan and was
removed from the audit and release prerequisites. The next agent candidate is `skos-export`.

The affected capability is `ontology-taxonomy`; its registry status remains `planned` because SKOS
export is still open. Future export and UI work must preserve verification reasons, origin and
subset boundaries. Complete GDELT dictionaries remain in `gdelt-source-dictionaries`; reviewed
Ukrainian terminology remains in `review-ukrainian-terminology`. Reopening conditions for negative
publication decisions are in the linked closed-research section. No commits or pushes were made.

## OECD download follow-up, 2026-11-22

The user supplied `.data/f68de895-en.pdf` after the initial automated HTTP 403. `pdfinfo` identifies
OECD as author, the expected title and DOI `10.1787/f68de895-en`, 38 pages and the August 2024
edition. `pdftotext -layout` and a rendered inspection of page 30 confirm Figure 9 and the original
finding: the diagram is uncoded, while the seed includes local codes and engineering extensions.

`sha256sum .data/f68de895-en.pdf` returned:

```text
25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083
```

The unchanged 7,174,135-byte supplied PDF is archived as `oecd.pdf` under
`$DATA_DIR/taxonomy-verification/oecd-user-2026-11-22/`, with `oecd.json` recording acquisition as
user-provided, the source URI, title, DOI, edition, size and checksum. Text extraction and the
Figure 9 page render are preserved beside it. The original failed download receipt is retained.
The generic `file` utility guessed 39 pages; the PDF-aware `pdfinfo` tool reports 38, consistent
with the extracted pages and report numbering.

Updated the OECD review and regenerated the microelectronics snapshot through `reconcile()`.
The access-limit finding is removed and the supplied publication checksum is recorded. The
scheme stays `kb_normalized` and `unverified` because local extensions are unchanged. The source
URI, concept IDs, codes, labels, hierarchy and all verification-state counts remain unchanged.
Current-state documentation and the closed-research section now distinguish the resolved byte
availability from the still-negative official-status decision. Plan counts remain 111 total,
99 agent and 12 human; no new capability or research task was needed for this supplied input.

A regression initially failed with missing `source_sha256`; after the update it confirms the
pinned checksum, retained normalized/unverified status and removal of the obsolete access limit.
Follow-up validation passed: `make seed-check` (1,173 rows), `make ci` (655 passed,
64 local tests deselected), `make lint-md` and `git diff --check`. CI evidence is preserved in the
follow-up artifact directory as `ci.log`. Database integration, coverage and packaging were not
repeated for this metadata-only follow-up; the earlier task acceptance runs remain recorded above.
