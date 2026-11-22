# Semantic Model Contracts

## Work contract

```markdown
#### semantic-model-contracts

Ontology and taxonomy content needs its own contracted data model before any import.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: The accepted [contract compiler](current/data-contracts/compiler.md) and its local
  reference catalog interface, and the [deployment set](current/data-contracts.md#deployment-set)
  that registers its contracts.
- User-visible outcome: The `semantic` schema holds namespaces, entity classes, relation types,
  concept schemes, concepts, mappings, entity tags, attribute definitions, condition sets,
  comparison profiles, and rubrics, with per-locale labels.
- Scope boundary: The contracts and their validation rules: unique IDs, no cycles, parents exist,
  endpoints exist, mappings don't conflict, statuses, and verification states. No content import.
- Data and artifact paths: `contracts/core/semantic/`, `src/kn/semantic/`, `tests/semantic/`.
- Execution path: Write the contracts, compile, and add validation code with invalid fixtures for
  every rule.
- Acceptance gates: Fixtures with a cycle, a missing parent, a duplicate preferred label, an unknown
  endpoint, and an ID collision are rejected. `make ci` passes.
- Documentation target: A new `current/ontology-taxonomy.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The contract `kn.core.semantic` defines the 11 meta-model kinds in 18 normalized tables,
including a shared term registry, per-locale labels and explicit condition/profile/rubric members.
It uses `src/kn/contracts/resources/semantic/1.0.0.json` rather than a parallel
`contracts/core/semantic/` copy: the accepted deployment registry and wheel resource decision in
[record 0019](0019-data-contracts-storage-contract-registry.md) already establishes that location.
The registry automatically includes it in lint, compilation, upgrades, rebuilds and verification.
There are 62 generated artifacts including the manifest. No dependencies or seed loaders changed.

`kn.semantic.validate_model` validates complete JSON-wire snapshots without mutation or I/O.
Row shapes, enums, keys and references come from the contract; graph, label, lifecycle and mapping
rules live in focused semantic modules. Explicit caller-owned entity/evidence ID sets resolve
external references without inventing future identity or evidence tables. The current-state page
states the boundary between SQL constraints and application checks, and the requirement for future
writers to validate the entire proposed snapshot before writing.

Identifiers are explicit namespace-qualified strings, preserving leading zeroes. Each term has one
subtype. Scheme editions with overlapping codes use separate namespaces. Labels preserve original
Unicode while comparison uses NFC, case folding and collapsed whitespace. English and Ukrainian
preferred labels are required; extra language tags are supported. Primary hierarchies and
replacement chains are checked iteratively. Deprecated concepts remain resolvable.

Mapping validation catches directional inverses, duplicates, incompatible pair mappings and
conflicts inside exact-match components. Analyst crosswalks remain a separate kind. Scheme
verification requires publication metadata and a checksum but does not claim to verify a
publication. Tag review states, half-open intervals, class-compatible profile attributes and
positive exact rubric weights are validated. Domain conversion and ranking execution are outside
this task.

Fixture-driven improvements during review:

- A real-calendar timestamp without an end date was accepted because JSON Schema's RFC3339
  checker depends on an optional package. A failing February 30 regression now uses the standard
  library check, with no new dependency and without relying on an interval comparison.
- Two preferred labels using `en-GB` and `en-gb` were accepted when their text differed. A failing
  regression now checks preferred-language uniqueness without case.
- The shared identifier registry prevents collisions across semantic kinds; hierarchy validation
  remains linear on a 1,500-node chain, and reused codes and labels in another domain remain valid.
- Removed a redundant unique index identical to the namespace-label primary key during final DDL
  review. Generated outputs and bilingual CLI goldens reflect the final contract digest.

## Acceptance evidence

Status: accepted. Every declared acceptance gate passed.

- Initial `make plan-status`: 114 tasks; 102 agent, 12 human; 94 CLEAR, 8 RUN NEEDED,
  3 BLOCKED BY HUMAN, 9 HUMAN-GATED.
- `make contract-compile`: all three registered contracts compile; generated semantic DDL,
  Pydantic, dbt, wire schemas and manifest reviewed. No SATCOM/governance artifacts changed.
- Semantic fixtures reject every required case: primary cycle, missing parent, duplicate
  preferred label, unknown relation endpoint and ID collision. They also cover malformed inputs,
  invalid enums, scheme links, replacement chains, multilingual labels, mapping conflicts,
  external references, validity and comparison-policy consistency.
- After `source scripts/shared/common.sh`, `kn_load_env`, run
  `COVERAGE_FILE="$DATA_DIR/semantic-model-contracts/2026-11-22/coverage" .venv/bin/python -m pytest
  tests/semantic -o "cache_dir=$DATA_DIR/cache/pytest" --cov=kn.semantic --cov-report=term-missing
  --cov-fail-under=90`: 73 passed, semantic coverage 99.31%.
- An initial `make ci` exposed outdated deployment-directory and English/Ukrainian CLI golden
  expectations. Those now include the semantic contract. The next full gate passed 596 tests
  with 63 local database tests deselected.
- The sandbox could not reach PostgreSQL or Docker. With local database access enabled,
  `make test-integration` passed all 62 existing tests. The additional semantic round-trip test
  passed independently, including leading zeroes, Ukrainian labels, exact decimal values,
  deferred references, duplicate IDs, invalid statuses and missing parents. Scratch schemas were
  cleaned by the harness, and rebuild tests rolled back their transactions. No database service
  was started or stopped and no durable source data was rebuilt.
- `make lint-md`: passed after fixing wrapping findings; no broken links.

Final checks after the contract-index cleanup:

- `make ci`: passed; 596 tests passed and 63 database tests were deselected. Format, lint, typing,
  complexity, shell lint, catalog checks, contract drift, documentation links and spec-plan
  integrity all passed.
- `make test-integration`: passed; all 63 database tests passed, with 596 unit tests deselected.
- `make lint-md`: passed, including documentation links.
- `git diff --check`: passed. Scope review confirms no content import, dependency change, seed
  loader registration or unrelated user change.

Runtime coverage and final `ci.log` and `integration.log` are under
`$DATA_DIR/semantic-model-contracts/2026-11-22/`. There are no outstanding acceptance gates.

## Handoff

The accepted task is removed from the plan. Counts changed from 114 tasks to 113,
102 agent tasks to 101, and 12 human tasks remain;
93 CLEAR, 8 RUN NEEDED, 3 BLOCKED BY HUMAN and 9 HUMAN-GATED. Removed the task from the
prerequisites of `seed-vocabulary-import`, `identity-registry-contracts`,
`evidence-claim-contracts` and the optional ontology audit. Seed import and identity contracts now
link the available model. The ontology-taxonomy registry row links current behavior and remains
`planned`: `seed-vocabulary-import`, `verify-official-taxonomies`, `skos-export` and the group audit
remain open. The next agent task is `seed-vocabulary-import`.
