# Contract Lint Toolchain

## Commands and pins

```bash
kn contract lint
kn contract lint tests/contracts/fixtures/valid.yaml
kn contract lint tests/contracts/fixtures/bad-type.yaml --json
make contract-check
make contract-toolchain-check
```

Lint without a path checks the bundled SATCOM contract. Supplied paths also work with
`kn contract compile`; see the [compiler reference](compiler.md) for its stricter supported profile
and local reference catalogs. Success keeps the existing `contract_id`,
`version`, and canonical `digest` result. Equivalent YAML and JSON produce the same digest. Contract
versions use `major.minor.patch`; `apiVersion` must be exactly `v3.1.0` even though the upstream
schema accepts some older versions.

The [schema index](../../../../contracts/schemas/README.md) links the canonical packaged resources.
`schemas.py` verifies the ODCS and KN extension schema SHA-256 hashes in `resources/pins.json`
before validation. `make ci` checks them through `make contract-check` and planted tampering tests.
No schema is fetched during normal lint or compilation. The ODCS upstream source is the
[Bitol v3.1.0 release schema](https://raw.githubusercontent.com/bitol-io/open-data-contract-standard/v3.1.0/schema/odcs-json-schema-v3.1.0.json).
Its original byte checksum and the normalized local checksum are recorded separately; the content
differs only in non-ASCII JSON escaping.

Data Contract CLI `1.2.11` is locked in the `contract-tools` dependency group, outside runtime and
the normal `make bootstrap` environment. `make contract-toolchain-check` runs it through
`uv run --locked --isolated --only-group contract-tools`, on Python 3.12 by default. The tool
supports Python versions below 3.15; this restriction applies only to its development group.
The KN runtime still supports Python 3.12 and newer.

The target writes `version.txt`, `lint.json`, and `export.json` under
`$DATA_DIR/contract-toolchain/check-<run-id>/`. It passes the local pinned JSON Schema to external
lint and disables reference inlining. Its JSON Schema export is a probe: it omits KN metadata,
including the fixture's `kn.entityClass` and `kn.fieldId`. It therefore cannot replace the KN
compiler or establish lossless semantic export. Normal CI uses the local validator and tests,
without invoking this external tool. The first external tool run may need package downloads.

## Diagnostics and parsing

`lint.py` validates the standard and walks ODCS `customProperties`, including nested schema fields.
The registry rejects unregistered names, duplicate names on a node, incorrect placement, unknown
object members, missing required members, and bad values. KN metadata appears only within ODCS
`customProperties`; top-level `kn.*` keys fail the standard schema.

Failures return exit code 1. Structured validation and parse failures use `E_CONTRACT`, with
`path`, `rule`, and `hint` fields under `error` in JSON mode. Paths use `$` followed by JSON Pointer
segments, for example `$/schema/0/properties/0/customProperties/0/value`. Hints name the expected
constraint without echoing rejected values. Invalid syntax reports a line and column when the
parser provides them. Unreadable files use the existing `E_INPUT` error. Compile-profile refusals
after lint, such as an unsupported key or type, a missing stable field ID, or a nullable primary
key, are `E_CONTRACT` diagnostics with the same location format.

`document.py` accepts one UTF-8 JSON or YAML object, up to 8 MiB and 32 nesting levels. It rejects
duplicate mapping keys,
non-string keys, aliases, recursive input, unsafe tags, non-finite numbers, NUL characters in keys
or strings (PostgreSQL text cannot hold them), and YAML values outside the JSON data model. The same
reader loads reference catalogs. Implicit YAML dates remain strings. Input references and URLs are data;
lint does not retrieve or execute them. JSON is read directly to keep the bundled contract fast.

## Extension shapes

The registry is [kn-extensions.json](../../../../src/kn/contracts/resources/kn-extensions.json).
Each schema carries `x-kn-scopes` for contract, table, or field placement. Objects are closed;
reference strings must contain a non-whitespace character, and reference arrays are nonempty and
unique. These are structural contracts, not implementations of the referenced policies.
The [example values](../../../../tests/contracts/fixtures/extensions.json) cover every registered
name; tests place each value at its declared scope and plant invalid types and missing members.

| Family | Value and required members | Scope |
| --- | --- | --- |
| `kn.entityClass` | Ontology class reference | table |
| `kn.relation` | `type`, `sourceClass`, `targetClass` references | table |
| `kn.fieldId` | Stable field reference | field |
| `kn.identity` | `strategy`, `externalKeys`, `sourceRecordKey`, `attributes`, `matchProfile`; optional `sourceVersionField` | table |
| `kn.updatePolicy` | `mode`, `priorityCriteria`, `minimumSourceRank`, `minimumEvidenceClass`, `timeBasis`, `valueTolerance`, `freshnessSeconds`, `emptyValueHandling` | field |
| `kn.interchange` | `exposed`, `compatibility`; optional `aliases`, `counterpartMappingRefs` | contract, table, field |
| `kn.units` | `originalUnit`, `normalizedUnit`, `quantityType`, `conversionRule` | field |
| `kn.comparisonProfile` | Comparison profile reference | table, field |
| `kn.temporalProfile` | `asOf`, `nullSemantics`; optional event, published, observed, valid-from, valid-to, and recorded field references | contract, table, field |
| `kn.spatialProfile` | `geometryType`, `srid` fixed at 4326, `precision`, `coverageSemantics`, `validity` | field |
| `kn.evidence` | `required`, `assertionType`, `minimumClass`, `referenceFields` | contract, table, field |
| `kn.licensePolicy` | `policyRef`, `rights`, `exportAllowed`; optional `restrictions` | contract, table, field |
| `kn.enumRef` | Vocabulary reference | field |
| `kn.vocabularyRefs` | Allowed scheme references | field |
| `kn.index` | Array of `name`, `fields`, `method`, `unique` objects | table |
| `kn.partition` | `strategy`, `fields` | table |
| `kn.i18nKey` | Catalog key reference | contract, table, field |
| `kn.lineageRefs` | Array of `dataset`, `mapping` reference objects | contract, table, field |

SATCOM-specific extensions share this registry: `kn.storageSchema` and `kn.sourceProfile` at
contract scope; `kn.csv` at table scope; and `kn.foreignKey`, `kn.enum`, `kn.partialDate`,
`kn.precision`, and `kn.scale` at field scope. Compilation continues to enforce decimal consistency,
scalar logical types, required stable IDs, and resolvable composite foreign keys.

## Compilation boundary

Lint validates structure without resolving external definitions. Compilation additionally resolves
reference catalogs and emits the [supported artifacts](compiler.md#entry-points-and-artifacts),
including PostGIS templates, Pydantic and dbt. Runtime ontology and policy behavior remains owned by
its capability tasks. The shipped [development rebuild](rebuild.md) supplies the all-schema
reset and transactional reviewed-seed hook for the current compiled bundle.
