# OECD Product Taxonomy and Crosswalks

`microelectronics.oecd_2024.scheme` is the verified category tree from Figure 9 of OECD's
*Chips, nodes and wafers* (August 2024). It has 29 categories, four roots and 25 parent links.
Its publication URI and SHA-256 are recorded in the [publication review](verification.md).
Figure 9 on page 30 and the packaging boundary on page 31 were checked against the supplied PDF.

The existing `microelectronics.product_v1.scheme` retains all 76 concepts, original IDs, labels,
definitions, parents and normalized origin. It remains unverified as an official dictionary.
The official scheme is additive; existing product references do not move or get renumbered.

## Source labels and identifiers

The official scheme contains only the 29 Figure 9 categories. Its KN codes, such as `L.MCU`,
are internal identifiers, not publisher-assigned notations. Internal identifiers do not prevent
verification of the source categories and their relationships.

Figure 9 uses `Others` for both a root and a residual child. Their distinct preferred display
labels are `Others (O)` and `Others (O.OTHER)` to meet the meta-model's uniqueness rule; both
retain the exact original `Others` as an alternative label. Other preferred labels match the
source spelling. English source text fills both locale slots; Ukrainian terminology remains
unreviewed. Verification does not activate draft terms or certify translations.

## Explicit mapping decisions

`domains/microelectronics/seeds/oecd_2024.json` links to the packaged reviewed transcription and
76 individual mapping decisions. Every decision has a reason. The checked-in data explicitly
selects a target and mapping type; runtime code does not infer one from a name or ancestor walk.

| Decisions | Meaning | Example |
| --- | --- | --- |
| 29 `exactMatch` | Same Figure 9 category in both schemes | Product `L.MCU` to OECD `L.MCU` |
| 23 `broadMatch` | Target is a broader category than the local specialization | Product `L.MCU.ULP` to OECD `L.MCU` |
| 17 `analyst_crosswalk` | Local association whose stronger semantic relationship is not established | Sensor module `O.SENS.RANGE` to OECD `O.SENS` |
| 7 unmapped | Non-chip assets are outside Figure 9's semiconductor-type scope | Development kits, IP, software, production equipment and materials |

The 69 mapped decisions are stored as `semantic.concept_mappings`, with stable IDs under
`microelectronics.oecd_2024_crosswalk`. Their method is `reviewed OECD Figure 9 product crosswalk`.
The seven unmapped decisions create no mapping rows. Composite SoC, module and other ambiguous
labels use analyst crosswalks rather than claiming official equivalence. The paper's page 31
packaging discussion does not add SoC or chiplet nodes to Figure 9.

Crosswalks are reviewed KN decisions, not OECD endorsements of local engineering extensions.
The official scheme's verification does not promote the mixed product scheme or its extensions.

## Evidence and implementation boundary

Each mapping cites `urn:sha256:<digest>` of the actual packaged `oecd_2024.json` review bytes.
That artifact contains the PDF URI and checksum, Figure 9 locator, transcription and authored
mapping reasons. Publication provenance on new terms retains their original proposal row locator
and adds the publication URI, checksum, locator, review path and evidence ID.

`kn.semantic.oecd_reference` validates the strict review shape, distinct category and decision
codes, complete category coverage, existing parents, acyclic hierarchy and supported mapping
choices. Source categories require exact mappings; local extensions cannot claim exact matches.
`kn.semantic.seed_oecd` imports the separate tree, enriches the original row reconciliation and
requires stored nodes, labels, mappings and citation metadata to match the review.

The seed publication resolver explicitly supplies the known review artifact as evidence. It does
not derive a trusted registry from mapping rows or create claim/evidence records for a future
engine. Ordinary semantic validation still rejects references absent from a caller's registry:

```python
from kn.semantic import validate_model
from kn.semantic.oecd_reference import publication_references
from kn.semantic.seeds import RESOURCES, reviewed_snapshot

validate_model(reviewed_snapshot(), publication_references(RESOURCES))
```

An edit to a review reason changes its evidence ID. Previously stored mapping evidence then
fails validation until the reviewed seed is reconciled and promoted. Missing review files, unknown
evidence, altered mapping types or targets, source disagreements and incomplete decisions fail
before database writes. The loader remains offline and independent of the working directory.
Normal rebuilds load the official scheme and mappings through the existing seed hook. General
entity and claim evidence remains the responsibility of its owning engines.

## Verification

- `make seed-check`: deterministic staging, all 1,173 original proposal rows reconciled, and new
  concept/mapping IDs included in their originating rows without changing status counts.
- `make ci`: independent 29-node/25-edge Figure 9 fixture, preservation of all original product
  rows, source label alternatives, each mapping class, explicit unmapped cases, evidence resolution,
  malformed references, changed review bytes and source disagreements.
- `make test-integration`: all 825 terms and 69 mappings round-trip, four verified schemes remain
  distinct, and two rebuilds plus an idempotent load reproduce the same content.
- `make build`: packages the reviewed transcription, decisions and scheme verification metadata.

[Task record 0023](../../records/0023-ontology-taxonomy-oecd-official-product-scheme.md) records the
acceptance evidence. Runtime comparison and test evidence is under
`$DATA_DIR/taxonomy-verification/oecd-scheme-2026-11-22/`.
