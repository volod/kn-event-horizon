# Contract Compiler

## Work contract

```markdown
#### contract-compiler

Generated DDL and models must come only from contracts, deterministically.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: The [pinned lint schemas and initial SQLAlchemy profile](current/data-contracts.md)
  and their remaining semantic reference and ODCS export gaps. Generated metadata applies to scratch
  schemas of the
  [integration test harness](current/runtime-platform.md#integration-tests).
- User-visible outcome: `kn contract compile` writes DDL, Pydantic models, JSON Schema, dbt source
  definitions, and contract docs into `generated/`, and `--check` fails on drift.
- Scope boundary: Reference checks, canonical serialization, the contract digest, and templates
  for PostGIS geometry, checks, comments, and indexes. Python platform policy covers roles and
  grants. Keep one editable development baseline and version evolution after first release.
- Data and artifact paths: `src/kn/contracts/`, `generated/`, `src/kn/db/`,
  `tests/contracts/`.
- Execution path: Extend the shared model and SQLAlchemy compiler where a required ODCS feature
  is unsupported. Keep engine exports deterministic and update the CI drift manifest.
- Acceptance gates: Compiling twice is byte-identical. Generated DDL applies to the integration
  database. A broken reference fails. Drift fails CI.
- Documentation target: `current/data-contracts.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

Implemented supplied YAML/JSON compilation with optional local typed symbol catalogs. The shared
model retains ODCS and KN metadata and binds catalog definitions into the digest. Templates emit
PostgreSQL DDL, strict Pydantic models, dbt sources and documentation alongside the existing engine
exports. Pydantic is the only added runtime dependency; its locked version was already present in
the isolated contract-tool dependency graph.

SQLAlchemy remains the deployment interface. Generated DDL separates table creation from deferred
references, quotes identifiers, preserves Unicode in ASCII SQL literals, and renders comments,
indexes, PostGIS geometry validity checks and partitioned parents. Runtime identity, evidence,
rights and policy engines are not implemented by compile-time symbol resolution. Partition bounds
remain reviewed migration inputs. The initial SATCOM contract digest is unchanged; only its
reviewed artifact manifest changes. The broader rebuild task stays open.

Regression-first improvements cover strict model names shadowing imports, duplicate composite
constraints, stale generated files on recompilation, unsafe previous manifests, and migration
helpers silently losing new metadata. Additive evolution refuses those unsupported changes.
Updated bilingual help goldens cover supplied sources and the new reference catalog option.

## Acceptance evidence

Status: accepted. All declared gates passed.

- Initial `make plan-status`: 114 tasks, 103 agent, 11 human; 95 CLEAR, 8 RUN NEEDED,
  2 BLOCKED BY HUMAN, 9 HUMAN-GATED.
- `make db-up`: passed; local PostGIS was started for scratch-schema verification.
- `source scripts/shared/common.sh && kn_load_env && kn_db_test_env &&
  .venv/bin/python -m pytest tests/integration/test_contract_compiler.py`: 3 passed.
  The full SATCOM SQL, Unicode comments, geometry validity/type/SRID rejection, GiST index and
  partitioned parent were executed against PostGIS, rather than only inspecting generated strings.
- `kn contract compile --output <run>/generated`, then the same command with `--check`: passed.
  Runtime artifacts are preserved at `$DATA_DIR/contract/compiler-3Dc3KJMc/generated/` (103 artifacts
  plus the manifest). Repeated compiles and independent-process checks are also unit tests.
- Targeted compiler, template and bilingual CLI tests: 33 passed before the final added regressions.
- `make lint-md`: passed, including documentation links.
- `make ci-local`: passed. All required `make ci` checks passed; 426 lightweight tests passed,
  followed by all 39 local integration tests. No requested gate was skipped. Earlier fixture and
  golden failures were corrected and passed in this final run.
- Independent processes with `PYTHONHASHSEED=1,42,99` produced identical artifact digests.
- `git diff --check`: passed. `make quality-report` reports no Python or shell file above 250 lines.
- Scratch-schema cleanup: no `kn_test_*` schema remained. `make db-down` stopped the service
  started for this task; its data volume and generated runtime evidence were preserved.
- Final `make plan-status`: 113 tasks, 102 agent, 11 human; CLEAR 94, other statuses unchanged.

## Handoff

Tasks decreased from 114 to 113 (agent 103 to 102; human stays 11; CLEAR 95 to 94).
`development-rebuild-mode` and `semantic-model-contracts` no longer require the completed task;
the implementation audit still requires the full-platform rebuild. The `data-contracts` capability
remains planned until that rebuild gate passes. No other capability status changes.
