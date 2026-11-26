# 0047 Object lineage lookup

## Work contract

```markdown
#### object-lineage-lookup

Operators must be able to trace any object or field back to every record and decision behind it.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: The [record versions, change sets and claim lineage](current/object-identity.md#partial-update-tracking)
  and the [selected facts and explained outcomes](current/evidence-model.md#fact-projection).
- User-visible outcome: `kn lineage <kn-id|qualified-identifier> [--field <field-id>]` shows, in
  both locales and as JSON, the identity history, identifiers, links with match records, record
  versions and change sets, claims, and the selected canonical fact. Outbound exchange receipts
  join the view once the exchange ledger exists.
- Scope boundary: A read-only, rights-filtered query layer and CLI over the identity and evidence
  schemas. The dashboards reuse it in `analyst-fact-explanation`.
- Data and artifact paths: `src/kn/identity/lineage.py`, `src/kn/cli.py`, `tests/identity/`.
- Execution path: Use fixture objects with a merge, a split, a partial update, and a conflict.
- Acceptance gates: Each fixture returns the complete chain down to archive record IDs. A merged ID
  shows its survivor's lineage with the merge event. Restricted evidence is withheld and counted.
  Golden outputs exist in both locales.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

Both dependencies were available: record versions, change sets and claim lineage from record 0045,
and the fact projection and explained outcomes from record 0046. The task adds a read-only view in
three modules and the `kn lineage` command:

- `src/kn/identity/lineage.py` resolves the reference, chooses the covered objects and builds the
  identity sections from the journal state; `lineage_records.py` lists source records, versions,
  change sets and sightings.
- `src/kn/evidence/lineage.py` defines the `EvidenceRows` reader protocol, its PostgreSQL
  implementation `SqlEvidenceRows`, the rights filter and the JSON normalization of rows.
- `src/kn/i18n/lineage_output.py` renders localized section headings; `kn.operations` opens the
  database in a read-only transaction; `src/kn/cli.py` parses the command.

Decisions:

- Coverage: a lookup covers the terminal successors of the reference and every object that
  redirects to them. A merged ID therefore returns its survivor's view with the merge event, and
  only the requested ID differs. Holdings are selected by their current owner, so a split
  successor does not show the links and identifiers its sibling received.
- Split claims: a claim keeps the KN ID it was made about. A claim about a split object belongs to
  the successor that now holds its source record; the projection leaves such claims unattributed,
  and the lookup shows them with the record they came from.
- Qualified identifiers: namespaces can contain colons (`inventree:vl-itree:part`), so every colon
  is tried as the separator. The identifier must lead to exactly one current owner; otherwise the
  command reports `E_INPUT` and names no candidate.
- Rights: evidence rows carry rights. `--permit` lists the rights an audience may see; without it,
  every statement is visible, as for the internal audience of canonical selection. Withheld rows
  are counted by kind, as the plan requires for operators. A claim whose rights are unknown, such
  as a fact naming a claim the view does not hold or a claim without its evidence row, fails
  closed for a restricted audience. Identity attributes and match features have no rights
  statement, so a restricted audience sees none of their values.
- Facts: only current fact versions of the chosen audience are shown, with the outcomes, review
  items and decisions they name. Fact history stays available through `facts_as_of`.
- Gaps: a lookup reports broken references instead of hiding them, so the implementation audit can
  find a claim whose version is missing from the journal or a current fact still stored under a
  merged KN ID, the limitation recorded in the evidence model.
- Read-only access: production code sends no SQL strings, so the transaction uses the
  `postgresql_readonly` execution option. The reference is resolved before the database is opened.
- Outbound exchange receipts are not part of the view; `exchange-binding-ledger` adds them.
- Release coverage: the bilingual release gate no longer lists `lineage` as a blocker, since
  goldens now exist in both locales. Root help goldens list the new command.
- Fixes during implementation: the first fixture used `identity-review:` decision references, which
  rebuild requires to exist in the review journal; it now uses opaque fixture references like the
  other identity fixtures. A first `SET TRANSACTION READ ONLY` statement broke the rule against SQL
  strings and was replaced by the execution option.

## Acceptance evidence

Status: accepted. Initial `make plan-status`: 115 tasks, 103 agent, 12 human; BLOCKED BY HUMAN=3,
CLEAR=90, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=103, MODEL=12.

| Gate | Evidence |
| --- | --- |
| Each fixture returns the complete chain down to archive record IDs | `test_every_fixture_returns_the_complete_chain_to_archive_records` for both offers, the split object, both successors and the qualified identifier: every fact and outcome claim is listed, and every claim and confirmation reaches its version, change set, fetch and archive record ID with no gap |
| A merged ID shows its survivor's lineage with the merge event | `test_a_merged_id_shows_its_survivors_lineage_with_the_merge_event`: the view of the merged ID equals the survivor's except for the requested ID, and includes the reviewed merge, the moved link and its match record |
| Restricted evidence is withheld and counted | `test_restricted_evidence_is_withheld_and_counted` (2 claims, 1 fact), `test_an_audience_sees_its_facts_and_no_identity_values_without_rights`, `test_a_restricted_excerpt_is_withheld_from_permitted_evidence`, and the fail-closed gap tests |
| Golden outputs exist in both locales | [lineage goldens](../../../tests/e2e/fixtures/lineage-cli.json) for a merged ID, a split successor, a qualified identifier with `--field` and a restricted audience; `tests/e2e/test_lineage_cli.py`, and `tests/integration/test_lineage_cli.py` through the PostgreSQL CLI |

- Execution path: `tests/identity/lineage_fixtures.py` builds a merge of two offers whose prices
  conflict, a partial update followed by an unchanged sighting, a split after both records were
  tracked, and a record with restricted rights, then projects facts for two audiences.
  `tests/identity/test_lineage.py` (17 tests) and `test_lineage_cli.py` (2) cover the view and the
  CLI refusals without a database.
- `tests/integration/test_lineage_cli.py` rebuilds a disposable database from the fixture journal,
  stores the evidence rows, runs every golden case in both locales as text and JSON, and checks
  that the transaction was read-only and no row changed. It passed on a disposable Compose project
  with service state under `$DATA_DIR/object-lineage-lookup/run-20261126/service/`.
- Full local integration and heavy suites on the same service: all 121 selected tests passed,
  none skipped (`$DATA_DIR/object-lineage-lookup/run-20261126/integration.log`). The Compose
  project was stopped afterwards; its data volume stays with the run evidence.
- `make ci`: passed, 1419 tests with 121 integration or heavy tests deselected
  (`$DATA_DIR/object-lineage-lookup/run-20261126/ci.log`). `make test-bilingual`: 104 passed;
  `en/lineage/` and `uk/lineage/` evidence is under `$DATA_DIR/e2e/bilingual-BA88dlzm/`.

## Handoff

The task left the plan. `object-identity-implementation-audit` no longer requires it and links the
lineage lookup and this record for tracing values to raw records. `analyst-fact-explanation`
names the lineage view as its dependency and keeps its stricter rule that a dashboard leaves no
restricted count. `exchange-binding-ledger` still adds outbound receipts to `kn lineage`. Final
`make plan-status`: 114 tasks, 102 agent, 12 human; BLOCKED BY HUMAN=3, CLEAR=89,
HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=102, MODEL=12. Next required agent priority is
`identity-incremental-writes`.

`object-identity` remains `planned`. No commit or push was made.
