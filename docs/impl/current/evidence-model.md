# Evidence Model

The evidence contracts and the shared human verification protocol are implemented. Claims,
evidence, confirmations, aliases, translations, relation assertions, canonical fact versions,
selection outcomes, review items and review decisions have registered storage, deterministic keys,
database constraints and as-of views. [Partial-update tracking](object-identity.md#partial-update-tracking)
writes claims and confirmations into these shapes, and [canonical selection](#canonical-selection)
projects each field's value from them through its update policy. Every registered dataset exposes
current human verification metadata through the
[shared read projection](#current-verification-reads). The
[operator review queue](#operator-review-queue) is available; the ingestion engine remains
planned.
The [lineage lookup](object-identity.md#lineage-lookup) reads these rows through
`kn.evidence.lineage`, withholding and counting what an audience's rights do not permit.
Existing source verification labels retain their meanings and grant no human timestamp.

## Evidence contracts

The registered `kn.core.evidence` ODCS contract,
[`resources/evidence/claims/1.0.0.json`](../../../src/kn/contracts/resources/evidence/claims/1.0.0.json),
shares the `evidence` schema with `kn.core.human_verification`. It defines 11 tables and 148
fields at development version `1.0.0`.
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
`kn.evidence` on claims, and shared `kn.humanVerification` on every table; review decisions
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
review items and decision events; decision IDs bind the canonical event. The
[operator queue](#operator-review-queue) authenticates reviewers and journals their decisions.

## Canonical selection

`kn.evidence.selection.select(subject, claims, policy, context, knowledge_from, previous, retired)`
returns the fact version, its review items and one explained outcome per evaluated claim, or None
when no claim is eligible. A `Subject` is a KN ID, stable field ID and canonical condition set; the
`Context` supplies the rank table, audience, accepted reviews and an optional redirect resolver.
Selection evaluates every claim of the subject at once with total orders over claim content, so
the input or arrival order never changes a value. Claims that a recorded claim supersedes are
history; they are not evaluated. `retired` names claims that a claim of another subject
superseded, such as a correction that moved the value to another condition set. An emptied claim
states no value, so it may carry another condition set than the predecessor it follows.

Ranks come from `kn.evidence.ranking.RankTable.read()`, which reads the reviewed
[rank table](../../../contracts/core/policies/source-ranks.yaml). A `field_group` override applies
to the stable field IDs equal to it or below it at a dot boundary (`microelectronics.offer` covers
`microelectronics.offer.unit_price`). The longest matching group wins over a source-wide override,
and an unlisted source is `unranked`. A claim named by an accepted review selection, or a
`decided` claim whose decision is accepted, ranks `owner_entered`.

A claim is eligible when its evidence rights are permitted for the `Audience` (`internal` permits
all), it is not a signal (`gdelt:` sources) or an `extracted_candidate`, whatever the policy
minimums say, it is not rejected, a `decided` claim has its accepted decision, and it meets the
minimum rank and evidence class. A missing reason other than `source_empty` is not a value.
Ineligible claims are explained as `ignored` with the criterion that excluded them; claims the
audience may not see are left out of the explanation entirely. A fact key includes the audience.

Claims whose values agree within `valueTolerance` (numbers in one normalized unit, other values
when equal) support one candidate. Agreement within a tolerance is not transitive, so a claim joins
a candidate only when it agrees with every claim already in it: two equal-rank claims that differ
by more than the tolerance always conflict, whichever values and dates lie between them. Numbers in
different normalized units, or without one, never agree; at equal rank they conflict, and on a
`fixed` field they open review. Text agrees only when it is identical, including its language tag.
A candidate ranks by its best claim, so repetition and confirmations add no rank. At equal
strength a reviewed claim represents its candidate. Object values follow merge redirects before
they are compared.

| Mode | Rule as implemented |
| --- | --- |
| `priority` | Declared `priorityCriteria` order of source rank and evidence class. Data time decides tied candidates only when one source states all of them and every time is known. Otherwise the tie is a `conflict` with a `fact_conflict` item and no selected claim. |
| `latest_observed` | Newest data time on the policy's `timeBasis` first, then the declared criteria; an unknown time sorts last. `stale(fact, policy, at)` returns the winner's age once it exceeds `freshnessSeconds`; zero declares no limit. |
| `accumulate` | Every eligible candidate is a member (`Selection.members`); the fact row names the best one and each member's outcome is `filled`. A record's newer version supersedes its own earlier item, and an item leaves when no current claim supports it or it is rejected. |
| `fixed` | The candidate with the earliest data time, or observed time, holds. A different value is `conflict` with a `fixed_value_change` item naming the challengers, and the held claim stays selected. An accepted review selection holds instead, the most recently accepted one first, and settles claims recorded by the decision. Different values that share the earliest time, or the latest review, hold nothing: the fact is `conflict` with a `fixed_value_change` item (`fixed_values_tie`) naming every candidate. |

An empty claim never fills. When an eligible `source_empty` claim outranks the current leader, or
no other value exists, its predecessor stays a candidate and an `empty_claim` item opens, unless
`emptyValueHandling: allow_clear` or an accepting review gives `unresolved_reason: cleared`. Under
the default `review` handling the same holds when it retracts a value that the leader neither
outranks nor agrees with, so an equal-rank retraction never settles a conflict and a retracted
newest revision never brings back an older one silently; under `allow_clear` such a retraction
takes effect and the leader stands. A rejected empty claim restores its predecessor without
review. An empty claim is ignored when the leader outranks or agrees with the value it retracts.

The optional `kn.updatePolicy` member `highImpact` marks rule-6 fields. Their value needs a
primary claim or an accepted review; otherwise the fact is `review_pending` with a `high_impact`
item. An owner-entered winner over a differing first-party candidate sets `owner_override` and
opens an `owner_override` item until a review accepts the owner claim. The fact names the most
urgent open item: conflict, fixed change, empty claim, then high impact.

Verification is `disputed` for an open conflict, fixed change or empty-claim review, `verified` when
the selected claim is the one an accepted review chose, `corroborated` for support from two or
more sources, and `unreviewed` otherwise. Source labels and human verification timestamps never
rank, verify or resolve a claim. Applied review outcomes give each claim the time of the latest
active decision about it, whatever order storage returns the events in. A claim rejected in one
review item stays ineligible, even if another item later accepts it, until that rejection is
revoked or superseded.

`previous` explains the change: `filled` when the previous version had no selected value,
`replaced` when the new value differs, `corroborated` when it agrees, and `conflict` for open
conflicts, fixed changes and empty-claim reviews. Clearing is `replaced`. Under `accumulate` a new
member fills and a departed one replaces.

## Fact projection

`kn.evidence.projection.subjects(claims, resolve)` groups claims by subject under their terminal
survivor, using `State.resolve` from the identity registry. An emptied claim joins its
predecessor's subject. A claim about a split object names no single subject and is returned as
unattributed. `successors(claims)` gives, for each superseded claim, when its first successor was
recorded, whatever that successor's subject.
`history(subject, claims, policy, context, superseded)` replays selection at every claim
recording time of the subject, every time a decision about its claims changes and every time
`superseded` retires one of them, using only decisions recorded by then. It returns `Version`s with
half-open knowledge intervals. Decisions about other claims add no replay, so the cost of a
subject does not grow with the size of the review log. Pass `successors` of every stored claim,
as the review CLI's refresh does. A claim that changes nothing a version states, such as an
ignored claim or a new runner-up, adds its outcome to that version and leaves no new version.
The version's outcome, deciding criterion and runner-up therefore describe the comparison when it
opened, and its outcome rows include claims evaluated while it stayed current, also those later
superseded. Review item keys stay stable while their candidates do not change.

`write(connection, versions, tables)` stores the history in a savepoint of the caller's
transaction: it sets `knowledge_to` on stored versions, then writes items, facts and outcomes
idempotently. A stored version of the same fact that the history does not contain, for example
after a policy change, refuses the write; the projection is rebuilt rather than patched.

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

All 73 deployed tables declare `kn.humanVerification`, including the 50 tables in the
[original inventory](../records/0028-adhoc-human-verification-model-review.md). The extension
declares `strategy` (`external` or `decision-log`), `resolver` (`contract-v1`), `recordFields`
and `fieldContexts`. With
`defaultFieldContext: record`, every field includes its record's declared content and its own
value. An explicit `fieldContexts` entry can define a narrower context. Fields use stable IDs;
a field context must contain its reviewed value plus meaningful units, conditions, locale and
other context. The compiler rejects unknown IDs or incomplete contexts and retains declarations
in generated artifacts. Registry validation refuses any table without a strategy and a context
for every field. The combined baseline requires representative replay fixtures for every owner
and table. A decision-log declaration enables explicit review of an audit record on its own scope.

`declared_coverage(contract)` reads declarations as `Coverage` values.
`ContractResolver.registered(contracts)` builds the deployed resolvers from those declarations.
It refuses unknown datasets/fields and incomplete or
mistyped keys, locks the target row, then checks `content_version()` against the declared content.
The digest includes explicit nulls and exact decimal/date/timestamp values. Custom resolvers can
implement `TargetResolver` for immutable artifacts or derived values, including their model,
inputs and window. Declared content must include meaningful revision/context fields; the resolver
cannot infer omitted provenance. Verification annotations stay outside the digest. Advancing
`source_records.last_seen` preserves the record stamp, while an explicit review of that field
binds its own value.
An identity object's `revision_event` binds its current lifecycle revision even when a restore
returns the state to its previous value.

## Current verification reads

Use `resolver.dataset(contract_id, table_name)` to get a dataset and
`dataset.target(stored_row, purpose, field_id=None)` to build a review request for its typed
content. The known primary key includes locale for semantic labels and the package's
`import_id` for SATCOM. A changed SATCOM package has a different snapshot key even if some
cells match the preceding package.

`kn.review.projection.read(connection, dataset, key, purpose, rights=...)` returns
`VerifiedRow` with column-name `values`, a record `Stamp` and field `Stamp` values keyed by
stable field ID. The key is a tuple of `KeyPart` values, available from `dataset.key(stored_row)`.
Choose the review purpose explicitly. A field decision leaves the record and sibling field
stamps null. The read computes versions from the values it returns and batches exact-target
decision lookup for the row. Unreviewed fields, including explicit null values, expose the
three nullable metadata fields.

The trusted application supplies `ReadRights` for the audience. Its `data(dataset, row, field_id)`
check authorizes the row with `field_id=None` and then authorizes each field. Missing or denied
rows return `None`; denied fields are omitted. Stamps require access to every field in their
declared context and access to the reviewer and evidence of every decision in the exact-target
history via `decision(event)`. The same decision check protects a decision-log row's payload.
A hidden branch cannot reveal its existence through a timestamp, principal, decision ID or count.

## Trusted decision application

`kn.review.store.submit(connection, journal, resolver, request, authenticate, clock)` is the shared
write entry point for covered workflows. `authenticate` supplies a trusted `Reviewer` independently
of request data. It must establish a human principal and authorization for the target purpose;
agent, import and unauthenticated contexts are refused. Requests cannot supply a reviewer,
recording time, acceptance stamp or source `verified` attribute. The
[identity CLI](object-identity.md#operator-lifecycle-commands) uses local terminal approval for
its workflow decisions. The review CLI uses the same local-account and controlling-terminal
boundary. Broader service authentication remains outside this local operator workflow.

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
`Journal(data_dir, domain)` uses `$DATA_DIR/decisions/<domain>/human-verification-v1.jsonl`;
new CLI decisions use this path, with `core` as the default domain. Existing root-level logs
remain readable, and old events retain their hashes. Domain slugs cannot escape this directory.
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

A durable append can survive a rolled-back SQL transaction. Run
`kn.review.store.replay(connection, journal, resolver)` after loading targets in a caller-owned
transaction. Exact matches replay with their original actors, dates and IDs. Absent records are
`pending`, or `orphan` when the caller sets `complete=True` after restoring all inputs. Changed
versions report `stale`, and unknown datasets, fields or key definitions report `incompatible`.
Unresolved decisions remain in the durable journal. A SQL failure rolls back the replay batch.
`replay_target` restores a single known target. `projection(connection, target)` is a trusted
exact-version lookup in the installed SQL history, while the journal retains every prior event.

The development rebuild replays identity history and reviewed seeds before restoring matching
reviews. SATCOM import then replays reviews for restored SATCOM snapshots and any restored
decision-log targets. The normal commands publish nonempty reports after commit under
`$DATA_DIR/human-verification/<run-id>/replay.json`. JSON command output includes its path as
`verification_replay`. The report carries contract ID, dataset, target digest and replay state for
each target. The durable journal has the full events. Restoring other inputs can be followed by
another replay; the raw engine and external exchange paths have their own planned work.

## Operator review queue

`kn review list`, `kn review decide` and `kn review replay` operate on the configured PostgreSQL
connection (`KN_DATABASE_URL` and its password file) and `DATA_DIR`. A relative `--data-dir` resolves
from the project root. The queue is an internal operator read surface: its claim values, provenance,
identity features and reviewers are not an audience-filtered export. English output escapes source
text; `--json` uses stable, ASCII JSON keys.

```bash
kn review list --json
kn review list --overrides
kn review decide --domain microelectronics --item ITEM_ID --select CLAIM_KEY \
  --outcome accept --request-id review-42 --performed-at 2026-11-26T12:00:00Z \
  --reason "Compared the cited evidence" --evidence review:42
kn review replay --json
```

`list` includes deterministic item IDs, registered kinds, candidates, exact target scope/version,
state, current causal heads and verification metadata. Fact items include the reviewed claim rows;
identity items include scored features and profile versions. Historical settled items remain
visible. `--overrides` limits queue items to owner overrides and also returns every current
canonical fact flagged `owner_override`, including one whose item is already settled. Source dispute
rates count distinct reviewed claims per source: an explicitly rejected candidate or a nonselected
candidate in an accepted choice is disputed. Revoked and conflicted heads contribute no current
assessment; duplicate events never inflate counts. Rates support manual rank-table review and do
not change ranks themselves.

Queue kinds come from the evidence contract's review-kind vocabulary. Fact conflicts, fixed-value
changes, empty claims, high-impact values and owner overrides consume claim candidates. Identity
matches and drift consume durable match events. Relation candidates and quarantine can record a
workflow acceptance or rejection; their future domain producers supply their own operational
side effects through this registered seam.

`decide` takes an exact item or a verification target, an outcome (`accept`, `reject`, `revoke`, or
`supersede`), reason, evidence reference, exact performed time and request ID. A fact decision also
requires `--select`, including when rejecting a candidate. `--predecessor DECISION_ID` is repeatable;
use it to replace or revoke a decision, or consume all conflicting heads with `supersede`. Subsequent
decisions on a target stay in its original domain log. Same-reviewer/request-ID retries preserve
the original event; cross-domain request-ID reuse fails.

The CLI obtains the principal from the local OS account. It requires private operator-owned
storage and explicit `yes` on `/dev/tty`, displaying the escaped reviewed values and the exact
request, scope and version before application. Neither source data nor flags can supply a reviewer.
An agent or redirected stdin cannot approve a human decision. Unavailable or declined local
approval returns `E_REVIEW_AUTH`; invalid input returns `E_INPUT`, and SQL failures return
`E_DATABASE`. Listing and replay do not create human acceptance.

Fact decisions append a shared decision and an evidence `review_decisions` row. A selected existing
claim ranks `owner_entered` through `kn.review.selection.accepted_reviews(applied_events)`;
rejections exclude the named claim. The result retains historical snapshots for `Reviews.at`, so
revocation removes current acceptance without rewriting earlier canonical versions. Concurrent
independent heads grant no selection until resolved. Workflow acceptance stamps the exact review
item; it does not approve every candidate or manufacture a factual timestamp on its claim rows.
Record/field factual verification uses the independent exact-target interface below.

An accepted identity choice registers the source link, authoritative keys and normalized identity
attributes using the original journaled observation and profile. Changed discriminating attributes
on an existing source link open `identity_drift` review; they do not silently replace identity data.
Authority already held by another object must be resolved before accepting a conflicting choice.
Decisions are fsynced before identity effects and SQL projections, and retries recover interrupted
batches. An unapplied choice for a source record with a newer match observation is stale and
requires review of that newer observation. Identity effects retain their decision reference and
are validated on identity replay.
Rejecting or revoking the workflow acceptance clears its stamp; an already recorded identity link
remains a historical operation. Correct ownership through a new reviewed choice or the explicit
identity lifecycle commands, rather than deleting history.

### Record and field verification

Prepare a target with `kn review list --target QUERY.json --json`. The query contains
`contract_id`, `dataset`, complete typed `key`, `purpose`, and optional stable `field_id`:

```json
{
  "contract_id": "kn.core.semantic",
  "dataset": "namespace_labels",
  "key": [
    {"field_id": "semantic.namespace_labels.namespace_id", "kind": "string", "value": "space.demo"},
    {"field_id": "semantic.namespace_labels.locale", "kind": "string", "value": "en"}
  ],
  "purpose": "terminology",
  "field_id": "semantic.namespace_labels.label"
}
```

Omit `field_id` for a record review. Save the returned `target` object as `TARGET.json`; submit it
with `kn review decide --target TARGET.json` and the same decision options above, without
`--item` or `--select`. The target carries its exact version; the command refuses changed contents
instead of approving the latest row implicitly. The result and read projections expose a nullable
stamp only for active acceptance of this exact purpose, scope and version. Rejection, revocation,
a content change or competing heads leave the stamp null and retain all events. A field approval
does not approve the row or sibling fields.

### Reattachment and verification

After restoring claims and their review items, run `kn review replay`. It reads root and domain
journals, reapplies exact matches idempotently and reports each decision as `applied`, `orphan`,
`stale`, or `incompatible`. A missing claim candidate is an orphan even if its queue row survives.
Unresolved events remain in the log. `list` reports unattached events without applying them.
A decision whose SQL transaction failed can be recovered with replay, retaining its original actor,
times and ID. Automatic replay after raw restoration remains owned by `rebuild-from-raw`.

Verification is network-free: `tests/review/` covers protocol, causal selection, safe paths and
English/JSON goldens; `tests/integration/test_review_queue.py`,
`test_review_recovery.py`, `test_review_refresh.py`, `test_identity_review_recovery.py` and
`test_review_operator.py` cover SQL effects, rollback recovery,
two rebuilds, missing claims, scope isolation, actual CLI approval and override listing.
Run these against `make db-up`, then `make ci`. The acceptance commands and implementation findings
are in [record 0052](../records/0052-evidence-model-review-queue-cli.md).

## Known limitations

These include the accepted and scheduled findings of the
[evidence model audit](../records/0053-evidence-model-evidence-model-implementation-audit.md#findings).

- Cross-contract references are checked by the owning engines, not SQL foreign keys.
- Legacy identity review events without the original observation/profile cannot register complete
  identity evidence. Resolve a fresh observation before accepting them. Reopen migration support
  if an operational legacy backlog needs it.
- Queue listing scans stored items, matches and decisions. Pagination and service authentication
  remain future operator-service work; revisit this when measured queue size makes the local
  workflow slow.
- The loader role can still update claim rows; the writer never does, and a re-insert detects
  changed content under a stored key.
- Condition and qualifier objects are canonical JSON; approved condition field IDs arrive with
  domain contracts.
- Domain field policies still arrive with domain contracts. No deployed contract currently declares
  `kn.updatePolicy`; the queue stores decisions and exposes applied `Reviews` without inventing a
  policy. The CLI refreshes canonical histories for fields with a registered policy. Fixture tests
  exercise selection with explicit policies.
- Fact history uses current identity resolution for every version; facts stored under a KN ID
  that was later merged are not closed automatically. Rebuild the projection after a merge. The
  [lineage lookup](object-identity.md#lineage-lookup) reports such a fact as
  `fact_subject_superseded`.
- A curated claim ranks by its own `source_id`. Ranking it as the source it cites arrives with
  `curated-source-method`.
- Corroboration counts distinct `source_id` values; syndicated copies under different source IDs
  are not detected.
- A fact version's outcome, deciding criterion and runner-up describe it when it opened, so they
  can differ between arrival orders that end in the same canonical value, items and members. A
  later claim that changes nothing else adds an outcome row instead of a new version, so every
  current claim has a row on the current version. Read competing values from those rows, without
  claims superseded by the as-of time. Reopen this if an analyst view needs the strongest
  competitor stored on the fact itself.
- Text agreement is exact. The same text in another Unicode normalization form, or with a
  differently cased language tag, opens a conflict instead of corroborating. Reopen this when a
  source fixture shows such conflicts in review.
- A rejection of a claim in one review item outlasts a later acceptance of the same claim in
  another item until the rejection is revoked or superseded. This keeps a rejected claim out of
  selection; reopen it if operators report accepted choices that have no effect.
- `kn review decide` and `kn review replay` refresh every subject whose field declares a policy.
  A subject replays only at its own claim and decision times, about 2 ms per subject with 1,000
  unrelated decisions in the audit probe. Reopen this when refresh time is measurable against the
  operator workflow at the declared volume.
- Tracked claims carry no event, published or valid time, and a delivery states each field once.
  The `valid_from` and `published` time bases therefore see no data time on a tracked claim, and
  a record can claim only one item of an `accumulate` field. `tracked-claim-times-and-sets` adds
  both.

## Verification

- `tests/evidence/` checks contract enums against the Python vocabularies, wire validators for a
  row of every table, deterministic keys, refused provenance and value cases, multilingual
  fallback without fact duplication, retired-concept reporting, policy digests and
  version-bound verification.
- `tests/integration/test_evidence.py` checks database rejections, no-op re-inserts, tampered
  rows, provenance lookups, permuted as-of views, one current fact and no active duplicate
  relation. `test_evidence_verification.py` checks stored-claim targets, stale content and
  unreviewed changed or labeled claims, including numeric fields with new units or conditions.
  The combined model baseline loads every evidence table as the evidence loader.
- `tests/evidence/test_selection.py`, `test_candidates.py`, `test_selection_modes.py` and
  `test_projection.py` check every outcome, mode and verification state of the update policy:
  fill, replace, ignore, owner override, support by a higher-ranked source, repetition,
  same-source revisions, equal-rank conflict, stale prices, fixed-field review and ties, accepted
  challengers, empty claims and equal-rank retractions, high-impact gating, eligibility, audiences,
  tolerance chains, reviewed representatives, merge survivors, distinct entity classes and every
  arrival permutation of two five-claim sets in all four modes, one with an equal-rank
  disagreement, a unit mismatch and a retraction.
  `test_projection_corrections.py` checks corrections and retractions across condition sets and
  that decisions about other claims add no replay. `tests/integration/test_evidence_selection.py`
  writes histories to PostgreSQL, checks as-of views and closed versions, idempotent rewrites and
  drift refusal. `tests/integration/test_review_refresh.py` checks that applied decisions
  reproduce every projected fact, outcome, item and decision row after two rebuilds.
- `tests/review/` checks typed composite and locale targets, scope/purpose separation, key types,
  null completeness, UTC and clock errors, actor refusal, event digests, graph conflicts,
  revocation, retry identity, wire schemas and ODCS coverage validation.
- `make model-baseline` tests unreviewed reads across all registered tables, semantic locale isolation,
  SATCOM snapshot isolation, unchanged re-import, exact dates, reviewers and decision IDs
  across two rebuilds, and byte-for-byte preservation of source cells and archived files.
  PostgreSQL tests additionally cover restricted reviewers/evidence, unresolved replay and
  identity restoration. [Acceptance record](../records/0051-evidence-model-human-verification-projections.md).
- `tests/integration/test_human_verification.py` checks PostgreSQL concurrency, repeated requests,
  stale/unknown targets, transaction rollback, caught application failures and exact replay.
- `tests/integration/review_fixtures.py` adds a composite-key semantic label review to
  `make model-baseline`. Two fixture rebuilds retain identical stored events and projections.
- `make ci` checks generated-contract drift, typing, lint, complexity and deterministic tests;
  `make ci-local` adds database service and other local acceptance checks.

Acceptance evidence and task counts are retained in
[record 0032](../records/0032-evidence-model-human-verification-contracts.md),
[record 0044](../records/0044-evidence-model-evidence-claim-contracts.md),
[record 0046](../records/0046-object-identity-canonical-fact-selection.md),
[record 0051](../records/0051-evidence-model-human-verification-projections.md),
[record 0052](../records/0052-evidence-model-review-queue-cli.md) and the
[implementation audit, record 0053](../records/0053-evidence-model-evidence-model-implementation-audit.md).
