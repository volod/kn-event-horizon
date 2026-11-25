# 0046 Canonical fact selection

## Work contract

```markdown
#### canonical-fact-selection

Sources declare nothing, so KN must decide by explicit rules how each new claim fills, replaces, or
leaves an object's value. Arrival order must never decide.

- Serves: `evidence-model` -- [Evidence model](../design/spec.md#evidence-model)
- Agent status: CLEAR
- Dependencies: The [reviewed source rank override format and catalogue IDs](current/source-management.md#reviewed-inputs-and-identifiers)
  and the [canonical fact, outcome and policy shapes](current/evidence-model.md#selection-and-review-shapes).
- User-visible outcome: The engine projects each field's canonical value through its update
  policy. The modes are `priority`, `latest_observed`, `accumulate`, and `fixed`. A candidate value
  ranks by its best supporting claim: source rank, then evidence class, then data time within one
  source. Every change is explained as filled, replaced, ignored, corroborated, or conflict, with
  the deciding criterion. Selection flags owner overrides of first-party values for review.
  Identity redirects are followed. Conflicts, and high-impact facts
  without primary evidence, go to review.
- Scope boundary: The `kn.updatePolicy` semantics; the reviewed source rank table
  `contracts/core/policies/source-ranks.yaml`, with `owner_entered` as the highest class and review
  decisions ranked through it; evidence classes; verification states derived from support and
  review; eligibility (minimum rank and evidence class, rights, conditions); empty-claim handling;
  freshness and `stale` labels; audience-specific selection from eligible evidence. Identity
  resolution uses the [available matcher](current/object-identity.md#match-resolution).
  Domain policies come with domain contracts.
  Only the matching accepted human decision can supply human-verification metadata for the
  selected claim; timestamps alone never bypass eligibility or resolve a conflict.
- Data and artifact paths: `src/kn/evidence/`, `contracts/core/policies/`, `tests/evidence/`.
- Execution path: Write fixture-first tests for each outcome, mode, and verification state in the
  specification, then the selector.
- Acceptance gates: An empty field is filled by the first eligible claim. A higher-ranked value
  replaces it, and a lower-ranked value is ignored and stays visible. An owner-entered value
  outranks a manufacturer value and is flagged `owner_override`. A value that a higher-ranked
  source also supports wins, while repeated claims or confirmations from one source add no rank.
  A newer datasheet revision from the same source replaces the older one. Different values from
  two sources of equal rank and evidence class conflict. Under `latest_observed`, a newer price
  wins, and an old winner shows as `stale`. A different value on a `fixed` field opens review, and
  an outranking empty claim opens review without clearing. Every permutation of arrival order
  gives identical canonical values. Fixtures keep organization, model, spacecraft, constellation,
  program, and service distinct, and a contradictory ownership claim stays conflicted. Claims
  about a merged object are selected under its survivor. Signals never fill canonical fields.
- Documentation target: `current/evidence-model.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

Both dependencies were available: the reviewed rank override format and the canonical fact,
outcome, review item and policy shapes of record 0044. The selector is pure and lives in
`src/kn/evidence/`: `ranking.py` (rank table, audiences, accepted reviews, eligibility),
`candidates.py` (value agreement, candidate grouping and the mode orders), `modes.py`
(`priority`/`latest_observed`, `fixed` and `accumulate` plans), `planning.py` (empty claims,
high-impact gating, owner overrides), `selection.py` (`select` and the explained rows) and
`projection.py` (survivor subjects, knowledge-time history, `stale` and the PostgreSQL writer).
It writes only the registered `canonical_facts`, `selection_outcomes` and `review_items` shapes.

- Arrival order: `select` evaluates the whole claim set of a subject with total orders that end in
  the claim key, so input order cannot matter. Version history is replayed at claim and decision
  recording times, which are stored data.
- Outcomes: the specification defines `filled`, `replaced` and `corroborated` as changes against
  the current value, and the contract says an ignored claim leaves no version. `select` therefore
  takes the previous version: values are order-independent, while the change outcome of a version
  depends on the stored history before it. An ignored claim or a new runner-up adds an outcome
  row to the current version instead of a new version.
- Field groups: the rank format had no matching rule. A group matches a stable field ID equal to
  it or below it at a dot boundary, and the longest match wins over a source-wide override.
- Data time: in `priority` it decides tied candidates only when one source states all of them
  and every time is known. A different source is never newer, and an unknown time is a conflict.
- `fixed`: "first" uses the claim's data time or observed time, never recording order. An
  accepted review selection holds instead and settles the claims recorded by that decision; a
  later different claim opens review again. Review items of a fixed field name only the
  challengers, so a rejection keeps the held value.
- Empty claims: an outranking `source_empty` claim restores the predecessor it supersedes as a
  candidate, so review keeps the value. A rejected empty claim restores it without review, and an
  accepted one or `allow_clear` gives `cleared`. Other missing reasons are not values.
- `accumulate`: one fact row per key is a contract rule, so the row names the best member and the
  union is the set of `filled` outcomes of that version (`Selection.members`).
- High impact: no contract declared rule-6 fields. The optional `kn.updatePolicy` member
  `highImpact` (default false) was added to the extension registry, and the schema pin in
  `src/kn/contracts/resources/pins.json` was updated. No contract uses the policy yet, so no
  generated artifact or contract digest changed. Without primary evidence or an accepted review
  the fact is `review_pending`.
- Reviews: the review queue does not exist yet, so `Reviews` takes accepted selections,
  rejections and accepted decision IDs with their recording times. `Reviews.at` keeps a later
  decision out of earlier versions. A `decided` claim whose decision is not accepted is
  ineligible, and source labels never verify.
- Signals and AI candidates: `gdelt:` sources and `extracted_candidate` evidence are never
  eligible, even under a policy whose minimum would admit them.
- Owner overrides: only a claim whose own table rank is `owner_entered` sets the flag; a review
  decision is deliberate and is not flagged. An accepted owner claim keeps the flag but opens no
  item.
- Improvement found during implementation: object values were compared by the KN ID as stated,
  so a claim naming a merged organization conflicted with one naming its survivor. `Context`
  now takes the identity resolver, and assessed values name the survivor before comparison;
  a split object keeps its stated ID. A regression test covers both cases.
- Complexity: the first `planned`, `fixed` and `history` exceeded the gate (radon D, cognitive
  above 15) and were split at the empty-claim effect, the fixed-field contest and version
  closing.

## Acceptance evidence

Status: accepted. Initial `make plan-status`: 116 tasks, 104 agent, 12 human; BLOCKED BY HUMAN=3,
CLEAR=91, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=104, MODEL=12.

| Gate | Evidence |
| --- | --- |
| An empty field is filled by the first eligible claim | `test_the_first_eligible_claim_fills_and_a_higher_ranked_value_replaces` (`filled`, `first_eligible`) |
| A higher-ranked value replaces it | Same test: second version `replaced` by `source_rank`, first version closed at the second's start |
| A lower-ranked value is ignored and stays visible | `test_a_lower_ranked_value_leaves_no_version_and_stays_visible`; `test_a_value_a_higher_ranked_source_also_supports_wins` |
| An owner-entered value outranks a manufacturer value and is flagged `owner_override` | `test_an_owner_value_outranks_the_maker_and_is_flagged_for_review`, `test_an_accepted_owner_override_is_still_flagged_but_needs_no_review` |
| A value a higher-ranked source also supports wins; repetition and confirmations add no rank | `test_a_value_a_higher_ranked_source_also_supports_wins`, `test_repeated_claims_from_one_source_add_no_rank_and_no_corroboration`; confirmations are not selection inputs |
| A newer datasheet revision from the same source replaces the older one | `test_a_newer_datasheet_revision_from_the_same_source_replaces_the_older`, `test_a_different_source_never_wins_by_being_newer` |
| Different values from two sources of equal rank and evidence class conflict | `test_equal_rank_and_evidence_from_two_sources_conflict` |
| Under `latest_observed`, a newer price wins and an old winner shows as `stale` | `test_a_newer_price_wins_and_an_old_winner_shows_stale` and two further `latest_observed` tests |
| A different value on a `fixed` field opens review | `test_a_different_value_on_a_fixed_field_opens_review_and_never_applies`, `test_a_fixed_field_review_settles_the_claims_it_saw` |
| An outranking empty claim opens review without clearing | `test_an_outranking_empty_claim_opens_review_and_does_not_clear`, plus clearing and never-fill cases |
| Every permutation of arrival order gives identical canonical values | `test_every_arrival_order_gives_identical_canonical_values`: all 120 orders of five claims in `priority`, `fixed` and `accumulate`; `test_an_empty_claim_gives_the_same_value_in_every_arrival_order`: all 24 orders |
| Fixtures keep organization, model, spacecraft, constellation, program and service distinct | `test_distinct_entity_classes_with_one_name_stay_distinct_facts` |
| A contradictory ownership claim stays conflicted | `test_a_contradictory_ownership_claim_stays_conflicted` (high-impact, both claims kept) |
| Claims about a merged object are selected under its survivor | `test_claims_about_a_merged_object_are_selected_under_its_survivor`, `test_object_values_naming_a_merged_object_support_its_survivor` |
| Signals never fill canonical fields | `test_signals_never_fill_canonical_fields` |

- Execution path: `tests/evidence/selection_fixtures.py` holds ranked fixture sources and claim
  builders. `tests/evidence/test_selection.py` (20 tests), `test_selection_modes.py` (9) and
  `test_projection.py` (13) cover every outcome, mode and verification state, eligibility,
  audiences, tolerance and accepted, rejected and unaccepted reviews. `test_policy.py` (12)
  adds the optional `highImpact` member and the packaged rank table.
- `tests/integration/test_evidence_selection.py` (2 tests) writes histories to PostgreSQL:
  as-of current and earlier views, closed versions, outcome and item rows, an idempotent rewrite,
  deferred reference checks and refusal of a history that differs from the stored one. It ran
  with `tests/integration/test_evidence.py` on a disposable Compose project (15 of 15 passed),
  with service state under `$DATA_DIR/canonical-fact-selection/run-20261125/service/`.
- Full `tests/integration` suite on the same service: 119 of 119 passed with none skipped
  (`$DATA_DIR/canonical-fact-selection/run-20261125/integration.log`).
- `make ci`: passed, 1397 tests with 120 integration or heavy tests deselected
  (`$DATA_DIR/canonical-fact-selection/run-20261125/ci-2.log`).

## Handoff

The task left the plan. `object-lineage-lookup` no longer requires it and links the fact
projection in `Dependencies`. `object-identity-implementation-audit` no longer requires it and
links the evidence model limitations for facts stored under a later-merged KN ID. Added scope:
`review-queue-cli` derives the selector's accepted reviews from applied decisions and reports
per-source dispute rates; `curated-source-method` ranks curated claims as the source they cite;
`mapping-and-quality-rules` projects the facts of the subjects a load touches. Final
`make plan-status`: 115 tasks, 103 agent, 12 human; BLOCKED BY HUMAN=3, CLEAR=90,
HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=103, MODEL=12. Next required agent priority is
`object-lineage-lookup`.

`object-identity` and `evidence-model` remain `planned`. Domain contracts declare their field
policies with their own tasks. No commit or push was made.
