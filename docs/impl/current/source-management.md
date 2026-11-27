# Source Management

A [development rebuild](data-contracts/rebuild.md) loads 37 space, 65 microelectronics, and
17 GDELT candidates into `system.source_catalogue`. All 119 start in `candidate` with
`access_verification=unverified`. Scheduling requires a separately reviewed
crawler configuration and approval. Catalogue rows carry no scheduling authority.

## List sources

Set `KN_DATABASE_URL` and `KN_DATABASE_PASSWORD_FILE` for the rebuilt database before running
`kn source list`.

```bash
kn source list
kn --json source list
```

The command can connect as a database login with the `kn_system_reader` role. It lists sources
by domain and original worksheet row. The headings, lifecycle labels, and access status use
English. Names and cadence retain the original proposal text. Each `--json` entry includes the
catalogue ID, domain,
nullable original ID, label, priority, cadence, structured access notes, access verification
status, and lifecycle state. A newly upgraded empty database lists zero candidates until its
first development rebuild.

## Source health and freshness

Use the deployed database and the crawler profile for the source you want to inspect. These
examples read the candidate referenced by the HTTP fixture. The `kn_system_reader` role can run
these commands.

```bash
kn source status tests/sources/fixtures/config/http.yaml
kn --json source status tests/sources/fixtures/config/http.yaml
```

Status reads one stream. It defaults to scope `default` and namespace `live`. Use
`--scope SCOPE` for another scope and `--backfill` for the profile's backfill namespace.
The command reads the deployed catalogue and the
[registered history and checkpoint tables](ingestion-engine.md#run-history-and-health) in one
query. It works for paused and other catalogue states. It validates the profile and uses its
monitoring settings without opening the archive, invoking adapters, or reading enablement
evidence files. An invalid profile or an ID absent from the deployed catalogue returns
`E_SOURCE_CONFIG`. A successful report exits zero for any health state.

| Field or group | Meaning |
| --- | --- |
| `lifecycle_state`, `state` | Current catalogue state and latest run attempt outcome. `never_run` means no attempt exists and `unfinished` means the latest attempt has no terminal outcome. Within a logical run, the highest attempt number wins. Across runs, start time and then run ID determine order. |
| `last_attempt_at`, `last_success_at` | Latest attempt's start and most recent `success` finish time, including replay. JSON also gives the latest attempt's run ID, number, mode and finish time. All times use UTC. |
| `last_confirmed_at`, `stale` | A fetch ending in `success` or `not_modified` confirms freshness at its finish time. A stream is stale before its first confirmation or when the confirmation age exceeds `schedule.freshness_seconds`. Without that value, the threshold is twice the longest gap between consecutive scheduled runs, so `0 */2 * * *` gives 14,400 seconds and `0 6 * * 1-5` gives six days. `freshness_threshold_seconds` reports the value used. A future confirmation has zero age until the clock catches up. |
| `consecutive_failures`, `failing` | The streak counts `partial`, `blocked` and `failed` fetch outcomes since the latest confirmed fetch. The failing flag turns on at the configured `monitoring.alert_thresholds.consecutive_failures`. |
| Counts, bytes, and requests | Record, claim, reject and quarantine counts, bytes received, and requests used and budget come from the latest attempt. JSON uses `null` for unmeasured figures and keeps a measured zero. English text displays missing values as `unknown`. |
| `checkpoint_revision`, `cursor_lag_seconds` | The greatest committed checkpoint revision, or zero before the first. For a time watermark, lag is elapsed whole seconds, clamped to zero for a future watermark. Otherwise status uses the latest attempt's stored lag when present. |
| `last_error_code` | Latest recorded error observation for the stream, even after a later error-free run. Observation time orders errors; run ID, attempt and occurrence number break ties. |

The stable JSON result is under `source_status`. The operations mart can consume that row or use
`kn.sources.status.read_source_status(connection, stream, policy)` with
`kn.sources.status.monitoring_policy(config)` for the same crawler thresholds.
[Space analytics marts](../plan.md#space-analytics-marts) owns materialization. Status evaluates
only the stale and consecutive-failure thresholds. `monitoring.freshness_sla_seconds` and the
reject, quarantine and cursor-lag alert thresholds are declarations for that mart.

## Reviewed inputs and identifiers

The [ODCS contract](../../../contracts/core/system/source-catalogue.odcs.json) deploys beside
system governance. Its eight lifecycle values are `candidate`, `investigating`,
`sampling_authorized`, `approved`, `enabled`, `paused`, `retired`, and `rejected`.

Each `domains/<domain>/seeds/sources.json` points to the packaged reviewed snapshot.
Microelectronics uses exact native IDs such as `microelectronics:D01`. Space and GDELT
use the original worksheet row number as a fixed local ID, such as `space:row-4` or
`gdelt:row-5`, with a null `original_id`. These keys stay fixed when listing or ordering
changes. Preserve each assigned key when adding a later proposal version. Every row retains
its workbook name, SHA-256, sheet name, row number, and every original cell. Coverage,
watchlist, and ingestion-order guidance sheets stay with their original proposals.

Proposal access statements, including source-provided review labels, remain unverified metadata.
A [human verification decision](evidence-model.md) requires an authorized actor and an exact
target and version. Proposal priority `P0`, `P1`, or `P2` is an investigation priority.

The reviewed [source rank policy](../../../contracts/core/policies/source-ranks.yaml) starts
with an empty `overrides` list. Each override has an exact qualified `source_id`, a
[rank class](../../design/spec.md#update-policy) in `rank`, and an optional `field_group`.
Rebuild refuses unknown IDs, invalid classes, and duplicate scopes before inserting candidates.
[Canonical selection](evidence-model.md#canonical-selection) resolves a `field_group` as a stable
field ID prefix at a dot boundary; the longest matching group wins over a source-wide override.

Reapplying reviewed seeds preserves identical rows. A conflicting row aborts the catalogue
seed load and rolls back any partial insert.

## Validate crawler configurations

```bash
kn source validate tests/sources/fixtures/config/http.yaml
kn source validate tests/sources/fixtures/config/curated.yaml
kn --json source validate tests/sources/fixtures/config/adapter.yaml
```

The command reads one YAML or JSON configuration and returns `source_id`, `state`, and
`status: valid`.
An invalid configuration exits with status 1. JSON errors contain `E_SOURCE_CONFIG`, a
JSON Pointer prefixed by `$`, a rule, and a hint. Diagnostics omit input values. Start from the
[crawler configuration template](../../guide/templates/source-crawler-config.yaml), which
validates as a candidate HTTP JSON profile and names every property the
[version 1 JSON Schema](../../../src/kn/sources/config/crawler.schema.json) can require outside
counterpart instance profiles. A lightweight test keeps the template valid and complete.
Keep each domain's reviewed configuration under `domains/<domain>/sources/<source-id>.yaml`.
The validator works offline using the packaged schema and reviewed catalogue.

| Block | Version 1 declaration |
| --- | --- |
| `identity` | Exact qualified `source_id`, bilingual labels and owner. Drafts can use a proposed qualified ID. Enablement requires an ID in the reviewed catalogue. |
| `access` | Method, endpoints and controls, plus the matching file, watch, or adapter profile where applicable. |
| `schedule` | Five-field numeric cron in UTC, including ranges, lists and steps on wildcards or ranges. Restrict either the day of month or the day of week, because cron implementations combine the two differently (`cronDays`). The schedule must match at least one calendar date (`cronNeverRuns`). Set `freshness_seconds` to override the default stale threshold of twice the longest gap between runs. |
| `cursor` | `snapshot_hash`, `updated_since`, `id_range`, or `window`, with the fields and overlap required by the strategy, and a backfill namespace distinct from `live`. |
| `raw` | `warc` or `blob`, retention in days (at most 36,525, like the reviewed rights retention) and redistribution policy. |
| `parse` | `kn.domains.<domain>.<module>:<function>`, native schema or codebook edition, and a SHA-256 schema fingerprint. Validation checks the names against the profile and its owning domain. |
| `mapping` | Ordered native `record_key` fields and optional `version_field`. Field mappings name contract field IDs and units. Optional mappings cover native codes, classes, relations, identifiers, identity attributes and time semantics. Keep native codes such as `"001"` quoted. |
| `quality` | Required native fields, numeric ranges, expected volume, quarantine limit and batch-stop conditions. |
| `errors` | Distinct HTTP status or parser signal conditions, each with a standard error code and its assigned retry class. |
| `monitoring` | Freshness SLA, alert thresholds and expected record counts. |
| `rights`, `approval`, `verification` | Permission and review, lifecycle and approval reference, and evidence paths for enablement. |
| `exchange` | Counterpart direction, field ownership, and export profile and write approval when the direction includes export. |

HTTP JSON, CSV, XML, feed, permitted HTML and remote bulk profiles declare HTTPS endpoints,
exact DNS hosts, redirect policy, request and byte limits, a timeout of at most 3,600 seconds,
rate limits, content types and conditional requests. Use `auth_env` for the credential alias and
`secret_query_parameters` to declare names for redaction. Endpoints containing those
parameters fail validation.

- `curated_file` declares the directory under the domain's `curation` tree and which fields
  contain the cited URI, capture time and curator.
- `bulk_file` with `access.package` declares a location variable, a default path under
  `DATA_DIR`, a versioned dataset contract, expected files and CSV headers and dialect, and
  unpacking limits. Drive profiles add the key-file environment alias and bounded network
  controls for `www.googleapis.com`.
- `http_json` with `access.watches` declares bilingual query aliases, owner, purpose, lookback,
  split floor and result cap. These profiles require a window cursor.
- `adapter_api` declares the reviewed `inventree` adapter, resource allowlist and `limit`
  pagination. InvenTree raw data is private by default. An export policy that permits sharing
  requires an owner export approval reference.

### Enablement evidence

Use `approval.state: enabled` with an approver and an approval reference. The corresponding
rights review must record granted permission, a terms URI, reviewer, review timestamp with
offset, licence, export policy, and retention. Raw retention must fit within the review.
Raw redistribution must also fit the export policy. Both `owner_private` and `forbidden`
require `raw.redistribution: forbidden`. A restricted export policy permits forbidden or
restricted raw redistribution.

List nonempty fixture files in `verification.fixtures` and put a pytest JUnit XML report path
in `verification.test_report`. Use paths relative to the repository root or, for a standalone
configuration, its containing directory. The UTF-8 report must fit within 8 MiB and contain at
least one named test case and zero failures, errors or skips. Use a single `testsuite` or
a `testsuites` root with direct suite children. Each case belongs directly to its suite.
Review establishes which source and revision the report covers.

A successful draft validation reports its declared state, including `candidate`.
[`kn source run` and `kn source replay`](ingestion-engine.md#run-and-replay-a-snapshot) require
both `approval.state: enabled` with passing evidence and an enabled row in the deployed
catalogue. A candidate row or missing rights decision produces zero requests.

### Error codes and pagination

| Code | Retry class | Meaning |
| --- | --- | --- |
| `transient_network` | `transient` | Temporary transport failure. |
| `rate_limited` | `rate_limit` | Throttled request (HTTP 429). Honor Retry-After within the run budget. |
| `auth_failed` | `permanent` | Credentials failed (HTTP 401). |
| `permission_denied` | `permanent` | Source refused access (HTTP 403). |
| `not_modified` | `none` | The conditional response reports unchanged content (HTTP 304). |
| `payload_invalid` | `permanent` | The response cannot be parsed as the expected format. |
| `schema_drift` | `permanent` | The native schema changed. |
| `integrity_lost` | `permanent` | Key, time or payload integrity failed. |
| `budget_exhausted` | `permanent` | This run has used up its approved budget. |

The schema owns the error vocabulary. Ingestion consumers can look up a retry class through
`kn.sources.config.schema.retry_class_for`. Only the transient and rate-limit classes are
retryable.

HTTP pagination will run through KN's archive-first fetch path. That path must capture every
response, including malformed bodies, transient responses and partial pages, before parsing or
advancing pagination. dlt exposes response hooks and returns decoded pages with response context.
Using its REST client would require adapting that control flow to KN's archive and request-budget
ordering, so version 1 adds neither the dlt REST client nor its paginators. Revisit standalone
paginator reuse if the fetch implementation can exercise it against archived-response fixtures
while preserving that ordering. See the [dlt REST client API](https://dlthub.com/docs/api_reference/dlt/sources/helpers/rest_client/client).

The [raw archive design review](../records/0054-adhoc-raw-archive-storage-design.md) records how the
planned fetch path uses the existing `warc` and `blob` profile values and which measurements would
justify changing the fetch index backend.

## Onboard a source

The [onboarding guide](../../guide/source-onboarding.md) covers documentation review, bounded
sampling, investigation, fixtures, review, enablement approval, and scheduling. It provides
templates for the terms dossier, crawler configuration, investigation report, fixture
sanitization worksheet, and review checklist. Sampling and enablement each require a recorded
owner decision.

`make fixture-check` runs in `make ci` and scans regular UTF-8 files under directories named
`fixtures` anywhere in `tests/`. It refuses recognizable credentials, personal data patterns,
and files it cannot inspect. Diagnostics report locations and rule categories. The
[fixture procedure](../../guide/source-onboarding.md#4-build-and-sanitize-fixtures) lists the
formats and explains the manual review for rights and sensitive data.

## Verification

- `make ci` reconciles every seed against its original proposal row, validates malformed
  inputs and rank references, checks both CLI locales, and detects generated-contract drift.
- `make ci` also runs the crawler fixtures, checks the declared retry class for every code, and
  exercises CLI diagnostics and enabled configurations with missing or failing evidence.
- The fixture check has regression cases for planted credentials and personal data, encodings,
  approved placeholders, and unscannable files.
- `make ci` measures the longest gap between scheduled runs, including weekday, month-end and
  leap-day schedules, refuses schedules that never run or restrict both day fields, and derives
  the default stale threshold without a database.
- `make test-integration` checks repeated PostgreSQL rebuilds, the reader role, and rollback
  on seed conflicts or unknown override IDs. The [combined baseline](data-contracts/model-baseline.md)
  compares all stored catalogue fields across two rebuilds.

[Catalogue record 0035](../records/0035-source-management-source-catalogue-import.md),
[crawler configuration record 0036](../records/0036-source-management-crawler-config-schema.md),
and [onboarding record 0037](../records/0037-source-management-source-onboarding-workflow.md)
preserve the member gates. The
[source admission audit](../records/0038-source-management-source-admission-implementation-audit.md)
records the handoff. The
[source status record](../records/0060-source-management-source-status-monitoring.md) gives
the fixture commands and results for both operator output formats, the registered vocabulary,
the freshness boundary, and the reader role. The
[source management audit](../records/0061-source-management-source-management-implementation-audit.md)
reproduces the member gates and records its findings.

## Known limitations

- A reviewed lifecycle decision cannot yet reach the deployed catalogue, and only proposal rows
  can be catalogued. Rebuild loads every row as `candidate`, so running a source needs an
  `enabled` row that the next rebuild erases.
  [Source lifecycle registry](../plan.md#source-lifecycle-registry) owns both.
- A `sampling_authorized` profile cannot run, and its decision fields are not declared.
  [Source sampling admission](../plan.md#source-sampling-admission) owns bounded samples.
- Rate limits are declared but not enforced across runs, and no `robots.txt` check exists yet.
  An interrupted attempt keeps unmeasured request counters, so status can report fewer requests
  than its run made. [HTTP fetch safety](../plan.md#http-fetch-safety) owns all three.
- Replay requires an enabled source, and a fetch after a development rebuild that has not
  replayed the archive ends in `E_INPUT` with an unfinished attempt.
  [Rebuild from raw](../plan.md#rebuild-from-raw) owns both.
- A profile in any other lifecycle state validates with its schedule and reports its state.
  `kn source run` and `kn source replay` refuse it with `enabledState` before any request.
  [Flow generation](../plan.md#kestra-flow-generation) must emit flows only for enabled sources.
- Status flags failures only when `monitoring.alert_thresholds.consecutive_failures` is set, and
  an unfinished attempt is not a failure. Such a stream turns stale after its threshold. Reopen
  when the operations mart defines alerting on the other declared thresholds.
- Version 1 has no request body or OAuth token exchange, so a GraphQL source such as
  `microelectronics:C03` or an OAuth source needs an additive, optional block when its
  onboarding task begins. Existing profiles stay valid.
