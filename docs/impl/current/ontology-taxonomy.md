# Ontology and Taxonomy

The semantic meta-model and [reviewed vocabulary seeds](ontology-taxonomy/seeds.md) are available.
The packaged ODCS
contract `src/kn/contracts/resources/semantic/1.0.0.json` defines `kn.core.semantic` in the `semantic`
schema and is registered after governance and SATCOM in the [deployment
set](data-contracts.md#deployment-set). Source installations and wheels use the same contract.
`make contract-compile` writes its 62 review artifacts to
`generated/contracts/kn.core.semantic/`; `make contract-check` detects drift.
Normal database upgrades and development rebuilds deploy it through the shared Alembic baseline.

## Datasets and identifiers

The contract has 18 tables:

| Tables | Purpose |
| --- | --- |
| `namespaces`, `namespace_labels` | Domain and scheme/edition boundaries and localized names |
| `terms` | Shared IDs, original string codes, kind, status and definition |
| `labels`, `alternative_labels` | Preferred labels, localized definitions, inverse relation labels and alternatives |
| `entity_classes` | Classes and their primary parent |
| `relation_types` | Source/target classes, cardinality, minimum evidence and guarded errors |
| `concept_schemes` | Origin, publisher, edition, publication URI, checksum and verification reason |
| `concepts` | Scheme, primary parent and replacement link |
| `concept_mappings` | SKOS mapping type or analyst crosswalk, method and evidence |
| `entity_tags` | Entity, concept, method, evidence, review state and validity |
| `attribute_definitions` | Entity class, value type, unit and quantity type |
| `condition_sets`, `condition_values` | Named observation conditions and exact original values |
| `comparison_profiles`, `profile_attributes` | Entity class, condition set, attributes and required fields |
| `rubrics`, `rubric_criteria` | Profile-bound analyst criteria, positive decimal weights and direction |

A namespace ID is `<domain>.<code>`, for example `space.esa_gpt_1_1`. Each term ID is
`<namespace-id>.<original-code>`. Codes stay strings, so `001` never becomes `1`. A scheme or edition
with reused codes needs a separate namespace. Namespace parts use lowercase ASCII identifiers;
native term codes allow ASCII letters, digits, underscores, dots, colons and hyphens. IDs are
explicit, independent of input ordering, and shared across semantic kinds. A term has exactly one
matching subtype row. Namespaces and terms cannot reuse an ID.

Named terms and namespaces require preferred labels in `en` and `uk`; additional language tags
are supported. Concept preferred labels are unique per scheme and language; other named terms
are unique within their kind and namespace. Comparison uses Unicode NFC, case folding and collapsed
whitespace, while storage preserves the original text. Each term has one preferred label per
language tag, compared without case. Alternative labels require a preferred label in the same
locale and must be distinct. Relations require localized inverse labels.

## Validation interface

```python
from kn.semantic import ExternalReferences, validate_model

validate_model(snapshot, ExternalReferences(
    entity_ids=frozenset(known_entity_ids),
    evidence_ids=frozenset(known_evidence_ids),
))
```

A snapshot is a dictionary of contracted table names to row arrays. Missing datasets are empty;
unknown datasets or fields, missing required values, blank strings, coercion and invalid enums
fail. Values use the compiler's JSON wire encoding: aware timestamp strings and exact decimal
strings. Validation is offline and does not mutate input, connect to a database or import content.
An empty snapshot is valid. External registries default to empty, so tags and mappings require
explicit evidence IDs and tags also require known entity IDs.

`kn.semantic.structure` derives row shapes, primary keys, unique indexes and foreign references
from the contract. `kn.semantic.terms` checks qualification, kinds, primary hierarchy cycles,
scheme membership, labels and replacement chains. Walks are iterative and support deep trees.
Deprecated concepts retain their rows and remain valid endpoints. A replaced concept requires a
successor in the same scheme; other statuses cannot carry replacement links. Primary parents stay
within a concept scheme. Multiple parent relationships are outside this primary-tree profile.

`kn.semantic.policies` rejects self, duplicate and conflicting mappings, including reversed
broad/narrow mappings and conflicts within transitive exact-match components. Analyst crosswalks
stay separate from SKOS mappings. Scheme origin remains one of `official`, `kb_normalized`,
`kb_extension`, `service_extension`, or `native`; verification never rewrites it. Verification
states are `unverified` and `verified`, both with a reason. Verified schemes require publisher,
edition, a credential-free HTTP(S) publication URI and a lowercase SHA-256 checksum. These checks
establish evidence shape; the [publication reviews](ontology-taxonomy/verification.md) bind
reviewed scheme metadata to the checked seed content and record comparison boundaries.

Tag verification states are `unreviewed`, `corroborated`, `verified`, `disputed`, and `rejected`.
Validity intervals are half-open and increasing when both ends exist; unknown ends stay null.
Timestamps are checked for real calendar dates and explicit offsets without optional format
checker dependencies. Comparison attributes and conditions must belong to the profile's entity
class; rubric criteria must name a profile attribute and use a positive exact decimal weight.

Failures raise the existing `ContractError` with a JSON Pointer, a rule such as `semantic.cycle` or
`semantic.endpoint`, and a value-free hint. A cycle names the parent or replacement link of a row on
the cycle, for example `$/concepts/12/parent_id`. A publication URI must also be a valid IRI:
whitespace, control characters, the backtick and `<>"{}|\^` are refused, because RDF serializations
cannot write them; percent-encoding and non-ASCII characters are allowed. Row-shape failures use the
existing JSON Schema rule names. The [seed reconciliation command](ontology-taxonomy/seeds.md) is
separate from model validation; rebuilds load only explicitly reviewed packaged files.

## Lifecycle report

Deprecated and replaced concepts stay valid endpoints, so validation accepts them. Review needs the
opposite view, which `kn.semantic.lifecycle.lifecycle_report(snapshot, external_uses=None)` gives:
one finding per retired concept that is still in use, with its status, the end of its replacement
chain and that successor's status, and every use. A use is a child concept, a mapping endpoint, an
entity tag, a replacement link, or a record of another engine. `external_uses` maps concept IDs to
such records, for example the claims that cite them; the owning engines supply it. Every seed
reconciliation writes the report for the combined reviewed content under `lifecycle`. The reviewed
seeds hold only `draft` concepts, so the report is empty today.

## Enforcement boundary and verification

PostgreSQL enforces primary keys, unique indexes, nullability, enums and deferred internal foreign
keys. The full-snapshot validator additionally enforces graph, label, lifecycle, external reference
and policy rules. Direct SQL writes do not enforce those application rules; future reviewed seed
and content writers must call `validate_model` on the complete proposed snapshot before writing.
External object/evidence reference integrity belongs to their owning engines. Units and quantity
types are preserved identifiers, and condition values preserve original text; this task does not
execute conversions, ranking or evidence selection.

- `make ci`: compilation drift, type/lint/complexity checks and network-free fixture validation.
- `tests/semantic/`: all 11 meta-model kinds, hierarchy cycles, missing parents, duplicate labels,
  unknown endpoints, ID collisions, lifecycle, schemes, mappings, policies and malformed input.
  `test_lifecycle.py` reports deprecated parents, mapping endpoints, tags, replacement chains and
  external uses; `test_integrity.py` covers cycle locations and publication IRIs.
- `tests/integration/test_semantic.py`: exact PostgreSQL round trip, deferred references, leading
  zeroes, Unicode, decimals, duplicate IDs, invalid status and missing parents.
- `make test-integration`: the new round trip and existing registry deployment/rebuild verification.

The [task record](../records/0020-ontology-taxonomy-semantic-model-contracts.md) contains acceptance
evidence. The [separate verified OECD product scheme and crosswalks](ontology-taxonomy/oecd.md)
are available alongside the original mixed product vocabulary.
[Seed import and proposal reconciliation](ontology-taxonomy/seeds.md) and
[official publication comparison](ontology-taxonomy/verification.md) are available.
[SKOS Turtle export](ontology-taxonomy/skos.md) preserves labels, hierarchy, mappings, scheme
origins, verification states and publication boundaries. The
[implementation audit](../records/0025-ontology-taxonomy-ontology-taxonomy-implementation-audit.md)
of the group records its findings and their dispositions.

## Known limitations

- Every `uk` label is a copy of the English proposal text, and every concept definition is a JSON
  dump of the proposal columns. Both are stored and exported as if they were Ukrainian labels and
  definitions. `vocabulary-text-integrity` in the [plan](../plan.md) corrects them; translations
  come from `review-ukrainian-terminology`.
- Exported term URIs use `urn:kn:term:<id>`, and `kn` is not a registered URN namespace.
  `decide-vocabulary-uri-namespace` lets the owner choose a base before any consumer stores the
  URIs.
- Each concept has one primary parent. A scheme with several broader concepts per concept needs a
  secondary hierarchy table, which is additive; reopen when a reviewed scheme needs one.
- Mappings are not restricted to concepts of different schemes. SKOS links schemes with mapping
  properties by convention, not by an integrity condition, and no reviewed mapping joins one
  scheme. Reopen when reviewed content does.
- Nothing re-checks the pinned publications for changed bytes; `official-publication-drift-check`
  in the plan adds that.
