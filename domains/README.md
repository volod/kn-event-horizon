# Domain Packages

Each directory under `domains/` is a knowledge domain package: `space`, `gdelt`, and
`microelectronics`. The [specification](../docs/design/spec.md#repository-layout) defines the full
package layout. For now each package holds seed proposals only.

## Seed proposals

`<domain>/seeds/proposals/<workbook>/` holds a lossless JSON conversion of one proposal workbook
that the project owner supplied. Each workbook directory contains:

- `workbook.json`: the source workbook name, its SHA-256, the conversion rules, and one entry per
  sheet with the output file, its SHA-256, and its record count.
- One `<sheet>.json` per sheet. Table sheets use format `kn.seed-proposal.table`, with `title`,
  `notes`, `header_row`, `columns` (key, original label, and spreadsheet column), and `records`
  (`source_row` plus `values`). README sheets use format `kn.seed-proposal.notes`, with `rows` of
  raw cells keyed by spreadsheet column.

Conversion rules: cell text is verbatim, empty cells are `null`, numeric cells are JSON numbers,
and codes such as CAMEO `01` stay strings. Formulas were never evaluated. Formula cells keep their
cached value, and the formula text is recorded under `formulas_not_evaluated`. Non-ASCII
characters are escaped, so the files are ASCII. Every non-empty workbook cell was checked against
the JSON. The conversion is recorded in
[task record 0002](../docs/impl/records/0002-adhoc-knowledge-platform-specification.md).

## Status of the data

Every file has `"status": "unreviewed_proposal"`. These are inputs to the seed import, not facts
and not official taxonomies:

- Tagging examples, templates, and hypothetical rows are test fixtures only.
- Concepts that name an official standard stay unverified until they are checked against the
  official publication.
- Source rows are candidates. No source is enabled because a row exists.
- Identifiers such as `S01` or `APP.*` repeat across domains with different meanings, so the import
  qualifies every identifier with its domain and scheme.

The [ontology and taxonomy](../docs/design/spec.md#ontology-and-taxonomy) and
[source management](../docs/design/spec.md#source-management) sections define how these files
become reviewed seed data.

The repository test suite checks each proposal directory against its manifest, including the set
of sheet files, SHA-256 digests, proposal status, and row counts. This check covers the converted
JSON. Verification against an official vocabulary remains a separate review.
