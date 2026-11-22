# Record 0017: data-contracts-implementation-audit

## Work contract

Original plan task, copied before implementation:

```markdown
#### data-contracts-implementation-audit (optional)

Every schema, model, and generated artifact comes from the contract compiler, so a flaw in the
toolchain or the rebuild multiplies across every later contract.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: The accepted task records of the group, including the
  [development rebuild](current/data-contracts/rebuild.md), and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Later groups compile their contracts with a verified, deterministic
  toolchain. The audit record gives every check a result and every finding a disposition. The
  current-state page lists known limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: ODCS and `kn.*` extension validation and its messages; deterministic output
  across runs, platforms, and input order; type, nullability, key, and unit mapping to DDL, models,
  and JSON Schema; identifier length limits and reserved words; cross-contract references; a rebuild
  that fails midway; the path to `release-migration-mode`, so that generated DDL can later drive
  versioned migrations without a compiler rewrite. Fixes only; new behavior becomes plan tasks.
- Data and artifact paths: `contracts/`, `src/kn/contracts/`, `src/kn/db/`, `generated/`,
  `tests/contracts/`, `tests/integration/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Compile
  twice and compare bytes, compile with a shuffled input order, interrupt a rebuild, and compare a
  contract change with its generated DDL.
- Acceptance gates: Two compiles give byte-identical output. An interrupted rebuild leaves no
  partial schema in use. Every finding has a severity, evidence, and a disposition, no `blocker` is
  accepted, and every fix starts from a failing regression test. `make ci` passes with the scheduled
  tasks in the plan.
- Documentation target: `current/data-contracts.md` listed in the [areas index](current.md#areas).
```

Prerequisites: the task has no `Requires` entry. The group's required tasks were accepted in
[record 0011](0011-data-contracts-satcom-schema-governance.md),
[record 0014](0014-data-contracts-contract-toolchain-pin.md),
[record 0015](0015-data-contracts-contract-compiler.md), and
[record 0016](0016-data-contracts-development-rebuild-mode.md).

## Implementation and decisions

The audit worked through the six [implementation audit](../../guide/planning-workflow.md#implementation-audits)
checks against the [data contracts](../../design/spec.md#data-contracts) section, the
[development and release phases](../../design/spec.md#development-and-release-phases), and the
records of the group. The [data contracts page](../current/data-contracts.md) and its
[compiler](../current/data-contracts/compiler.md), [rebuild](../current/data-contracts/rebuild.md)
and [toolchain](../current/data-contracts/toolchain.md) references describe the resulting behavior
and its known limitations.

Three decisions came from the user during the audit:

- `generated/` is committed, as the [repository layout](../../design/spec.md#repository-layout)
  states. Contract output lives in `generated/contracts/<contract-id>/`, because later generators
  own `generated/kestra/` and `generated/dbt/` and a drift check compares an exact file set. The
  packaged digest manifest `1.0.0.artifacts.json` was removed, so one drift rule remains.
- No SQL text reaches the database. The user asked whether `schema.sql` meant raw SQL in
  deployment, then asked to replace every raw SQL case with Alembic and SQLAlchemy. The source
  package `schema.sql` is archived evidence that nothing parses or executes, the generated
  `postgresql/schema.sql` is a review artifact, and no tracked `.sql` file exists. The rebuild,
  however, executed the compiled DDL string (DC-13), and the platform policy and catalog reads were
  SQL strings outside the Alembic run (DC-14). `kn db upgrade` is now `alembic upgrade head`, its
  environment converges the platform policy on every run, rebuild drops the schemas and runs the
  same upgrade, and every statement is a SQLAlchemy or Alembic construct. The specification's data
  contracts paragraph and its development-phase bullet were amended to state this rule.
- SATCOM is a data integration example: owner-supplied, prefetched files from a real space source,
  the first of several such datasets. The audit therefore checked it as a source integration
  (DC-16), and the specification and current-state page now say that later prefetched datasets
  come through one shared path.

### Findings

| ID | Severity | Check | Finding and evidence | Disposition |
| --- | --- | --- | --- | --- |
| DC-01 | major | 3, 4 | Generated constraint names collided or overflowed. Two references `(a2, b2, c2)` and `(a2, b2, d2)` were both named `fk_child_a2_b2`, because the convention used only two columns, and PostGIS refused the DDL with `DuplicateObject`. A table `pk_foo` beside table `foo` failed with `DuplicateTable`. A 48-character table and field gave a 105-character check name in `postgresql/metadata.json` while SQLAlchemy truncated the DDL name to 60 characters, so rebuild verification failed with `compiled check constraint mismatch`. | Fixed: `src/kn/contracts/names.py` derives every name once, foreign key names cover every column, names over 63 bytes keep 54 characters and gain an 8-digit SHA-256 suffix, and compilation refuses coinciding relation and constraint names. Foreign key names are in `metadata.json` and the compiled-catalog check. Regression tests in `tests/contracts/test_physical.py` and `test_long_and_composite_generated_names_apply_and_verify`. SATCOM single-column references lost a trailing underscore (`fk_<table>_import_id`). |
| DC-02 | major | 2, 3 | A single-column integer primary key compiled to `BIGSERIAL`, because SQLAlchemy treats it as autoincrement: the database would mint load-order identifiers that no contract declared. The planted contract showed `k BIGSERIAL NOT NULL`. SATCOM keys are composite text, so SATCOM was not affected. | Fixed: every column has `autoincrement=False`. Regression test `test_integer_primary_keys_take_no_server_generated_values`. |
| DC-03 | minor | 4 | Names reserved by generated targets were not checked. Tables `none`, `true`, `false` produced `class None(...)`, a `SyntaxError` in `pydantic/models.py`. Tables named after Avro primitive types produced records that the Avro specification forbids (fastavro accepts them). A stale list refused tables such as `field` and `decimal` with a wrong message, although the imports were already private. | Fixed: keyword class names and Avro primitive names are refused as reserved; the stale list was removed. Regression tests `test_names_reserved_by_generated_python_or_avro_are_refused` and `test_names_of_privately_imported_symbols_compile`. |
| DC-04 | major | 2, 5 | Compile-profile refusals were not actionable. A nullable or missing primary key, a missing `kn.fieldId`, an unsupported key, type or table kind, an invalid or duplicate name or field ID, and misplaced decimal or enum metadata raised plain `ValueError`, reported as `E_INPUT: operation failed` with no path or rule (13 planted cases). A broken reference reported `$/schema/countries/properties/country_iso2`, which is not a JSON Pointer into the document, and physical-design errors reported `$`. | Fixed: every refusal is a `ContractError` with a JSON Pointer to the node, a rule and a value-free hint. Regression tests in `tests/contracts/test_diagnostics.py` (15 cases). |
| DC-05 | major | 2, 4 | Generated wire and native validators accepted values that PostgreSQL rejects or changes. JSON Schema and Pydantic accepted `2**63` (`bigint out of range`). JSON Schema accepted 21 integer digits for `NUMERIC(38,18)` (overflow) and `0.0000000000000000001`, which PostgreSQL silently rounds to `0.000000000000000000`. It accepted the naive `2026-01-01T00:00:00`, which PostgreSQL read in the session zone (`Europe/Kyiv` gave `2025-12-31 22:00` UTC), and `yesterday` or `soon`, because `format` is only an annotation. | Fixed: integer bounds in JSON Schema and Pydantic, digit-limited decimal patterns that ignore leading and trailing zeros as PostgreSQL and Pydantic do, a date pattern, and a timestamp pattern with a required offset and at most six fractional digits. Regression tests in `tests/contracts/test_type_mapping.py`. |
| DC-06 | minor | 4 | A NUL character in a description or enum value compiled, and the generated DDL then failed on PostgreSQL with `invalid Unicode escape value`. The root-type hint told a reference catalog to be a "contract object". | Fixed: the shared reader refuses NUL in keys and strings, and the root hint names a JSON or YAML object. Regression tests in `tests/contracts/test_document.py`. |
| DC-07 | major | 3 | Additive evolution dropped comments. A new field was added without its description, and the description changes that `additions()` accepts were not applied. Alembic then reported `modify_comment` twice and `add_table_comment`, so `verify_structure`, which runs in `kn db verify`, `kn db upgrade` and before every import, refused the evolved database. | Fixed: `evolve()` adds new columns with comments and applies changed table and column descriptions. Regression test `test_additive_evolution_applies_the_comments_that_verification_compares`. |
| DC-08 | minor | 2 | Structural verification did not compare geometry types: Alembic reflects them as an unknown type (`Did not recognize type 'geometry'`), so a column altered from `geometry(Polygon,4326)` to `geometry(MultiPolygon,4326)` passed. | Fixed: verification compares `format_type` of every geometry column with the contract. Regression test `test_structural_verification_compares_geometry_types`. |
| DC-09 | minor | 5, 6 | The identifier rule existed three times (`loader.IDENTIFIER`, `physical.INDEX_NAME`, and the stale-artifact pattern in `compiler.py`) beside the registry pattern, and `_reference` used `assert` as a production check. | Fixed: one rule in `names.py`, used by all three and checked against the registry pattern by `test_one_identifier_rule_serves_the_loader_registry_and_physical_names`; the assertion became an argument. |
| DC-10 | minor | 2, 6 | `generated/` was ignored although the specification commits it, so reviewers saw changed digests instead of DDL and model diffs. `--check` without `--output` compared the packaged digest manifest while compile wrote `generated/`, two drift rules. The generated `schema.sql` had 432 lines with trailing blanks, which `git diff --check` would flag once committed. | Fixed by the user's decision: committed `generated/contracts/kn.space.satcom/`, one default directory for compile and check, `make contract-compile` refreshes it, the packaged manifest is removed, and literals with line breaks are escaped so trailing blanks can be stripped safely. Regression tests in `tests/contracts/test_generated.py`. |
| DC-11 | major | 3 | The deployment set is one hardcoded contract. `load_contract()` without arguments in rebuild, governance, verification, the Alembic environment and the baseline, and the `space.satcom_contract` marker in governance and evolution, know only SATCOM. `semantic-model-contracts` and `source-catalogue-import` add the first other storage contracts. `kn.storageSchema` outside the platform schemas compiles, and cross-contract SQL references are refused while the role policy grants no `USAGE` on other schemas. | Scheduled feature: `storage-contract-registry` in the data contracts group; both tasks gain a `Requires` entry. Listed under known limitations. |
| DC-12 | minor | 2 | A refused rebuild printed `E_INPUT: operation failed; check input files, options, and configuration.` and hid the guard. | Fixed: `cli.rebuild_refused` in `en` and `uk` names `KN_ENVIRONMENT=development`; the code stays `E_INPUT`. Regression test `test_rebuild_refusal_names_the_guard_in_both_locales`. |
| DC-13 | major | 2, 6 | The rebuild executed the compiled DDL string (`connection.exec_driver_sql(postgresql_ddl(contract))`) while upgrade created the same schema through the Alembic baseline: two mechanisms for one rule, against the specification's "same governance mechanism that release migrations use". Raised by the user. | Fixed: rebuild drops the schemas and runs `upgrade()`; the stamp and marker steps it duplicated are gone. Regression test `test_rebuild_creates_schemas_through_alembic_without_sql_text`, which first failed with the recorded `CREATE TABLE` string. |
| DC-14 | minor | 5 | The platform policy (extension, roles, grants, default privileges, schema owners), role switches and catalog reads were SQL strings (`sa.DDL`, `sa.text`), and the policy ran around the Alembic run instead of inside it. Raised by the user. | Fixed, with a specification change the user requested: typed elements in `src/kn/db/statements.py`, `CreateSchema` and `DropSchema`, Core queries over `src/kn/db/catalog.py`, and `governed_migrations` in the Alembic environment, so every run still converges the policy. `test_production_code_sends_no_sql_strings_to_the_database` fails on any new SQL string; statement tests in `tests/contracts/test_statements.py`. |
| DC-16 | major | 3 | The prefetched-dataset path does not extend to a second dataset. `kn.sourceProfile` in the pinned extension registry is `const: "satcom-csv/1"`; the dataset contract carries its own bookkeeping tables (`satcom_imports`, `satcom_files`, `satcom_rows`, `satcom_contract`); the commands are `kn space satcom` and `make satcom-*`; the archive is `$DATA_DIR/satcom-import/<digest>/` instead of the raw archive layout; and rebuild does not restore the data. The next dataset would copy the adapter, against "the core never branches on a source ID". | Scheduled feature: `prefetched-dataset-method` in the ingestion engine group, which `rebuild-from-raw` now requires. Listed under known limitations. |
| DC-15 | minor | 4 | Reordering tables or `customProperties` entries changes the digest and `contract.json`; after masking the digest every other artifact is byte-identical. Object key order and YAML versus JSON change nothing. | Accepted: the digest names the reviewed text exactly. Listed under known limitations with its reopening condition. |

No `blocker` was found. Two tasks were scheduled.

Observations that are not findings:

- A rebuild process killed with `SIGKILL` while it held the dropped schemas left the previous state
  in use before and after this audit: a concurrent reader saw the committed catalog and timed out on
  the dropped table's lock, and the server rolled back within 100 ms of noticing the client.
  `tests/integration/test_rebuild_interrupt.py` keeps this as gate evidence.
- Elasticsearch `date` keeps milliseconds while PostgreSQL and Avro keep microseconds. `date_nanos`
  cannot hold dates before 1970, which satellite history needs. No Elasticsearch service exists.
- Contract diagnostic hints stay English in the `uk` locale, as in record 0014; the surrounding
  message is localized.
- Contract-level semantic metadata changes are additive in `additions()`; they have no DDL effect.

### Check results

1. **Implementation validation.** Passed. `make ci` and `make test-integration` passed before any
   change (431 and 49 tests). `make db-verify`, `make contract-toolchain-check` (Data Contract CLI
   1.2.11), and the documented workflow in a throwaway database passed: the released and unset
   guards refused, rebuild, verify, import, a repeated import (`already_imported`), upgrade, and a
   second rebuild (0 rows afterwards) succeeded. The current-state pages matched the commands; they
   now describe the committed output, the Alembic-only deployment and the new limits.
2. **Specification conformance.** Valid contracts compile byte-identically twice (two processes
   with different hash seeds, and Python 3.12 and 3.13). Unknown extensions, missing fields and
   broken references fail with located diagnostics (DC-04). Drift fails CI through the committed
   output (DC-10). Rebuild from empty creates every schema, and loader roles cannot run DDL
   (`tests/integration/test_rebuild.py`). Decimal exactness and the deployment mechanism were gaps
   (DC-05, DC-13, DC-14); the deployment set is scheduled (DC-11).
3. **Design scope.** Expensive to change later: the constraint naming rule and its hash suffix,
   the 48-character identifier limit, stable field IDs, one storage schema per contract, the
   `generated/contracts/<contract-id>/` layout, the `E_CONTRACT` diagnostic shape, the contract
   digest over the source document, the installed-contract marker, and the Alembic environment as
   the only deployment entry. Release migration mode extends `evolve()` on the same metadata and
   names (DC-07), without a compiler rewrite. A new prefetched dataset does not yet fit by
   extension (DC-16). Findings: DC-01, DC-02, DC-07, DC-11, DC-16.
4. **Corner cases.** Long, reserved, colliding and Unicode names; NUL text; out-of-range and
   over-precise numbers; naive and over-precise timestamps; shuffled object keys, tables and
   extensions; hostile contract IDs for the default directory; a killed rebuild; repeated and
   concurrent rebuilds under the advisory lock; and a rebuild from no KN schemas were exercised.
   Time zones apply only to timestamp wire values (DC-05); the compiler stores no times itself.
5. **Best practices.** Typed and network-free unit tests, named constants, value-free
   diagnostics, least-privilege roles, and identifier quoting by the dialect hold. Findings: DC-04,
   DC-09, DC-14. Every changed Python file stays below 250 lines.
6. **Debt.** The stale class-name list (DC-03), the duplicated identifier rule (DC-09), the second
   drift rule (DC-10) and the second schema-creation path (DC-13) were removed. No `TODO`, skipped
   check or weakened gate was found. One test that tolerated `KeyError` for invalid contracts was
   left as is: no mutation raises it, and the new diagnostics tests assert the exact code.

## Acceptance evidence

Status: accepted on 2026-11-22. Docker Engine 29.9.3, Compose v5.7.1, PostgreSQL 18.7, PostGIS
3.7.0, Linux x86_64, Python 3.12.3 and 3.13.18.

Scripts and logs are in `$DATA_DIR/acceptance/data-contracts-implementation-audit-20261122/`:
`ci-before.log`, `integration-before.log`, `db-verify-before.log`, `toolchain.log`,
`validation.sh` with `validation.log` and `validation-after.log`, `determinism.log` with the
`compile-a`, `compile-b` and `compile-313` outputs, `unit-regressions-before.log` and
`unit-regressions-after.log`, `integration-regressions-before.log` and
`integration-regressions-after.log`, `integration-rebuild-sql-before.log`, `integration-after.log`,
`db-verify-after.log`, `ci-after.log`, and the final gate logs.

| Gate | Evidence | Result |
| --- | --- | --- |
| Two compiles give byte-identical output | Two `kn contract compile` processes with `PYTHONHASHSEED=1` and `987`, and one on Python 3.13; `diff -r` | Identical; tree hash `23d2dd0c...` before the fixes. The committed output is checked by `make contract-check` |
| An interrupted rebuild leaves no partial schema in use | `tests/integration/test_rebuild_interrupt.py` | Passed before and after the fixes: catalog, sentinel row and `verify` unchanged; the next rebuild succeeded |
| Every construct the compiler accepts has a generated-output test | `tests/contracts/test_references.py`, `test_templates.py`, `test_physical.py`, `test_type_mapping.py`, `tests/integration/test_contract_compiler.py`, `test_contract_governance.py` | Every extension family, logical type, index method, partition, geometry template, enum, partial date and reference shape compiles in a test; DDL applies on PostGIS |
| Every finding has a severity, evidence, and a disposition; no accepted `blocker` | The findings table | 8 major and 8 minor; 13 fixed, 2 scheduled, 1 accepted; no `blocker` |
| Every fix starts from a failing regression test | `unit-regressions-before.log`, `integration-regressions-before.log`, `integration-rebuild-sql-before.log` | 57 unit, 3 integration and 1 rebuild test failed before the fixes; afterwards 125 and 15 passed |
| `make ci` passes with the scheduled tasks in the plan | `make ci` | exit 0; `508 passed, 55 deselected`; 0 spec-plan findings |

The unit suite grew from 431 to 508 tests and the local-only suite from 49 to 55.

At the user's request, the local development database was then rebuilt and restored from the
original package: `KN_ENVIRONMENT=development make db-rebuild`, `make db-verify`,
`make satcom-validate`, and `make satcom-import` twice (`imported`, then `already imported`). The
32 tables hold the same 25,546 rows as before, from the same snapshot `7ec6001f...` under contract
digest `9b5aeb08...`. All 88 foreign keys carry the names in the committed `metadata.json`, and none
of the 30 old trailing-underscore names remains. Evidence: `local-db-before.txt`,
`local-db-rebuild.log`, `local-db-import.log`, and `local-db-after.txt`.

## Handoff

Plan counts before: 112 tasks (101 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 93,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `semantic-model-contracts`; priority human task
`provide-inventree-instance-access`.

Plan counts after: 113 tasks (102 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 94,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `storage-contract-registry`; priority human task
unchanged.

Completion changes: `data-contracts-implementation-audit` left the plan. `storage-contract-registry`
joined the data contracts group (DC-11), and `semantic-model-contracts` and
`source-catalogue-import` require it. `prefetched-dataset-method` joined the ingestion engine group
(DC-16) and requires `storage-contract-registry`, `warc-raw-store`, and `mapping-and-quality-rules`;
`rebuild-from-raw` requires it and replays prefetched datasets. The registry changes
`data-contracts` from `shipped` to `planned`, because required work is open again. The specification
states that deployment is `alembic upgrade head` and that no SQL text is executed. Capabilities
affected: `data-contracts`; `runtime-platform`, whose policy now runs inside the Alembic
environment; and `ingestion-engine`, which gains the prefetched-dataset task.

Notes for later tasks:

- A generator or contract change is reviewed in the `generated/` diff: run `make contract-compile`
  and commit the result with the change.
- A new database statement that SQLAlchemy cannot express is a typed element in
  `src/kn/db/statements.py`; the guard test refuses SQL strings in production code.
- Other development databases created before this audit keep their old single-column foreign key
  names until their next `make db-rebuild` and `make satcom-import`; `make db-verify` passes either
  way. The local database of this audit was rebuilt.
