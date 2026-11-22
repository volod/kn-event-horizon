# Contract Compiler

## Entry points and artifacts

```bash
kn contract compile
kn contract compile contracts/example.yaml --references contracts/references.json
kn contract compile contracts/example.yaml --references contracts/references.json --output generated
kn contract compile contracts/example.yaml --references contracts/references.json \
  --output generated --check
make contract-check
make contract-compile
```

Without a source, compilation uses the bundled SATCOM contract. Without an output directory, it
writes `generated/` relative to the working directory. `make contract-compile` keeps the existing
runtime destination `$DATA_DIR/contract/current/`. These are generated review artifacts. Normal upgrades
consume SQLAlchemy metadata through Python Alembic revisions. The explicit
[development rebuild](rebuild.md) executes DDL freshly compiled from the bundled contract, with
role policy supplied separately by shared Python governance.

| Path inside the output | Content |
| --- | --- |
| `contract.json` | Canonical, lossless ODCS input with all KN extensions |
| `references.json` | Canonical reference catalog used for this compilation |
| `postgresql/metadata.json` | Columns, types, keys, checks, indexes, comments and partition intent |
| `postgresql/schema.sql` | Generated PostgreSQL DDL from the same SQLAlchemy metadata |
| `pydantic/models.py` | Strict Pydantic v2 models, one class per table |
| `dbt/sources.yaml` | dbt source definitions with table and column metadata |
| `docs/contract.md` | Model and stable field ID reference |
| `avro/<table>.json` | Exact decimal/date/timestamp Avro schemas |
| `elasticsearch/<table>.json` | Strict mappings with automatic type detection disabled |
| `jsonschema/<table>.json` | Closed JSON Schema wire validation with KN metadata |
| `manifest.json` | Contract digest and SHA-256 for every generated artifact |

SATCOM generates 103 artifacts plus the manifest. Files use ASCII and LF line endings. JSON uses
sorted object keys and compact separators. YAML source definitions use JSON syntax, which is also
valid YAML. Source array order remains significant, including column order, composite keys and
policy priority criteria. Reordering JSON object keys or using equivalent YAML changes no bytes.

The contract digest covers canonical input. With a reference catalog, it covers the canonical
`{"contract": ..., "references": ...}` object instead. Changing a referenced definition therefore
changes the digest even when the contract text stays the same. The whole supplied catalog is
included, including unused definitions; keep it limited to the compilation context.

Elasticsearch decimal fields remain keyword strings: precision is preserved, but numeric range
aggregation is unavailable. Partial dates remain keywords. No Elasticsearch service or Avro
transport is provisioned by compilation.

## Supported profile and reference resolution

The compiler accepts flat ODCS object/table models, stable `kn.fieldId` on every field, a
`kn.storageSchema`, and a non-null primary key on every table. `kn.csv` defaults to false and
`kn.sourceProfile` is optional outside the SATCOM adapter. Scalar types are string, integer,
number, boolean, date and timestamp. SQL identifiers are lowercase letters, digits and underscores,
start with a letter, and have at most 48 characters. PostgreSQL reserved words are quoted.
Unsupported ODCS properties and nested types fail rather than being dropped.

`--references` accepts a local JSON or YAML object through the same bounded, duplicate-rejecting
parser as contracts. It never fetches URLs. Each reference kind maps IDs to definition objects:

```json
{
  "entityClass": {"space.satellite": {}, "core.organization": {}},
  "relation": {
    "space.operates": {
      "sourceClass": "core.organization",
      "targetClass": "space.satellite"
    }
  },
  "vocabulary": {"space.status": {"values": ["active", "retired"]}}
}
```

Kinds are `entityClass`, `relation`, `matchProfile`, `normalizer`, `comparator`, `mapping`, `unit`,
`quantityType`, `conversionRule`, `comparisonProfile`, `licensePolicy`, `vocabulary`, and `dataset`.
IDs cannot cross kind boundaries. The caller supplies reviewed definitions from the owning domain;
this compiler is not an ontology importer or a policy executor. Relation endpoint classes must
match their definition. `kn.enumRef` requires a unique, nonempty string `values` array and generates
the same enum validation as `kn.enum`; an explicit enum must agree with it.

Identity keys and attributes, temporal fields, evidence fields, indexes and partition columns
resolve to existing fields. Table and field scope accept column names or stable IDs. Contract
scope requires globally unique stable IDs. Foreign keys remain within the contract and target the
ordered primary key of an existing table with matching source types. Repeated declarations of one
composite reference generate one constraint. Cross-contract SQL foreign keys are refused.
`kn.i18nKey` must occur in both packaged interface catalogs. Aliases, rights codes and spatial
coverage semantics remain declared metadata rather than external symbol references.

Every registered KN extension family is retained in `contract.json`. Table and field metadata also
travels in dbt, JSON Schema, Avro and Pydantic exports. Resolving a symbol establishes referential
integrity, not the runtime implementation of identity matching, evidence selection, unit conversion
or rights enforcement. Those remain owned by their respective capability tasks.

## PostgreSQL and native model templates

Generated DDL creates tables first, then sorted deferred foreign keys, indexes and comments. This
supports cyclic references without depending on set iteration order. Schemas and PostGIS must
already be provisioned by the Python platform policy. Check and enum literals are escaped by the
PostgreSQL dialect; non-ASCII literals use PostgreSQL Unicode escapes, preserving original text.
No contract field is treated as executable SQL.

`kn.spatialProfile` maps a WKT string field to `geometry(<type>,4326)`. Typmods enforce geometry type,
dimension and SRID. Checks enforce `ST_IsValid` and, with `validity: required`, nonempty geometry.
Precision and coverage semantics remain metadata; coordinates are never rounded. Geometry fields
cannot be primary keys or carry scalar enum/partial-date checks. `kn.index` emits named indexes
with the selected PostgreSQL method and uniqueness. Index names are unique across the schema;
unique indexes require btree, while hash and spgist require a single column. PostgreSQL remains
the final authority for access-method/type compatibility and extension-specific operator classes.

`kn.partition` emits a range, list or hash partitioned parent. Primary keys and unique indexes
must include partition columns. Child partitions and their bounds are not inferred: they require
reviewed migrations before inserting data. Arbitrary SQL checks, predicates and operator classes
are outside this profile.

Pydantic models forbid extra fields and coercion, preserve exact `Decimal`, require aware UTC-capable
timestamps, and retain nullable versus required fields. Date values remain native dates; partial
dates remain strings. SQL uses `NUMERIC(precision,scale)` and `TIMESTAMP WITH TIME ZONE`; wire decimal
values remain strings. Geometry validation occurs in PostGIS; portable models carry WKT strings
and spatial metadata. Python keywords and Pydantic attribute names use field aliases. Private
module imports prevent column names such as `date` and `str` from shadowing Python types.

## Drift and verification

With `--output --check`, compilation compares the exact file set, manifest and bytes without
writing anything. Missing, changed, extra or symlinked artifacts fail. Normal recompilation removes
obsolete engine files named by the previous generated manifest, preserving unrelated files.
Malformed or unsafe previous manifests fail before writes; symlinked destinations are refused.
Compilation is not an atomic directory transaction: an interrupted write can leave drift, which
`--check` detects and a rerun repairs.

Without `--output`, `--check` compares the bundled SATCOM artifacts against the reviewed packaged
`1.0.0.artifacts.json`. Custom contracts require an explicit output for checking. `make ci` runs the
bundled manifest check, so generator or mapping changes fail until their output is reviewed and
that manifest is refreshed. Copy the reviewed generated `manifest.json` into the packaged manifest
after an intentional SATCOM generator change; do not bypass the drift check.

`tests/contracts/test_compiler.py`, `test_templates.py` and `test_references.py` cover supplied
contracts, reference kinds, endpoint mismatches, strict native models, deterministic bytes, stale
files, unsafe manifests and drift. `tests/integration/test_contract_compiler.py` executes generated
SQL in scratch schemas: the complete SATCOM model, Unicode comments, invalid geometry and SRIDs,
GiST indexes, and a partitioned parent. Run `make ci-local` after `make db-up` for both test sets.
The acceptance evidence is in
[record 0015](../../records/0015-data-contracts-contract-compiler.md).
