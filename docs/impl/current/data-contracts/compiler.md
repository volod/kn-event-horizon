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

Without a source, compilation covers every contract in the
[deployment set](../data-contracts.md#deployment-set): each goes to `<root>/<contract-id>/`, where
the root is `--output` or `generated/contracts/`, and the result lists every contract under
`contracts`. A check without a source also refuses a directory under the root that belongs to no
registered contract. `--references` needs a source, because registered contracts name their own
catalogs. With a source and no output directory, compilation writes
`generated/contracts/<contract-id>/` relative to the working directory, and `--check` compares the
same directory. A contract ID that is not a plain file name (letters, digits, `.`, `_`, `-`, not
starting with `.`) needs `--output`. `make contract-compile` refreshes the committed
`generated/contracts/` from the project root, and `make contract-check` compares it byte for byte.
Other generators keep their own directories under `generated/`.

These are review artifacts; nothing executes them. Normal upgrades and the
[development rebuild](rebuild.md) both run the Alembic baseline over the same SQLAlchemy metadata,
and the platform policy uses typed SQLAlchemy statements, so no SQL text reaches the database.

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

Including manifests, SATCOM generates 101 artifacts, governance 11, and the semantic meta-model 62.
Files use ASCII and LF line endings, and no line ends in a blank, so `git diff --check` stays clean.
JSON uses sorted object keys and compact separators. YAML source definitions use JSON syntax,
which is also valid YAML. Source array order remains significant, including column order,
composite keys and policy priority criteria. Reordering JSON object keys or using equivalent YAML
changes no bytes.
Reordering tables or `customProperties` entries changes only `contract.json` and the digest, which
every artifact embeds; see [known
limitations](../data-contracts.md#observed-package-and-limitations). Two processes with different
hash seeds, and Python 3.12 and 3.13, give byte-identical output.

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
Unsupported ODCS properties and nested types fail rather than being dropped. Every refusal is an
`E_CONTRACT` diagnostic with a rule, a value-free hint, and a JSON Pointer into the supplied
document, for example `$/schema/0/properties/2/customProperties` for a misplaced `kn.precision`.
Table names whose generated Python class would be `None`, `True`, or `False`, and names of Avro
primitive types (`null`, `boolean`, `int`, `long`, `float`, `double`, `bytes`, `string`), are
refused as reserved. Generated models import their dependencies privately, so tables such as
`field` or `decimal` compile.

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
supports cyclic references without depending on set iteration order. `src/kn/contracts/names.py`
derives every constraint name once, for DDL, `postgresql/metadata.json`, and catalog verification:
`pk_<table>`, `fk_<table>_<every referencing column>`, and `ck_<table>_<field>_<geometry|enum|precision>`.
A name over the PostgreSQL limit of 63 bytes keeps its first 54 characters and gains `_` and eight
hex digits of its SHA-256. Compilation refuses names that coincide: a table named like another
table's primary key index, an index named like a table, or two references that derive one name.
Integer primary keys are plain `BIGINT` with no sequence or default. Schemas and PostGIS must
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

Pydantic models forbid extra fields and coercion, preserve exact `Decimal`, require aware
UTC-capable timestamps, bound integers to the `BIGINT` range, and retain nullable versus required
fields. Date values remain native dates; partial dates remain strings. SQL uses
`NUMERIC(precision,scale)` and `TIMESTAMP WITH TIME ZONE`; wire decimal values remain strings.
Geometry validation occurs in PostGIS; portable models carry WKT strings and spatial metadata.
Python keywords and Pydantic attribute names use field aliases. Private module imports prevent
column names such as `date` and `str` from shadowing Python types.

JSON Schema wire validation accepts only values that PostgreSQL stores unchanged. Integers have the
`BIGINT` range. A `NUMERIC(p,s)` string has at most `p - s` integer digits and `s` fractional digits,
ignoring leading and trailing zeros as PostgreSQL and Pydantic do, because PostgreSQL silently
rounds extra fractional digits. Dates match `YYYY-MM-DD`. Timestamps need an explicit offset (`Z` or
`+hh:mm`) and at most six fractional digits; PostgreSQL would read a naive timestamp in the session
time zone. These are patterns, because `format` is only an annotation in JSON Schema 2020-12.

## Drift and verification

With `--check`, compilation compares the exact file set, manifest and bytes of the output directory
without writing anything. Missing, changed, extra or symlinked artifacts fail. Normal recompilation
removes obsolete engine files named by the previous generated manifest, preserving unrelated files.
Malformed or unsafe previous manifests fail before writes; symlinked destinations are refused.
Compilation is not an atomic directory transaction: an interrupted write can leave drift, which
`--check` detects and a rerun repairs.

Each committed `generated/contracts/<contract-id>/` is the drift reference for that registered
contract. `make ci` runs `make contract-check`, so a contract, mapping or generator change fails
until `make contract-compile`
refreshes the directory and the diff is reviewed and committed. Review the generated DDL and models
in that diff; do not bypass the check.

`tests/contracts/test_compiler.py`, `test_templates.py` and `test_references.py` cover supplied
contracts, reference kinds, endpoint mismatches, strict native models, deterministic bytes, stale
files, unsafe manifests and drift. `test_physical.py` covers derived names, `test_type_mapping.py`
the wire and native value ranges, `test_diagnostics.py` located refusals, and `test_generated.py`
the committed output and default directories. `tests/integration/test_contract_compiler.py` executes
generated SQL in scratch schemas: the complete SATCOM model, Unicode comments, invalid geometry and
SRIDs, GiST indexes, and a partitioned parent. `tests/integration/test_contract_governance.py`
applies long and composite names and verifies the compiled catalog, evolves with comments, and
refuses a changed geometry type. Run `make ci-local` after `make db-up` for both test sets. The
acceptance evidence is in [record 0015](../../records/0015-data-contracts-contract-compiler.md), and
the audit of the group in [record
0017](../../records/0017-data-contracts-data-contracts-implementation-audit.md).
