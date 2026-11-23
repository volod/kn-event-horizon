# Source Management

A [development rebuild](data-contracts/rebuild.md) loads 37 space, 65 microelectronics, and
17 GDELT candidates into `system.source_catalogue`. All 119 start in `candidate` with
`access_verification=unverified`. Scheduling requires a separately reviewed
crawler configuration and approval. Catalogue rows carry no scheduling authority.

## List sources

Set `KN_DATABASE_URL` and `KN_DATABASE_PASSWORD_FILE` for the rebuilt database before running
`kn source list`.

```bash
kn --locale en source list
kn --locale uk source list
kn --json source list
```

The command can connect as a database login with the `kn_system_reader` role. It lists sources
by domain and original worksheet row. The headings, lifecycle labels, and access status use
the selected interface language. Names and cadence retain the original proposal text. The
`--json` output is identical in both locales. Each entry includes the catalogue ID, domain,
nullable original ID, label, priority, cadence, structured access notes, access verification
status, and lifecycle state. A newly upgraded empty database lists zero candidates until its
first development rebuild.

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
Claim ranking and field-group resolution belong to `canonical-fact-selection`.

Reapplying reviewed seeds preserves identical rows. A conflicting row aborts the catalogue
seed load and rolls back any partial insert.

## Validate crawler configurations

```bash
kn source validate tests/sources/fixtures/config/http.yaml
kn --locale uk source validate tests/sources/fixtures/config/curated.yaml
kn --json source validate tests/sources/fixtures/config/adapter.yaml
```

The command reads one YAML or JSON configuration and returns `source_id`, `state`, and
`status: valid`.
An invalid configuration exits with status 1. JSON errors contain `E_SOURCE_CONFIG`, a
JSON Pointer prefixed by `$`, a rule, and a hint. Diagnostics omit input values. Use the
[version 1 JSON Schema](../../../src/kn/sources/config/crawler.schema.json) for the exact field
names and the [HTTP fixture](../../../tests/sources/fixtures/config/http.yaml) as a starting point.
Keep each domain's reviewed configuration under `domains/<domain>/sources/<source-id>.yaml`.
The validator works offline using the packaged schema and reviewed catalogue.

| Block | Version 1 declaration |
| --- | --- |
| `identity` | Exact qualified `source_id`, bilingual labels and owner. Drafts can use a proposed qualified ID. Enablement requires an ID in the reviewed catalogue. |
| `access` | Method, endpoints and controls, plus the matching file, watch, or adapter profile where applicable. |
| `schedule` | Five-field numeric cron in UTC, including ranges, lists and steps on wildcards or ranges. Set `freshness_seconds` to override the default of twice the schedule interval. |
| `cursor` | `snapshot_hash`, `updated_since`, `id_range`, or `window`, with the fields and overlap required by the strategy, and a backfill namespace distinct from `live`. |
| `raw` | `warc` or `blob`, retention in days and redistribution policy. |
| `parse` | `kn.domains.<domain>.<module>:<function>`, native schema or codebook edition, and a SHA-256 schema fingerprint. Validation checks the names against the profile and its owning domain. |
| `mapping` | Ordered native `record_key` fields and optional `version_field`. Field mappings name contract field IDs and units. Optional mappings cover native codes, classes, relations, identifiers, identity attributes and time semantics. Keep native codes such as `"001"` quoted. |
| `quality` | Required native fields, numeric ranges, expected volume, quarantine limit and batch-stop conditions. |
| `errors` | Distinct HTTP status or parser signal conditions, each with a standard error code and its assigned retry class. |
| `monitoring` | Freshness SLA, alert thresholds and expected record counts. |
| `rights`, `approval`, `verification` | Permission and review, lifecycle and approval reference, and evidence paths for enablement. |
| `exchange` | Counterpart direction, field ownership, and export profile and write approval when the direction includes export. |

HTTP JSON, CSV, XML, feed, permitted HTML and remote bulk profiles declare HTTPS endpoints,
exact DNS hosts, redirect policy, request and byte limits, timeout, rate limits, content types
and conditional requests. Use `auth_env` for the credential alias and
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

A successful draft validation reports its declared state, including `candidate`. A fetch consumer
must validate the reviewed profile and require `approval.state: enabled` before issuing a scheduled
request.

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

## Onboard a source

The [onboarding guide](../../guide/source-onboarding.md) covers documentation review, bounded
sampling, investigation, fixtures, review, enablement approval, and scheduling. It provides
templates for the terms dossier, investigation report, fixture sanitization worksheet, and
review checklist. Sampling and enablement each require a recorded owner decision.

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
- `make test-integration` checks repeated PostgreSQL rebuilds, the reader role, and rollback
  on seed conflicts or unknown override IDs. The [combined baseline](data-contracts/model-baseline.md)
  compares all stored catalogue fields across two rebuilds.

[Catalogue record 0035](../records/0035-source-management-source-catalogue-import.md),
[crawler configuration record 0036](../records/0036-source-management-crawler-config-schema.md),
and [onboarding record 0037](../records/0037-source-management-source-onboarding-workflow.md)
preserve the member gates. The
[source admission audit](../records/0038-source-management-source-admission-implementation-audit.md)
records the handoff. Run history and source health belong to
[ingestion state contracts](../plan.md#ingestion-state-contracts) and
[source status monitoring](../plan.md#source-status-monitoring).
