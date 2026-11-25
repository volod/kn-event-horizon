# Evidence Model

The evidence contracts and the shared human verification protocol are implemented. Claims,
evidence, confirmations, aliases, translations, relation assertions, canonical fact versions,
selection outcomes, review items and review decisions have registered storage, deterministic keys,
database constraints and as-of views. Partial-update tracking, canonical selection, the review
queue and dataset-wide verification projections remain planned and write into these shapes.
Existing source verification labels retain their meanings and grant no human timestamp.

## Evidence contracts

The registered `kn.core.evidence` ODCS contract,
[`resources/evidence/claims/1.0.0.json`](../../../src/kn/contracts/resources/evidence/claims/1.0.0.json),
shares the `evidence` schema with `kn.core.human_verification`. It adds 11 tables and 148 fields;
the registry now defines 73 tables and 706 fields at development version `1.0.0`.
`make contract-compile` writes its reviewed artifacts under
[`generated/contracts/kn.core.evidence/`](../../../generated/contracts/kn.core.evidence/docs/contract.md).

| Table | Key | Holds |
| --- | --- | --- |
| `evidence_records` | `evidence_id` | Source, fetch and archive record IDs, redacted origin URI, fetch time, locator kind and locator, rights, licensed excerpt, code and contract digests, curator |
| `claims` | `claim_key` | KN ID, stable field ID, conditions, source record and version, change set and kind, predecessor, decision reference, provenance copy, original value and unit, one typed value or missing reason, unit conversion, assertion type, evidence class, extraction confidence, imported source label, event/published/valid times with precision, observed and recorded times |
| `claim_confirmations` | `confirmation_id` | Re-observation of an unchanged claim: source version, evidence, fetch, observed time |
| `aliases` | `alias_id` | Weak alias with language, normalized key and normalizer, citing its claim; not unique |
| `text_translations` | `translation_id` | Derived translation of a text claim with method and provenance; one per language |
| `relation_assertions` | `assertion_id` | Subject, relation type, object, qualifiers, validity, review state, opening claim, knowledge interval |
| `relation_supports` | `assertion_id`, `claim_key` | Claims supporting an assertion |
| `canonical_facts` | `fact_version_id` | Knowledge-time version of a field's selected claim or unresolved reason, with mode, policy digest, outcome, deciding criterion, winner and runner-up criteria, verification label, owner override and validity |
| `selection_outcomes` | `outcome_id` | Outcome and criterion of each evaluated claim against the resulting fact version |
| `review_items` | `item_id` | Registered kind, subject, sorted candidates, reason code and opening reference |
| `review_decisions` | `decision_id` | Append-only outcome, selected claim, predecessor, reviewer, reason, performed and recorded times, shared verification decision and canonical event |

The contract declares `kn.temporalProfile` on claims, evidence, confirmations, relations and facts,
`kn.evidence` on claims, and record-scope `kn.humanVerification` on every table; review decisions
use the `decision-log` strategy. `kn.evidence` now accepts `assertionField` instead of a single
`assertionType`, because claim rows carry their own assertion type.

PostgreSQL enforces the rules that a row can check on its own. Generated JSON Schema and Pydantic
models enforce the same null rules through the bounded
[`kn.presence` extension](data-contracts/compiler.md#postgresql-and-native-model-templates):

- exactly one of the six value columns or `missing_reason` per claim, and exactly one selected
  claim or `unresolved_reason` per fact version;
- complete pairs: text and language, normalized unit and conversion rule, each time and its
  precision, an excerpt and its rights, and a relation's close time and reason;
- `NOT NULL` origin URI, fetch time and fetch ID on every claim and evidence row, and enums for
  every closed vocabulary;
- one current version per fact key (`facts_current_idx`, `knowledge_to IS NULL`) and one active
  assertion per relation key (`relations_active_idx`, `closed_at IS NULL`).

Foreign keys within the contract are deferred. KN IDs, source records, source versions, change
sets and concept IDs belong to other contracts; their owning engines check them, so SQL cannot
reject an unknown KN ID by itself.

## Claims and provenance

`kn.evidence.model` defines immutable `Evidence`, `Claim`, `Confirmation` and `Alias` rows, and
`kn.evidence.values` the typed claim values: text with a BCP-47 tag, exact number with optional
unit conversion, boolean, partial date, concept, object reference, or `Missing` with a reason. A
claim embeds its evidence, so the claim's origin URI, fetch time and fetch ID always equal the
evidence row's. Validation refuses:

- missing provenance, naive or date-only times, an evidence record time before its fetch, and
  origin URIs with userinfo credentials;
- an excerpt without the rights that permit it, and text containing NUL;
- decimals PostgreSQL would round or overflow (scale 18, 20 integer digits) and confidences
  outside 0 to 1 with at most four places;
- a `source_empty` reason without `change_kind: emptied`, a changed or emptied claim without its
  predecessor, a decided claim without its review decision, evidence from another source, and an
  empty or reversed validity interval.

Keys are the shared `content_version` digest of the identifying columns. Recording times are
first-seen columns outside the key, so rerunning the same raw record with the same code yields the
same evidence ID and claim key. Any change to code digest, locator, source version, conditions or
value gives a new key. A confirmation is keyed by claim, source version and fetch.

## Idempotent writes

`kn.evidence.store.record(connection, records, tables=None)` writes rows and the evidence they
embed inside a savepoint of the caller's transaction and returns the number of new rows. An existing
key is a no-op; if its stored content differs, excluding first-seen and projection-owned columns,
the whole batch fails. `evidence_tables(schema)` compiles the tables once per schema. The writer
inserts and then reads back each row.

## As-of views

`kn.evidence.asof` returns deterministic SQLAlchemy selects:

- `claims_as_of(claims, knowledge_time, valid_time)`: claims recorded by the knowledge time that
  no successor recorded by then supersedes, ordered by KN ID, field ID and key;
- `facts_as_of(facts, knowledge_time, valid_time)`: the fact version whose half-open knowledge
  interval holds the time;
- `relations_as_of(relations, knowledge_time, valid_time)`: assertions open at the time.

A null knowledge time gives the current view. A null valid time applies no validity filter. A null
validity bound is unknown or open and never excludes a row.

## Multilingual text

`kn.evidence.text.Translation` attaches derived text to one text claim.
`source_text(claim_row, translation_rows)` rebuilds a `SourceText` whose original keeps the claim's
text, language tag and `claim:<key>` provenance; `display(..., locale)` applies the shared
[selection policy](localization.md#source-data-and-translations). Translations never create claims
or facts, so a fact key does not depend on the locale. Duplicate languages, including the
original's, and translations of another claim fail.

## Retired concepts in claims

`kn.evidence.concepts.concept_uses(rows)` maps each concept a claim states as its value to
`claim:<key>` references. `retired_concept_claims(snapshot, rows)` passes them to the
[lifecycle report](ontology-taxonomy.md#lifecycle-report), so a claim citing a deprecated or replaced
concept appears as an external use with the end of the replacement chain. Units and conditions
keep their own identifiers and are not concept citations.

## Selection and review shapes

`kn.evidence.facts.CanonicalFact` keys a fact by KN ID, field, condition set and audience
(`fact_key`) and a version by its content and knowledge start. `knowledge_to` is the only column a
later writer changes. A conflict or pending review names its review item; an owner override needs
a selected claim. `SelectionOutcome` records every evaluated claim, including `ignored` ones.
`kn.evidence.policy` reads a field's `kn.updatePolicy` as `UpdatePolicy` with a canonical
`digest`, gives rank and evidence-class orders from their vocabularies, and records ranking inputs
as `Criteria`. `kn.evidence.relations` and `kn.evidence.reviews` define assertions, supports,
review items and decision events; decision IDs bind the canonical event. Selection semantics,
review authentication and decision journals come with their plan tasks.

## Human verification of claims and facts

`kn.evidence.verification.target(record, purpose)` builds the record-scope target of a row from the
contract's declared coverage. Its version is the content digest that `ContractResolver` computes
from the stored row. A changed claim is a new row and target, and a fact that selects another
claim is a new version, so neither inherits an earlier decision. An imported
`source_verification_label` such as `verified` is ordinary content and leaves the stamp null.

## Human verification contracts

`kn.review.model` defines immutable, extra-field-refusing `Target`, `Request`, `Decision` and
`Stamp` models. Their [wire schemas](../../../contracts/core/evidence/README.md) are checked against
the models. The registered `kn.core.human_verification` ODCS contract owns
`evidence.human_verification_decisions`; `make contract-compile` derives its SQLAlchemy, PostgreSQL,
dbt and engine artifacts. This adds one table and eight fields to the previous 50-table,
465-field registry. The development contract version stays `1.0.0`.

A target binds contract ID, dataset, a complete typed primary key, exact content digest,
record/field scope, stable field ID for field scope, and purpose. Purposes are `factual`,
`publication`, `terminology`, `integrity` and `workflow`; they never grant each other's approvals.
Keys are sorted by stable field ID. Strings retain leading zeroes and locale components;
integers, booleans, decimal strings, complete dates and offset timestamps have distinct types.

`human_verified_at`, `human_verified_by` and `human_verification_decision_id` are all null or all
present. An accepted exact target supplies the original performed UTC instant, authenticated
principal and durable event ID. Unknown, changed, rejected, revoked and conflicted targets do not
acquire an acceptance stamp. Row and field decisions remain independent. Historical lookup of an
old version retains its original result; it is not a current-version approval.

## Coverage and target resolvers

The table extension `kn.humanVerification` declares `strategy` (`external` or `decision-log`),
`resolver` (`contract-v1`), `recordFields` and `fieldContexts`. Fields use stable contract field IDs;
a field context must contain its reviewed value plus meaningful units, conditions, locale and
other context. The compiler rejects unknown IDs or incomplete contexts and retains declarations
in generated artifacts. A decision-log declaration describes a technical audit record without
automatically approving the decision or its payload.

`declared_coverage(contract)` reads declarations as `Coverage` values. `ContractResolver` accepts
explicit coverage and registered contracts, refuses unknown datasets/fields and incomplete or
mistyped keys, locks the target row, then checks `content_version()` against the declared content.
The digest includes explicit nulls and exact decimal/date/timestamp values. Custom resolvers can
implement `TargetResolver` for immutable artifacts or derived values, including their model,
inputs and window. Declared content must include meaningful revision/context fields; the resolver
cannot infer omitted provenance. Verification annotations and transport counters stay outside
reviewed content. Missing coverage grants no implicit verification support.

All-table declarations, current metadata joins, invalidation across restore/identity operations,
rights filtering, exchange trust/loss reporting and coverage registration gates belong to the open
`human-verification-projections` task. The protocol is available for explicit fixture targets;
this does not claim that all registered rows already expose human verification metadata.

## Trusted decision application

`kn.review.store.submit(connection, journal, resolver, request, authenticate, clock)` is the shared
write entry point for covered workflows. `authenticate` supplies a trusted `Reviewer` independently
of request data. It must establish a human principal and authorization for the target purpose;
agent, import and unauthenticated contexts are refused. Requests cannot supply a reviewer,
recording time, acceptance stamp or source `verified` attribute. The
[identity CLI](object-identity.md#operator-lifecycle-commands) uses local terminal approval for
its workflow decisions. The general review queue and broader operator authorization remain planned.

Performed times require explicit offsets and normalize to UTC. Date-only, naive, invalid and
future performed times relative to the trusted recording clock fail. Recording time remains
separate. The SHA-256 decision ID binds the normalized event, including reason, evidence reference,
request ID and schema version. No backfill invents a date or actor.

The caller owns a short PostgreSQL READ COMMITTED transaction. A transaction advisory lock
serializes submissions before a row lock and journal lock; a savepoint prevents partial SQL
application even when the caller catches a failure. Same-principal/request-ID retries preserve the
original event and recording time. Reusing that key for different content fails. SQL rows are
inserted idempotently, with a unique request key; the API never updates or deletes an event.

## Durable history and conflicts

`Journal(data_dir)` writes private, fsynced, ASCII JSON Lines to
`$DATA_DIR/decisions/human-verification-v1.jsonl`, independently of disposable SQL schemas.
File locking covers validation, deduplication and append; the file and directory entry are synced
before SQL application. Symlink paths, malformed/torn lines, incompatible versions, missing or
cross-target predecessors and conflicting request IDs fail closed. Restore a damaged journal
before retrying; the protocol never silently truncates history.

Only operator-owned local journals are trusted for replay. A reviewer string or a valid content
hash in imported data does not establish authority. SQL and journal access are internal trusted
application boundaries; filesystem or database administrator tampering is outside this protocol.

Events form a causal graph, independent of input or wall-clock ordering. Accept, reject, revoke
and supersede retain history. Multiple live heads expose `conflict` with null metadata, including
conservative handling of independent approvals. An explicit `supersede` event can consume every
conflicting head and create a new acceptance. Partial supersession leaves a conflict. Revoke and
supersede require predecessors; an ordinary acceptance cannot consume multiple branches.

A durable append can survive a failed or rolled-back SQL transaction. It represents a pending
projection, not lost history. `replay_target(connection, journal, resolver, target)` restores one
known exact target with its original actors, dates and IDs. `projection(connection, target)` is an
exact-version historical lookup; resolve a current target before exposing it as current metadata.
Automatic all-target rebuild integration and pending/orphan/stale reports remain projection work.

## Known limitations

- Cross-contract references are checked by the owning engines, not SQL foreign keys.
- The loader role can still update claim rows; the writer never does, and a re-insert detects
  changed content under a stored key.
- Condition and qualifier objects are canonical JSON; approved condition field IDs arrive with
  domain contracts.
- Partial-update tracking, canonical selection, review queue journals and the lineage command are
  open plan tasks.

## Verification

- `tests/evidence/` checks contract enums against the Python vocabularies, wire validators for a
  row of every table, deterministic keys, refused provenance and value cases, multilingual
  fallback without fact duplication, retired-concept reporting, policy digests and
  version-bound verification.
- `tests/integration/test_evidence.py` checks database rejections, no-op re-inserts, tampered
  rows, provenance lookups, permuted as-of views, one current fact and no active duplicate
  relation. `test_evidence_verification.py` checks stored-claim targets, stale content and
  unreviewed changed or labeled claims. The combined model baseline loads every evidence table as
  the evidence loader.
- `tests/review/` checks typed composite and locale targets, scope/purpose separation, key types,
  null completeness, UTC and clock errors, actor refusal, event digests, graph conflicts,
  revocation, retry identity, wire schemas and ODCS coverage validation.
- `tests/integration/test_human_verification.py` checks PostgreSQL concurrency, repeated requests,
  stale/unknown targets, transaction rollback, caught application failures and exact replay.
- `tests/integration/review_fixtures.py` adds a composite-key semantic label review to
  `make model-baseline`. Two fixture rebuilds retain identical stored events and projections.
- `make ci` checks generated-contract drift, typing, lint, complexity and deterministic tests;
  `make ci-local` adds database service and other local acceptance checks.

Acceptance evidence and task counts are retained in
[record 0032](../records/0032-evidence-model-human-verification-contracts.md) and
[record 0044](../records/0044-evidence-model-evidence-claim-contracts.md).
