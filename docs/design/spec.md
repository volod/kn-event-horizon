# KN Event Horizon Specification

## Purpose

KN Event Horizon is a domain knowledge aggregator for industrial and technology awareness. It
collects evidence from public or legitimately licensed sources and normalizes it into domain
knowledge models governed by an explicit ontology and taxonomy. It preserves the provenance and
history of every claim. Every real-world object has one durable KN identity. Data about that
object from different sources is matched to it with explained, scored evidence, and its full
lifecycle and partial updates are tracked. Results are available through SQL, bilingual
English/Ukrainian dashboards and time-enabled maps, and read-only Obsidian vault exports.
Knowledge is exchanged with [InvenTree](https://inventree.org/) inventory instances through a
versioned interchange contract that tolerates InvenTree version changes. The first counterpart is
the owner's `vl-itree` instance. The design favors small-team maintenance, agent-assisted
development, and reproducibility.

It is not a general-purpose data lake, an autonomous agent framework, a media archive, a
real-time tracking or operations system, or an inventory, purchasing, or ERP system.

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
- **Identity first.** Each object gets one KN ID that is minted once, never reused, and kept
  through rebuilds. Matching source data to an object is a recorded, scored, reviewable decision.
  It is never a side effect of loading. See [Object identity](#object-identity).
- **Partial is not absent.** Sources declare nothing about completeness. A field a record does not
  mention is "not stated", and absence never clears or deletes anything. KN decides how each
  incoming value updates an object through declared [update policies](#update-policy).
- **Disabled by default.** A source collects nothing until its terms, limits, and permission are
  documented and a maintainer approves it.
- **Bilingual by design.** Every operator and user workflow works in `en` and `uk`, and facts are
  never duplicated per locale.
- **Versioned at the boundary.** The interchange contract and every adapter for an external system
  are versioned and compatibility-tested from their first task. KN does not control the external
  versions. See [Data interchange](#data-interchange).
- **Versioned storage with a development baseline.** Internal contracts start at `1.0.0`, edited
  in place until release. SQLAlchemy and Alembic support later reviewed evolutions. See
  [Development and release phases](#development-and-release-phases).

## Scope

The repository foundation includes:

- a Python 3.12+ `src` layout with an importable package and CLI;
- locked `uv` dependency management and Make entrypoints;
- deterministic tests, formatting, linting, typing, coverage, complexity, shell, and docs checks;
- GitHub Actions using the same CI entrypoint as local development;
- shared instructions for Codex, Claude Code, Cursor, and Gemini;
- a living capability registry and forward-plan/current-state lifecycle.

The product adds, in implementation order: a runtime platform, localization, data contracts, an
ontology and taxonomy model, object identity, a raw archive, an evidence model, a part and supply
model, source management, an ingestion engine, data interchange, InvenTree exchange, and Obsidian
export (the core engine). Identity, partial-update tracking, interchange, and compatibility are
initial requirements, not later refinements. After the core come space ELT, orchestration, and
space dashboards; then GDELT and microelectronics ELT and dashboards; then operations hardening and
release readiness. Optional local AI extraction comes last.

Exclusions: no Kubernetes, Kafka, Elasticsearch service, graph server, vector database, distributed agents,
or full GDELT replication. No satellite tasking or operations control. No public-facing custom
frontend; a minimal bilingual page is justified only where Superset, Kestra, and the CLI cannot meet
an acceptance test. No runtime dependency on a coding agent. No claims of comprehensive coverage or
ownership. No private customer data, private end-user terminal locations, or tracking of people.
No stock control, purchasing, sales, or build management inside KN. No real-time bidirectional
synchronization, and no deletion in a counterpart system. No personal contact data (people's
names, emails, phone numbers) is exchanged.

Target host: one Linux server with at least 32 GB RAM, 4 TB disk, and an NVIDIA GPU with 16 GB
VRAM used only by optional AI extraction. It runs Docker Engine with Compose v2. CPU is unspecified;
plan for 8-16 logical cores and confirm by measurement.

## Architecture

```text
 Git (reviewed)                                   $DATA_DIR (durable runtime inputs)
 contracts, interchange contract versions,        raw WARC archive, ledger, decision logs,
 seeds, match profiles, crawler configs,          identity event log, exchange ledger
 adapter profiles, external schema snapshots          ^             |
        |                                             | fetch       | replay
        v                                     approved sources,     |
 kn compiler --> generated DDL and models     InvenTree instances   |
        |                                                           v
        +-----------> PostgreSQL + PostGIS, database `kn` <--- kn engine: parse, map, change set,
                      schemas: system, semantic, identity,     validate, resolve identity, load
                      evidence, supply, interchange,           (CLI; Kestra when scheduled)
                      <domain>, analytics
                               |
          +--------------------+----------------------+-------------------------+
          v                    v                      v                         v
   dbt Core marts      Obsidian export (ZIP)   interchange packages    InvenTree adapter: probe,
          |                                    (versioned contract)    schema diff, profile,
          v                                                            plan, apply, read back
   Superset: en/uk dashboards, maps, read-only SQL Lab                 (vl-itree and others)
```

| Component | Choice | Boundary |
| --- | --- | --- |
| Contracts | ODCS v3, exact minor and JSON Schema checksum pinned; SQLAlchemy and Alembic governance | Validate and export supported artifacts; never silently drop custom extensions |
| Ontology and taxonomy | Reviewed JSON seed files loaded into the `semantic` schema; SKOS Turtle generated with RDFLib | SKOS is an interchange export; typed relation rules live in the meta-model |
| Storage | PostgreSQL with PostGIS, newest major that has an official PostGIS image at pin time; one database `kn` with one schema per domain | ACID, constraints, geometry, time series; no cross-database transactions needed |
| Raw archive | WARC 1.1 (ISO 28500:2017) via `warcio`; Parquet fetch ledger | Original bytes plus origin URI and fetch time; the only fetch output |
| Engine | Python 3.12+, HTTPX, Pydantic, psycopg 3 | Deterministic extract, parse, map, load |
| Identity | KN identity registry and append-only identity event log; declared match profiles with Fellegi-Sunter style weights | Deterministic resolution and scoring; no machine-learned matcher without a calibration gate |
| Interchange | KN interchange contract (ODCS, semantic versions from `0.1.0`), JSON Lines packages, schema-diff classifier | Versioned external boundary; never a second internal storage schema |
| InvenTree adapter | Versioned adapter profiles over the InvenTree REST API, selected by the probed API version; the `inventree` Python client is not required | Reads through the engine; writes only by approved, dry-run plans |
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
Identity events (mint, link, merge, split, retire) are appended to the identity log before the SQL
transaction that applies them commits. Replay applies the log before it replays raw records, so
every record resolves to the KN ID it received the first time. An outbound exchange writes its plan
to the exchange ledger before the first counterpart call, and its receipt after read-back. A
crash between the call and the receipt is recovered by reading the counterpart state, never by
blind resending.

At publication, each mart row or exported fact must have supporting evidence permitted for that
audience and use. This covers interchange packages and values written to a counterpart such as
InvenTree. Recompute the selection using eligible evidence. A restricted source cannot
supply the winning value through an unrestricted citation. Rebuild and restore apply the current
rights decisions and tombstones before opening reader access.

| Domain | Unit of analysis | Fixture that detects a wrong join or count |
| --- | --- | --- |
| Space | Service offering in a market for a stated period and customer segment | Two offers use the same constellation. Count the constellation once and retain both offers. |
| GDELT | Document revision for provenance, story cluster for independent-story counts | Two outlets syndicate one story. Preserve both document locators and count one cluster. |
| Microelectronics | Measurement of a device configuration under a specified condition set | Two measurements share a part number and differ in power boundary. Keep both and rank only within compatible conditions. |
| Supply (shared) | Orderable manufacturer part, and a supplier offer of it for a stated date and quantity | Two distributors sell one MPN, in tape-and-reel and cut-tape packaging. Keep one manufacturer part, two orderable variants, and two offers. Count the part once. |
| Interchange | Bound object pair (KN ID and counterpart object) and its field-level sync state | Two InvenTree parts are bound to two KN objects, and the objects are later merged. Report one redirect and one duplicate-binding conflict. Write nothing to either part until the owner resolves it. |

### Repository layout

```text
src/kn/                          core package: cli, compiler, archive, engine, semantic, identity,
                                 supply, interchange, export, i18n
src/kn/interchange/inventree/    InvenTree probe, schema capture, adapter, plan and apply
src/kn/domains/<domain>/         reviewed domain parsers and mapping helpers
contracts/core/                  core ODCS contracts: system, semantic, identity, evidence, supply,
                                 interchange ledger, export
contracts/core/identity/match-profiles/   reviewed match profiles per entity class
contracts/interchange/<version>/ versioned KN interchange contract and its upgrade steps
src/kn/db/                      Python platform policy and Alembic schema governance
interchange/inventree/schemas/<api-version>/   normalized InvenTree schema snapshots and digests
interchange/inventree/profiles/  adapter profiles, one per supported API version range
interchange/inventree/instances/ instance profiles (non-secret), such as vl-itree.yaml
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
identity/                            append-only identity event log (JSON Lines), never rewritten
exchange/<counterpart>/              append-only exchange ledger: bindings, plans, receipts
exchange/<counterpart>/<run-id>/     dry-run plans, change reports, and loss reports of one run
interchange/<run-id>/                interchange packages (ZIP) and manifests
runs/<run-id>/                       run manifests and redacted quarantine samples
exports/<profile>/<run-id>/          Obsidian vault ZIP and manifest
```

## Development and release phases

The project has two phases. The switch between them is the
[release readiness](#release-readiness) capability.

**Development phase** (from now until release approval):

- Storage contracts declare version `1.0.0` from their first model. During rapid development this
  version and the single Alembic baseline are updated in place; every edit changes a canonical
  digest, without adding development revisions or backward-compatibility branches.
- SQLAlchemy metadata, strict Elasticsearch mappings, Avro schemas, and validation schemas derive
  from the same ODCS definitions and reviewed `kn.*` metadata. Elasticsearch and Avro outputs are
  portable artifacts; no additional service is introduced.
- Normal deployment checks the installed digest. A changed development contract requires an
  explicit guarded rebuild and backfill from durable inputs. Development test data is disposable.
- At the first release, freeze contract `1.0.0` and the Alembic baseline. Subsequent schema changes
  require new semantic versions and reviewed Python Alembic revisions from contract diffs. Refuse
  destructive or incompatible changes until a reviewed expand/backfill/contract migration exists.
- There are no handwritten SQL deployment files. Development keeps the same governance mechanism
  that release migrations use, without accumulating revisions for provisional models.
- The raw archive, Git-managed seeds and curation files, decision logs, the identity event log, and
  the exchange ledger are the durable inputs. The database is a reproducible projection of them.
- Review decisions re-attach after rebuild by deterministic claim keys. A decision that no longer
  matches is reported as orphaned and is never silently dropped.
- KN IDs survive every rebuild because they come from the identity event log, not from load order.
  Rebuild does not merge, split, or retire objects on its own. When current code would group
  records differently from the log, the difference is reported as identity drift and becomes a
  review candidate. A mint during rebuild is logged and reported.
- **Boundary exception.** The development-phase rule covers KN's own storage schemas only. The
  [interchange contract](#data-interchange) has semantic versions from `0.1.0`. Its changes are
  classified by a contract diff, and each breaking change ships an upgrade step from the previous
  version. External adapter profiles, such as the [InvenTree profiles](#inventree-exchange), each
  declare the counterpart API versions they support. This code is required because counterpart
  systems change versions on their own schedule. Storage versions evolve independently.
- The ontology, taxonomy, and source-catalogue "data migrations" are the idempotent seed loads
  that every rebuild runs, using deterministic identifiers.
- Rebuild is refused in an environment marked as released.

**Release phase** (after release approval):

- Storage contracts stabilize at `1.0.0`, and datasets retain their versions and digests. The
  interchange contract is frozen at `1.0.0`, and later breaking changes need a new major version
  with an upgrade step and a deprecation window.
- Schema changes go through reviewed, versioned migrations generated from the contract diff. The
  migration tool is Alembic over contract-generated SQLAlchemy metadata. Release readiness verifies
  its safety on the full model. Destructive changes and incompatible releases are refused by default.
  Renames require stable field IDs and an alias plan, and changes follow
  expand -> backfill -> switch consumers -> contract.
- Seed changes become versioned data migrations.
- Rebuild stays available for disposable environments only.

## Knowledge integrity rules

These rules bind every capability and every domain.

1. **Entity types stay distinct.** Organization, program, mission, product model, physical asset,
   constellation, service, contract, filing, document, manufacturer part, orderable variant, and
   supplier offer are different classes. Identifiers are qualified strings (namespace plus native
   ID). Resolution uses an exact authoritative key first, then an existing source-qualified link,
   then a scored match over the class's declared identity attributes, then an alias candidate.
   Ambiguous matches go to review. Nothing merges by name alone. Split and merge history is kept.
2. **Relations stay distinct.** Legal ownership, operation, service provision and access,
   registration, launch event versus vehicle versus provider, program membership, partnership
   (MoU or LoI) versus contract or award, and filing versus licence versus deployment are separate
   relation types. Each declares allowed endpoints and minimum evidence in the ontology.
3. **Claim-level provenance.** Every claim records: origin URI, fetch time, fetch ID, native record
   locator, original value, original unit, conditions, normalized value and unit with the
   conversion rule, and the event, published, observed, valid-from, valid-to, and recorded times.
   It also records the parser code digest, the contract digest, the assertion type (declared,
   observed, derived, or reported), the extraction confidence, and the verification state
   (unreviewed, corroborated, verified, disputed, or rejected, as the
   [update policy](#update-policy) defines them).
4. **Origin on all data.** Source-derived rows carry their origin URI and fetch time, directly or
   through a non-null evidence reference. Seed rows carry their file path, SHA-256, sheet, and row.
   Curated observations carry the cited URI, capture time, and curator. Derived and aggregated rows
   carry lineage (model, inputs, window, filter) instead of a fake per-cell citation. Origin URIs
   are stored after credential redaction.
5. **Unknown is not zero.** Each value field holds either a value or a missing reason. No zero
   defaults, no clamping, no truncation. Lack of evidence is not absence of a capability.
6. **Conflicts are reviewed.** Contradictory claims are kept. Canonical selection uses the
   field's [update policy](#update-policy) (source rank, evidence class, data time, conditions),
   not the latest or most repeated value. High-impact facts (ownership, contracts, availability,
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
11. **Identity is durable and explained.** A KN ID is minted once, never reused, and never derived
    from a label. Every link from source data to an object records its method, features, score,
    probability, match-profile digest, and decision. Merged and retired IDs stay resolvable through
    redirects.
12. **Partial is not absent.** Sources do not declare whether a delivery is complete. A field a
    record does not mention is not stated, and a record that stops appearing only stops being
    confirmed. The field's update policy decides whether an incoming value fills a gap, replaces
    the current value, or stays evidence only. Arrival order never decides. Absence never deletes
    an object.
13. **Exchange preserves meaning.** Data sent to or received from another system keeps its KN ID,
    provenance reference, and rights. A value the counterpart cannot represent appears in a loss
    report and is never approximated silently. Imported counterpart data is evidence like any other
    source and never overwrites canonical facts directly.

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
- **Counterpart instances.** An InvenTree instance is the owner's private operational data. Its
  rights default to `owner_private`, so nothing read from it reaches dashboards, Obsidian vaults,
  or interchange packages unless the owner opts in. Reading uses a model allowlist. Users,
  contacts, addresses beyond country, orders, builds, and personal notes are never fetched.
- **Outbound writes.** KN writes only to an instance whose profile has an owner approval reference
  for writing. It uses a dedicated counterpart user with the least role permissions the export
  profile needs, and a token from the environment. Every write follows an approved dry-run plan.
  KN never deletes counterpart objects and never overwrites a counterpart edit to a field it owns
  without a review decision. It honors counterpart throttling and stays within a request budget.
  Vendor data whose licence forbids redistribution or caching never leaves KN.
- **Runtime isolation.** No host Docker socket and no root services where avoidable. Each schema has
  separate database roles: owner, loader, and reader. Loaders cannot run DDL. UI authorization
  (proxy authentication and Superset roles) and database least privilege are both required. CLI
  authorization is the database role whose credentials the operating-system account can read.

## Reproducible environment

The environment is created from `pyproject.toml` and committed `uv.lock`. Local development and
GitHub Actions both call Make targets and use the same locked development extra. GitHub Actions
runs only lightweight unit tests; tests that need a service endpoint, large memory, or a long run
time run on the development host through `make ci-local`. Tool caches follow `DATA_DIR`; the shared
environment helper chooses `UV_LINK_MODE=copy` only when uv's cache and the checkout live on
different filesystems.

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
running database `kn` with schemas `system`, `semantic`, `identity`, `evidence`, `supply`,
`interchange`, one schema per domain, and `analytics`. Later services are added by their
capabilities: Kestra (orchestration), Superset and Redis if its profile requires it (space
dashboards), the reverse proxy (operations hardening), the optional inference server (AI
extraction), and a test-only `inventree` profile with pinned InvenTree releases and their own
databases (InvenTree exchange). The test profile never connects to an owner instance. Volumes
live under `DATA_DIR`, services have healthchecks, and services reach each other over internal
networks. The database port is published only on the host loopback address, on a configurable,
non-standard default port, so that another PostgreSQL on the same host keeps the standard port.
Every TCP login needs a password. Secrets come from a local
`.env` or secret files that are never committed. Role bootstrap creates owner, loader, and reader
roles per schema. A version manifest records every pinned image, schema, and tool. Integration
tests run against the Compose database on the development host. GitHub Actions runs no database
test.

Boundary: a single host, not high availability. No Kubernetes and no managed cloud services.

Evaluation: from empty volumes, `make db-up` reaches healthy, and a restart preserves data. The
database answers on the host loopback port only with a password. It does not answer on another
host address or to a container on another Docker network, and no default production password
exists. Integration tests pass on the development host, and the GitHub gate passes without a
database.

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
- Interface catalogs and crawled data have independent languages. Interface keys must exist in
  every supported interface locale; missing interface translations fail validation.
- Vocabulary, entity labels, and crawled text retain their original text, language tag (or `und`
  when unknown), and source provenance, including Russian, Chinese, and other languages without
  English or Ukrainian versions. Optional translations are derived text with provenance, never
  replacements for the original or duplicate facts. Data display selects the requested language,
  then English, then the original. It reports the selected language, provenance, and whether a
  fallback occurred. An original already in the requested or fallback language is eligible in
  that order. Missing translations never block ingestion or discard source text.
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
- Multilingual data fixtures verify requested-language, English, and original fallback independently
  of interface catalogs, retaining original text and translation provenance without mutation.
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
| `kn.fieldId`, `kn.identity` | Stable logical field identity; external key definition; identity strategy; source record key and version field; the class's identity attributes with their normalizer, comparator, and authority level; the match profile reference |
| `kn.updatePolicy` | Field update mode, priority criteria order, minimum source rank and evidence class, time basis, value tolerance, freshness threshold, and empty-value handling |
| `kn.interchange` | Interchange exposure, field compatibility class (`stable`, `experimental`, `deprecated`), aliases of renamed fields, and counterpart mapping references |
| `kn.units`, `kn.comparisonProfile` | Original and normalized unit, quantity type, conversion rule, comparison gate |
| `kn.temporalProfile` | Event, published, observed, valid, and recorded times; as-of behavior; null semantics |
| `kn.spatialProfile` | Geometry type, SRID 4326, precision and coverage semantics, validity |
| `kn.evidence`, `kn.licensePolicy` | Evidence requirements, assertion type, rights and export restrictions |
| `kn.enumRef`, `kn.vocabularyRefs` | Controlled vocabulary and allowed tag schemes |
| `kn.index`, `kn.partition` | Reviewed physical design intent rendered as generated DDL |
| `kn.i18nKey` | Stable display key resolved through the message catalogs |
| `kn.lineageRefs` | Declared datasets and mappings, not observed runtime lineage |

The compiler (`kn contract lint|compile`) validates against a checksum-pinned ODCS schema and
closed KN extensions. It produces canonical digests, SQLAlchemy metadata and generated DDL,
strict Elasticsearch mappings, Avro schemas, JSON Schema validation, Pydantic models, dbt source
definitions, and contract documentation. Compile-time semantic references resolve against a local
reviewed catalog; no network lookup or runtime policy execution occurs during compilation. Decimal
values remain exact; partial dates stay strings with declared precision rather than invented days.
Unsupported types or metadata fail.
PostgreSQL deployment uses Python Alembic revisions and a shared Python role/extension policy;
there are no handwritten SQL deployment scripts. Generated artifacts cannot redefine contracts.

The initial SATCOM import contract preserves all 28 reference tables, native textual IDs,
composite keys, deferrable references, enums, decimal values, partial dates, claims, source
verification states, formulas and input claim references, aliases, and missing reasons. Source IDs
are scoped to this import and are not canonical KN UUIDs. Package bytes and raw CSV cells remain
immutable evidence; a typed projection does not promote assertions into verified facts. Workbook
formulas and charts remain in the archived workbook and are never silently flattened into facts.
The importer validates the complete package before one transactional load, is idempotent for
identical bytes, rejects conflicting records, and retains multiple source snapshots.

The KN interchange contract in `contracts/interchange/<version>/` is also ODCS. It compiles to
JSON Schema for packages and adapters, and to no DDL. Each interchange field references a storage
field ID. A storage field can change through rebuild without changing the interchange contract,
as long as its mapping is kept.

Boundary: not a general schema registry; no schema editing through a UI or a crawler.
Only the implemented ODCS profile is
accepted; broader ontology and interchange compilation remain separately planned.

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

### Object identity

Object identity is the core data model, and every other capability builds on it. Every real-world
object has one KN ID. Data about that object from any source, curated file, or counterpart system
is matched to that ID through recorded, scored decisions. The object's identity lifecycle and
every partial update of its data are tracked from the first load.

The `identity` schema holds:

- **object**: KN ID (a UUIDv7 minted on first sight, displayed as `kn:<uuid>`), entity class,
  identity lifecycle state, mint event, and current redirect;
- **identifier**: namespace and native ID, issuing authority, authority level, validity interval,
  and evidence. The authority levels are `authoritative`, `source_qualified`, and `weak`.
  Examples: an LEI, a NORAD ID, or a legal manufacturer plus exact MPN (authoritative);
  `inventree:vl-itree:part:42` or a distributor product ID (source-qualified); a SKU without its
  supplier, or a name (weak);
- **identity attribute**: the original value, normalized value, and evidence of each attribute
  that the class's match profile declares. For a manufacturer part these are the resolved legal
  manufacturer, the exact and normalized MPN, the package code, the packaging suffix, and the GTIN.
  For an organization they are the LEI, tax ID, registrable web domain, normalized legal name, and
  country;
- **source record**: a source-qualified record key, its versions with content and per-field
  hashes, its `last_seen` time, and its link to an object;
- **link**: the method (`authoritative_key`, `existing_link`, `scored_match`, `review_decision`,
  or `minted`), score, probability, match-profile digest, and decision reference;
- **match record**: the candidate set, the feature values, each comparator outcome and weight, the
  total score and probability, and the decision;
- **lifecycle event**: `minted`, `linked`, `unlinked`, `merged`, `split`, `reclassified`,
  `retired`, or `restored`, with its actor (engine or reviewer), reason, evidence, and time.

The identity event log in `$DATA_DIR/identity/` is append-only and is a durable input. The tables
are its projection. Rebuild applies the log before it replays raw records.

**Lifecycle.** Identity lifecycle is about the record of an object, and it is separate from the
object's real-world lifecycle. Announced, active, NRND, end-of-life, launched, and decommissioned
are claims with evidence, not identity states. The identity states are:

| State | Entered by | Rules |
| --- | --- | --- |
| `active` | `minted`, `restored` | Accepts links, claims, and bindings |
| `merged` | `merged` into an active object of the same class | Terminal; redirects to the survivor; its links and claims move with lineage |
| `split` | `split` into two or more active objects of the same class | Terminal; each link and claim moves to exactly one successor; a lookup by the old ID returns the successors for review |
| `retired` | `retired` (created in error, or the source asserts non-existence) | Still resolvable; no new links without `restored` |

A class change never mutates an object. A `reclassified` event retires the object and mints a
successor of the new class, linked by lineage. Merges, splits, and restorations are review
decisions, except a merge forced by two objects sharing one authoritative identifier. Redirect
chains resolve in one step. KN IDs are never reused or derived from labels.

**Matching.** Each entity class has a reviewed match profile in
`contracts/core/identity/match-profiles/`. A profile declares blocking keys and identity
attributes. Each attribute has a normalizer and a comparator (exact, normalized exact, graded
string similarity, numeric tolerance, date window, or set overlap). Each comparator's agreement
levels carry m and u probabilities in the Fellegi-Sunter sense. The profile also declares a prior,
a review threshold, a link threshold, and the attributes that discriminate. Resolution runs in
order:

1. An exact authoritative identifier links.
2. A record already linked through its source-qualified key keeps that link.
3. A scored match computes the summed log-likelihood weight and the posterior probability for
   each blocked candidate. It auto-links only when all of these hold: the probability reaches the
   link threshold, a discriminating attribute agrees, one candidate leads all others by the
   declared margin, and the profile is `calibrated`. A probability between the thresholds, or two
   close candidates, opens a review item. A lower probability mints a new object.
4. Alias candidates without a discriminating attribute never link automatically.

Profile validation rejects a profile whose link threshold can be reached by name or description
similarity alone. Until a class's profile passes calibration, every scored match goes to review.
Calibration uses held-out ground truth: pairs proven by authoritative identifiers, with those
identifiers masked during evaluation, plus reviewer decisions. It reports precision and recall at
both thresholds and the calibration error per probability band. A profile becomes `calibrated`
when precision at the link threshold is at least 0.99 on at least 200 held-out positive pairs. The
owner may change this gate in this section.

**Partial-update tracking.** Sources declare nothing about how complete a delivery is, so KN never
infers clearing or deletion from absence. The crawler configuration mapping names each source's
record key and, when the source supplies one, its version or `updated` field. Versions of one
record are ordered by that field, or by fetch time otherwise. For each mapped record the engine
compares every field with the record's previous version:

| Change | Effect on claims |
| --- | --- |
| `added`, `changed` | New claim superseding this record's previous claim for the field |
| `unchanged` | Confirmation of the existing claim with the new observed time; no new claim |
| `emptied` | New claim with missing reason `source_empty`; it changes the object only as its update policy allows |
| `not_stated` | No effect |

Each record has a `last_seen` time. A record that stops appearing keeps its claims. Those claims
stop being confirmed and age against each field's freshness threshold, and the object is never
deleted. An older version that arrives after a newer one is stored as history and does not become
current. A fragment that carries only a weak key, such as a price break with a SKU, resolves
through its record's existing link or its parent record. Weak keys alone never drive scored
matching. Each change set records its record version, fetch ID, archive record ID, and code
digest. The change set decides which claims exist. The [update policy](#update-policy) decides the
object's current value for each field.

**Lineage.** `kn lineage <kn-id|qualified-identifier> [--field <field-id>]` returns the identity
history, the identifiers, every link with its match record, the record versions and change sets,
the claims, the selected canonical fact, and any outbound exchange receipts. It is the identity
half of "Why this fact?". `kn identity show|resolve|history|merge|split|retire|restore` works in
both locales. A command that changes state writes a review decision and the identity event that
cites it.

Boundary: no merges across entity classes and no matching of people. No golden record overwrites
canonical facts, which still come from [fact selection](#evidence-model). No learned matcher
without the calibration gate.

Evaluation:

- Two rebuilds, and a rebuild after dropping the database, produce identical KN IDs, links,
  lifecycle states, and redirects.
- Fixtures cover one MPN from two manufacturers (two objects), packaging variants (distinct
  orderables), a renamed organization with a stable LEI (one object), name-only similarity
  (never auto-links), and permuted input order (same decisions).
- A merge and then a split restores links deterministically with history. A cross-class merge is
  refused. A redirect chain resolves in one step.
- Partial-update fixtures cover a price-only record, an emptied field, a field a record omits, a
  record that stops appearing, an identical re-delivery, and an out-of-order version.
- A match record reproduces its score and probability from its stored features and profile.
- Each calibrated class has a report with precision and recall at both thresholds.

Negative result: a class whose profile cannot reach the precision gate stays review-only for
scored matches, and exact authoritative keys still link. A source with no stable record key
cannot be change-tracked. Each of its records is new evidence, and identity resolution alone links
it.

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

Core and domain contracts define the datasets below. Objects, identifiers, identity attributes, and
links come from the [identity registry](#object-identity), and every claim refers to a KN ID.

- alias (language and normalized key; not unique), as a weak identifier of an object;
- claim: immutable, holding the [integrity-rule](#knowledge-integrity-rules) fields plus
  `supersedes`, the source record version, and the change kind that produced it;
- claim confirmation: a re-observation of an unchanged value, with its observed time and fetch ID;
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
duplicates. Fact selection follows [rule 6](#knowledge-integrity-rules) through the
[update policy](#update-policy), and unresolved fields stay null or conflicted with a reason.
`kn review list|decide` is bilingual. Each decision is appended to the decision log and replayed
by rebuild.

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

#### Update policy

Sources declare nothing about their deliveries. KN therefore decides, field by field, how a new
claim changes an object. Each contract field declares an update policy through `kn.updatePolicy`.
The canonical value is computed over all eligible claims with a total order, so the result never
depends on arrival order and a rebuild reproduces it. Claims whose values agree within the field's
tolerance support one candidate value. Candidates are ranked, and repetition never adds rank. Each
change is explained by one of these outcomes:

| Outcome | When |
| --- | --- |
| `filled` | The field had no eligible value, and the new claim is eligible |
| `replaced` | The new claim's value outranks the current winner under the priority rule |
| `ignored` | The new claim's value ranks lower; it stays visible as competing evidence |
| `corroborated` | The new claim supports the winning value; a confirmation from the same record never counts as independent support |
| `conflict` | The top candidates tie on every criterion and differ beyond tolerance, or a `fixed` field receives a different value; a review item opens |

A claim is eligible when it meets the field's minimum source rank and evidence class, is permitted
for the audience, matches the field's condition set, and is not rejected. High-impact fields
require primary evidence or a review decision ([rule 6](#knowledge-integrity-rules)). Signals and
AI candidates are never eligible for canonical fields.

**Source rank.** Each claim takes its rank from the reviewed source rank table
`contracts/core/policies/source-ranks.yaml`. The rank classes, highest first, are:

| Rank class | Sources |
| --- | --- |
| `owner_entered` | The owner's own entries, such as values typed into the owner's InvenTree instance, and every review decision |
| `first_party` | The source that issues the fact: a manufacturer for its part specifications, a distributor for its own prices and stock |
| `authorized_channel` | Authorized distributors and official registries reporting facts they do not issue |
| `third_party` | Aggregators, other databases, and other reports |
| `unranked` | Sources the table does not list yet |

A curated observation takes the rank of the source it cites. The table may override the class of
a single source or field group. A source's dispute rate, measured from review decisions, is
reported to support those overrides, and it never changes a rank by itself.

**Priority rule.** A candidate value's rank is the highest rank among its supporting claims. A
value that a higher-ranked source verifies therefore wins. The default criteria, in order:

1. **Source rank** of the candidate's best supporting claim.
2. **Evidence class** of that claim: a primary declaration or measurement, then a secondary report,
   then a derived value, then an extracted candidate.
3. **Data time**, using the field's time basis (valid-from, published, or observed). A newer value
   wins only over an older value from the same source, such as a newer datasheet revision.
4. **Tie.** Candidates from different sources with equal rank and evidence class, whose values
   differ beyond tolerance, give `conflict`.

**Verification states.** The verification states of [rule 3](#knowledge-integrity-rules) are
derived labels for display and filtering. They are not separate ranking criteria.

| State | Meaning |
| --- | --- |
| `unreviewed` | Supported by one source and no review decision |
| `corroborated` | Supported by two or more independent sources; confirmations, syndicated copies, and curated rows citing the same source are not independent |
| `verified` | Accepted by a review decision; it ranks through the decision's `owner_entered` class |
| `disputed` | Part of an open conflict |
| `rejected` | Rejected by a review decision; never eligible |

**Owner overrides.** When an `owner_entered` value wins over a `first_party` value that differs
beyond tolerance, the canonical fact is flagged `owner_override`. `kn review list --overrides`
lists these, so a typing error can be found and corrected at its source.

Each field uses one mode:

| Mode | Fields | Rule |
| --- | --- | --- |
| `priority` | Default; descriptive and technical facts | The priority rule above |
| `latest_observed` | Prices, stock, lead time, declared lifecycle status | Claims below the field's minimum rank are skipped. Data time decides first, then source rank, then evidence class. A winner older than the freshness threshold shows as `stale` with its age, never as current. |
| `accumulate` | Aliases, identifiers, documents, tags, substitutes, categories | The union of eligible items. A record's latest version replaces only that record's own earlier set. An item leaves only by a rejecting review decision or when no record still supports it. |
| `fixed` | Identity attributes such as legal manufacturer and exact MPN | The first authoritative value holds. A different value opens a review item and is never applied automatically. |

An empty claim (`source_empty`) never fills a field. By default, an empty claim that outranks the
current value opens a review item and does not clear it. A field may allow clearing only through
its `kn.updatePolicy`. Each canonical fact records its policy, mode, outcome, deciding criterion,
and the criteria values of the winner and the runner-up. "Why this fact?" shows them.

Evaluation:

- The first eligible claim fills an empty field (`filled`). A higher-ranked value replaces it
  (`replaced`). A lower-ranked value is ignored (`ignored`) and stays visible.
- An owner-entered value outranks a manufacturer value and is flagged `owner_override`. A
  third-party value that a first-party source also supports outranks an `authorized_channel`
  value.
- Two claims for one value from the same source, or a confirmation, never outrank one claim from
  a higher-ranked source.
- Under `latest_observed`, a newer price wins, and an old winner shows as `stale`.
- Different values from two sources of equal rank and evidence class give `conflict`. A newer
  datasheet revision from the same manufacturer replaces the older one. A different value on a
  `fixed` field opens review.
- An outranking empty claim opens review and does not clear the value.
- Every permutation of the claims' arrival order gives identical canonical values and outcomes.
- A signal never fills a canonical field.

Negative result: a field whose sources cannot be ranked defensibly uses `priority` with every
source at the same rank. Its disagreements then surface as conflicts rather than silent choices.

### Part and supply model

The `supply` schema is a cross-domain model of manufactured items and their supply. It serves
microelectronics, space components and terminals where needed, and InvenTree exchange. It holds as
complete a set of the information vendors deliver as permitted sources can supply. Every value is
a claim with the same provenance as any other fact.

Classes: organization roles (manufacturer, brand owner, distributor, authorized reseller, contract
manufacturer), product family, product model, manufacturer part (legal manufacturer plus exact
MPN), orderable variant (packaging or ordering suffix), supplier offer (supplier plus SKU for one
orderable variant), document reference, and typed substitute and cross-reference relations. The
[microelectronics domain](#microelectronics-elt) extends these classes and does not redefine them.

Vendor information coverage:

| Group | Content |
| --- | --- |
| Organization | Legal name, brands, aliases, LEI, tax or VAT ID, website, country, roles, parent or control |
| Part identity | Legal manufacturer, exact MPN, normalized MPN, family, series, model, revision, package or case code, ordering suffix, GTIN or EAN where published, vendor category with native code |
| Description | Short and long text in the original language, keywords, vendor last-updated time |
| Declared lifecycle | Preview, active, NRND, last-time-buy with dates, end-of-life, obsolete; product change and discontinuation notices with dates and documents |
| Technical parameters | Attribute-dictionary field IDs with raw value, unit, min, typical, max, qualifier, and condition set |
| Physical and packaging | Package type, pin count, dimensions, weight, moisture sensitivity level, packaging type, standard pack quantity, minimum order quantity, order multiple |
| Compliance and trade | RoHS status and directive version, REACH SVHC, halogen-free, conflict-minerals report, declared country of origin, ECCN, HTS or customs code, each per jurisdiction and cited |
| Documents and models | Datasheet, errata, application notes, reference manual, PCN or PDN, CAD symbol, footprint, and 3D model, each with URI, revision, publication date, hash, and rights |
| Supply offer | Supplier, SKU, packaging, pack quantity, minimum order quantity, multiple, price breaks (quantity, unit price, currency, customer class, tax basis, observed time), stock on hand, factory lead time, ship-from region, authorized-channel flag, product URI |
| Alternates | Manufacturer, distributor, or analyst substitutes, typed as drop-in, functional equivalent, upgrade, or cross-reference |
| Media | Product images and diagrams, link and hash only unless the licence permits copies |

Rules:

- The coverage matrix `contracts/core/supply/coverage.yaml` maps every group to contract field IDs
  or records an exclusion reason. A source's investigation report classifies every native field it
  delivers as mapped, kept raw-only with a reason, or excluded with a reason. Nothing a vendor
  delivers is dropped without a recorded reason.
- Prices, stock, and lead times are observations with an observed time. They never overwrite each
  other, and they are not shown as current past their source's freshness threshold.
- Declared lifecycle status is a cited claim, separate from [identity lifecycle](#object-identity).
- Country of origin and trade classifications are cited per jurisdiction and never inferred.
- Parameters use the attribute dictionary and observation model. A distributor's parametric value
  and a datasheet measurement are compared only under the comparison rules.
- Substitutes and cross-references are relations with their declaring source and never merge
  identities.
- Documents and media are link-and-hash references. Bytes are copied only where the licence
  permits.

Boundary: no pricing engine, quoting, purchasing, stock control, or BOM costing. No distributor
site scraping. Distributor data comes only through permitted APIs under their account terms, or
through curated observations. Pricing and stock licence limits, such as no caching or no
redistribution, are enforced through `kn.licensePolicy`.

Evaluation:

- A test fails when any coverage group has neither field IDs nor an exclusion.
- Fixtures: one MPN from two manufacturers is two parts. Packaging variants form one manufacturer
  part, two orderable variants, and two offers, and the part is counted once. A price break
  without quantity, currency, or observed time is rejected. Stock observations form a time series
  with stale labels. A substitute does not merge. Origin is never inferred.
- An interchange round trip preserves every mapped supply field.

Negative result: a group that no permitted source delivers stays in the matrix as
`no_permitted_source` with the reason. A group the contracts cannot type safely stays raw-only
with the reason.

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
| access | Method (`http_json`, `http_csv`, `http_xml`, `feed`, `bulk_file`, `curated_file`, `html_permitted`, `adapter_api` with a named reviewed adapter such as `inventree`), endpoints, allowed hosts, redirect policy, auth environment alias, request budget, rate limits, conditional requests |
| schedule | Cron in UTC, freshness threshold (default twice the schedule interval) |
| cursor | `snapshot_hash`, `updated_since`, `id_range`, or `window` with overlap; separate backfill namespace |
| raw | Format (`warc` or `blob`), retention, redistribution |
| parse | Parser entry point under `kn.domains.<domain>`, native schema or codebook edition, schema fingerprint |
| mapping | Native field -> contract field ID; units; native code -> concept with mapping type; class and relation mapping; source record key and version field; identifiers with authority level and identity attributes; time-field semantics |
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
5. Map them to candidate objects, claims, relations, and tags through the crawler configuration.
   Compute each record's field-level change set against its previous version.
6. Validate against the compiled models and the ontology rules.
7. Resolve identities through the [identity registry](#object-identity) and match profiles, and
   append identity events.
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
The core never branches on a source ID. On every change, `make ci-local` runs all source fixture
suites plus a full rebuild from the fixture archive. Logs are structured English JSON with secrets
redacted, and user-facing messages are localized.

Boundary: no exactly-once network claim, and no per-source special cases inside the core.

Evaluation:

- A rerun after an interrupted run resumes from the committed checkpoint without duplicates.
- A bad row, a malformed response, `429`, partial pagination, a schema change, and an unavailable
  source each produce the declared status, with no cursor jump and with secrets redacted.
- Existing good facts are kept and marked stale.
- Two rebuilds produce identical canonical tables by row hash.

Negative result: when a source cannot be expressed by configuration plus a parser, the engine gains
a general mechanism with tests, or the source stays disabled.

### Data interchange

Interchange separates three layers so that a change in one is absorbed by one mapping:

```text
KN storage schemas          KN interchange contract           counterpart adapter profiles
(rebuild-evolved,     <-->  (semantic versions from     <-->  (one per counterpart API
 internal only)              0.1.0, upgrade steps)             version range, e.g. InvenTree)
```

Adapters never read KN tables directly. KN tables hold counterpart-shaped data only in the raw
archive and the exchange ledger.

**Interchange contract.** Each object record carries its KN ID, class, identity lifecycle state and
redirects, identifiers with authority level, and identity attributes. It also carries fields keyed
by interchange field ID with a value or missing reason, unit, qualifier, condition set, validity,
provenance reference (claim key, origin URI, fetch time, licence), and record version. Relations
are records too. Retired and merged objects are exported as state, never as deletions.

**Package.** `kn interchange export` writes a ZIP with `manifest.json` and one JSON Lines file per
class in deterministic order. The manifest holds the contract version, producer instance ID, as-of
snapshot, watermark, scope and filters, counts and excluded counts, per-file SHA-256, rights
profile, and generator digest. A package is full or a delta since a watermark, is written
atomically and verified, and is never partial. `kn interchange validate` checks a package against
its declared version. `kn interchange import` treats a package as a source through the
[ingestion engine](#ingestion-engine) under the same update policies. A package never clears or
deletes anything by omission.

**Contract versioning.** `kn interchange diff` compares compiled contract versions field by field:

| Class | Examples | Required version change |
| --- | --- | --- |
| Compatible | Documentation; a constraint clarification that accepts the same packages | Patch |
| Additive | New optional field or class; new value in an open enum; rename that keeps the field ID and an alias; deprecation | Minor |
| Breaking | Removal; type, unit, or meaning change; optional to required; closed enum narrowed | Major (minor while `0.x`), plus an upgrade step |

CI fails when a version bump is smaller than its classification. An upgrade step in
`contracts/interchange/upgrades/` is a pure data transformation with fixtures. Readers accept any
supported version by chaining steps. Fields from a newer minor are kept as extension data and
round-tripped, and a newer major is refused with a diagnostic. During development every version
with an upgrade chain to the current one is supported. After release the current and previous
majors are supported for a declared deprecation window. An export may target an older supported
version only when every exported field maps back. Otherwise it is refused with a loss report.

**External schema evolution.** Counterpart API schemas are captured and normalized into schema
facts: resource, operation, method, field, type, format, required, read-only, nullable, enum,
filter, pagination, and authentication. Reviewed snapshots are keyed by the counterpart API
version and carry a digest. The contract diff classifier also compares two snapshots, limited to
what an adapter profile maps, and reports `compatible`, `compatible_with_review` (for example, a
new required-on-create field or a new enum value), or `breaking` (a field removed, renamed, moved,
retyped, or made read-only; a filter renamed; an endpoint moved or its method changed).

**Adapter profiles.** Each profile maps counterpart resources and fields to interchange field IDs
for a declared API version range, with capability flags. The probed API version and schema digest
select the profile. For a version that no profile covers, reads proceed only when the mapped
subset's diff against the nearest reviewed snapshot is `compatible`. Writes need a reviewed
profile that covers the exact version. Anything else stops with `schema_drift` and the
compatibility report.

**Exchange ledger.** The append-only ledger in `$DATA_DIR/exchange/<counterpart>/` is a durable
input. It records bindings (KN ID to counterpart instance, resource, and key, with binding time
and redirect state), per-field sync state, plans, and receipts. Sync state holds the last value KN
wrote and its hash, the last counterpart value seen and its hash, and the field owner. Each mapped
export field is owned by `kn` (KN may write it) or by the `counterpart` (KN only reads it). No
field has two owners.

**Echo suppression.** When an import reads a counterpart value equal to the last value KN wrote to
that bound field, the value is an echo of KN's own data. It confirms the binding and creates no
claim. Only values that differ from KN's last write are counterpart claims, at the counterpart's
source rank. KN's own exports therefore never come back as owner entries that would freeze them.

A three-way comparison of base, KN current, and counterpart current gives:

| State | Action |
| --- | --- |
| `in_sync` | Nothing |
| `kn_changed` | Update when KN owns the field |
| `counterpart_changed`, `both_changed` | Import the counterpart value as a claim. When it wins under the update policy, nothing is written back. When it loses on a KN-owned field, a review item opens, and KN does not overwrite it. |

Boundary: not a message bus and not real-time synchronization. No deletion is propagated. KN
storage is never generated from counterpart schemas. The contract is the only interchange format.

Evaluation:

- Contract versions compile deterministically. Diff fixtures cover each change class, and CI fails
  on an undersized bump.
- Two exports of one snapshot are byte-identical. Exporting and then importing into an empty
  rebuild reproduces objects, KN IDs, values, missing reasons, and provenance references.
- A `0.1.0` fixture package read through the upgrade chain equals a current export of the same
  data. Unknown newer-minor fields round-trip, and a newer major is refused.
- Restricted-rights fields are absent and counted as excluded in the manifest.
- Snapshot diff fixtures classify each external change type correctly.
- Three-way fixtures cover every sync state, and the ledger replays to identical bindings. An
  echoed value creates no claim.

Negative result: a change that no upgrade step can carry without loss needs a new major version
with a documented loss report. A counterpart version whose diff breaks a mapped field gets a new
profile, or it stays blocked for that field with the report.

### InvenTree exchange

KN exchanges part, supply, and parameter knowledge with [InvenTree](https://inventree.org/)
instances. The first counterpart is the owner's `vl-itree` instance
([repository](https://github.com/volod/vl-itree)). It is released together with KN on one pinned
InvenTree release, the newest stable release at release time, so no earlier InvenTree release is
supported. InvenTree is still a third-party application. Its releases, API, and schema change
outside KN's control, and any instance can be upgraded on its own. Each instance has a non-secret
instance profile at `interchange/inventree/instances/<instance-id>.yaml`. The profile uses the
crawler configuration blocks plus an `exchange` block: direction, export profile, field ownership,
and write approval reference. The [InvenTree design](integrations/inventree.md) holds the model
mapping and the `vl-itree` deployment facts.

**Target release.** Each joint KN and `vl-itree` release names one target InvenTree release, by
exact image tag and digest, and the `vl-itree` release tag that pins it. The KN test service, the
reviewed schema snapshot, the adapter profile, and the `vl-itree` image reference all name the
same release, and `deploy/versions.yaml` records all three values. The current target is
InvenTree `1.7.3` (API version 570), pinned by the `vl-itree` release `v0.1.0`. The
[target release](integrations/inventree.md#target-release) table lists its image digests. That
release meets the [vl-itree requirements](integrations/inventree.md#vl-itree-requirements): exact
image pins, TLS, and a password guard. A later target passes the upgrade check first, and the owner
then creates the next `vl-itree` release tag.

**Probe and capture.** Every session starts with `GET /api/`, which returns the software `version`
and the integer `apiVersion`. It then captures the instance's OpenAPI schema. Both responses are
archived to WARC. The schema is normalized, and its digest is compared with the target release's
reviewed snapshot. A mismatch means the instance changed outside the joint release. Reads continue
only when the diff of the mapped subset is `compatible`, writes stop, and the compatibility report
is raised to the operator. Earlier InvenTree API changes serve only as diff-classifier fixtures.

**Upgrade check.** A new InvenTree release is adopted only after
`kn inventree upgrade-check --release <tag>` passes. The check starts the candidate release in the
test service, seeds the synthetic catalogue, and captures and diffs the schema against the current
target. It then runs the import and export suite and writes a compatibility report. A profile is
extended, or a new profile replaces it, before `vl-itree` moves to the candidate. The candidate then
becomes the next joint target.

**Mapping.** Companies with manufacturer and supplier roles map to organization roles. Manufacturer
parts map to manufacturer parts (legal manufacturer plus MPN). Supplier parts and their price
breaks map to supplier offers and price observations. Generic parameters and parameter templates
map to attribute-dictionary field IDs with units. Part categories map to a KN classification
scheme through analyst crosswalks. Attachments map to document references, as links by default,
and tags map to tag concepts. An InvenTree part is the owner's internal part. It binds to a
product model or manufacturer part, and its fields are counterpart-owned by default. Stock is an
optional, read-only aggregate availability. Values that InvenTree cannot represent are listed in
the profile's loss report.

**Binding.** The exchange ledger is authoritative. Where the target release exposes model metadata,
KN also writes its KN ID and binding version under a `kn` key in the object's metadata. A metadata
KN ID with no matching ledger binding, such as on a duplicated InvenTree part, is a conflict.

**Import.** An instance is an `adapter_api` source with `owner_private` rights. Values the owner
entered in InvenTree take the `owner_entered` source rank, the highest one, so they win over vendor
data and are flagged `owner_override` where they differ from first-party values. Values KN wrote
earlier come back as echoes and create no claim. The source has a resource allowlist and required
`limit` pagination. It uses
`updated_since` cursors where the profile declares them, and otherwise full listings compared by
record hash. Identity resolves by binding first, then by `inventree:<instance>:<model>:<pk>`,
then by MPN and manufacturer or by supplier and SKU, then by scored match. Imported values change
KN objects only through their update policies. A bound InvenTree object that disappears marks its
binding `counterpart_missing`, and the report names it. KN does not delete its own object, and it
does not recreate the InvenTree object without an approved plan.

**Export.** `kn inventree plan --instance <id> --profile <id>` writes a dry-run plan. The plan lists
creates and updates per object and field, with before and after values, owners, conflicts, the
loss report, and the request estimate. `kn inventree apply --plan <id>` runs an approved plan in
dependency order: companies, parameter templates, manufacturer parts, supplier parts, price breaks,
then parameters. Each write is idempotent through bindings, read back, and compared, and a receipt
is appended. Creating internal parts and categories is off by default. The owner can enable it per
export profile.

**Connectivity.** An instance can run on another machine. KN then reaches it only over HTTPS with
certificate verification. The instance profile may name a non-secret CA certificate file, such as
the root of the instance proxy's internal CA, and verification is never disabled. KN connects by
the host name of the instance's site URL, which is the name the certificate covers. Plain HTTP is
allowed only over loopback or a private Docker network on the same host. A token never crosses a
network in plain HTTP.

**Test service and fixtures.** The Compose `inventree` profile runs the target release, and the
upgrade check runs a candidate release beside it. A seed script loads one synthetic catalogue.
Recorded WARC fixtures from the target release keep CI network-free, and `make test-inventree` runs
the live suite.

Boundary: no stock, order, build, or BOM-costing management in KN. No support for InvenTree
releases before the target. No InvenTree plugin is required; an optional read-only panel belongs to
the `vl-itree` repository. No write without an approved plan. No deletion and no personal data. KN
does not deploy or upgrade `vl-itree`. It prepares the version change and the compatibility report.

Evaluation:

- Probe and capture on the target release give a reviewed snapshot with a stable digest.
- The synthetic catalogue imports to the same KN objects, IDs, and claims on every run, and a
  second import is idempotent. Replay without network reproduces it.
- A plan is deterministic. A second apply is a no-op. Every written value reads back equal. An
  owner edit in InvenTree to a KN-owned field is imported as an owner claim and never overwritten.
  A value KN wrote is not re-imported as an owner claim. A value with a no-redistribution licence
  never leaves KN.
- A connection to a non-loopback instance over plain HTTP, or with a certificate that fails
  verification, is refused.
- An instance whose schema digest differs from the target allows reads only on a compatible diff
  and refuses writes. Planted removals, renames, read-only changes, and endpoint moves are
  classified `breaking`.
- The upgrade check reports a candidate release's differences and runs the exchange suite on it.
- `vl-itree` on the target release, reached over verified TLS, passes a read import and an
  approved write exchange with read-back.

Negative result: when the upgrade check finds that a needed field became read-only or disappeared,
the new profile marks that resource read-only and the loss report names it. The joint target stays
on the current release until the owner accepts the loss. An instance that cannot be reached or
authorized stays disabled with the reason.

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
  Families, models, manufacturer parts, orderable variants, and supplier offers are the shared
  [part and supply model](#part-and-supply-model) classes. The domain adds dies, IP blocks, kits,
  facilities, projects, benchmarks, and condition-bound observations.
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
  files, decision logs, the identity event log, the exchange ledger, and Git release artifacts.
  Copies are kept for 7 days daily and 4 weeks weekly. Proposed objectives are RPO <= 24 h and
  RTO <= 8 h, validated by a restore drill. An off-host encrypted destination is required beyond
  development.
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
  - SSRF, archive-traversal, and decompression-bomb limits;
  - no counterpart write without an approved plan, and no personal data in counterpart reads.

Boundary: no high availability and no promise of zero downtime.

Evaluation: a restore into an isolated instance passes hash, constraint, and dashboard checks with
the achieved RPO and RTO recorded. The performance and security suites pass on the target host.

Negative result: an objective that is not met is recorded with its measured value. The owner then
adjusts the objective or the hardware.

### Release readiness

The owner approves a release scope, which by default covers the core engine (including object
identity, data interchange, and InvenTree exchange), all three domains' ELT and dashboards,
Obsidian export, localization, and operations hardening.

- **Migration tool.** SQLAlchemy metadata and Python Alembic revisions generated from reviewed
  contract diffs; no handwritten SQL deployment scripts.
- **Baseline.** Freeze the existing editable development contracts and baseline at `1.0.0`.
  Dataset version and digest recording already exists; later versions get separate revisions.
- **Interchange freeze.** The interchange contract is frozen at `1.0.0` with an upgrade chain from
  every development version that has been exchanged. The joint release names its target InvenTree
  release, and `vl-itree` pins the same image tag.
- **Switch.** The environment is marked released, which refuses rebuild.
- **Checklist.** Every capability's evaluation has evidence.

Boundary: no compatibility promises before this switch.

Evaluation: migrating an empty database and a `1.0.0` -> `1.1.0` additive change preserves records,
identifiers, and provenance. A breaking change without a migration plan is refused. Drift is
detected. Rebuild is refused in the released environment.

Negative result: if an evolution cannot be generated safely, refuse it until a reviewed Python
expand/backfill/contract migration and preservation tests cover the gap.

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
| 4 | `runtime-platform` | shipped | Pinned Compose database reaches healthy from empty volumes, keeps data across restart, publishes its port on loopback only, and serves integration tests on the development host | [Runtime platform](../impl/current/runtime-platform.md) |
| 5 | `data-contracts` | planned | Contracts compile deterministically, invalid contracts fail, drift fails CI, rebuild creates every schema, loaders cannot run DDL | [Compiler and initial space profile](../impl/current/data-contracts.md) |
| 6 | `ontology-taxonomy` | planned | Every proposal row is classified, identifiers are stable, invalid hierarchies are rejected, SKOS round-trips | - |
| 7 | `object-identity` | planned | KN IDs survive rebuilds; lifecycle, matching, partial-update, and lineage fixtures pass; calibrated classes meet the precision gate | - |
| 8 | `raw-archive` | planned | WARC round trip, atomic write, ledger reindex, redaction, revisit, and corruption checks pass | - |
| 9 | `evidence-model` | planned | Conflict, time, provenance-lookup, idempotence, confirmation, update-policy, and decision-replay fixtures pass | - |
| 10 | `part-supply-model` | planned | Every vendor coverage group maps or records an exclusion; part, variant, offer, price, and substitute fixtures pass | - |
| 11 | `source-management` | planned | Catalogue import is complete; configuration validation refuses unapproved enablement; error and status mapping fixtures pass | - |
| 12 | `ingestion-engine` | planned | Failure-mode fixtures yield declared statuses without cursor jumps; two rebuilds produce identical canonical tables | - |
| 13 | `data-interchange` | planned | Contract diffs enforce version bumps; packages reproduce and round-trip; upgrade chains and three-way sync fixtures pass | - |
| 14 | `inventree-exchange` | planned | The target release imports deterministically; approved plans apply idempotently with read-back; schema drift blocks writes; the upgrade check classifies candidate releases; `vl-itree` passes read and write exchange | - |
| 15 | `obsidian-export` | planned | Fixture vault verifies hashes and links, excludes restricted rights and secrets, and reproduces identically | - |
| 16 | `space-elt` | planned | Permitted live samples load; launch, catalog, count, and tariff semantics are never conflated; rebuild reproduces the domain | - |
| 17 | `orchestration` | planned | Generated flows are deterministic; a scheduled window respects budgets; killed runs retry without duplicates | - |
| 18 | `space-dashboards` | planned | Bilingual bundles deploy reproducibly with equal filter results; maps render licensed boundaries; SQL Lab stays read-only | - |
| 19 | `gdelt-elt` | planned | Dictionaries carry edition and checksum; DOC queries handle caps and truncation; signals stay unverified | - |
| 20 | `gdelt-dashboards` | planned | Watch dashboards deploy in both locales with stated denominators and story-level counts | - |
| 21 | `microelectronics-elt` | planned | MPN identity, condition-bound observations, and matched-comparison exclusion fixtures pass | - |
| 22 | `microelectronics-dashboards` | planned | Bilingual comparison bundles never rank incomparable records | - |
| 23 | `localization` | planned | Key coverage, plural, golden-output, and screenshot checks pass in `en` and `uk`; the Kestra waiver is the only English-only path | [Catalog core](../impl/current/localization.md) |
| 24 | `operations-hardening` | planned | Restore drill, performance gate, and security suite pass on the target host with measured objectives | - |
| 25 | `release-readiness` | planned | Migration mode preserves data, refuses breaking changes and rebuild, freezes the interchange contract, and every evaluation has evidence | - |
| 26 | `ai-extraction` | planned | Labeled fixtures show zero unsupported published claims within the VRAM budget; ingestion is unaffected without it | - |

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

For any object, the operator can see its one KN ID and every source record matched to it, with
the match method, score, and decision. They can see its identity history and each partial update
as it arrived. The same part knowledge moves between KN and the owner's InvenTree instance in both
directions with its identity and provenance intact, across InvenTree upgrades, and nothing is
overwritten or lost without a report.
