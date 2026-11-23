# Crawler Configuration Schema

## Work contract

```markdown
#### crawler-config-schema

Crawler behavior, including ontology mapping, error mapping, and monitoring, must be declared and
validated.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Execution stage: MODEL
- Dependencies: The [reviewed catalogue and qualified source IDs](current/source-management.md).
- User-visible outcome: `kn source validate` checks a crawler YAML against its schema and refuses
  enablement without a rights review, an approval reference, fixtures, and passing tests.
- Scope boundary: The JSON Schema for every block in the specification, including source record
  keys and the `adapter_api` method, and the standard error-code table. Record whether the dlt
  REST client and paginators are adopted for HTTP pagination, given the raw-archive constraint. No
  runtime execution.
  Include the known HTTP, curated, prefetched-package, watch and counterpart adapter configuration
  shapes now, while keeping their later execution and source enablement separate.
- Data and artifact paths: `src/kn/sources/config/`, `domains/<domain>/sources/`,
  `tests/sources/`.
- Execution path: Use a schema-first design with valid and invalid fixture configurations, plus an
  error-code mapping test per code.
- Acceptance gates: Invalid fixtures fail with path-specific diagnostics. An enabled configuration
  without approval fails. The dlt decision is recorded with its reason.
- Documentation target: `current/source-management.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The packaged version 1 JSON Schema covers the source blocks, including field and ontology
mappings, record keys and version fields, and the method-specific declarations for HTTP,
curation, prefetched packages, watches, and InvenTree. The validator uses the reviewed
catalogue's exact qualified IDs for enabled sources. It checks file evidence locally and
accepts a UTF-8 pytest JUnit report with passing test cases. Approval review establishes the
report's scope and applicable source revision.

The schema owns the standard error codes and retry classes. Ingestion can reuse the lookup
and the normalized pagination declarations. The implementation uses no added dependencies.
The dlt REST client and paginators are deferred because KN's fetch layer must archive every
response before decoding or advancing pagination, within the source's request budget. The
[current-state decision](../current/source-management.md#error-codes-and-pagination) links the
dlt API and states the condition for reconsidering standalone paginator reuse.

| Finding | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| CRAWLER-01 | major | `test_allowlist_disallows_ip_literals` originally accepted a loopback literal as a hostname. Fetch admission consumes the allowlist. | Source management, fixed with a DNS host constraint and regression fixture. |
| CRAWLER-02 | major | `test_utf16_report_cannot_bypass_the_doctype_check` originally parsed a UTF-16LE report through NUL characters in the decoded string. Enablement consumes test reports. | Source management, fixed by rejecting NUL before parsing. |
| CRAWLER-03 | major | `test_standard_http_status_meaning` originally allowed a permanent HTTP refusal to map to a transient code and allowed 304 and 429 to be reclassified. Ingestion consumes the retry policy. | Source management, fixed with standard HTTP status mappings in the schema. |

## Acceptance evidence

Status: accepted.

- `.venv/bin/python -m pytest tests/sources` passed all 128 tests, including schema variants,
  stable paths for invalid profiles, every standard retry mapping, and fail-closed enablement.
- `kn --json source validate` accepted a config backed by the actual pytest JUnit report and
  exited 1 at `$/approval/reference` after removal of its approval reference.
- CLI smoke tests passed for all five profile fixtures and a missing Ukrainian label in both
  interface locales. The invalid fixture reported `$/identity/labels/uk`.
- The offline `uv build --out-dir "$run_dir/dist"` succeeded using the loaded environment and
  writable project uv cache. The extracted wheel included the schema and gave the same
  enablement results outside the checkout's import path.
- `make ci` passed all checks and 1,054 tests, with 92 local-only tests deselected. This task's
  gates are offline and fixture-based. `make lint-md` and `git diff --check` passed.
- Evidence is under `$DATA_DIR/crawler-config/check-BgGTPvsM/`.

## Handoff

`source-onboarding-workflow` now consumes the crawler validator. The source admission audit
keeps both acceptance records and still requires the onboarding workflow. Ingestion state
contracts can consume the error vocabulary through the current-state page. The
`source-management` capability remains planned pending onboarding and run status.

`make plan-status` changed from 124 to 123 tasks, from 111 to 110 in the agent lane, and from
15 to 14 in MODEL. The human lane stays at 13 and DELIVERY at 109. The next ready agent task
is `source-onboarding-workflow`.
