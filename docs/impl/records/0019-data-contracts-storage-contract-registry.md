# Record 0019: storage-contract-registry

## Work contract

Original plan task, copied before implementation:

```markdown
#### storage-contract-registry

Every later storage contract must deploy, rebuild, and verify through the same governance as the
SATCOM contract, the first prefetched source dataset. Upgrade, rebuild, verification, and the
installed-contract marker know only that one bundled contract, while more prefetched datasets and
the core models will each bring their own.

- Serves: `data-contracts` -- [Data contracts](../design/spec.md#data-contracts)
- Agent status: CLEAR
- Dependencies: Finding DC-11 of the [data contracts audit](records/0017-data-contracts-data-contracts-implementation-audit.md#findings),
  the [compiler](current/data-contracts/compiler.md), and the
  [development rebuild](current/data-contracts/rebuild.md).
- User-visible outcome: A reviewed registry lists every deployed storage contract and its schema.
  `kn db upgrade`, `kn db rebuild`, `kn db verify`, `make contract-check`, and
  `make contract-compile` cover every registered contract, and one installed-contract marker in
  `system` records the version and digest of each.
- Scope boundary: The registry; a contract-neutral marker that replaces `space.satcom_contract`;
  Alembic baseline creation of each contract as its schema owner; structural and compiled-catalog
  verification per contract, including two contracts in one schema; the evolution helper on the
  shared marker; refusal of a `kn.storageSchema` outside the platform schemas; and a recorded
  decision for references between registered contracts, either field-ID references checked at
  compile time or cross-schema foreign keys with the grants they need. Contract content stays with
  its owning tasks. No SQL text, as in the rest of deployment.
- Data and artifact paths: `src/kn/contracts/`, `src/kn/db/`, `generated/contracts/`,
  `tests/contracts/`, `tests/integration/`.
- Execution path: Add fixture contracts in another schema and a second dataset contract in `space`
  beside SATCOM, then make upgrade,
  rebuild, verification, and compilation pass for all of them while the SATCOM import and its tests
  keep passing.
- Acceptance gates: A rebuild from empty creates every registered contract and records each in the
  marker. Verification refuses a missing table, digest drift, or an unregistered table in any
  registered contract. A contract outside the platform schemas is refused before database access.
  Each contract compiles into its own `generated/contracts/<id>/`. `make ci` passes.
- Documentation target: `current/data-contracts.md` listed in the [areas index](current.md#areas).
```

Prerequisites: the task has no `Requires` entry. Its dependencies are the findings of
[record 0017](0017-data-contracts-data-contracts-implementation-audit.md) and the compiler and
rebuild references, which are current.

## Implementation and decisions

`src/kn/contracts/resources/registry.json` lists the deployed storage contracts in order, with
paths relative to the registry. `kn.contracts.registry` loads and validates it without database
access: files stay inside the registry directory, the governance contract comes first, and contract
IDs, field IDs, and per-schema table, primary key and index names are unique across the set. The
[deployment set](../current/data-contracts.md#deployment-set) section describes the behavior.

- **Contract-neutral marker.** The new governance contract `kn.system.governance` (`system`
  schema, table `installed_contracts`) holds one row per registered contract with version, digest,
  storage schema and table names. It is contract-defined like every other stored dataset. The
  SATCOM-specific `space.satcom_contract` table left the SATCOM contract, whose digest changed from
  `9b5aeb08...` to `498e7178...`; its archive manifest does not include the digest, so the archived
  package stays valid.
- **One baseline for every contract.** Revision `0001_baseline` replaces `0001_satcom`. It creates
  each registered contract as its schema owner, in registry order, and records the markers. The
  Alembic environment and the baseline read the set from the Alembic config, which `upgrade()`
  fills from the registry or from a validated fixture set; `rebuild()` and `verify()` accept the
  same set.
- **Verification.** `verify_contracts` (formerly `verify_contract`) requires the marker rows to
  equal the registry, compares the structure of every registered table through one combined
  SQLAlchemy metadata, and refuses any table in a KN schema that no registered contract defines,
  except `system.alembic_version`; partitions count with their parent. The compiled-catalog check
  of a rebuild runs per table of every contract.
- **Platform schemas.** The loader refuses a `kn.storageSchema` outside `platform.json` before it
  resolves references, so `kn contract compile` and every database command refuse it. `kn db`
  commands load the registry before creating an engine.
- **Compilation.** Without a source, `kn contract lint` and `kn contract compile` cover every
  registered contract and report them under `contracts`; `--output` is then a root with one
  directory per contract, and a check refuses a directory of an unregistered contract.
  `--references` needs a source. The committed `generated/contracts/` gained
  `kn.system.governance/`. The English and Ukrainian source help changed, so the help, lint and
  check goldens in `tests/e2e/fixtures/cli.json` were refreshed from the real output; only the
  wrapped help line and the contract summary lines changed.
- **Evolution.** `evolve()` reads and updates the shared marker; a keyword names another marker
  schema for scratch tests.
- **References between contracts (the recorded decision).** SQL foreign keys stay within one
  contract. Contracts refer to each other by stable field IDs, which the registry keeps unique, and
  by KN IDs that their owning engines check. A cross-schema foreign key would need `REFERENCES`
  grants and `USAGE` on another schema for owner roles, which the least-privilege policy refuses and
  verifies, and it would couple the drop and migration order of contracts. A capability whose
  integrity rule needs database-enforced references across schemas amends this with the grants it
  needs. The [data contracts](../../design/spec.md#data-contracts) section states the decision.
- **Fixtures.** `tests/contracts/fixtures/registry/` holds a second dataset contract in `space`
  beside SATCOM and a contract in `semantic`. Tests deploy them through the same functions; the
  bundled registry stays the governance and SATCOM contracts.

Not changed: `load_contract()` without a path still loads SATCOM for its adapter and tests, and
registered contracts remain package resources. Both are listed under known limitations. Verification
refusals, such as an old revision, still reach the operator as the generic
`E_INPUT: operation failed` message; the reason is only in the exception. That is a usability gap of
the CLI error surface, recorded here for the CLI owner.

## Acceptance evidence

Status: accepted on 2026-11-22. Docker Engine 29.9.3, PostgreSQL 18.7, PostGIS 3.7.0, Python
3.12.3. Logs are in `$DATA_DIR/acceptance/storage-contract-registry-20261122/`.

| Gate | Evidence | Result |
| --- | --- | --- |
| A rebuild from empty creates every registered contract and records each in the marker | `test_rebuild_creates_and_records_every_registered_contract`; throwaway-database CLI workflow in `validation.sh` and `validation.log` | Governance, SATCOM and both fixture contracts created; four marker rows with version, digest and schema; a second rebuild has the same catalog. The CLI rebuilt, verified, imported, re-imported (`already_imported`), upgraded and rebuilt again |
| Verification refuses a missing table, digest drift, or an unregistered table | `test_verification_refuses_missing_drifted_and_unregistered_tables` (5 cases), `test_the_default_deployment_refuses_a_fixture_contract_left_behind` | A dropped fixture table, a drifted and a missing marker row, and unregistered tables in `space` and `identity` are refused; a database holding an unregistered contract fails the default verification |
| A contract outside the platform schemas is refused before database access | `test_a_contract_outside_the_platform_schemas_is_refused`, `test_database_commands_refuse_an_invalid_registry_before_connecting` | `E_CONTRACT` with rule `storageSchema` at `$/customProperties/0/value`; `kn db upgrade` and `kn db verify` never create an engine |
| Each contract compiles into its own `generated/contracts/<id>/` | `test_each_registered_contract_compiles_into_its_own_directory`, `test_committed_generated_output_matches_a_fresh_compile`, `make contract-check` | Four directories for the fixture set; an extra or missing directory is drift; the committed output matches |
| `make ci` passes | `ci.log`, `ci-local.log`, `quality.log` | `make ci` exit 0 with 523 tests; `make ci-local` adds 62 integration tests; `make quality` reaches 92.43 % coverage and builds the package |

Further checks: the local development database failed `make db-verify` with revision `0001_satcom`
as expected (`local-db-verify-before.log`). `KN_ENVIRONMENT=development make db-rebuild`,
`make db-verify`, `make satcom-import` twice, and `make db-up` then passed
(`local-db-rebuild.log`): two marker rows, revision `0001_baseline`, and 31 `space` tables with
25,545 rows, the earlier 25,546 less the removed one-row marker table. The unit suite grew from 508
to 523 tests and the local-only suite from 55 to 62.

## Handoff

Plan counts before: 115 tasks (103 agent, 12 human); statuses BLOCKED BY HUMAN 3, CLEAR 95,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `storage-contract-registry`; priority human task
`provide-inventree-instance-access`.

Plan counts after: 114 tasks (102 agent, 12 human); statuses BLOCKED BY HUMAN 3, CLEAR 94,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `semantic-model-contracts`; priority human task
unchanged.

Completion changes: `storage-contract-registry` left the plan, and with it the last open task of
the data contracts group. Its ID left the `Requires` fields of `semantic-model-contracts`,
`source-catalogue-import` and `prefetched-dataset-method`; the first two now link the deployment
set. The registry changes `data-contracts` from `planned` to `shipped`. The data contracts section
of the specification states the registry and the reference decision. Capability affected:
`data-contracts`.

Notes for later tasks:

- A new storage contract is a file plus a registry entry, then `make contract-compile` and a
  development rebuild. `source-catalogue-import` adds its contract in `system` beside the
  governance contract.
- Other development databases created before this task need
  `KN_ENVIRONMENT=development make db-rebuild` and `make satcom-import`.
