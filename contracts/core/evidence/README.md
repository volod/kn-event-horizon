# Evidence contracts

The version 1 wire schemas here describe `kn.review.model` targets, requests, durable decisions
and nullable read stamps. Tests check their exact schema bytes against the typed models. Runtime
validation also enforces typed keys, scope, canonical event digests, causal outcomes and UTC rules;
JSON Schema alone does not establish actor authority or referential integrity.

The registered ODCS storage source is
[`resources/evidence/1.0.0.json`](../../../src/kn/contracts/resources/evidence/1.0.0.json).
`make contract-compile` refreshes its reviewed SQLAlchemy, DDL, dbt and engine artifacts under
[`generated/contracts/kn.core.human_verification/`](../../../generated/contracts/kn.core.human_verification/).
The storage contract keeps the development baseline at `1.0.0`.

The evidence model contract
[`resources/evidence/claims/1.0.0.json`](../../../src/kn/contracts/resources/evidence/claims/1.0.0.json)
registers claims, evidence, confirmations, aliases, translations, relation assertions, canonical
fact versions, selection outcomes, review items and review decisions in the same schema. Its
artifacts are under
[`generated/contracts/kn.core.evidence/`](../../../generated/contracts/kn.core.evidence/). Typed rows,
keys and views live in `kn.evidence`.

See the [current protocol](../../../docs/impl/current/evidence-model.md) for trusted entry points,
journal ownership, request retries, transaction behavior and remaining projection work.
