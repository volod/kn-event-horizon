# KN Event Horizon Specification

## Purpose

KN Event Horizon is a domain knowledge aggregator for industrial and technology awareness. It
collects evidence from public or legitimately licensed sources and normalizes it into domain
knowledge models governed by an explicit ontology and taxonomy. It preserves the provenance and
history of every claim. Results are available through SQL, bilingual English/Ukrainian dashboards
and time-enabled maps, and read-only Obsidian vault exports. The design favors small-team
maintenance, agent-assisted development, and reproducibility.

It is not a general-purpose data lake, an autonomous agent framework, a media archive, or a
real-time tracking or operations system.

| Domain ID | Scope | Order |
| --- | --- | --- |
| `space` | Launchers, spacecraft, constellations, ground systems, terminals, satellite services, tariffs, coverage, and the industrial ecosystem. Pilot: global SATCOM awareness. | First: ELT, then dashboards |
| `gdelt` | Selective GDELT media signals for cross-domain discovery. A signal, never a factual authority. | Second |
| `microelectronics` | Low-power sensing, MCU/SoC, FPGA, edge AI, optics, RF, and power electronics. Prospective technology first, product baselines in parallel. | Third |

Domain detail lives in the [space](domains/space.md), [GDELT](domains/gdelt.md), and
[microelectronics](domains/microelectronics.md) design pages.

The project is built on a small, production-shaped Python base developed with human and
coding-agent contributors. It makes product intent, forward work, current behavior, and quality
gates explicit enough that a fresh contributor can select and complete work without reconstructing
unwritten process.

The specification is living. A product need discovered during implementation expands this document
through [Extending This Specification](#extending-this-specification). It is not a fixed scope
fence, but behavior that has no specification, boundary, or evaluation is outside the product until
those are declared.

## Design principles

The trust chain is:

```text
domain problem -> bounded capability -> evaluation -> forward task
               -> code and tests -> current-state documentation
```

The product specification answers what and why. The plan answers what remains. Current-state pages
answer what exists. CI checks the joins so completion is a state transition, not a status note.

Product principles:

- **Contract first.** Git-managed ODCS contracts define every stored dataset. Reviewed seed files
  define ontology and taxonomy content. Generated artifacts are reproducible and never edited by
  hand.
- **Evidence over assertion.** Every claim keeps its origin, its original value, and the code that
  produced it. Conflicts are kept and reviewed, never overwritten.
- **Fetch once, transform many.** Source bytes are archived once. Every later transformation reads
  the archive.
- **Unknown is not zero.** A missing value carries a reason, and no default fills it.
- **Disabled by default.** A source collects nothing until its terms, limits, and permission are
  documented and a maintainer approves it.
- **Bilingual by design.** Every operator and user workflow works in `en` and `uk`, and facts are
  never duplicated per locale.
- **Simple until release.** Development uses rebuild-from-archive instead of versioned schemas and
  compatibility code. See [Development and release phases](#development-and-release-phases).

## Scope

The repository foundation includes:

- a Python 3.12+ `src` layout with an importable package and CLI;
- locked `uv` dependency management and Make entrypoints;
- deterministic tests, formatting, linting, typing, coverage, complexity, shell, and docs checks;
- GitHub Actions using the same CI entrypoint as local development;
- shared instructions for Codex, Claude Code, Cursor, and Gemini;
- a living capability registry and forward-plan/current-state lifecycle.

The product adds, in implementation order: a runtime platform, localization, data contracts, an
ontology and taxonomy model, a raw archive, an evidence model, source management, an ingestion
engine, and Obsidian export (the core engine). After the core come space ELT, orchestration, and
space dashboards; then GDELT and microelectronics ELT and dashboards; then operations hardening and
release readiness. Optional local AI extraction comes last.

Exclusions: no Kubernetes, Kafka, Elasticsearch, graph server, vector database, distributed agents,
or full GDELT replication. No satellite tasking or operations control. No public-facing custom
frontend; a minimal bilingual page is justified only where Superset, Kestra, and the CLI cannot meet
an acceptance test. No runtime dependency on a coding agent. No claims of comprehensive coverage or
ownership. No private customer data, private end-user terminal locations, or tracking of people.

Target host: one Linux server with at least 32 GB RAM, 4 TB disk, and an NVIDIA GPU with 16 GB
VRAM used only by optional AI extraction. It runs Docker Engine with Compose v2. CPU is unspecified;
plan for 8-16 logical cores and confirm by measurement.

## Architecture

```text
 Git (reviewed)                                        $DATA_DIR (durable runtime inputs)
 contracts, seeds, crawler configs, curation files     raw WARC archive, ledger, decision logs
        |                                                     ^             |
        v                                                     | fetch       | replay
 kn compiler --> generated DDL and models               approved sources    |
        |                                                                   v
        +--------------> PostgreSQL + PostGIS, database `kn` <---- kn engine: parse, map,
                         schemas: system, semantic, evidence,      validate, resolve, load
                         <domain>, analytics                        (CLI; Kestra when scheduled)
                                  |
                  +---------------+----------------+
                  v                                v
           dbt Core marts                   Obsidian export (ZIP)
                  |
                  v
           Superset: en/uk dashboards, maps, read-only SQL Lab
```

| Component | Choice | Boundary |
| --- | --- | --- |
| Contracts | ODCS v3, exact minor pinned with its JSON Schema checksum; Data Contract CLI as a build-time tool | Validate and export supported artifacts; never silently drop custom extensions |
| Ontology and taxonomy | Reviewed JSON seed files loaded into the `semantic` schema; SKOS Turtle generated with RDFLib | SKOS is an interchange export; typed relation rules live in the meta-model |
| Storage | PostgreSQL with PostGIS, newest major that has an official PostGIS image at pin time; one database `kn` with one schema per domain | ACID, constraints, geometry, time series; no cross-database transactions needed |
| Raw archive | WARC 1.1 (ISO 28500:2017) via `warcio`; Parquet fetch ledger | Original bytes plus origin URI and fetch time; the only fetch output |
| Engine | Python 3.12+, HTTPX, Pydantic, psycopg 3 | Deterministic extract, parse, map, load |
| Orchestration | Kestra OSS standalone, Process task runner, own `kestra` metadata database | Schedules, retries, concurrency; introduced with scheduled ingestion |
| Analytics | dbt Core with dbt-postgres in an isolated, pinned tool environment | Reviewed marts, tests, freshness |
| BI | Apache Superset OSS with `en` and `uk` enabled; own `superset` metadata database | Read-only `analytics` access, dashboards, maps, SQL Lab |
| Export | Python Markdown and YAML generator | Read-only, allowlisted Obsidian vault ZIP |
| AI (optional) | `llama.cpp` server with CUDA under a Compose `gpu` profile | Candidate extraction and translation only |
| Access | Caddy reverse proxy with TLS and authentication on a private network | No public database, Redis, or inference ports |
| Development | Git, Make, uv, pytest, Ruff, mypy, Docker Compose | English engineering artifacts |

Ready-made extract helpers, such as the dlt REST client and its paginators, may be adopted for HTTP
pagination when they leave original bytes in the raw archive. dlt pipelines that infer or evolve
schemas are not used, because contracts are authoritative.

Production Python lives below `src/kn/`. CLI parsing stays at the boundary and domain logic moves
to focused modules. Runtime artifacts resolve from `DATA_DIR` and never enter source packages.

### Replay and publication boundaries

The fetcher finalizes each permitted archive batch before the loader opens its SQL transaction.
The loader records the archive record IDs and commits the claims and cursor together. After a
crash between these steps, recovery reads the finalized batch and retries the load. An incomplete
archive file cannot advance the cursor. Curation enters at the evidence mapping step with a
reviewed locator. A review decision enters after identity resolution and cites its claim keys.

At publication, each mart row or exported fact must have supporting evidence permitted for that
audience and use. Recompute the selection using eligible evidence. A restricted source cannot
supply the winning value through an unrestricted citation. Rebuild and restore apply the current
rights decisions and tombstones before opening reader access.

| Domain | Unit of analysis | Fixture that detects a wrong join or count |
| --- | --- | --- |
| Space | Service offering in a market for a stated period and customer segment | Two offers use the same constellation. Count the constellation once and retain both offers. |
| GDELT | Document revision for provenance, story cluster for independent-story counts | Two outlets syndicate one story. Preserve both document locators and count one cluster. |
| Microelectronics | Measurement of a device configuration under a specified condition set | Two measurements share a part number and differ in power boundary. Keep both and rank only within compatible conditions. |

### Repository layout

```text
src/kn/                          core package: cli, compiler, archive, engine, semantic, export, i18n
src/kn/domains/<domain>/         reviewed domain parsers and mapping helpers
contracts/core/                  core ODCS contracts: system, semantic, evidence, export
contracts/supplemental/          approved supplemental SQL with its approval note
domains/<domain>/contracts/      domain ODCS contracts
domains/<domain>/seeds/          reviewed seed data; seeds/proposals/ holds the converted workbooks
domains/<domain>/sources/        crawler configurations, one YAML file per source
domains/<domain>/curation/       analyst-curated observation files with evidence
domains/<domain>/exports/        Obsidian export profiles
analytics/dbt/                   dbt project with one model folder per domain
analytics/dashboards/            semantic dashboard definitions and generated locale bundles
locales/en/, locales/uk/         message catalogs
deploy/                          Compose files and service configuration
generated/                       compiler output, committed and checked for drift
tests/fixtures/<domain>/<source-id>/   sanitized WARC fixtures and expected outputs
```

Runtime data, relative to `$DATA_DIR`:

```text
raw/<domain>/<source-id>/<run-id>/   WARC files of one source run, never rewritten
raw/ledger/                          Parquet fetch ledger, rebuildable from WARC files
decisions/<domain>/                  append-only review decision logs (JSON Lines)
runs/<run-id>/                       run manifests and redacted quarantine samples
exports/<profile>/<run-id>/          Obsidian vault ZIP and manifest
```

## Development and release phases

The project has two phases. The switch between them is the
[release readiness](#release-readiness) capability.

**Development phase** (from now until release approval):

- Contracts carry no version numbers. There are no migration files and no backward-compatibility
  code paths.
- Instead of a contract version, every loaded row records `contract_digest`, the SHA-256 of the
  canonical contract set, and `code_digest`, the Git commit of the parser that produced it.
- A schema change is applied with `kn db rebuild`. It drops and recreates the KN schemas from
  generated DDL, loads the reviewed seeds, and replays the raw archive, curation files, and
  decision logs through current code. Rebuild never fetches, and it does not touch the Kestra or
  Superset metadata databases.
- The raw archive, Git-managed seeds and curation files, and decision logs are the durable inputs.
  The database is a reproducible projection of them.
- Review decisions re-attach after rebuild by deterministic claim keys. A decision that no longer
  matches is reported as orphaned and is never silently dropped.
- The ontology, taxonomy, and source-catalogue "data migrations" are the idempotent seed loads
  that every rebuild runs, using deterministic identifiers.
- Rebuild is refused in an environment marked as released.

**Release phase** (after release approval):

- Contracts get semantic versions starting at `1.0.0`, and datasets record their versions.
- Schema changes go through reviewed, versioned migrations generated from the contract diff. The
  migration tool is selected by [release readiness](#release-readiness); Atlas Community Edition
  is the leading candidate. Destructive changes and incompatible releases are refused by default.
  Renames require stable field IDs and an alias plan, and changes follow
  expand -> backfill -> switch consumers -> contract.
- Seed changes become versioned data migrations.
- Rebuild stays available for disposable environments only.

## Knowledge integrity rules

These rules bind every capability and every domain.

1. **Entity types stay distinct.** Organization, program, mission, product model, physical asset,
   constellation, service, contract, filing, and document are different classes. Identifiers are
   qualified strings (namespace plus native ID). Resolution uses an exact authoritative key first,
   then a source-qualified native ID, then an alias candidate. Ambiguous matches go to review.
   Nothing merges by name alone. Split and merge history is kept.
2. **Relations stay distinct.** Legal ownership, operation, service provision and access,
   registration, launch event versus vehicle versus provider, program membership, partnership
   (MoU or LoI) versus contract or award, and filing versus licence versus deployment are separate
   relation types. Each declares allowed endpoints and minimum evidence in the ontology.
3. **Claim-level provenance.** Every claim records: origin URI, fetch time, fetch ID, native record
   locator, original value, original unit, conditions, normalized value and unit with the
   conversion rule, and the event, published, observed, valid-from, valid-to, and recorded times.
   It also records the parser code digest, the contract digest, the assertion type (declared,
   observed, derived, or reported), the extraction confidence, and the verification state
   (unreviewed, corroborated, verified, disputed, or rejected).
4. **Origin on all data.** Source-derived rows carry their origin URI and fetch time, directly or
   through a non-null evidence reference. Seed rows carry their file path, SHA-256, sheet, and row.
   Curated observations carry the cited URI, capture time, and curator. Derived and aggregated rows
   carry lineage (model, inputs, window, filter) instead of a fake per-cell citation. Origin URIs
   are stored after credential redaction.
5. **Unknown is not zero.** Each value field holds either a value or a missing reason. No zero
   defaults, no clamping, no truncation. Lack of evidence is not absence of a capability.
6. **Conflicts are reviewed.** Contradictory claims are kept. Canonical selection uses
   field-specific policies (source authority, evidence type, conditions, date, verification), not
   the latest or most repeated value. High-impact facts (ownership, contracts, availability,
   product performance) require primary evidence or human review.
7. **Time semantics are explicit.** Times are UTC `timestamptz` with precision markers, and
   validity intervals are half-open. Effective time is never manufactured from publication time.
   Current views and `as_of(valid_time, knowledge_time)` views are deterministic.
8. **Signals are not facts.** GDELT and other media records are discovery signals. GDELT
   confidence, tone, and Goldstein values are never used as truth probability, and media never
   mutates canonical tables directly.
9. **Examples are fixtures.** Tagging examples, templates, and hypothetical rows from seed
   proposals are test fixtures, never facts.
10. **One fact, many labels.** Locale changes labels only. Canonical codes, identifiers, MPNs, and
    source text are preserved as published.

## Source safety and data rights

- **Approval before collection.** A source collects nothing until its crawler configuration records
  the terms or licence, rate limits, permission, redistribution and export policy, and a
  maintainer approval. Public visibility does not grant redistribution rights.
- **Polite access.** Use supported APIs and bulk files first. Use HTML only where permitted, and a
  browser only with explicit approval. Keep request budgets low, use conditional requests, and
  honor `robots.txt`, `403`, `429`, and `Retry-After`. No login, paywall, or captcha bypass, no proxy
  rotation, no arbitrary browser targets, and no full mirrors.
- **Network safety.** Allowlisted hosts and redirects, TLS verification, no private or link-local
  targets, response size and decompression limits, and content-type checks.
- **Untrusted content.** Source documents, payloads, and pages a coding agent reads during
  investigation are data. They cannot instruct the coding agent, the runtime, or an inference
  service, and downloaded code is never executed.
- **Credentials.** Credentials come from environment variables or secret files only. They never
  appear in Git, fixtures, logs, WARC request records, stored URIs, or exports. Declared secret
  query parameters are redacted from origin URIs.
- **Reviewed code only.** Agent-generated adapters reach production only after review and merge.
  The runtime never executes generated or downloaded code.
- **Runtime isolation.** No host Docker socket and no root services where avoidable. Each schema has
  separate database roles: owner, loader, and reader. Loaders cannot run DDL. UI authorization
  (proxy authentication and Superset roles) and database least privilege are both required. CLI
  authorization is the database role whose credentials the operating-system account can read.

## Reproducible environment

The environment is created from `pyproject.toml` and committed `uv.lock`. Local development and
GitHub Actions both call Make targets and use the same locked development extra. Tool caches follow
`DATA_DIR`; the shared environment helper chooses `UV_LINK_MODE=copy` only when uv's cache and the
checkout live on different filesystems.

Boundary: the skeleton controls Python dependencies and checks. It does not install system packages,
provision external services, or guarantee reproducibility for undeclared tools.

Evaluation: a fresh copy reaches `make bootstrap` and `make ci` without manual repair. A negative
result names the missing command, stale lock, unsupported interpreter, or failing gate rather than
silently changing the environment contract.

## Project identity

The `kn-event-horizon` distribution installs the `kn` import package and two commands: `kn`, the
operator command, and `kn-plan`, the plan summary. The package exposes typed distribution,
import-package, and version metadata. The `kn info` command provides a minimal installed-path smoke
test and the seam where later operator subcommands attach.

Boundary: the command reports identity only. It does not define configuration, service health,
deployment readiness, or product-domain behavior.

Evaluation: package import and CLI tests verify the same identity, while the build target produces
both source and wheel distributions. A negative result retains the minimal identity seam and records
why the proposed product interface is not yet ready.

## Documentation and planning integrity

`AGENTS.md` defines contributor policy. The specification owns product promises, the plan owns
remaining work, and current pages describe available behavior. Task records preserve the work
contract and acceptance evidence after a task leaves the plan.

The closed-research register, `docs/impl/future-research.md`, owns research questions that were
investigated to a decision and then stopped. Each section is headed by the task id the question
carried in the plan and gives the question, the answer with links to its evidence, a reopening
condition, and the directions not to re-run. A reopening condition states what must become true,
such as a measured threshold or a change in available inputs, rather than further effort. When
reopening waits on an authorization or input, an open plan task can own that path and the section
names it. The register is not a backlog, a changelog, or a second copy of the evidence: open work
stays in the plan, available behavior in current pages, and measurements in task records.

An optional `Requires` field declares open task prerequisites across either lane. Plan summaries
skip tasks waiting on these prerequisites and rank the remaining tasks by required status, then
registry and document order. Contributors verify external or manual prerequisites from the task.

Boundary. The checks establish structural agreement. Product value, the strength of acceptance
criteria, completion evidence, and external prerequisites require contributor judgment. The
register check sees section headings, parts, and task references. Whether a reopening condition is
a number or a change in the world, and whether a direction is closed by measurement rather than by
budget, stay reviewer judgment. The register is history by design, so the plan's forward-language
check does not apply to it.

Evaluation. Fixtures exercise broken links, unknown capabilities, missing fields, wrong lanes,
invalid order, unknown and cyclic prerequisites, and scheduling across lanes. A malformed plan
fails with actionable diagnostics and the summary withholds scheduling suggestions. A valid plan
can report that every task in a lane is waiting. Register fixtures reject malformed headings,
closed questions that are still open tasks, missing or empty parts, and reopening tasks that are
not open. An empty register and a complete register pass. A research task that closes negative
meets its gate when its record holds the evidence and its register section states what would
reopen the question.

## Product capabilities

Each capability below states its behavior, boundary, evaluation, and valid negative result. The
[capability registry](#capability-registry) orders them.

### Runtime platform

A Compose stack pinned by image tag and digest. The first service is PostgreSQL with PostGIS,
running database `kn` with schemas `system`, `semantic`, `evidence`, one schema per domain, and
`analytics`. Later services are added by their capabilities: Kestra (orchestration), Superset and
Redis if its profile requires it (space dashboards), the reverse proxy (operations hardening), and
the optional inference server (AI extraction). Volumes live under `DATA_DIR`, services have
healthchecks, networks are internal, and no database port is published. Secrets come from a local
`.env` or secret files that are never committed. Role bootstrap creates owner, loader, and reader
roles per schema. A version manifest records every pinned image, schema, and tool. Integration
tests run against the Compose database locally and against a PostGIS service container in CI.

Boundary: a single host, not high availability. No Kubernetes and no managed cloud services.

Evaluation: from empty volumes, `make db-up` reaches healthy, and a restart preserves data. No
database port is reachable from outside the Compose network, and no default production password
exists. Integration tests pass locally and in CI.

Negative result: a version conflict is recorded in the manifest with the compatible fallback chosen.
Floating `latest` tags are never used.

### Localization

Every delivered user-facing and operator interface supports English (`en`) and Ukrainian (`uk`; the
code is never `ua`). This covers operator controls, validation errors, statuses, chart titles,
legends, tooltips, dashboard descriptions, exports, and user documentation. Engineering artifacts
(code, contracts, identifiers, logs, `AGENTS.md`) stay English.

- Message catalogs with stable keys live in `locales/`. The CLI takes `--locale en|uk` or
  `KN_LOCALE`. Machine-readable JSON output keeps stable keys and codes.
- Formatting uses CLDR plural rules and locale-aware numbers and dates. Machine data uses ISO
  formats. Times display in UTC by default, with optional `Europe/Kyiv`. Text is UTF-8 end to end.
- Vocabulary and entity labels are stored per locale with translation provenance. Originals are
  preserved, and facts are never duplicated per locale.
- Superset enables `en` and `uk`. Dashboards are generated as locale twins from one semantic
  definition over the same datasets and metrics. Obsidian exports produce one locale per vault.
- **Kestra waiver.** On 2026-11-20 the owner approved Kestra's native UI as an English-only
  engineering and administration tool behind the authenticated proxy. Every operator workflow
  (source status, run, retry, backfill, review queue, export) must be available bilingually
  through the `kn` CLI and Superset dashboards. Exposing any other upstream English-only screen to
  operators needs a new approval.
- A Ukrainian technical speaker reviews the core terminology before release.

Boundary: no runtime commercial translation service. Source text stays in its original language,
and machine translation is optional derived text (see [AI extraction](#ai-extraction)).

Evaluation:

- CI fails when a key is missing in either locale, a key is unused, or a CLI handler contains a
  user-facing literal string.
- Plural and formatting tests pass for both locales.
- CLI golden outputs exist in both locales.
- Browser screenshot smoke tests in both locales cover dashboards, filters, the map, the review
  queue, and the export README.

Negative result: when a pinned Superset `uk` catalog misses critical strings, a pinned overlay
catalog fills them. If that is impossible, the screen is recorded as a release blocker. Core
product UI never falls back to English silently.

### Data contracts

ODCS v3 contracts, with the exact minor version and JSON Schema checksum pinned by the toolchain
task. The official current version at review time was v3.1.0. Contracts define every stored
dataset. KN semantics use ODCS `customProperties` with documented `kn.*` names, validated against
KN extension JSON Schemas. No top-level keys are added to ODCS. The extension families are:

| Extension | Required behavior |
| --- | --- |
| `kn.entityClass`, `kn.relation` | Resolve against the ontology; compile references and endpoint validation |
| `kn.fieldId`, `kn.identity` | Stable logical field identity, external key definition, identity strategy |
| `kn.units`, `kn.comparisonProfile` | Original and normalized unit, quantity type, conversion rule, comparison gate |
| `kn.temporalProfile` | Event, published, observed, valid, and recorded times; as-of behavior; null semantics |
| `kn.spatialProfile` | Geometry type, SRID 4326, precision and coverage semantics, validity |
| `kn.evidence`, `kn.licensePolicy` | Evidence requirements, assertion type, rights and export restrictions |
| `kn.enumRef`, `kn.vocabularyRefs` | Controlled vocabulary and allowed tag schemes |
| `kn.index`, `kn.partition` | Reviewed physical design intent rendered as generated DDL |
| `kn.i18nKey` | Stable display key resolved through the message catalogs |
| `kn.lineageRefs` | Declared datasets and mappings, not observed runtime lineage |

The compiler (`kn contract lint|compile`) validates contracts against the pinned schema and the
extension schemas. It checks references to ontology classes, vocabulary schemes, and field IDs, and
produces a canonical serialization and a digest. It generates PostgreSQL DDL, Pydantic models and
JSON Schema for load validation, dbt source definitions, and contract documentation into
`generated/`. Data Contract CLI exports are used where they cover a feature; reviewed templates fill
PostGIS geometry, check constraints, comments, and indexes. Supplemental SQL (extensions, roles,
grants, functions) lives in `contracts/supplemental/` and needs an approval note. No handwritten DDL
may redefine a contract, and nothing alters schemas at runtime.

Boundary: not a general schema registry; no schema editing through a UI or a crawler. Data Contract
CLI is a pinned build-time tool, not a runtime dependency.

Evaluation:

- Valid contracts compile byte-identically twice.
- A missing required field, an unknown extension, or a broken reference fails with an actionable
  diagnostic.
- Generated drift fails CI.
- `kn db rebuild` from empty creates every schema.
- A loader role cannot execute DDL.

Negative result: when the exporter cannot express a required ODCS feature, compilation fails or a
narrow, tested template fills the gap. A contract is never changed to fit a lossy exporter.

### Ontology and taxonomy

The ontology and taxonomy are data held in the `semantic` schema. Core contracts define the
meta-model (see [Data contracts](#data-contracts)), and reviewed seed files supply the content.
Meta-model datasets:

- namespace;
- entity class: domain-qualified, with parent, definition, and per-locale labels;
- relation type: allowed source and target classes, cardinality, minimum evidence, inverse label,
  and the common errors it guards against;
- concept scheme: origin (`official`, `kb_normalized`, `kb_extension`, `service_extension`, or
  `native`), publisher, edition, source URI, and verification state;
- concept: code as a string, parent, per-locale labels, and status (`draft`, `active`,
  `deprecated`, or `replaced`, with a replacement);
- concept mapping: `exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`, or
  analyst crosswalk, with method and evidence;
- entity tag: entity, concept, method, evidence, status, and validity;
- attribute definitions, observation condition sets, comparison profiles, and analyst rubrics
  (used by microelectronics).

How seed content moves:

- The converted workbooks in `domains/<domain>/seeds/proposals/` are inputs to a reviewed import.
  The import writes reviewed seed files in `domains/<domain>/seeds/` and a reconciliation report
  that classifies every proposal row as `accepted`, `duplicate`, `needs_mapping`, or `rejected`,
  with a reason.
- Every rebuild loads the reviewed seed files with deterministic identifiers.
- Tagging examples and templates become fixtures. Unknown tags proposed by sources become pending
  suggestions, never automatic additions.
- All identifiers are qualified by domain and scheme. The proposals reuse `S01`-`S17` (space),
  `S01`-`S14` (microelectronics), and `S01`-`S13` (GDELT) with different meanings. `APP.*` means
  different things in GDELT and microelectronics.
- Relation names and directions are normalized, with inverse labels. The space proposal mixes
  `operates` with `operated_by`, and `member_of_constellation` with `contains_spacecraft`.
- Official schemes stay `unverified` until checked against the official publication (edition, URI,
  and checksum). These include ESA Generic Product Tree Issue 1 Rev 1, ESA Technology Tree v4.1
  (STM-277), the NASA 2024 Technology Taxonomy, EUSPA EU Space Market Report 2026 segments, ECS
  SRIA 2026, OECD "Chips, nodes and wafers" Figure 9, and the GDELT CAMEO, GKG theme, and GCAM
  lookups.
- Analyst extensions are never presented as official. The GDELT and some space schemes in the
  proposals are explicit subsets, never complete dictionaries.

SKOS Turtle export per scheme (`ConceptScheme`, `Concept`, `prefLabel` with language tags,
`altLabel`, `broader`/`narrower`, `notation`, `definition`, and mappings) is generated for
interchange. SKOS cannot enforce typed relations, so the meta-model enforces them.

Validation: unique identifiers; one preferred label per language per scheme; no cycles in a
primary hierarchy; parents exist; mappings don't conflict; relation endpoints exist; deprecated
concepts stay resolvable. A content change is a reviewed edit to a seed file followed by a rebuild
(development) or a data migration (release).

Boundary: no OWL reasoning, and no taxonomy editing in a UI. The structural rules (see
Validation) are enforced in code, not by SKOS.

Evaluation:

- Importing all five proposal sets classifies every row.
- Identifiers are identical across runs.
- Fixtures with a cycle, a missing parent, a duplicate label, an identifier collision, or an
  unknown relation endpoint are rejected.
- The SKOS export parses with RDFLib and round-trips its labels.

Negative result: unmappable rows stay `needs_mapping`. A scheme whose official source cannot be
verified stays `unverified` and is labeled so in every interface.

### Raw archive

Payloads approved for retention are written once as WARC 1.1 (ISO 28500:2017), gzip per record,
via `warcio`. Each source run gets its own directory, `$DATA_DIR/raw/<domain>/<source-id>/<run-id>/`.

- A request record is written with credential headers removed.
- A response record holds the status, headers, and the exact payload.
- A metadata record carries the run ID, crawler configuration digest, and code digest.
- Curated evidence captures and manual source files become resource records.

Every record carries `WARC-Target-URI` (the redacted origin URI), `WARC-Date` (fetch time in UTC),
`WARC-Payload-Digest`, and `WARC-Record-ID`. A response identical to the previous one for the same
request is written as a `revisit` record. Files are written to a temporary name, synced, and
renamed.

The Parquet fetch ledger under `$DATA_DIR/raw/ledger/` indexes each record: fetch ID, run, domain,
source, origin URI, fetch time, status, MIME type, payload SHA-256, size, and WARC path and offset.
`kn raw reindex` rebuilds it from the WARC files, and `kn raw verify` checks digests. Retention
follows the source's policy. Deleting a record writes a tombstone with reason and hash, and claims
that cite it are marked `evidence_tombstoned`. Keep tombstones among the durable inputs with
the affected record IDs, including revisit references. Reindex must reconstruct the ledger after
payload removal without treating an intentional deletion as archive corruption.

Boundary: no replay UI and no storage of unselected bulk files (for example, unfiltered GDELT
dumps). Fixtures are sanitized WARC excerpts committed under `tests/fixtures/`.

Evaluation:

- A write and read round trip preserves payload bytes and digests.
- An interrupted write leaves no visible partial file.
- Reindex reproduces the ledger exactly.
- Redaction tests show no credential in records or URIs.
- Revisit deduplication works.
- `verify` detects corruption.

Negative result: when WARC is unsuitable for a source shape, such as a very large bulk file, the
crawler configuration declares `raw_format: blob`. The bytes are then stored content-addressed with
the same ledger fields, and the reason is recorded.

### Evidence model

Core and domain contracts define:

- entity (UUID, class, canonical label, lifecycle);
- external ID (namespace plus native ID, unique within its domain);
- alias (language and normalized key; not unique);
- claim: immutable, holding the [integrity-rule](#knowledge-integrity-rules) fields plus
  `supersedes`;
- evidence: fetch ID, origin URI, fetch time, locator (JSON pointer, row, page, or offset), excerpt
  only when licensed, rights, and code and contract digests;
- relation assertion: subject, relation type, object, qualifiers, validity interval, evidence, and
  review state, with no active duplicates;
- canonical fact: the selected claim, the policy that selected it, and its intervals, held as a
  projection;
- review item: candidates, conflicts, and quarantine, with append-only decisions recording
  reviewer, reason, and time.

Domain tables extend entity with strictly typed attributes for frequently queried facts. Each
selected value links to a claim. Condition-dependent metrics use bounded observation tables keyed
by approved field IDs and condition sets, not a generic entity-attribute-value store.

Claim keys are deterministic, so re-running the same raw record with the same code creates no
duplicates. Fact selection follows [rule 6](#knowledge-integrity-rules), and unresolved fields stay
null or conflicted with a reason. `kn review list|decide` is bilingual. Each decision is appended to
the decision log and replayed by rebuild.

In the first release, an analyst can open "Why this fact?" from a canonical value in any domain
dashboard. The view preserves the dashboard snapshot and shows the selected value and unit, the
selection rule and reason, supporting source and locator, permitted competing claims, and the
applicable review decision. For unresolved fields it shows the conflict or missing-data reason.
Both locales read the same rights-filtered analytics projection as the displayed fact.

Boundary: no automatic truth from repetition or media volume. Cross-domain links between separate
entities are reviewed candidates, never merges.

Evaluation:

- Fixtures distinguish organization, model, spacecraft, constellation, program, and service.
- Two aliases resolve to one entity only with evidence.
- A contradictory ownership claim is kept, not merged.
- Event, observation, and effective times stay separate.
- A provenance lookup returns the native locator, origin URI, fetch time, code digest, and contract
  digest.
- A rerun creates no duplicates, and decisions survive a rebuild.

Negative result: a field with no defensible selection policy stays conflicted with its reason
recorded. The model never picks a winner arbitrarily.

### Source management

Sources are managed in two layers.

1. **Source catalogue (data).** Every candidate source in the seed proposals is loaded into
   `system.source_catalogue` by rebuild: 37 space, 65 microelectronics, and 17 GDELT rows. Each
   keeps its original identifier, priority, cadence, and access notes, which stay marked
   unverified. Lifecycle states are `candidate`, `investigating`, `sampling_authorized`,
   `approved`, `enabled`, `paused`, `retired`, and `rejected`. The catalogue lists sources and
   never enables them.
2. **Crawler configuration (Git, reviewed).** One YAML file per runnable source,
   `domains/<domain>/sources/<source-id>.yaml`, validated by a JSON Schema. Mapping, error
   handling, and monitoring are declared here. Code covers only parsing the configuration cannot
   express. The blocks are:

| Block | Content |
| --- | --- |
| identity | Catalogue reference, labels in `en` and `uk`, owner |
| access | Method (`http_json`, `http_csv`, `http_xml`, `feed`, `bulk_file`, `curated_file`, `html_permitted`), endpoints, allowed hosts, redirect policy, auth environment alias, request budget, rate limits, conditional requests |
| schedule | Cron in UTC, freshness threshold (default twice the schedule interval) |
| cursor | `snapshot_hash`, `updated_since`, `id_range`, or `window` with overlap; separate backfill namespace |
| raw | Format (`warc` or `blob`), retention, redistribution |
| parse | Parser entry point under `kn.domains.<domain>`, native schema or codebook edition, schema fingerprint |
| mapping | Native field -> contract field ID; units; native code -> concept with mapping type; class and relation mapping; identity keys; time-field semantics |
| quality | Required fields, ranges, expected volume, quarantine limit, batch-stop conditions |
| errors | Source conditions -> standard error codes and retry class |
| monitoring | Freshness SLA, alert thresholds, expected record counts |
| rights | Terms URI, reviewer and review time, licence, export policy, retention |
| approval | State, approver, approval reference |

`kn source validate` refuses an enabled configuration that lacks a rights review, an approval
reference, fixtures, or passing tests. Standard error codes include `transient_network`,
`rate_limited`, `auth_failed`, `permission_denied`, `not_modified`, `payload_invalid`,
`schema_drift`, `integrity_lost`, and `budget_exhausted`. Each has a retry class, and permanent
errors are never retried.

**Onboarding workflow** (coding-agent investigation, then implementation):

1. The agent builds a terms dossier from documentation only: terms, licence, rate limits, native
   schema or codebook, edition, cadence, and redistribution.
2. The owner authorizes bounded sampling (a human-lane task).
3. The agent captures a sample within a declared request budget into the raw archive and writes an
   investigation report: native keys, gaps, proposed mappings, and risks.
4. The agent writes the crawler configuration, parser, sanitized fixtures from the captured WARC,
   and tests. Engine changes this source needs go into the core with tests, and every earlier
   source's suite is rerun.
5. Review and merge.
6. The owner approves enablement (a human-lane task).
7. Scheduled runs begin.

Status monitoring covers, per source: last success, last attempt, state, a stale flag, record,
claim, reject, and quarantine counts, bytes, requests used against the budget, cursor lag, and the
last error code. It is available through `kn source status` and the operations mart.

Boundary: no generic web crawler, no discovery beyond allowlisted scope, and no source enabled
from a catalogue row alone.

Evaluation:

- The catalogue import loads every proposal row.
- The schema rejects an enabled configuration without rights and approval.
- Error-code mapping tests cover every code.
- Status figures computed from run fixtures match expectations.

Negative result: a source whose terms or permission cannot be confirmed stays `candidate` or
becomes `rejected` with the reason. Scraping never substitutes for it.

### Ingestion engine

Each run executes these steps:

1. Take an advisory lock per source and scope, and register the run.
2. Discover requests.
3. Fetch into WARC, or read from the archive in replay.
4. Parse native records with locators, and check the native schema fingerprint.
5. Map them to candidate entities, claims, relations, and tags through the crawler configuration.
6. Validate against the compiled models and the ontology rules.
7. Resolve identities.
8. Load in one transaction with the checkpoint, record quality results, and write a run summary.

Run statuses are `success`, `partial`, `not_modified`, `blocked`, `failed`, and `skipped`. A run with
incomplete or invalid data is never `success` without a recorded reason. Quarantine works per
record. A batch stops when key, time, or schema integrity is lost. Partial successes are kept.
Watermarks never advance past an unprocessed interval, and backfill uses its own cursor namespace.
Delivery is at least once with idempotent effect.

Commands: `kn source run` (fetch and transform), `kn source replay` (transform from the archive
only), and `kn db rebuild` (everything). Adapters return records and claims. They never run DDL or
write outside the engine loader.

Parsers are chosen in this order: structured API, CSV, JSON, XML, and feeds first; permitted HTML
tables and JSON-LD second; a browser only with approval; document extraction last.

The curated source method reads analyst-curated observation files from
`domains/<domain>/curation/`. Each row carries its cited URI, capture time, and curator, and a WARC
capture of the cited page is stored where that is permitted. The rows go through the same mapping
and validation. This method is required where no permitted machine-readable source exists, such as
tariffs, coverage statements, and operator disclosures.

**TDD growth rule.** The engine starts as a skeleton proven on a synthetic fixture source. Each real
source then adds failing fixture tests first, then the general engine change that makes them pass.
The core never branches on a source ID. On every change, CI runs all source fixture suites plus a
full rebuild from the fixture archive. Logs are structured English JSON with secrets redacted, and
user-facing messages are localized.

Boundary: no exactly-once network claim, and no per-source special cases inside the core.

Evaluation:

- A rerun after an interrupted run resumes from the committed checkpoint without duplicates.
- A bad row, a malformed response, `429`, partial pagination, a schema change, and an unavailable
  source each produce the declared status, with no cursor jump and with secrets redacted.
- Existing good facts are kept and marked stale.
- Two rebuilds produce identical canonical tables by row hash.

Negative result: when a source cannot be expressed by configuration plus a parser, the engine gains
a general mechanism with tests, or the source stays disabled.

### Obsidian export

`kn export obsidian --profile <id> --locale en|uk` writes a read-only, allowlisted subset of
canonical knowledge as a ZIP that opens as a vault without plugins. Profiles in
`domains/<domain>/exports/` select:

- domain, entity classes, primary classification, and tag filters;
- time window and allowed statuses and fields;
- link depth, entity and byte limits, and evidence detail;
- attachments and locale.

The export reads one `REPEATABLE READ` snapshot of database `kn` with an explicit as-of time.
By default it includes only accepted, export-permitted facts. Unverified candidates go in a
separate folder only when the profile opts in.

Notes:

- Note paths are stable, derived from immutable IDs and not from localized names.
- Frontmatter is flat YAML. Relations are labeled wikilinks.
- Targets outside the selection become explicit references, not broken links.
- Source and evidence notes carry URI, publisher, date, and rights.
- Pipes and unsafe HTML are escaped, and executable content is never written.
- Path normalization blocks traversal and reserved names.

`manifest.json` records the profile hash, locale, snapshot and watermarks, counts, excluded counts,
file hashes, contract digest, and generator digest. The vault is written to a temporary directory,
its links and hashes are verified, and it is zipped atomically. The same snapshot, profile, and
locale produce identical content hashes.

The default limit is 5,000 entities or 100 MB. An oversized selection is rejected, and an export
is never partial. Exports never overwrite an existing vault and never write back. Credentials, raw
caches, private URIs, and content not licensed for redistribution are always excluded.

Boundary: no synchronization, no Obsidian plugin, and no export server.

Evaluation:

- A fixture profile produces a ZIP whose manifest hashes verify.
- Every internal link resolves or is an explicit reference.
- Locale labels are correct.
- Restricted rights are excluded, and secrets and traversal are absent.
- A repeated export is logically identical.

Negative result: a profile that cannot stay within limits or rights is refused with a localized
explanation.

### Space ELT

The space domain package, with the global SATCOM awareness pilot. The [space design](domains/space.md)
defines its contracts, rules, and sources. Sources are onboarded in this order:

1. CelesTrak GP (OMM JSON) for catalog identities and snapshot counts.
2. Launch Library 2 for agencies, launcher configurations, launch events, and pads.
3. Natural Earth for reference country boundaries.
4. Operator disclosures, through the curated method, for at least two of Starlink, Eutelsat
   OneWeb, SES O3b mPOWER, and Telesat Lightspeed.

Account-based or regulatory sources (Space-Track, ESA DISCOS, UNOOSA, ITU Space Explorer) are
optional refinements. Other catalogue sources stay candidates for later onboarding through the same
workflow.

Boundary: public, aggregate awareness only. No real-time tracking, no orbit-derived coverage or
availability, no address-based availability checks, and no private pricing endpoints.

Evaluation:

- Permitted live samples exist for launches, a catalog snapshot, and at least two provider
  disclosure scopes.
- Planned and actual launches, cataloged and operational spacecraft, and declared and planned
  counts are never conflated.
- Tariff comparisons keep recurring and one-time amounts, country, currency, customer class, tax
  basis, and date separate.
- Unknown values display as unknown.
- A rebuild from the archive reproduces the domain.

Negative result: an inaccessible source gets a documented blocker and either an approved substitute
or an explicit deferral. Data is never invented to pass a test.

### Orchestration

Kestra OSS runs standalone with a PostgreSQL backend in its own `kestra` database. It uses the
Process task runner inside a dedicated non-root image that contains the pinned `kn` package and
runs `kn source run`. No host Docker socket is mounted.

Flows are generated from enabled crawler configurations: namespace `kn.<domain>`, flow ID equal to
the source slug, cron in UTC, concurrency 1, and retries only for transient error classes. They are
deployed through the Kestra API with scoped credentials, and a check detects drift. dbt refreshes
are debounced. The engine stays fully usable without Kestra through the CLI. Kestra's UI is covered
by the approved [Kestra waiver](#localization).

Boundary: Kestra metadata is never a business data model, and no flow runs shell built from
external input.

Evaluation:

- Flow generation is deterministic.
- A scheduled run over a declared window records correct statuses within request budgets.
- A worker killed mid-run retries without duplicates.
- A restart resumes from the committed checkpoints.

Negative result: when the pinned Kestra release lacks a working Process runner, a dedicated
constrained worker service takes its place. The Docker socket is still never mounted.

### Space dashboards

dbt models build the `analytics` marts listed in the [space design](domains/space.md#analytical-marts),
including `data_freshness`, `run_quality`, and `fact_evidence_lookup`. Superset reads only
`analytics` through a read-only role. SQL Lab is restricted to permitted schemas, with timeouts and
row limits enforced by database roles independent of UI settings.

Dashboards are code. A semantic definition generates locale twins (`en` and `uk`) with stable UUIDs
over the same datasets and filters, and a drift check compares exports with the generated bundles.

The dashboards are:

- Global SATCOM Overview;
- Service and Tariff Comparison;
- Market Coverage and Availability (map);
- Launchers, Launches and Satellite Models;
- Acquisition and Operations (source status, freshness, run quality, review queue).

[GDELT dashboards](#gdelt-dashboards) later adds the technology watch section. Every business
dashboard shows freshness and staleness. Maps use validated PostGIS GeoJSON and work without a paid
or external basemap.

Boundary: no custom BI frontend, and no hidden manual-only dashboard state.

Evaluation:

- Bundles deploy reproducibly in both locales with identical filter results.
- Point and MultiPolygon layers render with real licensed boundaries and labeled observations, and
  tooltips show source and time.
- Date filters change rows.
- SQL Lab cannot read `raw`, `evidence`, or restricted data.
- Screenshots in both locales show Cyrillic, missing-value labels, and freshness.

Negative result: if a Superset chart cannot render mixed layers, synchronized per-layer charts
replace it. If polygons cannot render, map acceptance is blocked and the chart choice goes to the
owner.

### GDELT ELT

GDELT is a discovery layer; see the [GDELT design](domains/gdelt.md). The full official
dictionaries (CAMEO event codes, actor types, countries, GKG themes, GCAM codebook) are imported as
sources with edition and checksum. The proposal workbook holds only subsets of them. DOC 2.0 API
watch manifests, with `en` and `uk` aliases, cover approved space and microelectronics technology
topics.

Queries split time windows when a result cap is reached, record truncation, deduplicate by
normalized URL, and keep metadata and permitted excerpts only. Candidate links to space and
microelectronics entities go to review. Selective GKG, Events, and Mentions import from the
15-minute files, filtered by watch criteria, is an optional refinement. BigQuery is used only with
an explicit budget approval.

Boundary: no full archive mirror, no claim of exhaustive coverage, and no paywalled full text. News
never updates truth, ownership, or lifecycle automatically.

Evaluation:

- Fixture and approved live-smoke queries handle pagination and truncation.
- Signals stay unverified, with their original source and native field semantics.
- Coverage statistics name the watch filters, the window, and missing intervals.

Negative result: if the current DOC API limits make a watch unusable, the limitation is recorded and
the watch is narrowed, or the optional selective file import is used instead.

### GDELT dashboards

The `technology_signal_daily` mart (date x domain x topic x unique source document) and the
technology watch section of the acquisition dashboard, in both locales. They label the monitored
sample and the review state of candidate links.

Boundary: no global event-frequency claims. Volume charts state their denominator and watch scope.

Evaluation: dashboard bundles deploy in both locales. Signal counts match fixture expectations, and
syndicated duplicates are counted once per story cluster.

Negative result: a metric whose denominator cannot be established is not shown.

### Microelectronics ELT

Low-power sensing, compute, FPGA, edge AI, power, and RF. Prospective technology comes first, with
product baselines in parallel; see the [microelectronics design](domains/microelectronics.md).

- Products, families, models, MPNs, dies, IP blocks, and development kits are typed separately.
- Condition-bound observations follow the attribute dictionary and comparison profiles.
- Legal manufacturer, design location, wafer fab, assembly and test site, and parent ownership are
  separate facts.

The first sources are structured: MLPerf Tiny results, then CORDIS project datasets, then curated
vendor datasheet observations for the watchlist families.
The [target-market policy dimension](domains/microelectronics.md#target-market-policy) adds
dated, cited trade and export-control information alongside technical comparisons. Selecting a
market changes the policy detail only. Technical rank, score, and membership depend solely on
the comparison profile and its measurement conditions.

Boundary: no ranking on headline TOPS, and no origin inferred from headquarters. An announcement is
not availability.

Evaluation:

- MPN identity requires the legal manufacturer and the exact MPN.
- A record with unknown required comparison fields is excluded from matched ranking but stays
  visible.
- Units and conditions round-trip.
- Benchmark versions and power boundaries are kept.

Negative result: a profile whose required conditions no source supplies stays unranked with the
missing fields listed.

### Microelectronics dashboards

Bilingual comparison dashboards that compare only matched condition sets, a technology scouting
view that shows the analyst rubric as an editable policy (not a prediction), and the technology
watch.

Boundary: no ranking across comparison groups, and no comparison of advertised peak values against
measured results without a label.

Evaluation: bundles deploy in both locales. Fixtures prove that incomparable records never share
a ranking.

Negative result: a comparison that cannot be matched is shown as a list of candidates with their
missing conditions.

### Operations hardening

- **Access.** A reverse proxy with TLS and authentication fronts Superset and Kestra on a private
  network. Superset roles are `analyst_read`, `dashboard_author`, and `admin`.
- **Backups.** Nightly compressed per-database backups plus globals, the raw ledger and changed WARC
  files, decision logs, and Git release artifacts. Copies are kept for 7 days daily and 4 weeks
  weekly. Proposed objectives are RPO <= 24 h and RTO <= 8 h, validated by a restore drill. An
  off-host encrypted destination is required beyond development.
- **Disk.** Logical quotas over 4,000 GB:

| Use | GB |
| --- | ---: |
| PostgreSQL data and WAL | 1,200 |
| Raw archive | 1,000 |
| Export, cache, temp | 200 |
| Local rolling backups | 600 |
| Images, models, logs | 300 |
| Free reserve | 700 |

Non-essential ingestion stops at 80% usage, and non-critical writes stop at 90%.

- **Memory.** Starting budgets at 32 GB, to be replaced by measurements:

| Service | Budget |
| --- | --- |
| PostgreSQL | 9 GB |
| Kestra | 4 GB, JVM capped near 2 GB |
| Superset web | 3 GB |
| Redis | 0.5 GB, if required |
| Superset worker (optional) | 2 GB |
| Proxy | 0.25 GB |
| On-demand tools | 2-3 GB |
| Optional inference | 4-6 GB host RAM |
| OS reserve | at least 5 GB |

  Heavy jobs (dbt, export, inference, document extraction) never run concurrently when their
  measured sum breaks headroom.

- **Performance.** On the target server, with 50k catalog rows, 100k article rows, and 1M
  observations, a warm aggregated dashboard and a map of up to 5k features each reach p95 <= 5 s,
  with 2 readers and 1 ingest running. Ingestion stays bounded with no out-of-memory failure.
- **Security.** The suite proves:
  - schema isolation between domains;
  - no DDL by loaders;
  - denied restricted facts and unauthorized users;
  - secrets absent from logs and ZIPs;
  - SSRF, archive-traversal, and decompression-bomb limits.

Boundary: no high availability and no promise of zero downtime.

Evaluation: a restore into an isolated instance passes hash, constraint, and dashboard checks with
the achieved RPO and RTO recorded. The performance and security suites pass on the target host.

Negative result: an objective that is not met is recorded with its measured value. The owner then
adjusts the objective or the hardware.

### Release readiness

The owner approves a release scope, which by default covers the core engine, all three domains'
ELT and dashboards, Obsidian export, localization, and operations hardening.

- **Migration tool.** Selected by a bounded comparison against the contract diff. Atlas Community
  Edition is the leading candidate; supplemental SQL stays versioned.
- **Baseline.** Contracts are baselined at `1.0.0`, and dataset version recording begins.
- **Switch.** The environment is marked released, which refuses rebuild.
- **Checklist.** Every capability's evaluation has evidence.

Boundary: no compatibility promises before this switch.

Evaluation: migrating an empty database and a `1.0.0` -> `1.1.0` additive change preserves records,
identifiers, and provenance. A breaking change without a migration plan is refused. Drift is
detected. Rebuild is refused in the released environment.

Negative result: if no candidate tool handles the generated DDL safely, migrations are written from
reviewed templates and the gap is recorded.

### AI extraction

An optional local `llama.cpp` server with CUDA under the Compose `gpu` profile proposes candidate
claims and translations from permitted text. The model and quantization are chosen by benchmark
and licence within the measured 16 GB VRAM. Prompts and schemas are versioned in Git, and the model
digest, prompt revision, and settings are recorded.

The service has no tools, network, SQL, secrets, or write access. Its output is validated for type,
unit, source span, and uncertainty. Critical facts need human review. Translations are derived text
with provenance, and the original is kept.

Boundary: never a truth authority, DDL engine, or orchestration agent. The CPU path and all
structured ingestion work without it.

Evaluation: against manually labeled fixtures, precision, recall, coverage, and hallucinated-evidence
counts are reported, with zero unsupported published claims. Ingestion is unaffected when the
service is down.

Negative result: a model that cannot meet the gate within the VRAM budget is not enabled.

## Capability Registry

Every product capability appears here exactly once. Status is `planned` when the capability is
specified and has open plan work, or `shipped` when current-state documentation describes its
available implementation. Capabilities that the starter template provides are described in the
[contributor guide](../guide/README.md) instead, so the current-state area holds only this
project's own product behavior. A shipped capability may still have optional extension work.

Row order is the implementation line. Hard dependencies come first, then work that changes another
capability's evaluation inputs, then required work before capabilities with only optional work, then
upstream before downstream.

| # | Capability | Status | How it is evaluated | Implementation |
| --- | --- | --- | --- | --- |
| 1 | `reproducible-environment` | shipped | A fresh locked environment reaches the complete CI gate without manual repair | [Development guide](../guide/development.md) |
| 2 | `project-identity` | shipped | Import, CLI, and distribution-build tests agree on the `kn-event-horizon` identity | [Product core](../impl/current/product-core.md) |
| 3 | `documentation-integrity` | shipped | Link, registry-plan, task-lane, metadata, ordering, prerequisites, forward-language, and closed-research register checks pass over fixtures and the repository tree | [Documentation checks](../guide/development.md#documentation-checks) |
| 4 | `runtime-platform` | planned | Pinned Compose database reaches healthy from empty volumes, keeps data across restart, exposes no port, and serves integration tests locally and in CI | - |
| 5 | `localization` | planned | Key coverage, plural, golden-output, and screenshot checks pass in `en` and `uk`; the Kestra waiver is the only English-only path | - |
| 6 | `data-contracts` | planned | Contracts compile deterministically, invalid contracts fail, drift fails CI, rebuild creates every schema, loaders cannot run DDL | - |
| 7 | `ontology-taxonomy` | planned | Every proposal row is classified, identifiers are stable, invalid hierarchies are rejected, SKOS round-trips | - |
| 8 | `raw-archive` | planned | WARC round trip, atomic write, ledger reindex, redaction, revisit, and corruption checks pass | - |
| 9 | `evidence-model` | planned | Identity, conflict, time, provenance-lookup, idempotence, and decision-replay fixtures pass | - |
| 10 | `source-management` | planned | Catalogue import is complete; configuration validation refuses unapproved enablement; error and status mapping fixtures pass | - |
| 11 | `ingestion-engine` | planned | Failure-mode fixtures yield declared statuses without cursor jumps; two rebuilds produce identical canonical tables | - |
| 12 | `obsidian-export` | planned | Fixture vault verifies hashes and links, excludes restricted rights and secrets, and reproduces identically | - |
| 13 | `space-elt` | planned | Permitted live samples load; launch, catalog, count, and tariff semantics are never conflated; rebuild reproduces the domain | - |
| 14 | `orchestration` | planned | Generated flows are deterministic; a scheduled window respects budgets; killed runs retry without duplicates | - |
| 15 | `space-dashboards` | planned | Bilingual bundles deploy reproducibly with equal filter results; maps render licensed boundaries; SQL Lab stays read-only | - |
| 16 | `gdelt-elt` | planned | Dictionaries carry edition and checksum; DOC queries handle caps and truncation; signals stay unverified | - |
| 17 | `gdelt-dashboards` | planned | Watch dashboards deploy in both locales with stated denominators and story-level counts | - |
| 18 | `microelectronics-elt` | planned | MPN identity, condition-bound observations, and matched-comparison exclusion fixtures pass | - |
| 19 | `microelectronics-dashboards` | planned | Bilingual comparison bundles never rank incomparable records | - |
| 20 | `operations-hardening` | planned | Restore drill, performance gate, and security suite pass on the target host with measured objectives | - |
| 21 | `release-readiness` | planned | Migration mode preserves data, refuses breaking changes and rebuild, and every evaluation has evidence | - |
| 22 | `ai-extraction` | planned | Labeled fixtures show zero unsupported published claims within the VRAM budget; ingestion is unaffected without it | - |

## Extending This Specification

A capability gap is a product discovery, not an automatic refusal and not permission for silent
scope growth. Use this lifecycle in order:

1. State the problem in operator or domain terms.
2. Amend the owning section of this specification, including what the capability does not do.
3. Declare the measurement, acceptance signal, and valid negative result before implementation.
4. Add a `planned` registry row with that evaluation.
5. Put tasks under the capability in the implementation line; every task declares `Serves`.
6. Build and evaluate, document available behavior under current state, remove finished plan scope,
   and change the registry row to `shipped` with its implementation link. Follow the
   [completion workflow](../guide/planning-workflow.md#completion-transition) for the evidence and
   dependency handoff.

When implementation reveals that an existing capability has the wrong boundary, update its section
instead of creating an implementation workaround that the specification cannot explain.

## Specification and plan integrity

The registry and [implementation plan](../impl/plan.md) are two views of one product. The executable
contract requires:

- every task serves a registered capability and sits in its capability group;
- every capability declares an evaluation;
- every planned capability has at least one open task;
- every shipped capability links to its current-state documentation, or to the contributor guide
  when the template provides it;
- groups follow registry order in each task lane;
- every task declares the required outcome, boundary, execution, and acceptance fields;
- lane statuses match whether an agent can finish independently or a human action gates acceptance;
- required tasks precede optional refinements within a capability;
- explicit task prerequisites identify open tasks, form no cycles, and keep required work
  independent of optional refinements;
- every closed-research section names a task that is no longer open, carries its four parts in
  order, and names only open tasks as reopening paths.

The check is structural by design. Product priority changes are made by editing the registry order,
not by adding heuristics to the checker.

## Success criteria

The foundation succeeds when a team can create a locked environment, run a tested package, and use
any supported agent without duplicating project policy. A maintainer can determine what the
product promises, what work remains, which research questions were closed and what would reopen
them, which task is next in each lane, what behavior exists, and how every capability is evaluated
from repository files alone.

The product succeeds when an operator can see, in either language, what is publicly known about a
domain (for example, SATCOM systems, launches, services, tariffs, and coverage) and where each
value came from. They can see when each value was fetched, which values are unknown or disputed,
and how fresh each source is. They can do this without the system ever presenting a signal,
example, or unverified proposal as a fact.
