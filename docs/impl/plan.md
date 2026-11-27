# KN Event Horizon Implementation Plan

Forward-only: this file describes work that remains. Available behavior and durable results belong
in [current-state documentation](current.md). Product behavior and evaluation belong in the
[specification](../design/spec.md). Research questions that stopped, with what would reopen them,
belong in the [closed-research register](future-research.md).

The agent lane groups tasks by the result a consumer can use. Each delivery group ends with
its implementation audit. `Serves` identifies the specification owner of each task. Open
`Requires` entries gate work across both lanes. Choose the first ready required task in written
order, checking its external dependencies, then optional extensions when required work waits.
Human approvals stay in their own lane and apply only to the scope described there.

Follow the [contract and fixture checks](../guide/schema-first-development.md) for each group.
The integrated model and backfill audit gates release approval. A consumer can start as soon as
its own producers pass their audits. Run `make plan-status` for lane counts and next candidates.
Record findings during implementation and at each handoff under the
[planning workflow](../guide/planning-workflow.md#implementation-audits).

The project uses ODCS storage contract version `1.0.0` and a single editable Python
SQLAlchemy/Alembic baseline during development. Rebuild and backfill replace development revision
chains. First release freezes this baseline and enables subsequent versioned migration history.
The external interchange contract and counterpart adapters remain
independently versioned. Object identity, interchange, and InvenTree
compatibility are core work and come before the domain pipelines.
Source tasks follow the [onboarding workflow](../guide/source-onboarding.md) and the
[TDD growth rule](../design/spec.md#ingestion-engine). Each source adds failing fixtures first, then
general engine changes, and reruns every earlier source suite plus a rebuild from the fixture
archive.

## Agent Implementation Tasks

### Source runs and health -- `source-management`

#### source-status-monitoring

Operators need per-source health and freshness without opening Kestra.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Dependencies: The [fixture runner](current/ingestion-engine.md#run-and-replay-a-snapshot)
  and [run history and health fields](current/ingestion-engine.md#run-history-and-health).
- User-visible outcome: `kn source status` shows the last success and attempt,
  state, stale flag, counts, bytes, budget use, cursor lag, and last error code, and feeds the
  operations mart.
  Read the registered run and checkpoint tables.
- Scope boundary: Status computation from run records and the CLI. Dashboards come in
  `space-dashboard-bundles`.
- Data and artifact paths: `src/kn/sources/status.py`, `tests/sources/`.
- Execution path: Compute status from fixture runs covering every run status and error code.
- Acceptance gates: Stale detection follows the configured threshold. Every error code renders.
  Golden outputs cover English text and stable JSON.
- Documentation target: `current/source-management.md` listed in the
  [areas index](current.md#areas).

#### source-management-implementation-audit

Every source enters through the catalogue, the crawler schema, and the onboarding workflow, so a gap
there repeats in every source that follows.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Requires: `source-status-monitoring`
- Dependencies: The [engine skeleton record](records/0059-ingestion-engine-engine-skeleton.md),
  the accepted status-monitoring record and the
  [implementation audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Every later source is onboarded through verified, enforced declarations. The
  audit record gives every check a result and every finding a disposition. The current-state page
  lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: catalogue states and transitions, with sources disabled by default; crawler
  schema strictness, defaults, and messages; licence, rate-limit, and robots fields that are
  enforced, not advisory; error-code completeness; status freshness, stale and failing thresholds,
  and clock skew; templates that match what the engine needs; new source kinds, such as APIs, bulk
  files, and curated input, without schema changes. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/system/`, `src/kn/sources/`, `domains/<domain>/sources/`,
  `docs/guide/source-onboarding.md`, `docs/guide/templates/`, `tests/sources/`, `docs/impl/plan.md`,
  and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks.
  Validate a crawler file with an unknown key, one without a licence, and a disabled source with a
  schedule, and onboard one fixture source from the templates alone. Interrupt a fixture run before its
  checkpoint, retry it and compare status, history and cursor with an uninterrupted run.
- Acceptance gates: Each invalid crawler file is refused with a stable error code. A
  disabled source cannot run. The templates cover every field the schema requires. Every finding has
  a severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/source-management.md` listed in the [areas
  index](current.md#areas).

### Acquisition, mapping and replay -- `ingestion-engine`

#### http-fetch-safety

Every fetch must be safe and polite by construction.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `source-management-implementation-audit`
- Dependencies: HTTPX as the justified dependency.
- User-visible outcome: The engine fetches only allowlisted hosts and redirects over verified TLS,
  within byte and request budgets. It uses conditional requests, honors `robots.txt`, `429`, and
  `Retry-After`, and injects credentials from the environment with redaction.
- Scope boundary: The HTTP client, SSRF guard, limits, backoff with jitter, error-code mapping, and
  budget accounting. No browser automation.
- Data and artifact paths: `src/kn/engine/http/`, `tests/engine/`.
- Execution path: Use fixture servers for redirects, private-IP targets, oversized and compressed
  bodies, `429`, `403`, and non-JSON `200` responses.
- Acceptance gates: Each hostile fixture produces its declared error code without a request to a
  disallowed target. No secret appears in logs or WARC files.
- Documentation target: `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### tracked-claim-times-and-sets

Partial-update tracking builds every claim without its stated times and accepts one statement per
field. A tracked source therefore cannot feed two update-policy rules: a newer datasheet revision
kept as another record conflicts with the older one instead of replacing it, because neither claim
has a valid-from or published time, and a record that lists several items of an `accumulate`
field, such as documents or aliases, can claim only one of them.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: Finding EMA-10 of the [evidence model
  audit](records/0053-evidence-model-evidence-model-implementation-audit.md#findings), the
  [partial-update tracker](current/object-identity.md#partial-update-tracking) and the
  [update-policy modes](current/evidence-model.md#canonical-selection).
- User-visible outcome: A mapped statement carries its event, published and valid times with their
  precision into its claim. A record can state several items of an `accumulate` field, each item
  claims separately, and an item that a later version drops loses that record's support only.
- Scope boundary: The statement and delivery shapes, item-level field hashes and change classes
  for set-valued fields, and the claims and confirmations they imply, added so that existing v1
  journal events and change sets keep their hashes. Mapping native fields to these shapes stays in
  `mapping-and-quality-rules`, and the selection rules do not change.
- Data and artifact paths: `src/kn/identity/tracking/`, `contracts/core/identity/`,
  `tests/identity/`, `tests/evidence/`.
- Execution path: Track two datasheet revisions as separate records with valid-from times and
  project the fact. Track a record whose document list gains and then loses an item across
  versions and project the `accumulate` fact.
- Acceptance gates: The newer revision replaces the older one with `data_time` as the deciding
  criterion. The `accumulate` fact holds the union of current items, and a dropped item leaves it
  only when no other record still states it. Existing v1 journals replay with unchanged hashes,
  change sets and claims. `make ci` passes.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).

#### mapping-and-quality-rules

Most source-specific behavior must live in configuration, not code.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `http-fetch-safety`, `tracked-claim-times-and-sets`
- Dependencies: The [partial-update tracker and its crawler mapping helpers](current/object-identity.md#partial-update-tracking).
- User-visible outcome: Crawler configurations map native fields to contract field IDs. They also
  map units with logged conversions, native codes to concepts with mapping types, classes and
  relations, identifiers and identity attributes, time semantics, and source record keys with
  field-level change sets. Quality rules quarantine records or stop batches as declared.
- Scope boundary: The general mapping and quality engine, with no source-specific branches. The
  units table covers the dimensions that contracts declare. Loads project the canonical facts of
  the subjects they touch through the [fact projection](current/evidence-model.md#fact-projection)
  and each field's declared policy.
- Data and artifact paths: `src/kn/engine/mapping/`, `src/kn/engine/quality/`, `tests/engine/`.
- Execution path: Fixture configurations exercise every mapping and rule type, plus the failure
  modes from the specification.
- Acceptance gates: A bad row is quarantined, a broken key stops the batch, an unmapped code stays
  a string, and an unknown value never becomes zero. Partial pagination leaves the cursor in place.
- Documentation target: `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### curated-source-method

Facts without a permitted machine-readable source need a disciplined manual path.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `mapping-and-quality-rules`
- Dependencies: none.
- User-visible outcome: Analysts add rows to `domains/<domain>/curation/` files, each with the cited
  URI, capture time, and curator. `kn source run` loads them through the same mapping and
  validation, and stores WARC captures of cited pages where permitted.
- Scope boundary: The curated file format, its validation, and evidence capture. A curated claim
  takes the rank of the source it cites in [canonical selection](current/evidence-model.md#canonical-selection).
  No editing UI.
- Data and artifact paths: `src/kn/engine/curated/`, `domains/fixture/curation/`,
  `tests/engine/`.
- Execution path: Fixture curated files with valid, missing-evidence, and conflicting rows.
- Acceptance gates: A row without a cited URI and capture time is rejected. Conflicts reach the
  review queue. Rebuild reproduces curated claims.
- Documentation target: `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### dataset-package-locations

The SATCOM package can only be read from a local directory, so the owner cannot publish a new
version on Google Drive for unattended re-import.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Dependencies: The [prefetched datasets](../design/spec.md#ingestion-engine) design and the current
  [SATCOM import](current/data-contracts.md#source-preservation-and-import). Unit tests use a local
  stub of the Drive API; the live run belongs to `publish-satcom-drive-package`.
- User-visible outcome: `KN_SATCOM_SOURCE` in `.env` selects a local directory, a local ZIP, or
  `gdrive:<file-id>`, and `make satcom-fetch` stages that package under
  `$KN_RAW_ARCHIVE_DIR/staging/space/satcom/<run-id>/` for `make satcom-import`. An unchanged Drive
  file ends `not_modified` after one metadata request.
- Scope boundary: The location resolver; the Drive v3 metadata and download client with a
  read-only service-account key from `KN_GDRIVE_CREDENTIALS_FILE`; SHA-256 verification; safe
  unpacking with file-count and size limits, the staging run directory with its manifest, and the
  SATCOM commands as the first user. The module names no dataset, so `prefetched-dataset-method`
  reuses it.
  This task stages packages for the existing import. Commit to the shared archive in
  `prefetched-dataset-method`. No scheduler, no other Drive operation, and no link-sharing URLs.
- Data and artifact paths: `src/kn/engine/packages/`, `Makefile`, `.env.example`, `pyproject.toml`,
  `uv.lock`, `$KN_RAW_ARCHIVE_DIR/staging/space/satcom/`, `tests/engine/`.
- Execution path: Write failing tests first: one snapshot identity from a fixture directory, its
  ZIP, and the Drive stub; `not_modified`; hostile ZIPs; a Google-native item; a SHA-256 mismatch; a
  missing key file; and no key path or token in logs. Then implement, adding `google-auth` as the
  one runtime dependency with its lock update.
- Acceptance gates: The prefetched-dataset evaluation items pass on fixtures without network access.
  `make satcom-fetch satcom-import` from a ZIP of `.data/satcom_enriched_package` reaches the
  existing snapshot `7ec6001f...` as a no-op. Output and logs hold no key material. `make ci`
  passes.
- Documentation target: `current/data-contracts.md` listed in the [areas index](current.md#areas).

#### prefetched-dataset-method

Owner-supplied datasets arrive as prefetched files. The SATCOM package is the first of several, but
its integration is dataset-specific code beside the engine.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `mapping-and-quality-rules`, `dataset-package-locations`
- Dependencies: Finding DC-16 of the [data contracts audit](records/0017-data-contracts-data-contracts-implementation-audit.md#findings),
  the current [SATCOM import](current/data-contracts.md#source-preservation-and-import) as the first
  dataset, and the `bulk_file` access method of the
  [crawler configuration](../design/spec.md#source-management).
- User-visible outcome: A prefetched dataset is a source with a reviewed configuration. `kn source
  run` reads its supplied package directory, archives the package in the raw archive, and loads the
  typed projection and raw cells through the engine loader. SATCOM moves to this path with its data,
  tests, and evidence unchanged, and a further dataset needs only its contract, configuration, and
  parser.
- Scope boundary: A package profile in the source configuration (expected files and headers, CSV
  dialect, snapshot identity); package locations from `dataset-package-locations`, with the
  location variable named in the configuration; shared import, file, and raw-cell bookkeeping keyed
  by source ID
  instead of per-dataset tables; a `kn.sourceProfile` that is not fixed to `satcom-csv/1`; archive
  placement in committed blob batches under `$KN_RAW_ARCHIVE_DIR/captures/`; and replay from the
  archive. Preserve every SATCOM file byte for byte and keep every cell.
  Execute no formulas or SQL. Identical bytes are a no-op. No fetching from the network.
- Data and artifact paths: `src/kn/engine/`, `src/kn/domains/space/satcom/`,
  `domains/space/sources/`, `tests/engine/`, `tests/domains/space/satcom/`.
- Execution path: Add a second synthetic fixture dataset with failing tests first, then move the
  generic parts of the SATCOM adapter into the engine until both pass with the SATCOM suite
  unchanged.
- Acceptance gates: Both datasets import, re-import as a no-op, and come back identically from the
  archive. No core module names a dataset. A tampered archive and a package with a missing or extra
  file are refused. `make ci` passes.
- Documentation target: `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### capture-retention-enforcement

Captures record an expiry and a deletion scope, but nothing withdraws a capture whose retention
ended, claims that cite a withdrawn capture never become `evidence_tombstoned`, and a purge leaves
no record beyond its tombstone. Restoring a backup taken before a purge therefore brings the
removed bytes back while `kn raw verify` still reports success.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `source-management-implementation-audit`
- Dependencies: Findings RAA-07 and RAA-08 of the [raw archive
  audit](records/0057-raw-archive-raw-archive-implementation-audit.md#findings), the retention rules
  of the [fetch ledger specification](../design/spec.md#capture-schema-and-fetch-ledger), and the
  current [withdrawal interface](current/raw-archive.md#layout-and-withdrawal).
- User-visible outcome: The engine withdraws each capture whose source policy or expiry ends its
  retention, with a reason code, and purges it where its deletion scope requires. Claims that cite
  it become `evidence_tombstoned` and stay so after a rebuild. A purge leaves a durable record, so
  verification of a restored archive names every purged capture whose bytes came back until the
  purge is applied again.
- Scope boundary: Expiry and policy selection, the purge record as a new versioned archive file
  that leaves version 1 tombstones readable, claim status changes and their replay, and the restore
  report. Rights decisions stay with source management and schedules with orchestration.
- Data and artifact paths: `src/kn/archive/`, `src/kn/engine/`, `tests/archive/`, `tests/engine/`.
- Execution path: Fixture-first. Expire one of two captures and withdraw a revisit target with a
  purge. Restore a backup taken before the purge with the current tombstones, verify, and purge
  again.
- Acceptance gates: An expired capture is withdrawn once, and a rerun writes nothing new. Its
  claims are `evidence_tombstoned` before and after a rebuild. Verification of the restored backup
  names each purged capture until the purge is applied again. Afterwards its bytes are gone and
  every retained capture replays. The `committed-v1` archive fixture still reads. `make ci` passes.
- Documentation target: `current/raw-archive.md` and `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### rebuild-from-raw

Schema changes during development must cost a rebuild, never a re-fetch or a lost decision.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `curated-source-method`, `prefetched-dataset-method`, `capture-retention-enforcement`
- Dependencies: none.
- User-visible outcome: `kn db rebuild` replays the committed archive, curated files, prefetched
  datasets, and decision logs through current code, and reports orphaned decisions. It can replay
  after the loss of the raw ledger.
- Scope boundary: Replay ordering, the replay of every source suite in `make ci-local`, and
  canonical row-hash comparison. No network access during rebuild.
- Data and artifact paths: `src/kn/db/`, `src/kn/engine/replay.py`, `tests/integration/`.
- Execution path: Rebuild the fixture archive twice and compare row hashes of all canonical tables.
- Acceptance gates: Two rebuilds are identical, including one with the ledger removed. A network
  call during rebuild fails the test.
  A tombstoned input stays suppressed after reindex and replay. Decisions re-attach or are reported.
  Human-verification times, reviewers and decision IDs survive replay exactly. A changed or missing
  target remains stale, pending or orphaned, and never receives a newly fabricated verification.
  `make ci-local` runs the rebuild on every change, and `make ci` stays green without a database.
- Documentation target: `current/ingestion-engine.md` listed in the
  [areas index](current.md#areas).

#### fragment-claims-follow-splits

A weak-key fragment claims through its parent record's link and has no link of its own, so a split
cannot assign its claims. They leave lineage and canonical selection until the raw replay tracks
the fragment again.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: Finding OIA-05 of the [object identity
  audit](records/0049-object-identity-object-identity-implementation-audit.md#findings) and the
  `claim_successor_missing` gap of the [lineage lookup](current/object-identity.md#lineage-lookup).
- User-visible outcome: After a split, each claim of a weak-key fragment belongs to the successor
  that holds its parent record, in `kn lineage` and in the fact projection, without a rebuild.
- Scope boundary: Durable fragment-to-parent lineage in the identity journal, added as an optional
  field so existing v1 event hashes stay valid, and its use by the lineage view and the fact
  projection. Splits still assign links, identifiers and attributes. Tracking never runs the
  matcher.
- Data and artifact paths: `src/kn/identity/`, `src/kn/evidence/`, `contracts/core/identity/`,
  `tests/identity/`, `tests/evidence/`.
- Execution path: Start from `test_a_fragment_claim_that_no_split_successor_holds_is_a_gap`. Track a
  parent and a fragment, split the parent's object, then project facts and look up both successors.
- Acceptance gates: The fragment's claims appear under exactly one successor in lineage and the
  fact projection, and no `claim_successor_missing` gap remains. A parent record relinked to another
  object takes later fragment claims with it. Existing v1 journals replay with unchanged hashes.
  `make ci` passes.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).

#### ingestion-engine-implementation-audit

Every source runs through the engine, so a defect in fetch safety, mapping, or replay would recur in
every source suite and every rebuild.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `http-fetch-safety`, `mapping-and-quality-rules`, `curated-source-method`,
  `dataset-package-locations`, `prefetched-dataset-method`, `rebuild-from-raw`,
  `fragment-claims-follow-splits`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Every source runs on a verified, source-neutral engine. The audit record
  gives every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: the TDD growth rule, with no source-specific branches in general engine
  code; allowlist, redirect, TLS, size, timeout, and rate-limit enforcement; retry and backoff with
  `Retry-After`; pagination end and a lost cursor; encoding and content-type detection; partial
  records and change sets; quality rule severities; citation checks on curated rows; replay and
  rebuild with identical claims; interruption and resume; throughput at the declared volume. Fixes
  only; new behavior becomes plan tasks.
- Data and artifact paths: `src/kn/engine/`, `src/kn/db/`, `domains/fixture/`, `tests/engine/`,
  `tests/integration/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Run
  every source suite and a rebuild from the fixture archive. Plant a redirect to a host outside the
  allowlist, an oversized body, a mislabeled encoding, a lost cursor, and a run stopped midway.
- Acceptance gates: Each planted fetch hazard is refused or recovered as the specification states. A
  rebuild reproduces every claim. No engine module branches on a source ID. Every finding has a
  severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/ingestion-engine.md` listed in the [areas index](current.md#areas).

### Parts and measurements -- `part-supply-model`

#### vendor-information-coverage

The knowledge base must hold everything vendors publish about a part, so the target field set has
to be known before the contracts are fixed.

- Serves: `part-supply-model` -- [Part and supply model](../design/spec.md#part-and-supply-model)
- Agent status: CLEAR
- Execution stage: MODEL
- Research: yes
- Dependencies: Public documentation of representative vendor channels: manufacturer product pages
  and datasheets for the watchlist families, distributor API documentation for the catalogue rows
  C01-C03, and the InvenTree API schema. The 195 pending microelectronics attribute dictionary rows
  in the
  [seed reconciliation](current/ontology-taxonomy/seeds.md#unmapped-rows-and-ownership).
- User-visible outcome: The coverage matrix `contracts/core/supply/coverage.yaml` maps every
  information group in the specification to field IDs or an exclusion. It lists each studied
  channel's documented fields with a classification and licence notes on caching and
  redistribution.
- Scope boundary: Documentation reading only; no data endpoints are called. Field IDs are proposed
  here and fixed in `supply-model-contracts`.
- Data and artifact paths: `contracts/core/supply/coverage.yaml`, `tests/supply/`, and the task
  record.
- Execution path: Read each channel's public field documentation and classify every field. Add a
  test that fails on an unclassified group or field.
- Acceptance gates: Every group has field IDs or an exclusion reason. Every documented channel field
  is mapped, raw-only, or excluded with a reason. A channel whose documentation is inaccessible is
  recorded as a blocker, which is a valid negative result.
- Documentation target: A new `current/part-supply-model.md` page listed in the
  [areas index](current.md#areas).

#### supply-model-contracts

Parts, orderable variants, and supplier offers need typed, identity-aware contracts that every
domain and counterpart shares.

- Serves: `part-supply-model` -- [Part and supply model](../design/spec.md#part-and-supply-model)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `vendor-information-coverage`
- Dependencies: none.
- User-visible outcome: The `supply` schema holds organization roles, product families and models,
  manufacturer parts, orderable variants, and supplier offers. It also holds price, stock, and
  lead-time observations, declared lifecycle, compliance and trade claims, physical and packaging
  attributes, document references, and substitute relations. Each identity class has a match
  profile.
- Scope boundary: Contracts, constraints, selection policies for supply fields, and fixtures.
  Own the shared attribute dictionary, typed measurement/observation shapes, unit/condition rules
  and comparison-profile interfaces from the vendor coverage work. Domains extend these definitions
  instead of supplying a competing base later. Author match profiles against the early identity
  profile schema; no scored matcher or source parser is needed to validate the model.
- Data and artifact paths: `contracts/core/supply/`, `src/kn/supply/`, `tests/supply/`.
- Execution path: Write the contracts from the coverage matrix, compile, and rebuild. Add
  fixture-first tests for the specification's rules.
- Acceptance gates: One MPN from two manufacturers is two parts. Packaging variants give one
  manufacturer part, two orderable variants, two offers, and one part count. A price break without
  quantity, currency, or observed time is rejected. Stock observations form a time series with
  stale labels. A substitute never merges identities. Origin is never inferred from headquarters.
- Documentation target: `current/part-supply-model.md` listed in the
  [areas index](current.md#areas).

#### part-supply-model-implementation-audit

The supply model is shared by the microelectronics domain and the InvenTree exchange, so a missing
field or a wrong key would spread into both.

- Serves: `part-supply-model` -- [Part and supply model](../design/spec.md#part-and-supply-model)
- Agent status: CLEAR
- Requires: `vendor-information-coverage`, `supply-model-contracts`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: The domain and exchange groups extend a verified supply model. The audit
  record gives every check a result and every finding a disposition. The current-state page lists
  known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: coverage matrix completeness, with every vendor field mapped, raw-only, or
  excluded with a reason; MPN normalization and manufacturer aliases; supplier SKU, packaging, and
  pack quantity; price breaks with currency and observation time; lifecycle and availability states;
  parameter units and qualifiers; extension by a domain without redefinition; mapping to the
  interchange contract and InvenTree resources. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/supply/`, `src/kn/supply/`, `tests/supply/`,
  `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Load
  MPNs that differ only in case, punctuation, or a packaging suffix, a price break in a second
  currency, and a vendor field missing from the coverage matrix.
- Acceptance gates: The coverage test fails on any unlisted vendor field. MPN variants resolve as
  the identity rules require. A domain contract that redefines a supply field is refused. Every
  finding has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix
  starts from a failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/part-supply-model.md` listed in the [areas
  index](current.md#areas).

### Versioned exchange and synchronization -- `data-interchange`

#### interchange-contract

Exchange with any counterpart needs one versioned, documented shape for KN objects.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `part-supply-model-implementation-audit`
- Dependencies: none.
- User-visible outcome: The versioned interchange record and package-manifest schemas at `0.1.0`
  compile to JSON Schema before a runtime exporter exists. Stable object, field and verification
  records give every adapter one early compatibility boundary.
- Scope boundary: Object, identifier, field, relation, missingness, provenance, human verification,
  lifecycle, full/delta manifest and loss-report definitions. Snapshot queries, ZIP writing and
  CLI behavior belong to `interchange-package-export`.
- Data and artifact paths: `contracts/interchange/`, `src/kn/interchange/`, `tests/interchange/`.
- Execution path: Compile the record and manifest definitions; validate synthetic examples for
  each supply class, composite key, lifecycle state, field change and optional verification scope.
- Acceptance gates: Valid fixtures round-trip exactly; invalid references, missing reasons,
  versions and verification metadata fail with diagnostics. Full/delta and rights/loss metadata
  have fixed schemas. No runtime tracker, human projection, raw replay or counterpart is needed.
  `make ci` passes.
- Documentation target: A new `current/data-interchange.md` page listed in the
  [areas index](current.md#areas).

#### interchange-schema-evolution

Both the interchange contract and counterpart schemas will change. Each change must be classified
before it can break an exchange.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `interchange-contract`
- Dependencies: none.
- User-visible outcome: `kn interchange diff` classifies contract changes as compatible, additive,
  or breaking, and CI fails on an undersized version bump. Upgrade steps chain older packages to
  the current version. The same classifier compares normalized external schema snapshots for
  adapter profiles.
- Scope boundary: A diff keyed by field ID; the version-bump gate; the upgrade-step format and
  runner; extension data for unknown newer-minor fields; refusal of newer majors; older-version
  export with a loss report; the external schema-fact model with its `compatible`,
  `compatible_with_review`, and `breaking` classes. A second contract version exists only as a test
  fixture.
- Data and artifact paths: `contracts/interchange/upgrades/`, `src/kn/interchange/evolution/`,
  `tests/interchange/`, `tests/fixtures/interchange/`.
- Execution path: Write diff fixtures for every row of the specification's change table and every
  external change type, then the classifier and the upgrade runner.
- Acceptance gates: Each fixture change gets its declared class. An undersized bump fails the check.
  A `0.1.0` fixture package read through the chain equals direct fixture serialization at that version.
  Unknown newer-minor fields round-trip byte-identically, and a newer major is refused. An
  older-version export with an unmappable field is refused with a loss report.
- Documentation target: `current/data-interchange.md` listed in the
  [areas index](current.md#areas).

#### exchange-ledger-contracts

Bindings, plans and receipts must have stable storage before synchronization algorithms or a live
counterpart begin creating durable references.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `interchange-contract`
- Dependencies: The ledger and synchronization states in the specification, using synthetic
  counterpart IDs and authored object/version fixtures rather than a live service.
- User-visible outcome: Registered contracts define counterpart bindings, field ownership,
  three-way versions/hashes, plans, approvals, receipts, conflicts and resumable operation keys.
- Scope boundary: Schema, deterministic keys, uniqueness and version constraints, provenance,
  rights and verification references, and model-only replay. Counterpart calls, sync decisions,
  crash recovery and merge handling remain in `exchange-binding-ledger`.
- Data and artifact paths: `contracts/core/interchange/`, `src/kn/contracts/resources/`,
  `src/kn/interchange/ledger/`, `tests/interchange/`, `tests/integration/`.
- Execution path: Compile and rebuild the ledger with synthetic rows covering every state and
  every later receipt field; plant duplicate bindings, mismatched versions and incomplete keys.
- Acceptance gates: The compiled model preserves all three comparison versions and idempotency
  keys, rejects duplicate active bindings, and round-trips approvals/receipts with provenance.
  Fixture replay is deterministic without lineage CLI, a sync engine or a counterpart endpoint.
  `make ci` and integration checks pass.
- Documentation target: A new `current/data-interchange.md` page listed in the
  [areas index](current.md#areas).

#### interchange-package-export

The early interchange schema needs a runtime exporter once canonical selection and change
tracking are available.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Requires: `interchange-contract`
- Dependencies: The accepted interchange schema and manifest definitions.
- User-visible outcome: `kn interchange export` writes an atomic, verified deterministic ZIP
  from one snapshot; `kn interchange validate` checks a package against its declared version.
- Scope boundary: Runtime snapshot queries, full/delta selection, rights filtering and excluded
  counts, packaging and validation. Consume the early contracts without redefining their fields.
- Data and artifact paths: `src/kn/interchange/`, `$DATA_DIR/interchange/<run-id>/`,
  `tests/interchange/`.
- Execution path: Export rebuilt fixture objects, including a merged/retired object, changed
  fields, human review metadata and restricted evidence; verify the manifest and every file.
- Acceptance gates: Two exports are byte-identical and every hash verifies. Restricted data is
  absent and counted. Lifecycle redirects and delta watermarks remain correct. Optional human
  metadata preserves nulls, purpose and target version; unsupported fields appear in the loss
  report. A partial package never becomes visible. `make ci` passes.
- Documentation target: `current/data-interchange.md` listed in the [areas index](current.md#areas).

#### exchange-binding-ledger

Repeated exchanges need durable bindings and sync state, so nothing is resent blindly or
overwritten unseen.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Requires: `exchange-ledger-contracts`
- Dependencies: none.
- User-visible outcome: The append-only exchange ledger in `$DATA_DIR/exchange/<counterpart>/`
  records bindings, per-field sync state, plans, and receipts, and rebuild replays it into the
  `interchange` schema. `kn lineage` shows outbound receipts.
- Scope boundary: The ledger format and replay, field ownership, echo suppression of values KN
  wrote, the three-way comparison, redirect handling for bindings of merged objects,
  duplicate-binding detection, and crash recovery that reads counterpart state instead of resending.
  No counterpart adapter.
  Consume the early exchange-ledger contract for every binding, version, plan and receipt; this
  task owns synchronization behavior rather than a second schema definition.
- Data and artifact paths: `contracts/core/interchange/`, `src/kn/interchange/ledger/`,
  `$DATA_DIR/exchange/`, `tests/interchange/`.
- Execution path: Use fixture ledgers and a fake counterpart that records calls. Cover every sync
  state and a crash between a call and its receipt.
- Acceptance gates: Replay reproduces bindings and sync state. Each three-way fixture gives its
  declared action. A counterpart value equal to KN's last write creates no claim, and a different
  value becomes a counterpart claim. Two bound objects that merge produce one redirect and one
  duplicate-binding conflict, and no write. A simulated crash recovers without a duplicate call.
- Documentation target: `current/data-interchange.md` listed in the
  [areas index](current.md#areas).

#### interchange-package-import

A package must come back into KN as evidence, with its identity and provenance intact.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Requires: `interchange-schema-evolution`, `interchange-package-export`,
  `ingestion-engine-implementation-audit`
- Dependencies: none.
- User-visible outcome: `kn interchange import <package>` commits the original ZIP as a blob
  capture and loads it through the engine. KN IDs resolve directly for the same producer, and
  identifiers and attributes resolve them for other producers. Each imported claim cites the
  package and the original provenance reference.
- Scope boundary: The package source method under the same update policies (a package never
  clears or deletes by omission), rights checks on import, and round-trip tests. Packages from
  other producers default to `owner_private` rights until reviewed.
- Data and artifact paths: `src/kn/interchange/importer.py`, `tests/interchange/`,
  `tests/integration/`.
- Execution path: Export a fixture domain, rebuild empty, import, and compare.
- Acceptance gates: The round trip into an empty rebuild reproduces objects, KN IDs, values, missing
  reasons, and provenance references. A second import is idempotent. A delta package changes only
  its fields. An older upgradable package imports through the chain. A package with a forbidden
  licence is refused.
- Documentation target: `current/data-interchange.md` listed in the
  [areas index](current.md#areas).

#### data-interchange-implementation-audit

The interchange contract is the versioned external boundary, so a design flaw found after
counterparts depend on it costs a major contract version.

- Serves: `data-interchange` -- [Data interchange](../design/spec.md#data-interchange)
- Agent status: CLEAR
- Requires: `interchange-contract`, `interchange-schema-evolution`, `exchange-ledger-contracts`,
  `interchange-package-export`, `exchange-binding-ledger`, `interchange-package-import`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Counterpart adapters build on a verified, versioned boundary. The audit
  record gives every check a result and every finding a disposition. The current-state page lists
  known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: semver rules and the diff classifier; upgrade steps across every supported
  version; package integrity and partial packages; binding uniqueness and field ownership; echo
  suppression under rounding, unit, and whitespace normalization; three-way conflict states; lost or
  duplicated receipts; a package from a newer contract version; loss reports; a second counterpart
  type through adapter profiles without contract changes. Fixes only; new behavior becomes plan
  tasks.
- Data and artifact paths: `contracts/interchange/`, `contracts/core/interchange/`,
  `src/kn/interchange/`, `tests/interchange/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks.
  Classify planted compatible and breaking diffs, import a package twice and out of order, plant an
  echo that differs only by rounding, and import a package that declares a newer minor version.
- Acceptance gates: Every planted diff gets its expected class. Repeated and reordered imports are
  idempotent. An echo never becomes a new claim. A package from an unknown major version is refused
  with a report. Every finding has a severity, evidence, and a disposition, no `blocker` is
  accepted, and every fix starts from a failing regression test. `make ci` passes with the scheduled
  tasks in the plan.
- Documentation target: `current/data-interchange.md` listed in the [areas index](current.md#areas).

### InvenTree adapter and upgrade -- `inventree-exchange`

#### inventree-test-service

Compatibility claims need the target InvenTree release to test against, isolated from the owner's
instance.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Dependencies: Docker Engine with Compose v2. The joint target release is InvenTree `1.7.3` (API
  version 570), pinned by the `vl-itree` release `v0.1.0`. Its
  [target release](../design/integrations/inventree.md#target-release) table gives the InvenTree,
  PostgreSQL, Redis, and Caddy image tags and digests.
- User-visible outcome: `make inventree-up` and `make inventree-down` run the target release in
  the Compose `inventree` profile with its own database. `INVENTREE_RELEASE=<tag>` starts a
  candidate release beside it for the upgrade check. A seed command loads one synthetic catalogue:
  companies, manufacturer parts, supplier parts, price breaks, parameter templates, parameters,
  categories, parts, and attachment links.
- Scope boundary: Test-only services on an internal network with loopback access for tests, a
  TLS proxy with a generated test CA so that certificate verification is exercised, generated
  non-secret credentials, the seed script, and the four image tags and digests plus the
  `vl-itree` release tag in `deploy/versions.yaml`. No connection to an owner instance.
- Data and artifact paths: `deploy/compose.yaml`, `deploy/inventree/`, `deploy/versions.yaml`,
  `tests/fixtures/inventree/seed/`, `Makefile`.
- Execution path: Pin the four images by the tags and digests of `vl-itree` `v0.1.0`, start them
  from empty volumes, and seed the service through the API.
- Acceptance gates: The target release reaches healthy from empty volumes, and `GET /api/` reports
  version `1.7.3` and API version 570. The seed loads the
  catalogue, and the API reports the expected counts. No port is published beyond loopback.
  `make ci` stays green without Docker.
- Documentation target: A new `current/inventree-exchange.md` page listed in the
  [areas index](current.md#areas).

#### inventree-schema-registry

The adapter must know which InvenTree API it is talking to, and must notice when an instance stops
matching the reviewed target.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-test-service`, `data-interchange-implementation-audit`,
  `ingestion-engine-implementation-audit`
- Dependencies: The pinned test service.
- User-visible outcome: `kn inventree probe --instance <id>` reports the software version, API
  version, schema digest, and selected profile. `kn inventree schema capture` archives the API
  root and the OpenAPI schema to WARC and writes a normalized snapshot with its digest to
  `interchange/inventree/schemas/<api-version>/`. `kn inventree schema diff` reports the
  compatibility of two snapshots for the mapped subset.
- Scope boundary: The probe, capture, normalization into schema facts, and the reviewed snapshot
  of the target release. Classifier fixtures for the
  [documented change kinds](../design/integrations/inventree.md#diff-classifier-fixtures). The
  design page's verification items, checked on the target release. No snapshots of earlier
  releases.
- Data and artifact paths: `src/kn/interchange/inventree/`, `interchange/inventree/schemas/`,
  `tests/interchange/inventree/`, `tests/fixtures/inventree/`.
- Execution path: Capture the target release twice, compare the digests, and run the classifier
  over mutated copies of the snapshot.
- Acceptance gates: Two captures give identical normalized digests. Planted removals, renames,
  read-only changes, filter renames, and endpoint moves of mapped fields are `breaking`, and an
  added optional field is `compatible`. An unreachable or non-InvenTree host fails with a declared
  error code.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-adapter-profiles

The target release needs one reviewed mapping to the interchange contract, with a safe policy for
instances that drift from it.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-schema-registry`, `part-supply-model-implementation-audit`
- Dependencies: The [resource mapping](../design/integrations/inventree.md#resource-mapping).
- User-visible outcome: The target profile in `interchange/inventree/profiles/` maps each resource
  in the design page to interchange field IDs. It records endpoints, filters, cursors, the binding
  location, capability flags, default field owners, and a loss report. The probed schema digest
  selects the profile.
- Scope boundary: The target profile, the drift policy (reads only on a compatible diff, writes
  refused), and a validator that resolves every mapped field in the target snapshot.
- Data and artifact paths: `interchange/inventree/profiles/`,
  `src/kn/interchange/inventree/profiles.py`, `tests/interchange/inventree/`.
- Execution path: Validate the profile against the target snapshot, and generate the loss report
  from the supply model.
- Acceptance gates: Every mapped field resolves in the target snapshot. The loss report classifies
  every supply field as native, parameter, metadata, or not representable. A drifted schema is
  refused for writes, and allowed for reads only with a compatible diff.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-read-import

InvenTree data must enter KN as evidence matched to existing objects, and change them only through
the update policies.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-adapter-profiles`, `data-interchange-implementation-audit`,
  `ingestion-engine-implementation-audit`
- Dependencies: The pinned test service. No owner instance is used here.
- User-visible outcome: An InvenTree instance profile runs as an `adapter_api` source through
  `kn source run` and `kn source replay`. Allowlisted resources are archived, mapped through the
  profile, change-tracked per record, and resolved to KN IDs. Identity resolves by binding, then
  source-qualified ID, then MPN and manufacturer or supplier and SKU, then scored match.
  Owner-entered values carry the `owner_entered` rank, and values KN wrote come back as echoes.
- Scope boundary: The instance profile schema (crawler blocks plus `exchange`), `owner_private`
  rights, the resource allowlist, `limit` pagination, `updated` cursors where declared and
  otherwise full listings compared by record hash, metadata binding reads, the
  `counterpart_missing` binding state, HTTPS with certificate verification and an optional CA
  file for non-loopback instances, and the instance template. No writes.
- Data and artifact paths: `interchange/inventree/instances/`, `src/kn/interchange/inventree/`,
  `tests/interchange/inventree/`, `tests/fixtures/inventree/`.
- Execution path: Work fixture-first against recorded WARC from the target release, then run live
  against the test service.
- Acceptance gates: The synthetic catalogue yields the same KN objects, IDs, and claims on every
  run, and a second run is idempotent. A part deleted in InvenTree marks its binding
  `counterpart_missing` and deletes nothing in KN. An owner-entered InvenTree value wins over a
  manufacturer value and is flagged `owner_override`. A value KN wrote earlier creates no
  claim. A non-loopback connection over plain HTTP, or with a failing certificate, is refused.
  Contacts, users, orders, and notes are never requested.
  Replay without network reproduces the import, and a rebuild keeps every KN ID.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-write-export

KN knowledge must reach InvenTree only through deterministic, approved, verifiable plans.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-read-import`
- Dependencies: none.
- User-visible outcome: `kn inventree plan` writes a dry-run plan with per-field changes, owners,
  conflicts, a loss report, and a request estimate. `kn inventree apply --plan <id>` applies an
  approved plan in dependency order, with idempotent writes, metadata bindings, read-back checks,
  and receipts. Exchange conflicts reach the review queue.
- Scope boundary: Writes for companies, parameter templates, manufacturer parts, supplier parts,
  price breaks, parameters, and attachment links. Part and category creation sits behind an
  export-profile flag. No deletion. Only licence-filtered values. Throttling and request budgets
  apply. Apply refuses an instance profile without a write approval reference, and an instance
  whose schema digest differs from the profile.
- Data and artifact paths: `src/kn/interchange/inventree/export/`, `$DATA_DIR/exchange/inventree/`,
  `tests/interchange/inventree/`.
- Execution path: Work fixture-first with recorded responses, then run live on the test service.
- Acceptance gates: A plan is deterministic. A second apply is a no-op. Every written value reads
  back equal. A manual InvenTree edit to a KN-owned field is imported as an owner claim and never
  overwritten. A no-redistribution value never appears in a plan. An unapproved or drifted instance
  refuses to apply.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-upgrade-check

InvenTree releases arrive on their own schedule. Each candidate must be checked before `vl-itree`
or the joint target moves to it.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-write-export`
- Dependencies: The candidate release image, pulled by tag and digest.
- User-visible outcome: `kn inventree upgrade-check --release <tag>` starts the candidate beside
  the target, seeds it, captures and diffs its schema, runs the import and export suite against
  it, and writes a compatibility report. The report lists the profile changes needed before
  `vl-itree` may move.
- Scope boundary: The command, the report, and the procedure for promoting a candidate to the joint
  target (new snapshot, new or extended profile, version manifest, and the matching `vl-itree`
  tag). No change to a live instance.
- Data and artifact paths: `src/kn/interchange/inventree/upgrade.py`,
  `$DATA_DIR/exchange/upgrade-check/<run-id>/`, `docs/guide/inventree-upgrade.md`,
  `tests/interchange/inventree/`.
- Execution path: Run the check with the target as its own candidate, then with a fixture
  candidate whose schema carries planted changes.
- Acceptance gates: The target checked against itself reports `compatible` and a passing suite.
  The fixture candidate reports each planted change with its class and the affected profile
  fields. A failing suite blocks promotion.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-exchange-implementation-audit

InvenTree is an uncontrolled third party, so drift, permission, and partial-failure handling must
hold before the owner's inventory depends on the adapter.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-test-service`, `inventree-schema-registry`, `inventree-adapter-profiles`,
  `inventree-read-import`, `inventree-write-export`, `inventree-upgrade-check`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. The checks run against the
  test service on the target release. `vl-itree-read-acceptance` and `vl-itree-write-acceptance`
  stay open and are reviewed for the readiness of their inputs.
- User-visible outcome: Owner instance runs start from a verified adapter. The audit record gives
  every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: probe and drift handling, with reads only on a compatible diff and writes
  refused; token expiry and permission errors per role; throttling with `429` and `Retry-After`;
  `limit` pagination under concurrent edits; locked objects (`409`); partial failure during apply,
  with resume and read-back; duplicated InvenTree objects and metadata KN IDs without bindings; echo
  suppression for values InvenTree normalizes; refusal of non-loopback plain HTTP; the upgrade check
  against the next release. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/inventree/`, `src/kn/interchange/inventree/`,
  `interchange/inventree/`, `tests/interchange/inventree/`, `docs/impl/plan.md`, and the task
  record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Stop an
  apply midway and resume it. Plant a `409`, a `429`, a revoked token, and an edited schema
  snapshot, and duplicate a bound part in the test service.
- Acceptance gates: An interrupted apply resumes without duplicate writes. Each planted error maps
  to its error code and stops or retries as the specification states. A duplicated bound part is a
  conflict. Every finding has a severity, evidence, and a disposition, no `blocker` is accepted, and
  every fix starts from a failing regression test. `make ci` passes with the scheduled tasks in the
  plan.
- Documentation target: `current/inventree-exchange.md` listed in the [areas
  index](current.md#areas).

### Owner instance exchange and calibration -- `counterpart-acceptance`

#### vl-itree-read-acceptance

The owner's instance must import correctly on the target release before any write is proposed.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: RUN NEEDED
- Requires: `inventree-exchange-implementation-audit`, `provide-inventree-instance-access`,
  `align-vl-itree-release`
- Dependencies: Read access to `vl-itree` on the target release over HTTPS, its CA certificate if
  it uses the proxy's internal CA, and network access to it from the run host.
- User-visible outcome: An archived schema capture and a read-only import of `vl-itree`, with the
  reviewed instance profile, and a report of losses, unmapped resources, identity matches, and
  update-policy outcomes.
- Scope boundary: Read-only capture and import within a request budget. No writes.
- Data and artifact paths: `interchange/inventree/instances/vl-itree.yaml`, `$KN_RAW_ARCHIVE_DIR`,
  `$DATA_DIR/exchange/vl-itree/<run-id>/`, and the task record.
- Execution path: Probe, confirm the target digest, capture, and import. Then replay the import
  without network.
- Acceptance gates: The probe matches the target snapshot digest over verified TLS. The replay gives
  identical KN objects. Every unmapped native field is listed with a reason. The request count stays
  within the budget.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### identity-match-calibration

Match probabilities mean something only after they are measured on real records.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: RUN NEEDED
- Research: yes
- Requires: `vl-itree-read-acceptance`
- Dependencies: Archived authorized samples that carry authoritative identifiers, starting with the
  `vl-itree` read import and the first vendor sources. Owner-labeled pairs are optional. The
  [match resolution](current/object-identity.md#match-resolution) gates, including the veto by a
  disagreeing discriminating attribute, define which held-out pairs count as automatic links.
- User-visible outcome: A calibration report per class gives precision and recall at both
  thresholds and the calibration error per probability band. Profiles that meet the gate are marked
  `calibrated` and may auto-link.
- Scope boundary: Ground truth comes from pairs proven by authoritative identifiers, with those
  identifiers masked, plus reviewer decisions. Weights and thresholds change only through reviewed
  profile edits. No learned matcher.
- Data and artifact paths: `contracts/core/identity/match-profiles/`,
  `$DATA_DIR/identity-eval/<run-id>/`, `tests/identity/`, and the task record.
- Execution path: Replay the archived samples, build masked pair sets, and fit and evaluate weights
  on held-out folds.
- Acceptance gates: Each calibrated class reaches at least 0.99 precision at the link threshold on
  at least 200 held-out positive pairs. A class that misses the gate stays review-only. That is a
  valid negative result, recorded in the closed-research register.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).

#### vl-itree-write-acceptance

The first write into the owner's inventory must apply exactly as approved and verify itself.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: RUN NEEDED
- Requires: `approve-inventree-write-exchange`, `inventree-exchange-implementation-audit`
- Dependencies: The write approval, and a write-capable token for the `kn-exchange` user in the
  environment.
- User-visible outcome: The approved first plan is applied to `vl-itree` with receipts and
  read-back. A re-import shows the written values bound to unchanged KN IDs.
- Scope boundary: The approved plan only. Later exchanges use the same commands.
- Data and artifact paths: `$DATA_DIR/exchange/vl-itree/`, and the task record.
- Execution path: Re-plan, confirm the plan equals the approved one, apply, re-import, and compare.
- Acceptance gates: Every read-back is equal. A second apply is a no-op. KN IDs and bindings are
  unchanged after the re-import. Any read-only or lost field is in the report.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### counterpart-acceptance-implementation-audit

Verify the owner instance exchange and calibration handoff against its specification and the next consumer.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: RUN NEEDED
- Requires: `vl-itree-read-acceptance`, `identity-match-calibration`, `vl-itree-write-acceptance`
- Dependencies: Group acceptance records and the
  [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Reconcile the authorized read and write receipts against the owner-approved
  fields. Recompute held-out precision with authoritative identifiers masked and
  verify the calibration decision.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: [Current-state areas](current.md#areas).

### Space collection and replay -- `space-elt`

#### space-domain-contracts

Canonical space tables must represent the preserved source examples without conflating their meanings.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: [Space domain model](../design/domains/space.md#domain-model) and the initial
  [space example dataset](current/data-contracts.md#source-preservation-and-import).
- User-visible outcome: The `space` schema holds every pilot table, with claim links,
  coverage-kind and availability vocabularies, and space selection policies.
- Scope boundary: Contracts, domain policies, and fixtures. No source parsers.
  Adopt common identity, evidence and verification traits and declare extension points for source
  mappings. SQL/fixture rebuilds validate this task without a running ingestion pipeline.
  Resolve the physical/field-ID boundary between existing SATCOM snapshot projections and
  canonical space tables now. Never register two contracts over the same table or reinterpret
  imported rows as canonical facts. Any required internal rename has an explicit adapter/backfill
  mapping that preserves all source files, cells and snapshot identifiers.
- Data and artifact paths: `domains/space/contracts/`, `src/kn/domains/space/`,
  `tests/domains/space/`.
- Execution path: Write the contracts from the design page, add the missing ontology classes as
  reviewed seed rows as needed, compile, and rebuild. Resolve the two pending seed relations
  (regulatory Activity and EUSPA concept endpoints) without conflating classes and concepts.
- Acceptance gates: Every table compiles and rebuilds. Fixtures prove that planned and actual
  launches, cataloged and operational status, and recurring and one-time tariff amounts cannot be
  stored in the same field. Reuse the real SATCOM mixture to preserve model versus individual
  spacecraft identity, mass bases, claim qualifiers, financial bases and missing reasons.
- Documentation target: A new `current/space-domain.md` page listed in the
  [areas index](current.md#areas).

#### space-source-terms-review

Space sources need documented terms and limits before any sample is fetched.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Research: yes
- Dependencies: Public documentation for CelesTrak, Launch Library 2, Natural Earth, and the four
  candidate operators' terms of use.
- User-visible outcome: A terms dossier per pilot source (licence, rate limits, permitted access,
  redistribution, current API edition) and catalogue state `investigating`.
- Scope boundary: Documentation only; no data endpoints are called.
- Data and artifact paths: `domains/space/sources/dossiers/`, and the task record.
- Execution path: Follow the dossier template for each source and flag operator sites whose terms
  forbid automated access, so those go to the curated method.
- Acceptance gates: Every pilot source has a dossier or a recorded blocker. A source with
  prohibitive terms is valid as a negative result.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-source-celestrak-gp

Catalog identity and constellation snapshots start from CelesTrak GP data.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `authorize-space-source-sampling`, `space-domain-contracts`,
  `ingestion-engine-implementation-audit`
- Dependencies: Sampling authorization with a request budget. The CelesTrak usage policy.
- User-visible outcome: Selected constellation groups load as orbital element sets, spacecraft
  identities (NORAD and COSPAR as separate identifiers), and membership candidates with snapshot
  counts.
- Scope boundary: OMM JSON for the authorized groups only. No ephemeris, no coverage, and no
  operational status from orbit data. Engine improvements found here go into the core.
- Data and artifact paths: `domains/space/sources/celestrak_gp.yaml`,
  `src/kn/domains/space/celestrak.py`, `tests/fixtures/space/celestrak_gp/`,
  `$KN_RAW_ARCHIVE_DIR/captures/space/`.
- Execution path: Follow the onboarding workflow steps 3-4: bounded sample capture, investigation
  report, config, parser, sanitized fixtures, and failing tests first.
- Acceptance gates: Fixtures and the authorized sample load. A rerun creates no duplicates. A
  6-digit catalog number round-trips. The rebuild reproduces the result. All earlier suites pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-source-launch-library

Launch events, vehicles, providers, and pads come from Launch Library 2.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-source-celestrak-gp`
- Dependencies: Sampling authorization covering Launch Library 2. Its current rate limits and API
  version.
- User-visible outcome: Agencies, launcher configurations, launch events (scheduled and actual
  separate), pads, and manifest associations load with qualified IDs.
- Scope boundary: Upcoming and historical launches within the budget. Manufacturer and provider
  stay separate relations. The pad geometry precision is recorded.
- Data and artifact paths: `domains/space/sources/launch_library.yaml`,
  `src/kn/domains/space/launch_library.py`, `tests/fixtures/space/launch_library/`.
- Execution path: Follow the onboarding steps 3-4, with pagination and incremental cursors through
  the general engine.
- Acceptance gates: Planned and actual launches stay distinct. Payload links never invent
  spacecraft. Identities reconcile with CelesTrak only through qualified IDs. All earlier suites
  pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-source-natural-earth

Maps need versioned, licence-reviewed reference boundaries.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-source-launch-library`
- Dependencies: Sampling authorization and the Natural Earth terms. The neutral-boundary policy
  wording.
- User-visible outcome: Country polygons load with edition, validity, simplified BI copies, and
  the boundary-policy note.
- Scope boundary: A manual file source using the reviewed archive format for the release package.
  No disputed-border judgments.
- Data and artifact paths: `domains/space/sources/natural_earth.yaml`,
  `tests/fixtures/space/natural_earth/`.
- Execution path: Use a bulk-file method through the engine, PostGIS validity checks, and
  antimeridian fixtures.
- Acceptance gates: Every geometry is valid or repaired with an audit record. The originals are
  kept. All earlier suites pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-source-operator-disclosures

Service, tariff, and coverage facts need cited operator evidence.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-source-natural-earth`, `ingestion-engine-implementation-audit`
- Dependencies: Sampling authorization covering cited-page capture. A curator for at least two
  providers.
- User-visible outcome: Curated observations for at least two of the four candidate providers load
  as services, plans, tariff observations, metrics, and country-level coverage. Each carries a
  coverage kind, an availability status, and missing-price reasons.
- Scope boundary: Curated files and permitted page captures only. No address-based checks, no
  private endpoints, and no orbit-derived coverage.
- Data and artifact paths: `domains/space/curation/`, `domains/space/sources/operator_disclosures.yaml`,
  `tests/fixtures/space/operator_disclosures/`.
- Execution path: Write the curated-file schema for SATCOM observations from the design page, and
  fixture-first tests for comparability rules.
- Acceptance gates: Tariff fixtures keep recurring and one-time amounts, currency, tax, class, and
  date separate. A missing price records its reason. Coverage never comes from orbits. All earlier
  suites pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-elt-integration-gate

The space domain must prove its acceptance criteria on archived samples before dashboards.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-source-operator-disclosures`, `source-management-implementation-audit`
- Dependencies: Archived authorized samples from every pilot source.
- User-visible outcome: One command rebuilds the space domain from the archive and runs the
  identity, time, provenance, and conflation checks.
- Scope boundary: Verification and fixes in the existing parsers and engine. No new sources.
- Data and artifact paths: `tests/domains/space/`, `$DATA_DIR/runs/<run-id>/`.
- Execution path: Rebuild, query the acceptance assertions, and record source-specific limitations.
- Acceptance gates: Every [space ELT](../design/spec.md#space-elt) evaluation holds on archived
  samples. Provenance lookup works for a sampled fact from each source. The rebuild is identical
  twice.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-elt-implementation-audit

The space domain is the first real pilot, so the patterns its sources set are copied by every later
domain.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-domain-contracts`, `space-source-terms-review`, `space-source-celestrak-gp`,
  `space-source-launch-library`, `space-source-natural-earth`,
  `space-source-operator-disclosures`, `space-elt-integration-gate`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Later domains copy verified source patterns. The audit record gives every
  check a result and every finding a disposition. The current-state page lists known limitations,
  and each scheduled finding is a plan task.
- Scope boundary: Focus: source terms recorded and enforced per source; element set epochs, time
  scales, and stale element sets; NORAD ID reuse and catalog identity; scheduled and actual launch
  events and their revisions; boundary editions and disputed territories; operator claims with dates
  and conditions; source-specific code that belongs in configuration; the optional Space-Track and
  regulatory sources without contract changes. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `domains/space/`, `src/kn/domains/space/`, `tests/domains/space/`,
  `tests/fixtures/space/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Replay
  a revised launch event, a stale element set, and a boundary edition change, and run each source
  suite alone and together.
- Acceptance gates: Revisions update events through the update policy without duplicates. Stale or
  superseded inputs are marked, not shown as current. Each source suite passes alone and together.
  Every finding has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix
  starts from a failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

### Evidence vault export -- `obsidian-export`

#### obsidian-export-core

Users need a safe, read-only Obsidian subset of the knowledge base.

- Serves: `obsidian-export` -- [Obsidian export](../design/spec.md#obsidian-export)
- Agent status: CLEAR
- Dependencies: none.
- User-visible outcome: `kn export obsidian --profile <id>` writes a verified vault
  ZIP and manifest from one snapshot.
- Scope boundary: Profiles, the snapshot read, deterministic notes and links, rights filtering,
  limits, safe paths, the manifest, and the atomic ZIP. No scheduling and no writeback.
- Data and artifact paths: `src/kn/export/obsidian/`, `domains/fixture/exports/`,
  `$DATA_DIR/exports/`, `tests/export/`.
- Execution path: Fixture-domain tests for link closure, explicit references, escaping, traversal
  names, oversized selections, and restricted rights.
- Acceptance gates: Manifest hashes verify. Every internal link resolves or is an explicit
  reference. A repeated export is identical. Restricted content and secrets are absent. An
  oversized selection is refused.
- Documentation target: A new `current/obsidian-export.md` page listed in the
  [areas index](current.md#areas).

#### obsidian-space-profile

The SATCOM knowledge needs a reviewed export profile on real data.

- Serves: `obsidian-export` -- [Obsidian export](../design/spec.md#obsidian-export)
- Agent status: CLEAR
- Requires: `space-elt-implementation-audit`, `obsidian-export-core`
- Dependencies: Rights flags recorded by the space sources.
- User-visible outcome: A `satcom_public` profile exports constellations, services, launchers,
  organizations, concepts, sources, and evidence, with separate `en` and `uk` vaults.
- Scope boundary: Profile definition and verification on space data. No new export features.
- Data and artifact paths: `domains/space/exports/`, `tests/export/`.
- Execution path: Export from a rebuilt fixture archive and open the vault structure in tests.
- Acceptance gates: Both vaults verify. Excluded-rights counts match the source flags. The size
  stays within limits.
- Documentation target: `current/obsidian-export.md` listed in the
  [areas index](current.md#areas).

#### obsidian-export-implementation-audit

Exported vaults leave KN's control, so a rights, link, or determinism defect cannot be withdrawn
once a vault is shared.

- Serves: `obsidian-export` -- [Obsidian export](../design/spec.md#obsidian-export)
- Agent status: CLEAR
- Requires: `obsidian-export-core`, `obsidian-space-profile`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Shared vaults come from a verified, deterministic export. The audit record
  gives every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: rights and licence filtering across notes, attachments, and front matter;
  deterministic names and content; stable links when objects merge, split, or retire; file-name
  safety across operating systems, including reserved names, length, case collisions, and Cyrillic;
  text language and fallback metadata; vault verification; export after the knowledge base
  changes; further domain profiles. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `src/kn/export/obsidian/`, `domains/<domain>/exports/`, `tests/export/`,
  `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Export
  twice and compare bytes, export after a merge and a retire, and plant a restricted value, names
  that differ only in case, and a reserved file name.
- Acceptance gates: Two exports give identical bytes. No restricted value appears in the vault.
  Links to merged or retired objects resolve to successors. File names are valid on Linux, macOS,
  and Windows. Every finding has a severity, evidence, and a disposition, no `blocker` is accepted,
  and every fix starts from a failing regression test. `make ci` passes with the scheduled tasks in
  the plan.
- Documentation target: `current/obsidian-export.md` listed in the [areas index](current.md#areas).

### Scheduled space ingestion -- `orchestration`

#### kestra-service

Scheduled ingestion needs a pinned orchestrator without host-level privileges.

- Serves: `orchestration` -- [Orchestration](../design/spec.md#orchestration)
- Agent status: CLEAR
- Dependencies: A pinned Kestra OSS release whose Process task runner is confirmed.
- User-visible outcome: Kestra runs with its own `kestra` database. A dedicated non-root image
  holds the pinned `kn` package and runs `kn source run`.
- Scope boundary: The service, the runner image, and internal networking. The UI uses English.
  Proxy authentication comes in `reverse-proxy-auth`. No Docker socket.
- Data and artifact paths: `deploy/compose.yaml`, `deploy/kestra/`, `deploy/versions.yaml`.
- Execution path: Pin by digest, check that a smoke flow runs `kn info` through the Process runner,
  and record the confirmed release behavior.
- Acceptance gates: The smoke flow succeeds. No container mounts the Docker socket. Runner
  processes are non-root.
- Documentation target: A new `current/orchestration.md` page listed in the
  [areas index](current.md#areas).

#### kestra-flow-generation

Schedules must follow reviewed crawler configurations, not hand-edited flows.

- Serves: `orchestration` -- [Orchestration](../design/spec.md#orchestration)
- Agent status: CLEAR
- Requires: `kestra-service`, `source-management-implementation-audit`
- Dependencies: Scoped Kestra API credentials in the environment.
- User-visible outcome: `kn flows generate` and `kn flows deploy` produce one flow per enabled
  source (namespace `kn.<domain>`, cron in UTC, concurrency 1, transient-only retries) and detect
  drift.
- Scope boundary: Generation, deployment, the drift check, and debounced dbt refresh hooks. No
  flows for disabled sources.
- Data and artifact paths: `src/kn/orchestration/`, `generated/kestra/`, `tests/orchestration/`.
- Execution path: Golden-file tests for generated YAML, plus a deployment test against the local
  service.
- Acceptance gates: Generation is byte-identical twice. A disabled source yields no flow. Drift is
  reported.
- Documentation target: `current/orchestration.md` listed in the [areas index](current.md#areas).

#### scheduled-space-ingestion

Approved space sources must run unattended within their budgets.

- Serves: `orchestration` -- [Orchestration](../design/spec.md#orchestration)
- Agent status: RUN NEEDED
- Requires: `kestra-flow-generation`, `approve-space-source-enablement`,
  `space-elt-implementation-audit`
- Dependencies: Enablement approval and a declared run window (default 72 hours) on a host with
  network access.
- User-visible outcome: Approved space sources run on schedule with recorded statuses, budgets, and
  freshness.
- Scope boundary: The declared window only. Kill-and-retry and restart checks are included.
- Data and artifact paths: `$KN_RAW_ARCHIVE_DIR/captures/space/`, `$DATA_DIR/runs/`, and the
  task record.
- Execution path: Deploy the flows, run the window, kill one worker mid-run, and restart the stack
  once.
- Acceptance gates: Every scheduled slot has a run with a declared status. Request counts stay
  within budgets. The killed run retries without duplicates. Checkpoints survive the restart.
- Documentation target: `current/orchestration.md` listed in the [areas index](current.md#areas).

#### orchestration-implementation-audit

Generated flows run unattended, so scheduling, secrets, and failure handling must hold before real
sources run on them.

- Serves: `orchestration` -- [Orchestration](../design/spec.md#orchestration)
- Agent status: RUN NEEDED
- Requires: `kestra-service`, `kestra-flow-generation`, `scheduled-space-ingestion`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. Review the scheduled run
  and its recorded source budgets.
- User-visible outcome: Unattended runs start from verified, generated flows. The audit record gives
  every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: flows generated only from reviewed configurations, with no hand edit
  surviving a deploy; deterministic generation; overlapping runs and concurrency limits; retries
  within source budgets; missed schedules after downtime; time zones and daylight-saving changes;
  secrets kept out of flow definitions and logs; removal of flows for disabled sources; Kestra
  upgrades against pinned versions. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/kestra/`, `src/kn/orchestration/`, `generated/kestra/`,
  `tests/orchestration/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks.
  Generate twice and compare, disable a source and redeploy, simulate downtime across a schedule,
  and search flows and logs for a planted secret.
- Acceptance gates: Generation is byte-identical. A disabled source has no deployed flow.
  Overlapping runs of one source are prevented. No secret appears in a flow or log. Every finding
  has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/orchestration.md` listed in the [areas index](current.md#areas).

### Space analytics and dashboards -- `space-dashboards`

#### superset-service

Dashboards need a pinned, bilingual, read-only BI service.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Dependencies: A pinned Superset release that bundles a `uk` catalog.
- User-visible outcome: Superset runs with `en` and `uk` enabled, its own `superset` metadata
  database, a read-only `analytics` connection, and SQL Lab restrictions.
- Scope boundary: The service, roles, the overlay catalog for missing critical strings, and
  configuration. The proxy comes later, so Superset binds only to the internal network until then.
- Data and artifact paths: `deploy/superset/`, `deploy/compose.yaml`, `deploy/versions.yaml`.
- Execution path: Pin by digest, check the language switch, and test that the read-only role cannot
  reach other schemas.
- Acceptance gates: Both locales render. SQL Lab cannot read `raw`, `evidence`, or domain schemas
  directly. Timeouts and row limits apply through database roles.
- Documentation target: A new `current/space-dashboards.md` page listed in the
  [areas index](current.md#areas).

#### space-analytics-marts

Dashboards may read only reviewed, tested marts.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Requires: `space-elt-implementation-audit`
- Dependencies: dbt Core and dbt-postgres in an isolated, pinned tool environment.
- User-visible outcome: The `analytics` schema holds every space mart in the
  [design](../design/domains/space.md#analytical-marts), with localized label joins and freshness
  models.
- Scope boundary: The dbt project, tests, sources from generated definitions, and freshness. No
  dashboards.
- Data and artifact paths: `analytics/dbt/`, `generated/dbt/`, `tests/analytics/`.
- Execution path: Build against the rebuilt fixture archive, with dbt tests for keys,
  comparability filters, and unknown handling.
- Acceptance gates: `dbt build` passes on fixtures and archived samples. No mart turns unknown
  into zero. Incomparable tariffs are filtered.
- Documentation target: `current/space-dashboards.md` listed in the
  [areas index](current.md#areas).

#### dashboards-as-code

Dashboards must deploy reproducibly from one definition in both locales.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Requires: `superset-service`
- Dependencies: The pinned Superset import and export API.
- User-visible outcome: `kn dashboards build` and `kn dashboards deploy` generate `en` and `uk`
  twin bundles with stable UUIDs from a semantic definition and detect drift.
- Scope boundary: The generator, deployment, and drift check, plus a fixture dashboard. Space
  content comes in the next task.
- Data and artifact paths: `src/kn/dashboards/`, `analytics/dashboards/`, `tests/dashboards/`.
- Execution path: Golden bundle tests, and a deploy test against the local service.
- Acceptance gates: Bundles are identical twice. The twins share datasets and filters. Drift is
  reported. Interface catalogs stay separate from data text; fixtures cover requested-language,
  English, and original fallback with the selected language and provenance visible.
- Documentation target: `current/space-dashboards.md` listed in the
  [areas index](current.md#areas).

#### analyst-fact-explanation

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Requires: `space-analytics-marts`, `dashboards-as-code`
- Dependencies: The read-only [lineage view](current/object-identity.md#lineage-lookup), which
  counts withheld rows for operators; this view must leave no restricted value, locator or count.
  A fact version's outcome, deciding criterion and runner-up describe the version when it opened
  ([finding EMA-06](records/0053-evidence-model-evidence-model-implementation-audit.md#findings)).
  Competing values come from the claims current at the as-of time, read through the version's
  selection outcomes without claims superseded by then.
- User-visible outcome: An analyst can open "Why this fact?" on a selected value and see why
  it won, the evidence, permitted alternatives, and any applicable review decision.
- Scope boundary: Shared read-only analytics projection and bilingual dashboard detail view.
- Data and artifact paths: `analytics/dbt/`, `analytics/dashboards/`, `tests/dashboards/`.
- Execution path: Pass the canonical fact key and snapshot from the dashboard to the detail view.
  Reuse the audience-specific selection result and policy reason from the evidence model.
- Acceptance gates: From a fixture dashboard in each locale, verify the displayed winner, unit,
  rule, source locator, competing value, and review reason at two as-of dates. An unresolved
  conflict shows its reason. Restricted evidence leaves no value, locator, or count in the view.
  Human verification shows its optional time, reviewer, scope/version and decision, or an explicit
  unreviewed/stale state, independently of source verification labels and data observation dates.
- Documentation target: `current/space-dashboards.md` listed in the [areas index](current.md#areas).

#### space-dashboard-bundles

Operators need the SATCOM dashboards and map in both languages.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Requires: `analyst-fact-explanation`
- Dependencies: A map basemap decision with lawful terms, or the no-basemap fallback.
- User-visible outcome: The five space dashboards deploy in `en` and `uk`, with freshness
  indicators, evidence drill-down, and the coverage map.
- Scope boundary: Space content and the operations dashboard. The GDELT section comes in
  `gdelt-watch-dashboard`.
- Data and artifact paths: `analytics/dashboards/space/`, `tests/dashboards/`,
  `$DATA_DIR/e2e/<run-id>/`.
- Execution path: Define the dashboards, deploy, and run screenshot checks for Cyrillic, filters,
  missing values, and map layers.
- Acceptance gates: Every [space dashboards](../design/spec.md#space-dashboards) evaluation holds.
  The map renders licensed boundaries without a paid key.
- Documentation target: `current/space-dashboards.md` listed in the
  [areas index](current.md#areas).

#### space-dashboards-implementation-audit

Dashboards are what analysts trust, so mart tests, bilingual builds, and fact explanation must be
right before other domains reuse the pattern.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: CLEAR
- Requires: `superset-service`, `space-analytics-marts`, `dashboards-as-code`,
  `analyst-fact-explanation`, `space-dashboard-bundles`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Other domains reuse a verified dashboard pattern. The audit record gives
  every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: marts that read only reviewed models, with tests on grain, keys, and
  freshness; read-only database roles; deterministic builds in `en` and `uk`; fact explanation down
  to raw evidence for every shown value; filters, empty states, and denominators; map geometry and
  projection; deploy idempotency and Superset upgrades; reuse by the GDELT and microelectronics
  dashboards. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/superset/`, `analytics/`, `src/kn/dashboards/`,
  `tests/analytics/`, `tests/dashboards/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Build
  and deploy twice, explain a sample of values from each dashboard, and open each dashboard with an
  empty filter result and a stale source.
- Acceptance gates: Every sampled value explains down to its raw record. A repeated deploy changes
  nothing. Empty and stale states show a message, not an error or a silent zero. Every finding has a
  severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/space-dashboards.md` listed in the [areas index](current.md#areas).

### GDELT collection and correlation -- `gdelt-elt`

#### gdelt-domain-contracts

GDELT signals need their own schema that never writes canonical domain facts.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `source-management-implementation-audit`
- Dependencies: [GDELT design](../design/domains/gdelt.md).
- User-visible outcome: The `gdelt` schema holds watches, query runs, article metadata, native
  dictionaries, story clusters, signals, and candidate links.
- Scope boundary: Contracts and policies. The native Event and Mention tables are reserved until
  the optional stream import. No loader writes to space or microelectronics tables.
  Use the early evidence, verification and run-state interfaces. Offline compile/rebuild and role
  fixtures validate the schema; full archive/decision replay is a later integration gate.
- Data and artifact paths: `domains/gdelt/contracts/`, `src/kn/domains/gdelt/`,
  `tests/domains/gdelt/`.
- Execution path: Write the contracts from the design page, then compile and rebuild. Reconcile
  the pending field-mapping and ingestion-order proposals; defer native-only rows with reasons.
- Acceptance gates: The contracts compile. A role test proves the GDELT loader cannot write other
  domain schemas.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

#### gdelt-source-terms-review

GDELT access paths need verified limits and dictionary editions before collection.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Research: yes
- Dependencies: Public GDELT documentation, codebooks, and lookup indexes.
- User-visible outcome: A dossier covering current DOC 2.0 API limits, terms, codebook editions,
  and dictionary locations, plus catalogue state `investigating`.
- Scope boundary: Documentation only; no data queries.
- Data and artifact paths: `domains/gdelt/sources/dossiers/`, and the task record.
- Execution path: Follow the dossier template, and confirm or correct the proposal's limits.
- Acceptance gates: Each access path has a dossier or a blocker. A finding that DOC limits defeat
  the watch design is a valid negative result.
- Documentation target: A new `current/gdelt-domain.md` page listed in the
  [areas index](current.md#areas).

#### gdelt-source-dictionaries

Native codes must resolve against full official dictionaries, not workbook subsets.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-domain-contracts`, `authorize-gdelt-collection`,
  `ingestion-engine-implementation-audit`
- Dependencies: Collection authorization covering the lookup files and the
  [pending actor/geography and GCAM rows](current/ontology-taxonomy/seeds.md#unmapped-rows-and-ownership).
- User-visible outcome: CAMEO event codes, actor types, countries, known groups, GKG themes, and
  the GCAM codebook load as native schemes with edition and checksum.
- Scope boundary: Dictionary files only. Leading zeros are preserved. Sensitive actor attributes
  are restricted.
- Data and artifact paths: `domains/gdelt/sources/dictionaries.yaml`,
  `tests/fixtures/gdelt/dictionaries/`.
- Execution path: Follow onboarding steps 3-4, using bulk-file methods through the engine.
- Acceptance gates: Every proposal code is found in the official dictionary or flagged. Checksums
  are recorded. All earlier suites pass.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

#### gdelt-source-doc-watches

Technology watches need bounded, honest media discovery.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-source-dictionaries`
- Dependencies: Approved watch manifests for space and microelectronics topics.
- User-visible outcome: DOC 2.0 watch runs store article metadata with window splitting,
  truncation flags, and deduplication. Coverage statistics name the filters and gaps.
- Scope boundary: Metadata and permitted excerpts only. No full text, no native IDs for DOC
  results, and no exhaustiveness claims.
- Data and artifact paths: `domains/gdelt/sources/doc_watches.yaml`, `domains/gdelt/seeds/watches.json`,
  `tests/fixtures/gdelt/doc/`.
- Execution path: Follow the onboarding steps 3-4, with window and cap logic as general cursor
  features.
- Acceptance gates: A capped window splits. A non-JSON `200` fails. Syndicated items cluster.
  Signals stay unverified. All earlier suites pass.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

#### gdelt-cross-domain-candidates

Media signals should point reviewers at domain entities without changing them.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-source-doc-watches`, `space-elt-implementation-audit`
- Dependencies: none.
- User-visible outcome: Candidate links from GDELT documents to space entities appear in the review
  queue with evidence.
- Scope boundary: Candidate generation and review only. No automatic promotion.
- Data and artifact paths: `src/kn/domains/gdelt/linking.py`, `tests/domains/gdelt/`.
- Execution path: Fixture documents that mention known and ambiguous entities.
- Acceptance gates: Ambiguous mentions stay unresolved. An accepted link creates a reviewed relation
  candidate, never a canonical fact change.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

#### gdelt-elt-implementation-audit

Media signals must never become canonical facts, and GDELT limits change outside KN, so boundary and
window defects would corrupt the domain silently.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-domain-contracts`, `gdelt-source-terms-review`, `gdelt-source-dictionaries`,
  `gdelt-source-doc-watches`, `gdelt-cross-domain-candidates`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Watch signals rest on verified, bounded collection. The audit record gives
  every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: the rule that GDELT never writes canonical domain facts; DOC 2.0 window
  splitting, result caps, and truncated windows; duplicate and syndicated articles; dictionary
  editions and unknown codes; article time zones; candidate links that stay in review; honest
  denominators; the optional native streams. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `domains/gdelt/`, `src/kn/domains/gdelt/`, `tests/domains/gdelt/`,
  `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Plant a
  window that hits the result cap, an unknown code, and a syndicated duplicate, and search the
  domain schemas for any GDELT write.
- Acceptance gates: A capped window is split or reported, never treated as complete. Unknown codes
  are reported. No GDELT path writes a canonical domain fact. Every finding has a severity,
  evidence, and a disposition, no `blocker` is accepted, and every fix starts from a failing
  regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

### GDELT watch dashboard -- `gdelt-dashboards`

#### gdelt-watch-dashboard

Operators need the technology watch view with honest denominators.

- Serves: `gdelt-dashboards` -- [GDELT dashboards](../design/spec.md#gdelt-dashboards)
- Agent status: CLEAR
- Requires: `gdelt-elt-implementation-audit`, `space-dashboards-implementation-audit`
- Dependencies: none.
- User-visible outcome: The `technology_signal_daily` mart and the watch section of the acquisition
  dashboard deploy in `en` and `uk`.
- Scope boundary: The mart and dashboard content. No new collection.
- Data and artifact paths: `analytics/dbt/models/gdelt/`, `analytics/dashboards/gdelt/`,
  `tests/dashboards/`.
- Execution path: dbt tests for story-cluster counting, then dashboard bundles and screenshots.
- Acceptance gates: Counts match fixtures, with syndicated items counted once.
  Canonical fact fields linked from the watch open "Why this fact?".
  The sample and denominator labels show in both locales.
- Documentation target: A new `current/gdelt-dashboards.md` page listed in the
  [areas index](current.md#areas).

#### gdelt-dashboards-implementation-audit

The watch dashboard reports signal volume, so a denominator or window error would mislead without
any visible failure.

- Serves: `gdelt-dashboards` -- [GDELT dashboards](../design/spec.md#gdelt-dashboards)
- Agent status: CLEAR
- Requires: `gdelt-watch-dashboard`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Watch figures are shown to match their marts. The audit record gives every
  check a result and every finding a disposition. The current-state page lists known limitations,
  and each scheduled finding is a plan task.
- Scope boundary: Focus: denominators and normalization; partial and current days; gaps from capped
  or failed windows; time zones; bilingual labels; consistency with the space dashboard pattern.
  Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `analytics/dbt/models/gdelt/`, `analytics/dashboards/gdelt/`,
  `tests/dashboards/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Load a
  day with a failed window and a partial current day, and compare dashboard totals with the mart.
- Acceptance gates: Failed windows show as gaps, not zero. Dashboard totals match the mart. Every
  finding has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix
  starts from a failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/gdelt-dashboards.md` listed in the [areas index](current.md#areas).

### Microelectronics sources and observations -- `microelectronics-elt`

#### microelectronics-domain-contracts

Product identity and condition-bound observations need typed contracts.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `part-supply-model-implementation-audit`
- Dependencies: [Microelectronics design](../design/domains/microelectronics.md) and the
  [pending seed policies](current/ontology-taxonomy/seeds.md#unmapped-rows-and-ownership).
- User-visible outcome: The `microelectronics` schema holds families, models, MPNs, dies, IP
  blocks, kits, facilities, projects, benchmark runs, and observations with condition sets and
  comparison groups.
- Scope boundary: Contracts and policies that extend the shared part and supply classes rather
  than redefining them. Origin facts are stored but never gate anything until the owner policy
  exists.
  Reuse the shared measurement/attribute/condition definitions from `supply-model-contracts` and
  the common verification trait. Compile/rebuild fixtures validate these shapes before engines,
  raw replay, model matching or source permissions are available.
- Data and artifact paths: `domains/microelectronics/contracts/`, `src/kn/domains/microelectronics/`,
  `tests/domains/microelectronics/`.
- Execution path: Write the contracts from the design page and the reviewed attribute dictionary,
  then compile and rebuild. Resolve all 31 pending observation-schema, comparison-profile and
  rubric proposal rows to typed policies or explicit exclusions.
- Acceptance gates: MPN identity requires the legal manufacturer and the exact MPN. Typical and
  guaranteed values cannot share a field. Unit conversions are logged.
- Documentation target: `current/microelectronics-domain.md` listed in the [areas index](current.md#areas).

#### microelectronics-source-terms-review

Microelectronics sources need documented terms before sampling.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Research: yes
- Dependencies: Public documentation for MLPerf Tiny results, CORDIS datasets, and the watchlist
  vendors' datasheet terms, plus official trade-policy publications for target markets.
- User-visible outcome: A dossier per first-wave source and catalogue state `investigating`.
- Scope boundary: Documentation only.
- Data and artifact paths: `domains/microelectronics/sources/dossiers/`, and the task record.
- Execution path: Follow the dossier template.
- Acceptance gates: Each source has a dossier or a blocker. Prohibitive vendor terms move that
  vendor to curated datasheet observations or exclusion.
- Documentation target: A new `current/microelectronics-domain.md` page listed in the
  [areas index](current.md#areas).

#### microelectronics-source-mlperf-tiny

The benchmark layer starts from published MLPerf Tiny results.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Requires: `microelectronics-domain-contracts`, `authorize-microelectronics-sources`,
  `ingestion-engine-implementation-audit`
- Dependencies: Sampling authorization covering MLPerf Tiny results.
- User-visible outcome: Benchmark runs load with version, division, workload, boundary, and
  energy where reported, linked to systems and MPNs only through evidenced identity.
- Scope boundary: Published results only. No derived rankings across versions.
- Data and artifact paths: `domains/microelectronics/sources/mlperf_tiny.yaml`,
  `tests/fixtures/microelectronics/mlperf_tiny/`.
- Execution path: Follow onboarding steps 3-4.
- Acceptance gates: Results from different versions or divisions never share a comparison group.
  All earlier suites pass.
- Documentation target: `current/microelectronics-domain.md` listed in the
  [areas index](current.md#areas).

#### microelectronics-source-cordis

Funded research projects provide the prospective technology signal.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Requires: `microelectronics-source-mlperf-tiny`
- Dependencies: Sampling authorization covering the CORDIS datasets.
- User-visible outcome: Relevant projects, participants, funding, and dates load, with technology
  tags as candidates for review.
- Scope boundary: Official bulk datasets filtered by the approved topics. A project is never
  treated as a product.
- Data and artifact paths: `domains/microelectronics/sources/cordis.yaml`,
  `tests/fixtures/microelectronics/cordis/`.
- Execution path: Follow the onboarding steps 3-4, using the bulk-file method.
- Acceptance gates: Maturity stays separate from commercial availability. Tags are reviewable
  candidates. All earlier suites pass.
- Documentation target: `current/microelectronics-domain.md` listed in the
  [areas index](current.md#areas).

#### microelectronics-curated-datasheets

Product baselines need exact datasheet observations for the watchlist families.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Requires: `microelectronics-source-cordis`, `ingestion-engine-implementation-audit`
- Dependencies: A curator and permitted datasheet access for the selected families.
- User-visible outcome: Curated observations for selected MPNs load with datasheet revision, page,
  table, conditions, and qualifier.
- Scope boundary: Curated files only; no vendor site scraping.
- Data and artifact paths: `domains/microelectronics/curation/`,
  `tests/fixtures/microelectronics/datasheets/`.
- Execution path: Use the curated-file schema for observations, with fixture tests for comparison
  profile gates.
- Acceptance gates: Records with unknown required fields are excluded from matched groups but stay
  visible. All earlier suites pass.
- Documentation target: `current/microelectronics-domain.md` listed in the
  [areas index](current.md#areas).

#### target-market-policy-observations

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Requires: `microelectronics-curated-datasheets`, `authorize-microelectronics-sources`
- Dependencies: Official publications and source-specific approval for live samples.
- User-visible outcome: Cited trade and export-control measures can be queried by target market
  and effective date, with source coverage and missing classifications visible.
- Scope boundary: Informational policy evidence, including country and bloc scope.
- Data and artifact paths: `domains/microelectronics/`, `tests/fixtures/microelectronics/`.
- Execution path: Use the shared source workflow for each authority. Archive approved publications,
  map revisions and stated conditions, and link evidence to the applicable market scope.
- Acceptance gates: Offline fixtures cover a cross-border rule, a bloc rule, a superseded
  measure, and missing coverage. Replay reproduces the as-of results and source locators.
- Documentation target: `current/microelectronics-domain.md` listed in the [areas
  index](current.md#areas).

#### microelectronics-elt-implementation-audit

Product identity and condition-bound observations are the hardest part of the domain to change once
comparisons depend on them.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: CLEAR
- Requires: `microelectronics-domain-contracts`, `microelectronics-source-terms-review`,
  `microelectronics-source-mlperf-tiny`, `microelectronics-source-cordis`,
  `microelectronics-curated-datasheets`, `target-market-policy-observations`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Comparisons rest on verified product identity and observation conditions.
  The audit record gives every check a result and every finding a disposition. The current-state
  page lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: family, model, MPN, and die identity through the shared supply model;
  observation conditions such as temperature, voltage, and benchmark boundary; datasheet revisions
  and supersession; MLPerf version and division comparability; CORDIS project changes; policy
  measures with jurisdiction and validity; units; new product classes without contract changes.
  Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `domains/microelectronics/`, `src/kn/domains/microelectronics/`,
  `tests/fixtures/microelectronics/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Load
  two datasheet revisions with a changed value, observations under different conditions, and results
  from two benchmark versions.
- Acceptance gates: A newer datasheet revision replaces the older one from the same source.
  Observations under different conditions or benchmark versions are never compared as equal. Every
  finding has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix
  starts from a failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/microelectronics-domain.md` listed in the [areas
  index](current.md#areas).

### Microelectronics comparison dashboards -- `microelectronics-dashboards`

#### microelectronics-comparison-marts

Comparisons need marts that only ever group matched condition sets.

- Serves: `microelectronics-dashboards`
  -- [Microelectronics dashboards](../design/spec.md#microelectronics-dashboards)
- Agent status: CLEAR
- Requires: `microelectronics-elt-implementation-audit`, `space-dashboards-implementation-audit`
- Dependencies: none.
- User-visible outcome: The `analytics` schema holds one comparison mart per profile, a technology
  scouting mart with rubric inputs and missing-evidence flags, and a watch mart.
- Scope boundary: dbt models and tests. Rank from the technical comparison profile.
- Data and artifact paths: `analytics/dbt/models/microelectronics/`, `tests/analytics/`.
- Execution path: dbt tests for comparison-group isolation, unit normalization, and unknown
  handling.
- Acceptance gates: Fixtures prove that incomparable records never share a comparison group.
  Missing conditions are listed. No score is computed with incomplete rubric inputs.
- Documentation target: A new `current/microelectronics-dashboards.md` page listed in the
  [areas index](current.md#areas).

#### microelectronics-comparison-dashboards

Analysts need matched-condition comparisons and the scouting view in both languages.

- Serves: `microelectronics-dashboards`
  -- [Microelectronics dashboards](../design/spec.md#microelectronics-dashboards)
- Agent status: CLEAR
- Requires: `microelectronics-comparison-marts`, `gdelt-dashboards-implementation-audit`,
  `microelectronics-elt-implementation-audit`
- Dependencies: none.
- User-visible outcome: Comparison dashboards per profile, a technology scouting view that shows
  the rubric as editable policy, and a watch view, all in `en` and `uk`.
- Scope boundary: Dashboard bundles over the existing marts. No new collection.
- Data and artifact paths: `analytics/dashboards/microelectronics/`, `tests/dashboards/`,
  `$DATA_DIR/e2e/<run-id>/`.
- Execution path: Define the bundles, deploy, and run screenshot checks in both locales.
- Acceptance gates: An analyst can open "Why this fact?" from a canonical comparison value.
  Switch target markets with zero, one, and multiple policy matches. Only the cited market
  detail changes. Assert identical product IDs, row counts, scores, and ranks.
  No chart ranks across comparison groups. Advertised and measured values are
  labeled. Both locales render.
- Documentation target: `current/microelectronics-dashboards.md` listed in the
  [areas index](current.md#areas).

#### microelectronics-dashboards-implementation-audit

Comparison dashboards must group only matched conditions, so a grouping error would produce
plausible but wrong rankings.

- Serves: `microelectronics-dashboards` -- [Microelectronics
  dashboards](../design/spec.md#microelectronics-dashboards)
- Agent status: CLEAR
- Requires: `microelectronics-comparison-marts`, `microelectronics-comparison-dashboards`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Comparisons are shown to group only matched conditions. The audit record
  gives every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: matched-condition grouping in every mart; unit conversion; missing
  observations shown as missing; scouting signals kept apart from product facts; bilingual labels;
  reuse of the dashboard pattern. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `analytics/dbt/models/microelectronics/`,
  `analytics/dashboards/microelectronics/`, `tests/analytics/`, `tests/dashboards/`,
  `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Plant
  observations that differ in one condition, a missing value, and a unit that needs conversion.
- Acceptance gates: Mismatched conditions never share a comparison group. Missing values show as
  missing. Every finding has a severity, evidence, and a disposition, no `blocker` is accepted, and
  every fix starts from a failing regression test. `make ci` passes with the scheduled tasks in the
  plan.
- Documentation target: `current/microelectronics-dashboards.md` listed in the [areas
  index](current.md#areas).

### Integrated model and backfill -- `model-baseline`

#### development-model-baseline

Release evaluation needs one integrated rebuild and backfill across the complete registry.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Execution stage: MODEL
- Requires: `data-interchange-implementation-audit`, `space-elt-implementation-audit`,
  `gdelt-elt-implementation-audit`, `microelectronics-elt-implementation-audit`,
  `source-management-implementation-audit`
- Dependencies: The [contract workflow](../guide/schema-first-development.md), registered
  core/domain contracts, reviewed seeds and deterministic fixture data. No live source is needed.
  [Record 0030](records/0030-data-contracts-development-model-baseline.md) prepares the
  [registered-subset check](current/data-contracts/model-baseline.md); the complete checkpoint
  also needs fixtures from every registered owner.
- User-visible outcome: One compiled development baseline contains the identity, evidence, human
  verification, supply/measurement, source/run, exchange and three domain models together.
  Runtime tasks can use these definitions without introducing another interpretation of a key,
  timestamp, unit, missing reason or review scope.
- Scope boundary: Cross-contract compatibility, common traits and field IDs, constraints, seed
  references, permissions, rebuild/backfill and fixture round trips. This is a development
  checkpoint, not the release freeze or a promise that no future additive fields will be needed.
- Data and artifact paths: `contracts/`, `src/kn/contracts/resources/`, `generated/contracts/`,
  `src/kn/db/`, `tests/integration/`, `$DATA_DIR/model-baseline/<run-id>/`.
- Execution path: Compile the complete registry, load representative fixtures for every model,
  rebuild twice, and compare identifiers, values, review metadata and all contract markers.
  Extend `make model-baseline` and its fixture-owner coverage as prerequisite models register;
  the registered-subset run alone does not satisfy this checkpoint.
- Acceptance gates: Every registered contract compiles and rebuilds as one set. IDs and references,
  typed measurements, multilingual text, verification targets, cursors and exchange keys agree
  across owners. The real SATCOM fixture remains lossless. Two rebuilds preserve deterministic
  model data and human decision provenance; no live fetch or runtime engine is required. Review
  the generated diff as one baseline. Record recovery inputs, the development database backfill
  and post-rebuild verification in the checkpoint record. `make ci` and `make ci-local` pass.
  Existing snapshot-shaped SATCOM tables and new canonical tables have explicit ownership and
  non-colliding names/field IDs; original source fields are not silently reinterpreted.
- Documentation target: [Data contracts](current/data-contracts.md).

#### model-baseline-implementation-audit

Later engines and counterpart adapters will depend on the shared model boundaries and keys.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Requires: `development-model-baseline`
- Dependencies: The model task records and [implementation audit](../guide/planning-workflow.md#implementation-audits)
  checks. No live pipeline or owner access is needed.
- User-visible outcome: The integrated model has a documented result for every audit check and
  a disposition for every finding before release migration work.
- Scope boundary: Keys and versions, cross-model references, shared verification and measurement
  traits, source/run and exchange state, source preservation, extension points and rebuild replay.
  Fix in-scope defects; new capabilities follow the planning workflow.
- Data and artifact paths: `contracts/`, `src/kn/`, `tests/integration/`, and the task record.
- Execution path: Rerun model acceptance fixtures, plant mismatched references/traits, a changed
  review target, a missing unit/condition and a replay interruption, then complete the six checks.
- Acceptance gates: Every finding has severity, evidence and disposition. No blocker is accepted;
  fixes start with a failing regression. Extensions cannot silently redefine stable field IDs.
  `make ci` and the applicable integration checks pass.
- Documentation target: [Data contracts](current/data-contracts.md).

### Bilingual dashboard and map acceptance -- `localization`

#### bilingual-acceptance-suite

Release needs end-to-end proof that dashboards and maps work in both languages.

- Serves: `localization` -- [Localization](../design/spec.md#localization)
- Agent status: CLEAR
- Requires: `space-dashboards-implementation-audit`, `gdelt-dashboards-implementation-audit`,
  `microelectronics-dashboards-implementation-audit`
- Dependencies: Browser automation when product browser surfaces exist. The available CLI and
  multilingual data checks are documented in
  [current acceptance coverage](current/localization.md#bilingual-acceptance); the open
  [task record](records/0013-localization-bilingual-acceptance-suite.md) preserves partial evidence.
- User-visible outcome: One command verifies dashboard controls, filters, and maps in both languages
  and saves screenshots.
- Scope boundary: Dashboard and map interface text, formatting, and fact display. Source text in
  any language retains its language and provenance through ingestion and later translation.
- Data and artifact paths: `tests/e2e/`, `$DATA_DIR/e2e/<run-id>/` for screenshots, and `locales/`.
- Execution path: Extend `make test-bilingual` with browser paths against multilingual fixtures.
  Check key coverage, Cyrillic rendering, dates, numbers, units, and missing-value labels. Run
  `make bilingual-acceptance` to require all release paths. Retain screenshots and fallback metadata
  for both languages.
- Acceptance gates: Both languages pass on every dashboard and map with no untranslated critical
  strings. Missing data translations use the documented fallback and retain original metadata.
- Documentation target: `current/localization.md` listed in the [areas index](current.md#areas).

#### localization-implementation-audit

Message keys, plural rules, and locale fallback need verification across dashboards and maps.

- Serves: `localization` -- [Localization](../design/spec.md#localization)
- Agent status: CLEAR
- Requires: `bilingual-acceptance-suite`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Every dashboard and map works in `en` and `uk`. The audit record gives
  every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Dashboard and map key parity, Ukrainian plurals, number/date/unit formatting,
  missing-interface-key rejection, text expansion, Cyrillic rendering, and source-text fallback.
  Verify that the CLI uses English and that its JSON contract is stable.
- Data and artifact paths: `src/kn/i18n/`, `locales/`, `tests/e2e/`, `docs/impl/plan.md`, and the
  task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Remove
  one `uk` key, add a pseudo-locale with long strings, and render the plural cases 0, 1, 2, 5, 11,
  12, 21, and 22.
- Acceptance gates: A missing key fails the catalog check in either direction. The pseudo-locale
  shows no truncated or hard-coded string on the tested surfaces. Plural forms follow the CLDR rules
  for `uk`. Every finding has a severity, evidence, and a disposition, no `blocker` is accepted, and
  every fix starts from a failing regression test. `make ci` passes with the scheduled tasks in the
  plan.
- Documentation target: `current/localization.md` listed in the [areas index](current.md#areas).

### Security, recovery and performance -- `operations-hardening`

#### reverse-proxy-auth

Superset and Kestra must not be reachable without TLS and authentication.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: CLEAR
- Requires: `space-dashboards-implementation-audit`, `orchestration-implementation-audit`
- Dependencies: The owner's choice of authentication backend; the default is proxy basic or OIDC
  authentication on a private network.
- User-visible outcome: Caddy fronts Superset and Kestra with TLS and authentication. Superset
  roles map to database roles.
- Scope boundary: The proxy, its certificates, and role mapping. No public exposure.
- Data and artifact paths: `deploy/proxy/`, `deploy/compose.yaml`, `tests/integration/`.
- Execution path: Pin by digest, and test unauthenticated, analyst, and admin access.
- Acceptance gates: Unauthenticated requests are refused. An analyst cannot reach Kestra. No
  service port bypasses the proxy.
- Documentation target: A new `current/operations.md` page listed in the
  [areas index](current.md#areas).

#### security-test-suite

Security properties need one consolidated, repeatable proof.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: CLEAR
- Requires: `reverse-proxy-auth`, `obsidian-export-implementation-audit`,
  `ingestion-engine-implementation-audit`, `inventree-exchange-implementation-audit`
- Dependencies: none.
- User-visible outcome: `make security` runs the checks for schema isolation, loader DDL denial,
  restricted-fact denial, unauthorized users, secrets in logs and ZIPs, SSRF, archive traversal,
  decompression bombs, counterpart writes without approval, and personal data in counterpart
  reads.
- Scope boundary: Consolidation and gap filling across existing tests.
- Data and artifact paths: `tests/security/`, `Makefile`.
- Execution path: Map each property in the specification to a test. Withdraw permission for one
  of two supporting claims and rebuild the mart and ZIP from the remaining permitted evidence.
  Repeat with both supports restricted and verify that the value disappears from both outputs.
- Acceptance gates: Every property has a passing test, and a planted violation fails each test.
- Documentation target: `current/operations.md` listed in the [areas index](current.md#areas).

#### backup-restore-drill

Recovery objectives must be measured, not assumed.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: RUN NEEDED
- Requires: `provide-target-server-and-backup`, `security-test-suite`
- Dependencies: The target server, the off-host backup destination, and the archive
  [backup and restore order](current/raw-archive.md#back-up-and-restore).
- User-visible outcome: Nightly backups of databases, globals, committed archive batches and
  tombstones, decision logs, the identity event log, and the exchange ledger. A written runbook
  covers recovery with and without the optional fetch-index backup.
- Scope boundary: Backup jobs, retention, the restore drill into an isolated instance, and
  achieved RPO and RTO.
- Data and artifact paths: `deploy/backup/`, `docs/guide/operations-runbook.md`,
  `$DATA_DIR/backups/`, and the task record.
- Execution path: Restore into an isolated stack with an explicit archive root, apply current
  tombstones before opening reader access, rebuild the fetch index in its configured root, and
  verify hashes, constraints and dashboard queries. Time the drill including index recovery.
- Acceptance gates: The restore passes its checks with the index backup withheld. The achieved
  RPO and RTO are recorded against the proposed 24 h and 8 h objectives.
- Documentation target: `current/operations.md` listed in the [areas index](current.md#areas).

#### performance-gate

The target host must handle the declared load within the memory budget.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: RUN NEEDED
- Requires: `backup-restore-drill`, `gdelt-dashboards-implementation-audit`
- Dependencies: Access to the target server.
- User-visible outcome: A measured report covering synthetic load, dashboard and map p95, ingestion
  memory, disk growth and the scale triggers for the raw archive index.
- Scope boundary: Synthetic data only (50k catalog rows, 100k articles, 1M observations), with 2
  readers and 1 ingest. Exercise both many small sources across domains and one bulk-heavy source.
- Data and artifact paths: `tests/performance/`, `$DATA_DIR/perf/<run-id>/`, and the task record.
- Execution path: Declare lookup and reindex budgets before measuring, with full reindex inside
  the restore time budget. Generate the load, measure query plans and timings, and adjust the
  Compose limits. For each archive shape, record domain, source and capture counts, stored bytes,
  archive and index file counts, scoped lookup p95, file planning time, and full and scoped
  reindex duration and peak memory.
  Profile the warmed PostgreSQL identity submit benchmark on the target host to diagnose the
  [scale gate miss recorded on the base tree](records/0058-ingestion-engine-ingestion-state-contracts.md#findings).
- Acceptance gates: Dashboard and map p95 are at most 5 s. There is no out-of-memory failure. Any
  deviation is recorded with measurements. Record whether either archive shape meets the
  [reopening condition](future-research.md#raw-archive-format-selection----avro-and-iceberg-for-the-raw-archive).
  Verify the existing median submit ratio of at most 2.0 between 50,000 and 5,000 objects.
- Documentation target: `current/operations.md` listed in the [areas index](current.md#areas).

#### operations-hardening-implementation-audit

Authentication, isolation, and recovery protect every service, so a gap found after deployment
exposes the whole host.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: RUN NEEDED
- Requires: `reverse-proxy-auth`, `security-test-suite`, `backup-restore-drill`,
  `performance-gate`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. Inspect the measured
  restore and performance reports.
- User-visible outcome: The host runs on verified security controls. The audit record gives every
  check a result and every finding a disposition. The current-state page lists known limitations,
  and each scheduled finding is a plan task.
- Scope boundary: Focus: TLS and authentication on every endpoint published beyond loopback,
  and authentication on loopback endpoints such as the database port; session and cookie
  settings; schema isolation and least-privilege roles; loader DDL denial; secrets in the
  environment, logs, and backups; dependency and image vulnerability scans; outbound network limits;
  a test for each threat the specification names. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/proxy/`, `deploy/compose.yaml`, `tests/security/`,
  `tests/integration/`, `Makefile`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Run
  `make security`, scan every published port without credentials, try each role against a schema it
  must not reach, and search logs and generated files for a planted secret.
- Acceptance gates: No endpoint published beyond loopback answers without TLS and
  authentication, and no loopback endpoint answers without authentication. Each role is
  refused outside its grants. No planted secret appears in any output. Every finding has a severity,
  evidence, and a disposition, no `blocker` is accepted, and every fix starts from a failing
  regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/operations.md` listed in the [areas index](current.md#areas).

### Vocabulary publication namespace -- `vocabulary-namespace`

#### vocabulary-namespace-implementation-audit

Verify the owner's decision and its effect on the published interface.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: The [namespace decision and its retained evidence](records/0041-ontology-taxonomy-decide-vocabulary-uri-namespace.md).
- User-visible outcome: Exports reflect the approved namespace and preserve internal keys.
- Scope boundary: The approved public URI base, exports and stable internal term IDs.
- Data and artifact paths: The owner task record, its artifacts and the numbered audit record.
- Execution path: Re-export multilingual SKOS fixtures and compare term identities across parses.
- Acceptance gates: Check the group's evidence and downstream compatibility under the
  [audit procedure](../guide/planning-workflow.md#implementation-audits). Fix or gate blockers,
  assign every finding and run `make ci`.
- Documentation target: [Ontology and taxonomy](current/ontology-taxonomy.md).

### Published SATCOM package -- `satcom-publication`

#### satcom-publication-implementation-audit

Verify the owner's decision and its effect on the published interface.

- Serves: `ingestion-engine` -- [Specification](../design/spec.md#ingestion-engine)
- Agent status: CLEAR
- Requires: `publish-satcom-drive-package`, `ingestion-engine-implementation-audit`
- Dependencies: The accepted human task record and its retained evidence.
- User-visible outcome: Re-import behavior agrees with the recorded access decision.
- Scope boundary: The authorized Drive access outcome, cache behavior and evidence handling.
- Data and artifact paths: The owner task record, its artifacts and the numbered audit record.
- Execution path: Check permitted run receipts or the documented refusal and local fallback.
  Repeat cache and credential-redaction fixtures without issuing a new live request.
- Acceptance gates: Check the group's evidence and downstream compatibility under the
  [audit procedure](../guide/planning-workflow.md#implementation-audits). Fix or gate blockers,
  assign every finding and run `make ci`.
- Documentation target: [Data contracts](current/data-contracts.md).

### Release migration -- `release-readiness`

#### release-migration-mode

After release approval, schema change must preserve data instead of rebuilding.

- Serves: `release-readiness` -- [Release readiness](../design/spec.md#release-readiness)
- Agent status: CLEAR
- Research: yes
- Requires: `approve-release`
- Dependencies: The release approval and its scope.
- User-visible outcome: Contracts at `1.0.0` and versioned migrations generated from contract
  diffs. Destructive-change refusal, dataset versions, and the released-environment guard on
  rebuild are active. The interchange contract is frozen at `1.0.0` with its upgrade chain.
- Scope boundary: Release verification of the SQLAlchemy/Alembic governance against the full
  generated model, then baseline and guard. No feature work.
- Data and artifact paths: `contracts/`, `migrations/`, `src/kn/db/`, `tests/integration/`.
- Execution path: Verify Alembic on full-model fixture diffs, baseline, and add release migration tests.
- Acceptance gates: An empty-database migration and an additive `1.0.0` -> `1.1.0` change preserve
  records, identifiers, and provenance. A breaking change without a plan is refused. Rebuild is
  refused when released.
- Documentation target: A new `current/release.md` page listed in the
  [areas index](current.md#areas).

#### release-readiness-implementation-audit

Release migration mode ends rebuild-based development, so it must preserve every durable input and
decision before the first versioned migration ships.

- Serves: `release-readiness` -- [Release readiness](../design/spec.md#release-readiness)
- Agent status: CLEAR
- Requires: `release-migration-mode`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: The first release migrates without losing durable state. The audit record
  gives every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: migration generation from contract diffs; forward and rollback paths;
  preservation of identity, claims, decisions, and bindings; the move from the last development
  rebuild; the interchange contract freeze; joint release pins; drift between migrations and
  contracts. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/`, `migrations/`, `src/kn/db/`, `tests/integration/`,
  `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Apply
  every migration to a copy of the development database, roll back one step, and compare the data
  before and after.
- Acceptance gates: Migrations keep every identity, claim, decision, and binding row. A rollback
  restores the previous schema without data loss. Every finding has a severity, evidence, and a
  disposition, no `blocker` is accepted, and every fix starts from a failing regression test. `make
  ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/release.md` listed in the [areas index](current.md#areas).

### Vocabulary drift monitoring -- `vocabulary-drift`

#### official-publication-drift-check (optional)

The publication reviews pin checksums of mutable URLs, but nothing notices when a publisher
replaces the bytes behind a reviewed edition.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: RUN NEEDED
- Dependencies: Network access to the publishers listed in the
  [publication reviews](current/ontology-taxonomy/verification.md#primary-publications). The ESA
  GPT and OECD downloads may need the owner's browser, as in record 0022 and record 0023.
- User-visible outcome: `kn vocabulary drift-check` re-fetches each pinned publication within a
  request budget and reports `unchanged`, `drifted`, or `unreachable` per scheme, with the new
  checksum. A drifted publication keeps its reviewed state, marked as drifted, until a new
  comparison.
- Scope boundary: Fetch, checksum, and report only, through the source-safety rules: allowlisted
  hosts, size limits, no credentials. No automatic re-verification and no seed change.
- Data and artifact paths: `src/kn/semantic/`, `$DATA_DIR/taxonomy-verification/drift-<run-id>/`,
  `tests/semantic/`.
- Execution path: Unit tests use a local stub server for unchanged, drifted, redirected, oversized
  and unreachable publications; the declared run checks the real publishers once.
- Acceptance gates: Every stub case gives its status without network access. The declared run
  reports a status for every pinned publication and is retained under `DATA_DIR`. `make ci` passes.
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).

#### vocabulary-drift-implementation-audit (optional)

Verify the vocabulary drift monitoring handoff against its specification and the next consumer.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: RUN NEEDED
- Requires: `official-publication-drift-check`
- Dependencies: Group acceptance records and the
  [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Compare an unchanged publication with a changed edition. Check that drift
  preserves reviewed terms and opens an actionable review.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: [Current-state areas](current.md#areas).

### Incremental InvenTree updates -- `inventree-feed`

#### inventree-change-feed (optional)

Listing every resource is wasteful once the instance can report its own changes.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `counterpart-acceptance-implementation-audit`
- Dependencies: Access to `/api/audit/` for the exchange user on the target release.
- User-visible outcome: Incremental imports read the InvenTree audit log as a change feed and fetch
  only the changed objects. A periodic full listing catches missed events.
- Scope boundary: A cursor over audit events per resource and a profile capability flag. No
  webhooks or plugins.
- Data and artifact paths: `src/kn/interchange/inventree/`, `tests/interchange/inventree/`.
- Execution path: Use fixture audit pages from the target release, then compare live with a full
  listing.
- Acceptance gates: On the test service, a change-feed import followed by a full listing finds no
  difference. An audit gap triggers a full listing.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### inventree-feed-implementation-audit (optional)

Verify the incremental inventree updates handoff against its specification and the next consumer.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: CLEAR
- Requires: `inventree-change-feed`
- Dependencies: Group acceptance records and the
  [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Replay a gap and a duplicate audit page. Compare the result with a full listing
  and verify the recorded cursor.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: [Current-state areas](current.md#areas).

### Additional space sources -- `space-extensions`

#### space-source-space-track (optional)

Space-Track would corroborate catalog identity and status.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-elt-implementation-audit`
- Dependencies: An owner-provided Space-Track account and approval of its terms. Credentials stay
  in the environment only.
- User-visible outcome: Catalog status corroboration claims linked by NORAD ID, kept separate from
  GP data.
- Scope boundary: Authenticated API use within the documented limits. No redistribution beyond
  the terms.
- Data and artifact paths: `domains/space/sources/space_track.yaml`,
  `tests/fixtures/space/space_track/`.
- Execution path: Follow the onboarding workflow with credentials redacted from every record.
- Acceptance gates: Corroboration claims link without merging sources. Redaction tests pass. All
  earlier suites pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-source-regulatory-registers (optional)

UNOOSA registration and ITU filing evidence would add registration and intent facts.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-elt-implementation-audit`
- Dependencies: A terms review and sampling authorization for UNOOSA and ITU Space Explorer.
- User-visible outcome: Registration and filing records load as `regulatory_record` claims, never
  as deployment or ownership.
- Scope boundary: Permitted exports or pages only. Filing, licence, and deployment stay distinct.
- Data and artifact paths: `domains/space/sources/`, `tests/fixtures/space/`.
- Execution path: Follow the onboarding workflow, with document extraction last in parser order.
- Acceptance gates: No filing creates a constellation count or availability. All earlier suites
  pass.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### space-extensions-implementation-audit (optional)

Verify the additional space sources handoff against its specification and the next consumer.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: CLEAR
- Requires: `space-source-space-track`, `space-source-regulatory-registers`
- Dependencies: Group acceptance records and the
  [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Recheck each source authorization, quota and redistribution rule. Replay each
  permitted fixture and check refusal paths for denied access.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

### GDELT native stream sampling -- `gdelt-native`

#### gdelt-selective-native-streams (optional)

Selected GKG, Events, and Mentions rows would add native context to watches.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-elt-implementation-audit`
- Dependencies: Collection authorization for the 15-minute files. BigQuery only with an approved
  budget.
- User-visible outcome: Rows that match the watch criteria load with native grain and joins.
  Unselected files are discarded after filtering.
- Scope boundary: Bounded windows only; no archive mirror.
- Data and artifact paths: `domains/gdelt/sources/native_streams.yaml`,
  `tests/fixtures/gdelt/native/`.
- Execution path: A streaming filter over the manifest files, recording checksums and selected
  counts.
- Acceptance gates: Joins follow the documented keys. Coverage statistics name the missing
  intervals. The byte budget holds.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

#### gdelt-native-implementation-audit (optional)

Verify the gdelt native stream sampling handoff against its specification and the next consumer.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: CLEAR
- Requires: `gdelt-selective-native-streams`
- Dependencies: Group acceptance records and the
  [audit procedure](../guide/planning-workflow.md#implementation-audits).
- User-visible outcome: The group has reproducible acceptance evidence and owned follow-up work.
- Scope boundary: Verify this group's outputs, failure paths and downstream compatibility.
- Data and artifact paths: Group fixtures, the numbered audit record and the forward plan.
- Execution path: Replay a bounded interval with missing joins. Verify coverage counts, edition
  keys and the authorized byte budget.
- Acceptance gates: Reproduce the member gates, run the six audit checks and record each finding
  with evidence, severity and disposition. Fix blockers before handoff and run `make ci`.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

### Local extraction evaluation -- `ai-extraction`

#### local-llm-candidate-extraction (optional)

Local inference could propose candidate claims and translations from permitted text.

- Serves: `ai-extraction` -- [AI extraction](../design/spec.md#ai-extraction)
- Agent status: RUN NEEDED
- Requires: `space-elt-implementation-audit`
- Dependencies: The NVIDIA driver and Container Toolkit on the target host, and a model whose
  licence permits this use.
- User-visible outcome: An optional `gpu` profile serves a benchmarked model. Candidate claims
  enter the review queue with source spans.
- Scope boundary: Candidates and derived translations only. No tools, network, SQL, secrets, or
  writes for the inference service.
- Data and artifact paths: `deploy/inference/`, `src/kn/ai/`, `tests/ai/`,
  `$DATA_DIR/ai-eval/<run-id>/`.
- Execution path: Label the fixtures, benchmark candidate models within 16 GB VRAM, and evaluate
  precision, recall, and hallucinated evidence.
- Acceptance gates: Zero unsupported published claims on labeled fixtures. Ingestion passes with
  the service down. A model that misses the gate stays disabled, which is a valid negative result.
- Documentation target: A new `current/ai-extraction.md` page listed in the
  [areas index](current.md#areas).

#### ai-extraction-implementation-audit (optional)

Model-proposed candidates must stay candidates, so leakage into canonical facts or unrecorded
prompts would be costly to unwind.

- Serves: `ai-extraction` -- [AI extraction](../design/spec.md#ai-extraction)
- Agent status: RUN NEEDED
- Requires: `local-llm-candidate-extraction`
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks. The rerun needs the `gpu`
  profile host that the extraction task uses.
- User-visible outcome: Model candidates are shown to stay in review. The audit record gives every
  check a result and every finding a disposition. The current-state page lists known limitations,
  and each scheduled finding is a plan task.
- Scope boundary: Focus: candidate claims that stay in review until accepted; the model and prompt
  version recorded with every candidate; licence limits on input text; reproducibility with fixed
  seeds; evaluation drift between model versions; `gpu` profile resource limits; translations kept
  as candidates. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `deploy/inference/`, `src/kn/ai/`, `tests/ai/`, `docs/impl/plan.md`, and
  the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Rerun
  extraction with the recorded model, prompt, and seed, and search canonical tables for a candidate
  that skipped review.
- Acceptance gates: No candidate reaches a canonical value without a review decision. A rerun with
  the same model, prompt, and seed reproduces the candidates. Every finding has a severity,
  evidence, and a disposition, no `blocker` is accepted, and every fix starts from a failing
  regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/ai-extraction.md` listed in the [areas index](current.md#areas).

## Human-Assisted Tasks

### Ingestion engine -- `ingestion-engine`

#### publish-satcom-drive-package

Unattended re-import from Google Drive needs the owner's published package and a read-only account
that the owner shares it with.

- Serves: `ingestion-engine` -- [Ingestion engine](../design/spec.md#ingestion-engine)
- Agent status: BLOCKED BY HUMAN
- Requires: `dataset-package-locations`
- Dependencies: The owner uploads the SATCOM package as one ZIP file to Google Drive, without
  conversion to Google formats. The owner creates a Google Cloud service account with the Drive API
  enabled, shares the file with it as a viewer, stores its key file under `$DATA_DIR/secrets/` with
  mode `0600`, and sets `KN_SATCOM_SOURCE` and `KN_GDRIVE_CREDENTIALS_FILE` in `.env`. The owner
  states the data rights (default `owner_private`) and whether periodic fetches are approved. An
  agent prepares the checklist and the ZIP of `.data/satcom_enriched_package` with its SHA-256.
- User-visible outcome: A recorded live fetch from the owner's Drive file, the rights and approval
  decision, and the documented periodic command.
- Scope boundary: Publication, access, and approval only. Credentials stay out of Git. Scheduled
  collection beyond an operating-system timer comes with `scheduled-space-ingestion`.
- Data and artifact paths: `.env` (local only), `$DATA_DIR/secrets/`,
  `$KN_RAW_ARCHIVE_DIR/staging/space/satcom/`,
  and the task record.
- Execution path: The owner completes the checklist. The agent runs `make satcom-fetch
  satcom-import` twice, then again after the owner uploads a changed revision.
- Acceptance gates: The first fetch reaches the existing snapshot or imports a new one, the second
  ends `not_modified` after one metadata request, and a changed revision imports a new snapshot
  beside the earlier one. No key material appears in logs or the record. A refused access is a
  valid negative result: it is recorded, and the dataset stays on its local location.
- Documentation target: `current/data-contracts.md` listed in the [areas index](current.md#areas).

### InvenTree exchange -- `inventree-exchange`

#### provide-inventree-instance-access

Reading the owner's InvenTree instance needs access the owner grants and data boundaries the owner
sets.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: BLOCKED BY HUMAN
- Dependencies: The owner provides the instance's HTTPS site URL and, when the proxy uses its
  internal CA, the exported root certificate and its SHA-256 fingerprint for the instance profile.
  The owner also provides a dedicated `kn-exchange` InvenTree user with view-only roles
  `part_category`, `part`, and `purchase_order`, its token in the local environment, and the list
  of allowed resources. An agent prepares the access checklist and the instance profile template
  from the [vl-itree deployment
  facts](../design/integrations/inventree.md#the-vl-itree-deployment) and the `vl-itree` API user
  guide.
- User-visible outcome: A non-secret instance profile draft and a recorded access decision.
- Scope boundary: Access and facts only. Credentials stay out of Git. Write access is a separate
  decision in `approve-inventree-write-exchange`.
- Data and artifact paths: `interchange/inventree/instances/vl-itree.yaml`, and the task record.
- Execution path: The owner supplies access. The agent records the non-secret profile and checks
  the token with a read-only `GET /api/`.
- Acceptance gates: The instance answers with its software and API versions using the provided
  token, and the profile records the allowed resources.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### align-vl-itree-release

`vl-itree` must run exactly the target InvenTree release that KN is tested against, over TLS, and
with changed passwords, because it can run on another machine.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: HUMAN-GATED
- Requires: `inventree-test-service`
- Dependencies: The `vl-itree` release `v0.1.0` pins InvenTree `1.7.3` and meets the
  [vl-itree requirements](../design/integrations/inventree.md#vl-itree-requirements) in the
  repository. The owner deploys it on the instance through the release's one-time migration:
  offline backup, password rotation, TLS settings, and start. The owner then reports the HTTPS
  site URL, the certificate mode, and, in `internal` mode, the root certificate fingerprint. A
  later target passes `inventree-upgrade-check` and gets a new `vl-itree` release tag.
- User-visible outcome: `vl-itree` runs the target release from pinned images, serves HTTPS to
  other machines, and refuses to start with unchanged passwords. `deploy/versions.yaml` records
  InvenTree `1.7.3`, its image digest, and the `vl-itree` release tag `v0.1.0`.
- Scope boundary: The
  [vl-itree requirements](../design/integrations/inventree.md#vl-itree-requirements) and their
  deployment, in the `vl-itree` repository. KN never deploys `vl-itree`.
- Data and artifact paths: The `vl-itree` release tag `v0.1.0`, `deploy/versions.yaml`, and the
  task record.
- Execution path: The owner migrates and deploys the release. The agent records the versions that
  the instance reports over HTTPS.
- Acceptance gates: The instance reports version `1.7.3` and API version 570 over verified TLS
  from another machine. Its image reference matches `deploy/versions.yaml`. The launcher refuses
  a default password.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

#### approve-inventree-write-exchange

Writing KN knowledge into the owner's inventory is the owner's authorization.

- Serves: `inventree-exchange` -- [InvenTree exchange](../design/spec.md#inventree-exchange)
- Agent status: HUMAN-GATED
- Requires: `inventree-write-export`, `vl-itree-read-acceptance`
- Dependencies: An agent prepares a dry-run plan against `vl-itree` with its loss report and
  conflicts, and proposes the export profile and field ownership.
- User-visible outcome: An approval reference in the instance profile, a write-capable token for
  `kn-exchange` with the fewest roles the export profile needs, and the approved first plan ID.
- Scope boundary: Write authorization, the export profile, field ownership, and whether part and
  category creation is enabled.
- Data and artifact paths: `interchange/inventree/instances/vl-itree.yaml`, and the task record.
- Execution path: The owner reviews the dry run, then approves, narrows, or rejects it.
- Acceptance gates: The decision is recorded, and `kn source validate` accepts the instance profile
  with its write approval.
- Documentation target: `current/inventree-exchange.md` listed in the
  [areas index](current.md#areas).

### Space ELT -- `space-elt`

#### authorize-space-source-sampling

Fetching any space data sample needs the owner's authorization.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: HUMAN-GATED
- Requires: `space-source-terms-review`
- Dependencies: The terms dossiers. An agent proposes a request budget per source.
- User-visible outcome: A recorded authorization per pilot source, with budget, scope, and
  conditions, and catalogue state `sampling_authorized`.
- Scope boundary: Bounded sampling only, not scheduled collection.
- Data and artifact paths: `domains/space/sources/dossiers/`, and the task record.
- Execution path: The owner reviews each dossier and approves, narrows, or rejects it.
- Acceptance gates: Each pilot source has a decision and budget, or a rejection with its reason.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

#### approve-space-source-enablement

Scheduled collection of space sources needs maintainer approval after review.

- Serves: `space-elt` -- [Space ELT](../design/spec.md#space-elt)
- Agent status: HUMAN-GATED
- Requires: `space-elt-implementation-audit`
- Dependencies: The investigation reports, passing fixtures, and the crawler configurations. An
  agent prepares the approval checklist.
- User-visible outcome: Approval references recorded in each crawler configuration, and catalogue
  state `approved`.
- Scope boundary: Licence, rate, permission, and redistribution sign-off per source.
- Data and artifact paths: `domains/space/sources/`, and the task record.
- Execution path: The maintainer reviews each checklist. The agent records the approvals, and
  `kn source validate` confirms them.
- Acceptance gates: Every enabled source validates with an approval reference. A rejected source
  stays disabled.
- Documentation target: `current/space-domain.md` listed in the [areas index](current.md#areas).

### Space dashboards -- `space-dashboards`

#### review-space-dashboards

Whether the SATCOM dashboards answer the operator's questions is the owner's judgment.

- Serves: `space-dashboards` -- [Space dashboards](../design/spec.md#space-dashboards)
- Agent status: HUMAN-GATED
- Requires: `space-dashboards-implementation-audit`, `orchestration-implementation-audit`
- Dependencies: The deployed bundles on scheduled live data. An agent prepares a review guide with
  screenshots in both locales.
- User-visible outcome: Owner acceptance, or a list of changes attached to the owning tasks.
- Scope boundary: Product judgment on content, layout, and semantics.
- Data and artifact paths: The task record.
- Execution path: The owner walks the review guide, and the agent schedules any findings.
- Acceptance gates: An acceptance or a change list is recorded.
- Documentation target: `current/space-dashboards.md` listed in the
  [areas index](current.md#areas).

### GDELT ELT -- `gdelt-elt`

#### authorize-gdelt-collection

GDELT dictionary and DOC watch collection needs the owner's authorization.

- Serves: `gdelt-elt` -- [GDELT ELT](../design/spec.md#gdelt-elt)
- Agent status: HUMAN-GATED
- Requires: `gdelt-source-terms-review`
- Dependencies: The GDELT dossier and the proposed watch topics and budgets prepared by an agent.
- User-visible outcome: A recorded authorization for dictionaries and DOC watches, with budgets and
  approved topics.
- Scope boundary: Dictionaries and DOC watches only. Native streams and BigQuery need a separate
  decision.
- Data and artifact paths: `domains/gdelt/sources/dossiers/`, and the task record.
- Execution path: The owner reviews the dossier and topics, then approves, narrows, or rejects.
- Acceptance gates: A decision with budgets is recorded.
- Documentation target: `current/gdelt-domain.md` listed in the [areas index](current.md#areas).

### Microelectronics ELT -- `microelectronics-elt`

#### authorize-microelectronics-sources

Microelectronics sampling needs the owner's authorization.

- Serves: `microelectronics-elt` -- [Microelectronics ELT](../design/spec.md#microelectronics-elt)
- Agent status: HUMAN-GATED
- Requires: `microelectronics-source-terms-review`
- Dependencies: The dossiers and proposed budgets prepared by an agent.
- User-visible outcome: Recorded authorizations for MLPerf Tiny, CORDIS, datasheet capture,
  and official policy sources.
- Scope boundary: First-wave sources only.
- Data and artifact paths: `domains/microelectronics/sources/dossiers/`, and the task record.
- Execution path: The owner reviews and decides per source.
- Acceptance gates: Each first-wave source has a decision.
- Documentation target: `current/microelectronics-domain.md` listed in the
  [areas index](current.md#areas).

### Localization -- `localization`

#### review-ukrainian-terminology

Core Ukrainian terminology needs review by a Ukrainian technical speaker.

- Serves: `localization` -- [Localization](../design/spec.md#localization)
- Agent status: HUMAN-GATED
- Requires: `localization-implementation-audit`
- Dependencies: A Ukrainian technical speaker named by the owner. An agent prepares a glossary
  export of every `uk` UI string and every vocabulary label that still falls back to English, with
  context and the [translation review fields](current/ontology-taxonomy/text.md#label-and-review-rules).
- User-visible outcome: Reviewed Ukrainian terminology for dashboards, maps, and vocabulary labels.
- Scope boundary: Review and corrections of catalogs and labels.
- Data and artifact paths: `locales/uk/`, `domains/<domain>/seeds/`, and the task record.
- Execution path: The agent exports the glossary. The reviewer annotates it. The agent applies the
  corrections and reruns the bilingual checks.
- Acceptance gates: The reviewer signs off in the task record, and the bilingual checks pass after
  the corrections.
- Documentation target: `current/localization.md` listed in the [areas index](current.md#areas).

### Operations hardening -- `operations-hardening`

#### provide-target-server-and-backup

Measured operations need the real host and an off-host backup destination.

- Serves: `operations-hardening` -- [Operations hardening](../design/spec.md#operations-hardening)
- Agent status: BLOCKED BY HUMAN
- Dependencies: The owner provides access to the target server (at least 32 GB RAM, 4 TB disk,
  NVIDIA 16 GB VRAM), confirmed CPU, disk, and driver details, and an encrypted off-host backup
  destination. An agent prepares the host checklist.
- User-visible outcome: A recorded host profile and backup destination.
- Scope boundary: Access and facts only. Credentials stay out of Git.
- Data and artifact paths: `deploy/hosts/` (non-secret profile), and the task record.
- Execution path: The owner supplies access, and the agent records the non-secret profile.
- Acceptance gates: The host profile and backup destination are recorded, and the agent can reach
  the host with the provided access.
- Documentation target: `current/operations.md` listed in the [areas index](current.md#areas).

### Release readiness -- `release-readiness`

#### approve-release

Leaving the development phase is the owner's decision.

- Serves: `release-readiness` -- [Release readiness](../design/spec.md#release-readiness)
- Agent status: HUMAN-GATED
- Requires: `review-ukrainian-terminology`, `review-space-dashboards`,
  `counterpart-acceptance-implementation-audit`, `model-baseline-implementation-audit`,
  `localization-implementation-audit`, `operations-hardening-implementation-audit`,
  `vocabulary-namespace-implementation-audit`, `satcom-publication-implementation-audit`
- Dependencies: The evidence of every capability evaluation, compiled by an agent into a release
  checklist. Through their own prerequisites, these gates cover the bilingual suite, all three
  domains' dashboards, scheduled ingestion, security, the restore drill, InvenTree exchange with
  `vl-itree`, and identity calibration. If a newer stable InvenTree release exists at approval,
  the upgrade check runs on it first, so the joint release ships on the newest stable release.
- User-visible outcome: Approval of the release scope, or a narrowed scope with deferred
  capabilities named.
- Scope boundary: Release decision only.
- Data and artifact paths: The task record.
- Execution path: The owner reviews the checklist and decides.
- Acceptance gates: A recorded decision with its scope.
- Documentation target: `current/release.md` listed in the [areas index](current.md#areas).
