# SKOS Export Task Record

## Work contract

```markdown
#### skos-export

Vocabularies need a standard interchange format.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: RDFLib as the justified dependency.
- User-visible outcome: `kn vocabulary export --format skos --scheme <id>` writes Turtle with `en`
  and `uk` labels, hierarchy, notations, definitions, and mappings.
- Scope boundary: Export only. SKOS never becomes the source of truth.
- Data and artifact paths: `src/kn/semantic/skos.py`, `$DATA_DIR/skos/<run-id>/`,
  `tests/semantic/`.
- Execution path: Map the meta-model to SKOS terms, and keep analyst crosswalks as distinct
  mapping properties.
- Acceptance gates: The export parses with RDFLib, labels round-trip, and an analyst extension is
  never typed as an official scheme.
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).

```

## Implementation and decisions

- Added `kn.semantic.skos` and the real `kn vocabulary export --format skos --scheme <id>`
  command, with localized help, human results, stable JSON, and existing error conventions.
  Proposal import retains its existing command and flags under its own action parser.
- RDFLib 7.6.0 is the task's justified runtime dependency; `uv.lock` also adds its required
  pyparsing 3.3.3 dependency. No other dependency changed.
- The command reads only validated packaged reviewed seeds and publication manifests, with no
  database or network dependency. The snapshot API requires caller-owned external references.
- Stable `urn:kn:term:<qualified-id>` URIs preserve qualified IDs across runs and editions.
  The exporter retains bilingual labels, alternatives, definitions, exact string notations,
  hierarchy, status, deprecation and replacement links.
- Incoming and outgoing mappings retain their stored direction. Named RDF statements retain
  mapping IDs, methods and evidence. Analyst crosswalks use `urn:kn:semantic:analystCrosswalk`;
  no SKOS equivalence is inferred. Counterpart concepts and scheme descriptions are included
  without expanding unrelated hierarchies or mappings.
- Every described scheme retains origin, verification state and reason, publication metadata,
  review scope, comparison and content digest. Standard ConceptScheme typing never promotes
  an internal extension to an official vocabulary. Local notations and source-text fallback
  remain explicit. Only the selected scheme's concepts count toward the reported total.
- Unique `$DATA_DIR/skos/<run-id>/vocabulary.ttl` artifacts preserve prior exports. Unicode uses
  Turtle Unicode escapes so the files stay ASCII while parsed text remains unchanged.
- A broader Unicode regression first failed with RDFLib's `bad escape`: Python's generic
  `backslashreplace` generated an invalid Turtle escape for Latin accents. Explicit Turtle
  `\u` and `\U` escapes fix accents, Ukrainian text, supplementary characters, quotes,
  backslashes and newlines. The regression now passes.
- Split term metadata from localized label emission after the initial complexity gate reported
  cognitive complexity 19 in `_terms`; the normal threshold now passes without weakening checks.
- Updated the narrow SKOS reference, current-state index, seed and verification links, and registry.
  Reviewed help goldens change only the intentional top-level vocabulary description.

## Acceptance evidence

Status: accepted. All declared task gates passed.

1. Initial `make plan-status`: 111 tasks, 99 agent, 12 human; CLEAR=91, RUN NEEDED=8,
   BLOCKED BY HUMAN=3, HUMAN-GATED=9. No open task prerequisites; RDFLib is explicitly authorized
   by the task. The working tree was clean.
2. The first fixture suite failed collection with `ModuleNotFoundError: kn.semantic.skos` before
   implementation. The Latin-accent extension then failed parsing before its serialization fix.
3. Dependency resolution and installation: `make lock bootstrap`, with `UV_CACHE_DIR` under
   `$DATA_DIR/cache/uv`. The sandbox's read-only default uv cache and restricted DNS required the
   writable cache override and approved network access for dependency installation. Tests and
   exports remain offline.
4. `.venv/bin/python -m pytest tests/semantic/test_skos.py
   tests/semantic/test_skos_reviewed.py tests/semantic/test_skos_cli.py`: 39 passed. Adding
   `tests/semantic/test_seed_cli.py` to the initial run gave 45 passed, including both unchanged
   proposal-import locales.
5. `.venv/bin/python -m pytest tests/e2e/test_skos.py`: 1 passed. Real human and JSON CLI calls
   in both locales retain the verified OECD boundary and produce identical Turtle bytes.
6. `make ci` after implementation and the Unicode/complexity fixes: 731 passed, 64 local-only
   tests deselected; catalogs, contracts, format, lint, typing, complexity, shell, links, and
   specification/plan checks passed. The additional subprocess export test was added afterward.
7. Live acceptance, from the project root after `source scripts/shared/common.sh; kn_load_env`:

   ```bash
   export KN_SKOS_ACCEPTANCE_ROOT="$DATA_DIR/skos/acceptance-20261122T184637Z"
   .venv/bin/python "$KN_SKOS_ACCEPTANCE_ROOT/verify.py"
   ```

   All 32 real CLI exports passed: 16 schemes in `en` and `uk`, covering all 520 selected
   concepts. Every artifact parses with RDFLib. Preferred/alternative labels, primary hierarchy,
   mapping direction, origin and verification state match the reviewed inputs. Corresponding
   locale exports have identical SHA-256 values. The script and `summary.json` are retained
   under that acceptance directory; the summary records each export path, hash and triple count.
8. `make lint-md`: passed, including documentation links.
9. `UV_CACHE_DIR="$DATA_DIR/cache/uv" UV_OFFLINE=1 make build` after shared environment loading:
   passed, producing the source and wheel distributions. An extracted wheel, selected through
   `PYTHONPATH` from a directory outside the repository, exported and parsed the verified OECD
   scheme with 29 selected concepts. The receipt and extracted package are retained under
   `$DATA_DIR/skos/wheel-check-a0d6b1db6e84499a8a92a7e1433e32bf/`.
10. `git diff --check` and an ASCII scan of every changed/added source, document and fixture:
    passed.
11. Final `make ci`: passed with 732 tests passed and 64 integration/heavy tests deselected.
    All catalog, contract, formatting, lint, typing, complexity, shell, link, specification/plan
    and closed-research checks passed. The full log is retained as
    `$DATA_DIR/skos/acceptance-20261122T184637Z/ci.log`.
12. `make quality`: all checks, 732 tests, coverage and Markdown passed. Aggregate branch-aware
    coverage is 93.75%, above the unchanged 90% floor; `kn.semantic.skos` has complete coverage.
    The final build step failed because the sandbox's default uv cache is read-only. The
    separate writable-cache offline `make build` in item 9 passed, as did its wheel smoke test;
    no check was weakened. Coverage data is retained as `coverage.json` beside `ci.log`.
    All quality components therefore passed, with that environment override for the build.

## Handoff

The plan removes `skos-export` and its downstream prerequisites, marks `ontology-taxonomy` shipped,
and leaves its optional implementation audit open. Executable policy evaluation remains with its
own tasks. No database deployment, seed edits, OWL reasoning, taxonomy editing, or import from SKOS
was added. Database integration and heavy tests are outside this read-only export's acceptance;
no database service was started or modified.

`make plan-status` after acceptance edits: 110 tasks, 98 agent, 12 human; CLEAR=90, RUN NEEDED=8,
BLOCKED BY HUMAN=3, HUMAN-GATED=9. The next required agent task is
`identity-registry-contracts`; the optional ontology audit is also unblocked. No new plan task was
needed. There are no unresolved acceptance gates for `skos-export`.
