# SKOS Vocabulary Export

`kn vocabulary export --format skos --scheme <qualified-id>` exports one reviewed scheme as
Turtle. The exporter reads the same validated packaged snapshots and publication reviews used by
the [seed loader](seeds.md). It needs no database or network connection and never changes seeds,
proposals, or stored semantic data.

## Operator command

From the project root, load the shared environment so `.env` and `DATA_DIR` resolve normally:

```bash
source scripts/shared/common.sh
kn_load_env
.venv/bin/kn vocabulary export --format skos \
  --scheme microelectronics.oecd_2024.scheme --data-dir "$DATA_DIR"
```

Scheme IDs include the `.scheme` suffix. For an internal vocabulary, use for example
`gdelt.services.scheme`; its output retains origin `service_extension` and state `unverified`.
The available schemes and publication boundaries are listed in the
[verification reference](verification.md#decisions-and-boundaries).

Each invocation writes `$DATA_DIR/skos/<run-id>/vocabulary.ttl`. A unique run directory keeps earlier
exports intact. `--data-dir` overrides the CLI's `DATA_DIR` environment default, otherwise `.data`.
The shared environment resolves relative `DATA_DIR` from the project root; an explicitly supplied
relative `--data-dir` follows the invoking working directory, as for proposal import.

Both `--locale en` and `--locale uk` report the scheme, selected concept count, origin, verification
state, and path. Add `--json` for stable keys `status`, `format`, `scheme_id`, `concepts`, `origin`,
`verification_state`, and `path`. Operator results use the existing logging stream, stderr; the
Turtle is in the reported file. Invalid arguments return 2 with `E_ARGUMENTS`; an unknown scheme or
unwritable destination returns 1 with `E_INPUT`. Invalid semantic content retains the existing
`E_CONTRACT` diagnostic. Unknown schemes fail before creating an export directory.

## Interchange mapping

`src/kn/semantic/skos.py` provides `skos_graph(snapshot, scheme_id, references=...)` for an explicitly
validated complete snapshot and `export_scheme(scheme_id, data_dir)` for packaged reviewed content.
Callers supply the owning external-reference registry when a snapshot contains evidence or entity
references. Both functions validate the full semantic model before export.

Term URIs are `urn:kn:term:<qualified-id>`, independent of run IDs, ordering, publication URLs, and
working directory. The extension prefix `kn:` is `urn:kn:semantic:`. It records KN metadata without
assigning publisher identities to local codes.

| Semantic content | RDF output |
| --- | --- |
| Scheme and concept | `skos:ConceptScheme`, `skos:Concept`, `skos:inScheme` |
| Preferred and alternative labels | `skos:prefLabel`, `skos:altLabel`, retaining language tags and exact text |
| Original string code | `skos:notation`, preserving leading zeroes; this can be a local KN notation |
| Definition | Untagged `skos:definition` plus available localized definitions with language tags |
| Primary parent | Child `skos:broader` and parent `skos:narrower` |
| Root | `skos:topConceptOf` and scheme `skos:hasTopConcept` |
| Qualified ID and status | `dcterms:identifier`, `kn:status` |
| Deprecated or replaced term | `owl:deprecated true`; replacement also uses `dcterms:isReplacedBy` |
| Standard concept mapping | Corresponding `skos:exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, or `relatedMatch` |
| Analyst crosswalk | `kn:analystCrosswalk`, with no inferred SKOS equivalence |
| Mapping provenance | Named `rdf:Statement` at the mapping term URI, with subject, predicate, object, `kn:method`, and exact `kn:evidenceId` literal |
| Scheme publication | `dcterms:publisher`, `dcterms:source`, `kn:edition`, `kn:sourceSha256` when present |
| Scheme origin and verification | `kn:origin`, `kn:verificationState`, `kn:verificationReason` |
| Reviewed boundary | `skos:scopeNote` for verification reason and review scope; `kn:comparison`, `kn:contentSha256` |

Every selected concept is included, including draft and deprecated terms. Mappings touching the
selected scheme are included in their stored direction, including incoming mappings. Counterpart
concepts and their schemes receive labels and metadata, including publication scope notes, but
their hierarchies and further mappings are not expanded. The reported count includes only concepts
in the requested scheme. This preserves OECD crosswalks without presenting the mixed product tree
as official or claiming that the counterpart's whole vocabulary was exported.

All schemes use the standard `ConceptScheme` type; origin is explicit metadata. Official origin
does not imply verified status or complete dictionary coverage. Local extensions keep their own
scheme membership. The export retains source-text fallback in `uk` and proposal-derived
definitions; it does not certify translations or turn proposal text into official definitions.

The file is ASCII using Turtle `\u` and `\U` escapes for Unicode. Parsed labels retain accents,
Ukrainian text, quotes, backslashes, newlines, and characters outside the basic multilingual plane.
Unchanged content produces identical Turtle bytes across invocations and interface locales.
SKOS remains interchange only: typed relations, validation, editing, and reasoning stay outside
this export.

## Verification

- `tests/semantic/test_skos*.py`: all 16 reviewed schemes parse with RDFLib; preferred labels,
  hierarchy, definitions, alternatives, notations, lifecycle, mappings and publication metadata
  survive. Fixtures cover empty schemes, reordered input, malformed models, unknown schemes,
  Unicode escapes, both locales, JSON errors, output failures, and repeated exports.
- `tests/e2e/test_skos.py`: real subprocesses in both locales produce identical Turtle and retain
  the verified OECD scheme's boundary. `make test-bilingual` includes this path.
- `make ci`: formatting, lint, typing, complexity, contracts, documentation, catalogs, and unit tests.

[Task record 0024](../../records/0024-ontology-taxonomy-skos-export.md) records the retained command
runs and acceptance evidence.
