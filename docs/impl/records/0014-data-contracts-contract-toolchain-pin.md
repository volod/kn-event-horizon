# Contract Toolchain Pin

## Work contract

```markdown
#### contract-toolchain-pin

Contracts can only be authoritative once the standard and the exporter are pinned and checked.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: Network access to the Bitol ODCS releases and, if needed, the Data Contract CLI
  package. The initial profile pins v3.1.0; broader feature coverage remains to be validated.
- User-visible outcome: `kn contract lint` validates ODCS YAML against the pinned JSON Schema and
  the `kn.*` extension schemas.
- Scope boundary: The pinned schema with its checksum, the extension JSON Schemas for every family
  in the specification, and lint diagnostics. Compilation comes later.
- Data and artifact paths: `contracts/schemas/`, `src/kn/contracts/`, `tests/contracts/`,
  `deploy/versions.yaml`, `pyproject.toml`, `uv.lock`.
- Execution path: Vendor the schema file with its checksum. Run Data Contract CLI as a pinned
  development tool outside the runtime dependencies. Add valid and invalid fixture contracts.
- Acceptance gates: Valid fixtures pass. An unknown extension, a missing required field, and a bad
  type fail with actionable diagnostics. The checksum is verified in CI.
- Documentation target: A new `current/data-contracts.md` page listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Opened before implementation. The existing ODCS 3.1.0 schema was fetched from the pinned Bitol
release and checked against both its original byte checksum and normalized JSON content. It is
unchanged. The KN registry supplies closed JSON Schemas and placement metadata for every family in
the specification and all existing SATCOM extensions. Both schema pins are mandatory during lint
and compile; CI plants tampered schemas and missing pin entries.

`kn contract lint [source]` now validates YAML or JSON independently of compiler feature support.
Safe loading rejects ambiguous and non-JSON input, duplicate keys, aliases, non-finite numbers,
documents over 8 MiB, and nesting beyond 32 levels. Standard and extension failures report
`E_CONTRACT` with a JSON Pointer location, rule, and value-free constraint hint. The CLI source help
and affected English/Ukrainian help goldens were updated. The SATCOM source digest and reviewed
engine-artifact manifest are unchanged.

The existing loader delegates standard and extension value validation to the shared lint layer;
it retains the compiler's narrower profile and reference checks. A regression proves a contract
with a valid, lint-only ontology extension fails compilation instead of losing metadata.

Canonical schemas remain under `src/kn/contracts/resources/` so source installations and wheels
use the same bytes without a duplicate schema tree. `contracts/schemas/README.md` indexes them.
This reuses the existing packaging seam instead of relocating the already shipped ODCS resource.
Current docs were extended with a focused toolchain page instead of creating another area page.

Data Contract CLI 1.2.11 and its transitive dependencies are locked in the isolated `contract-tools`
development group. It is absent from runtime requirements and normal bootstrap dependencies.
The external tool's Python <3.15 limit is scoped to its group; KN keeps Python >=3.12 support.
`deploy/versions.yaml` records its pin, and a deterministic test checks agreement with project and
lock metadata. `make contract-toolchain-check` runs the exact locked tool with the local ODCS schema
and reference inlining disabled, then probes JSON Schema export.

Review found the first extension schema omitted the specified `accumulate` mode. A failing
regression reproduced that refusal before the enum and its checksum were corrected. A separate
failing regression established the explicit nesting-depth limit before it was implemented.

## Acceptance evidence

Status: accepted. All declared task gates passed.

- Initial `make plan-status`: 115 tasks, 104 agent, 11 human; 96 CLEAR, 8 RUN NEEDED,
  9 HUMAN-GATED, 2 BLOCKED BY HUMAN.
- Upstream verification: fetched the exact `upstream_url` from `pins.json`; SHA-256 matched
  `upstream_sha256`, and parsed content matched the ASCII-normalized vendored schema.
- `make contract-toolchain-check`: passed with Data Contract CLI 1.2.11. Evidence is under
  `$DATA_DIR/contract-toolchain/check-rpXIsYof/`: `version.txt`, `lint.json`, and `export.json`.
  External lint reports `passed` with the local ODCS schema. The export independently preserves
  the fixture's string field and required key, but omits `kn.entityClass` and `kn.fieldId`.
  It is a development probe, not a lossless KN exporter. No live data endpoint was contacted.
- `.venv/bin/python -m pytest tests/contracts -q`: passed, including every registered extension,
  valid and invalid fixtures, parser failure paths, schema tampering, and compiler refusal.
- Initial CI failures were the expected changed contract help/usage goldens; they were refreshed.
  One preliminary quality run encountered the interval between editing an extension schema and
  updating its pin. Final gates run after schema and pin edits are finished.
- Final `make ci`: passed all required checks and 371 tests; 36 integration tests deselected.
- Final `make quality`: passed all checks, 371 tests, 93.61 percent coverage against the unchanged
  90 percent floor, Markdown lint, documentation links, and source/wheel builds.
- Built-wheel inspection and extracted-wheel smoke run: both pinned schemas and their hashes are
  packaged, Data Contract CLI is absent from runtime metadata, and lint plus `compile --check`
  pass outside the checkout. Evidence: `wheel-check.json` beside the external tool reports.
- Final ASCII and schema-family review: all 18 specification extension names and eight additional
  SATCOM helper names are registered; changed files are ASCII and both final checksums agree.
- `git diff --check`: clean. No commit or push was made. No services were started. The temporary
  schema-generation script and extracted-wheel directory were removed; runtime evidence remains
  under `DATA_DIR`.
- No database service run is required by this task. The 36 `integration` tests remain deselected
  by the normal lightweight gate; no integration acceptance is claimed.

## Handoff

The plan removes this accepted task and its prerequisites from `contract-compiler`,
`data-contracts-implementation-audit`, and `vendor-information-coverage`. Counts change from
115 to 114 tasks, 104 to 103 agent tasks, and 96 to 95 CLEAR tasks; the 11 human tasks are unchanged.
`contract-compiler` is now the highest-priority agent task. The affected capability is
`data-contracts`; it remains `planned` because full compiler and rebuild gates are still open.
The registry and current-state index now link the available lint toolchain alongside the initial
space profile. Broader semantic reference resolution and exports stay with `contract-compiler`.
