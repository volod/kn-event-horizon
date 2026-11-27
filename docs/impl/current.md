# Current Implementation

This index describes behavior available now. For product intent read the
[specification](../design/spec.md); for work that remains read the [forward plan](plan.md). For
research questions that stopped, and what would reopen them, read the
[closed-research register](future-research.md).

## Documentation shape

Small areas stay as one page. When an area grows, its page becomes a short orientation and index,
and focused topics move under `current/<area>/`. New pages must be linked from their area in the same
change. Write behavior, modules, commands, and durable findings at the narrowest level.
[Task records](records/README.md) preserve acceptance evidence.

## Areas

Each page under [`current/`](current/README.md) is listed here with what it owns. The tooling and
documentation checks that came with the template are described in the
[development guide](../guide/development.md).

| Page | Owns |
| --- | --- |
| [Product core](current/product-core.md) | Distribution, `kn` import package, `kn` and `kn-plan` commands, and identity verification |
| [Runtime platform](current/runtime-platform.md) | Compose stack, the PostgreSQL and PostGIS service, `make db-*` targets, schemas, roles, the version manifest, the database integration test harness, and where each kind of test runs |
| [Localization](current/localization.md) | English CLI messages, dashboard and map catalog rules, CLDR formatting and source-text fallback |
| [Data contracts and space example import](current/data-contracts.md) | Pinned ODCS and KN extension lint, editable version 1.0.0 baseline, SQLAlchemy and Alembic governance, offline reference resolution, deterministic DDL/model/dbt artifacts, PostGIS templates, guarded all-schema rebuild and reviewed-seed hook, and lossless SATCOM example import within space |
| [Ontology and taxonomy](current/ontology-taxonomy.md) | Semantic contracts, qualified IDs, source-language labels with explicit fallback, hierarchy and mapping validation, verification evidence, tags and comparison policy definitions, reviewed vocabulary seeds, all-row proposal reconciliation and SKOS Turtle export |
| [Evidence model](current/evidence-model.md) | Claim, evidence, confirmation, alias, translation, relation, canonical fact, selection outcome and review contracts with null rules, deterministic keys, idempotent writes and as-of views; canonical selection through field update policies and knowledge-time fact projection; typed human verification decisions, trusted actor boundary, registered record and field projections, audience filtering, durable journal, causal conflicts and rebuild replay reports; operator review list/decide/replay, identity match/drift choices and source dispute rates |
| [Object identity](current/object-identity.md) | Identity registry, durable journal and rebuild, lifecycle commands, profile-driven matching, reproducible match decisions, field-level partial-update tracking and the rights-filtered lineage lookup |
| [Source management](current/source-management.md) | Reviewed source catalogue, qualified IDs, source listing, rank overrides, crawler validation, onboarding and fixture checks |
