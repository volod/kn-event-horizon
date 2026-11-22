# Record 0025: ontology-taxonomy-implementation-audit

## Work contract

Original plan task, copied before implementation:

```markdown
#### ontology-taxonomy-implementation-audit (optional)

Concept IDs, schemes, and crosswalks become references in claims, exports, and dashboards, so
changing them later breaks stored data and links.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: CLEAR
- Dependencies: The accepted task records of the group and the [implementation
  audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Claims and exports reference stable, verified concepts. The audit record
  gives every check a result and every finding a disposition. The current-state page lists known
  limitations, and each scheduled finding is a plan task.
- Scope boundary: Focus: stability of concept IDs and URIs across rebuilds; deprecation and
  replacement of concepts in use; hierarchy cycles and multiple parents; label parity in `en` and
  `uk`; seed reconciliation of added, changed, and removed rows; official editions and checksum
  drift; the SKOS round trip; a new domain scheme or edition without renumbering. Fixes only; new
  behavior becomes plan tasks.
- Data and artifact paths: `contracts/core/semantic/`, `src/kn/semantic/`,
  `domains/<domain>/seeds/`, `tests/semantic/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Rebuild
  twice and compare concept IDs, plant a cycle and a duplicate label, deprecate a concept that a
  claim uses, and parse the SKOS export with an independent parser.
- Acceptance gates: Concept IDs are identical across rebuilds. A cycle, a duplicate label, and a
  deprecated concept in use are reported. The SKOS export parses with an independent tool. Every
  finding has a severity, evidence, and a disposition, no `blocker` is accepted, and every fix
  starts from a failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/ontology-taxonomy.md` listed in the [areas
  index](current.md#areas).
```

The owner's request added: when the audit finds an issue or an opportunity, update the
specification and create the required tasks.

Prerequisites: the task has no open `Requires` entry. The group's tasks were accepted in
[record 0020](0020-ontology-taxonomy-semantic-model-contracts.md),
[record 0021](0021-ontology-taxonomy-seed-vocabulary-import.md),
[record 0022](0022-ontology-taxonomy-verify-official-taxonomies.md),
[record 0023](0023-ontology-taxonomy-oecd-official-product-scheme.md), and
[record 0024](0024-ontology-taxonomy-skos-export.md).

## Implementation and decisions

The audit worked through the six [implementation audit](../../guide/planning-workflow.md#implementation-audits)
checks against the [ontology and taxonomy](../../design/spec.md#ontology-and-taxonomy) section,
the [localization](../../design/spec.md#localization) data rules and the records of the group. The
[ontology page](../current/ontology-taxonomy.md) and its [seed](../current/ontology-taxonomy/seeds.md)
and [verification](../current/ontology-taxonomy/verification.md) references describe the resulting
behavior and its known limitations.

### Findings

| ID | Severity | Check | Finding and evidence | Disposition |
| --- | --- | --- | --- | --- |
| ON-01 | major | 2, 4 | A deprecated or replaced concept that is still in use was accepted without any report. In `planted-validation.log`, deprecating a concept used by an OECD crosswalk, deprecating a parent of active concepts, and replacing a concept with a deprecated successor were each `ACCEPTED silently`. The task gate requires such a concept to be reported. | Fixed: `kn.semantic.lifecycle.lifecycle_report` lists every retired concept in use with its uses (children, mappings, tags, replacement links, caller-owned records) and the end of its replacement chain; every reconciliation writes it under `lifecycle`. Regression tests in `tests/semantic/test_lifecycle.py` (7), which failed with `ModuleNotFoundError` first. Claims are scheduled: `evidence-claim-contracts` gained a gate that a claim citing a retired concept appears in the report. The specification states the report. |
| ON-02 | major | 4 | A changed proposal could not be reviewed. Removing one row of the space service sheet, with its manifest updated as a new conversion would, made `reconcile()` refuse before staging with `verification review is stale; compare changed content with publication` (`planted-removed-row.log`). The scheme was `space.services`, a local vocabulary with no publication, and the message did not name it. The new digest could only be computed from the staged content that was refused, and removed term IDs were never reported. | Fixed: staging continues, stages a stale scheme `unverified` with a request for a new comparison, and reports it under `stale_reviews` with the reviewed and the new digest; loading and `make seed-check` still refuse it, naming the scheme. Every reconciliation lists the added, changed and removed term IDs per domain under `changes`. Regression tests in `tests/semantic/test_seed_changes.py` (3); the stale-review test now checks both modes. |
| ON-03 | minor | 5 | A cycle diagnostic named only the table, `$/concepts`, in a scheme of up to 231 concepts. | Fixed: it names the link of a row on the cycle, for example `$/concepts/12/parent_id`. Regression test `test_a_cycle_names_a_concept_row_on_the_cycle`. |
| ON-04 | major | 2 | All 756 `uk` preferred labels equal their `en` labels and contain no Cyrillic (`onto_static` in the evidence directory). The validator requires a `uk` label for every named term, so the import copies the English text under `uk`; the database and SKOS (`"..."@uk`) present it as Ukrainian. The localization rules require labels to keep the language of their text and display to fall back from `uk` to `en` with the fallback reported. | Scheduled bug: `vocabulary-text-integrity`. Changing the label rule and 782 `uk` seed rows changes the content digests of all 16 publication reviews, which need a recorded new comparison, so it is too large for the audit. `review-ukrainian-terminology` now requires it. The specification states the label rule. |
| ON-05 | minor | 2 | All 520 concept definitions are JSON dumps of proposal columns, for example `{"class": "IC-Analog", "kb_node": "A", ...}`, stored as definitions and exported as `skos:definition`. The columns are already in provenance and the reconciliation. | Scheduled with ON-04 in `vocabulary-text-integrity`. The specification states that a definition is a definition or absent. |
| ON-06 | minor | 4 | A publication URI with a space, a quote or angle brackets passed validation, because only `urlsplit` and credentials were checked. The SKOS export then failed inside RDFLib with a bare `Exception`, which the CLI does not catch, so an operator would see a traceback. | Fixed: whitespace, control characters and `<>"{}|\^` are refused as not valid in an IRI; percent-encoding and non-ASCII remain allowed. Regression tests `test_a_publication_uri_must_be_a_valid_iri` (5) and `test_a_publication_uri_may_use_percent_encoding_and_non_ascii`. |
| ON-07 | minor | 2 | A mapping between two concepts of the same scheme is accepted. SKOS links schemes with mapping properties by convention; no integrity condition forbids it, and no reviewed mapping joins one scheme. A rule would invalidate the shared model fixture and the policy tests built on it. | Accepted: listed under known limitations; reopen when reviewed content maps within a scheme. |
| ON-08 | minor | 3 | Each concept has one primary parent, so a polyhierarchy cannot be expressed. No proposal needs one: the 29 OECD categories have 25 parent edges and 4 roots, and the reconciliation has no multi-parent row. | Accepted: a secondary hierarchy table would be additive. Listed under known limitations. |
| ON-09 | minor | 3 | Exported term URIs are `urn:kn:term:<id>`, but RFC 8141 namespace identifiers are registered and `kn` is not. The URIs become references in other systems once an export is shared, so the base is cheap to change only now. Choosing a base that the owner controls is the owner's decision. | Scheduled: human-gated `decide-vocabulary-uri-namespace`, in which the agent then applies the base. |
| ON-10 | minor | 3 | The publication reviews pin checksums of mutable URLs, and nothing notices when a publisher replaces the bytes behind a reviewed edition. | Scheduled feature, with a specification change: optional `official-publication-drift-check` (RUN NEEDED). |

No `blocker` was found. Four tasks or gates were scheduled; two findings were accepted.

Observations that are not findings:

- Two CLI rebuilds of a throwaway database give identical rows in all 18 semantic tables and the
  same 825 term IDs (`rebuild-identity.sh`, `rebuild-1.txt`, `rebuild-2.txt`). Term URIs derive
  only from these IDs.
- A new edition beside the old one, `space.esa_tt_4_2` with the codes of 4.1, validates without
  renumbering: the old IDs stay and the new ones are qualified by the new namespace.
- A planted cycle (`semantic.cycle`) and a case and whitespace variant of a preferred label
  (`semantic.label`) are refused, as the tests of record 0020 also show.
- No reviewed term is deprecated or replaced yet, so the lifecycle report is empty for the seeds.

### Check results

1. **Implementation validation.** Passed. `make ci-local` (732 unit and 64 integration tests) and
   `make seed-check` (1,173 rows: 612 accepted, 1 duplicate, 477 needing mapping, 83 rejected)
   passed before any change. All 16 schemes export through `kn vocabulary export`. The current
   pages matched the commands and counts; they now also describe the lifecycle report, change
   reporting, stale-review staging and the known limitations.
2. **Specification conformance.** Unique IDs, one preferred label per language and scheme,
   acyclic primary hierarchies, existing parents, non-conflicting mappings and endpoints map to
   code and tests. Gaps: ON-01, ON-04 and ON-05; ON-07 is accepted. The SKOS export parses with
   RDFLib and round-trips its labels, which the specification asks for, and with two independent
   parsers (below).
3. **Design scope.** Expensive to change later: qualified term IDs (`<domain>.<code>.<code>`) and
   one namespace per edition, which ON-02's change report now protects; the term URI base (ON-09);
   the single primary parent (ON-08); content digests that bind reviews to labels, codes and
   hierarchy; and the envelope format of reviewed seeds. A new edition or domain scheme fits by
   extension. Findings: ON-08, ON-09, ON-10.
4. **Corner cases.** Removed and changed proposal rows (ON-02), retired concepts in use (ON-01),
   cycles, case and whitespace label variants, a new edition, invalid IRIs (ON-06), Unicode labels
   (record 0020 tests) and rebuild repeatability were exercised. Time zones apply only to tag
   validity, which the validator checks.
5. **Best practices.** Typed, network-free tests, value-free diagnostics and offline validation
   hold. Findings: ON-03, ON-06. `seeds.py` would have grown to 285 lines, so the change report
   moved to `seed_changes.py` and database loading to `seed_loader.py`; no file exceeds 250 lines.
6. **Debt.** No `TODO`, skipped check or parallel implementation was found. The stale-review test
   was split to stay below the complexity limit rather than raising it.

## Acceptance evidence

Status: accepted on 2026-11-22. The independent-parser gate closed after the owner chose the
tools; [record 0026](0026-adhoc-independent-rdf-parsers-and-host-prerequisites.md) documents that
decision.

Scripts and logs are in `$DATA_DIR/acceptance/ontology-taxonomy-implementation-audit-20261122/`.

| Gate | Evidence | Result |
| --- | --- | --- |
| Concept IDs are identical across rebuilds | `rebuild-identity.sh`, `rebuild-1.txt`, `rebuild-2.txt`, `term-ids-1.txt`, `term-ids-2.txt` | Identical: 825 term IDs and the row hashes of 18 semantic tables |
| A cycle, a duplicate label, and a deprecated concept in use are reported | `planted-validation.log`; `test_lifecycle.py`; record 0020 tests | Cycle and duplicate label refused; retired concepts in use reported after ON-01 |
| The SKOS export parses with an independent tool | `skos/`, `jena-validate.log`, `parser-counts.log`, `skos-reference-check.log`; `tests/semantic/test_skos_independent.py` | Apache Jena RIOT 6.3.0 (`riot --validate`, strict) accepts all 16 exports without a warning. Oxigraph 0.5.13 parses them strictly, and its triples equal RDFLib's. The three parsers agree on every triple count. Both checks are now permanent: the Oxigraph test in `make ci`, and `make skos-reference-check` in `make ci-local` |
| Every finding has a severity, evidence, and a disposition; no accepted `blocker` | The findings table | 3 major and 7 minor; 4 fixed, 4 scheduled, 2 accepted; no `blocker` |
| Every fix starts from a failing regression test | `regressions-before.log` | Before the fixes: the lifecycle module was missing, and 3 change-staging, 1 cycle and 5 IRI tests failed. After: all 231 semantic tests passed |
| `make ci` passes with the scheduled tasks in the plan | `ci-local-final.log`, `quality.log` | `make ci-local` exit 0: 756 unit tests (732 before) and 64 integration tests; `make quality` reaches 93.87 % coverage and builds the package; 0 spec-plan findings with the four scheduled items |

## Handoff

Plan counts before: 110 tasks (98 agent, 12 human); statuses BLOCKED BY HUMAN 3, CLEAR 90,
HUMAN-GATED 9, RUN NEEDED 8. Priority agent task `identity-registry-contracts`; priority human task
`provide-inventree-instance-access`.

Plan counts after: 112 tasks (99 agent, 13 human); statuses BLOCKED BY HUMAN 3, CLEAR 90,
HUMAN-GATED 10, RUN NEEDED 9. Priority agent task `vocabulary-text-integrity`; priority human task
`decide-vocabulary-uri-namespace`.

Plan changes: `vocabulary-text-integrity` (required), `official-publication-drift-check`
(optional) and `decide-vocabulary-uri-namespace` (human lane) joined the ontology group.
`review-ukrainian-terminology` requires `vocabulary-text-integrity`, and `evidence-claim-contracts`
gained the lifecycle-report gate. `ontology-taxonomy-implementation-audit` left the plan. The
registry changes `ontology-taxonomy` from `shipped` to `planned`, because required work is open
again. The specification's ontology section states the change report, stale-review staging, the
label and definition rules, the lifecycle report and the drift check. Capabilities affected:
`ontology-taxonomy`, `evidence-model` (one gate) and `localization` (one prerequisite).
