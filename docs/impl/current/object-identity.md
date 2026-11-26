# Object Identity

The identity storage contract, durable journal, deterministic replay with incremental writes,
reviewed lifecycle commands, profile-driven matcher, field-level partial-update tracking and the
[lineage lookup](#lineage-lookup) are available and passed the
[object identity audit](../records/0049-object-identity-object-identity-implementation-audit.md).
Real-record calibration and fragment claims after a split remain in the [plan](../plan.md).

## Operator lifecycle commands

`kn identity show KN_ID` shows the requested object's class, state, anchor, mint event, terminal
successors, and current holdings. `kn identity resolve KN_ID` returns the terminal IDs in sorted
order, including multiple successors after a split. An active or retired object without a
successor resolves to itself. `kn identity history KN_ID` returns events involving the object
or its successor paths in journal order, with their original actor, time, evidence and decision
reference. These commands read the durable identity journal, including any event pending SQL
projection.

| Command | Operation |
| --- | --- |
| `identity merge KN_ID SURVIVOR` | Move current holdings to a distinct active object of the same class. |
| `identity split KN_ID SUCCESSOR SUCCESSOR ... --assign ITEM=KN_ID` | Assign every current link, identifier and attribute once. Repeat `--assign` with the holding's `event_id` from `show`. Use existing same-class active successors. |
| `identity retire KN_ID` | Retire the object and close its current links. |
| `identity restore KN_ID` | Return a retired object without a successor to the active state. Closed links remain historical. |
| `identity reclassify KN_ID ENTITY_CLASS --anchor-source SOURCE --anchor-key KEY` | Retire the old ID and mint a new-class successor in one event. Use an anchoring source key that has never minted an object. Current holdings move to the successor. |

Each mutation requires `--request-id`, `--performed-at` (an ISO 8601 instant with offset),
`--reason` and `--evidence` (a supporting reference). Review the displayed proposal on the
controlling terminal and enter `yes` to approve. The local Unix account supplies the reviewer
identity as `local:<account>`. The account must own `DATA_DIR` and the existing journal directories
and files, with group and other write permissions disabled. Give unattended workers separate
accounts that lack those permissions. The local protocol trusts the journal owner and processes
with equivalent access. Writes also require `KN_DATABASE_URL`, its configured password or password
file, and the identity and evidence loader privileges on an upgraded database.

`kn identity --data-dir PATH ACTION ...` overrides `DATA_DIR`; relative paths resolve from the
project root. When using a project's `.env`, load it with `scripts/shared/common.sh` and
`kn_load_env` before running the CLI. Help, headings, confirmations and diagnostics use English.
Use `--json` for structured output.
Success for a mutation returns the full identity event and `decision_id`. Input or transition
errors report `E_INPUT`, terminal or owner refusals report `E_IDENTITY_AUTH`, and SQL errors report
`E_DATABASE`. While a source adapter's interrupted match waits for its retry, a mutation reports
`E_INPUT` before the confirmation prompt and writes no review decision. Rerun the adapter first.

Merge, split and reclassification preserve the original link ID and source record ID while
changing link ownership. Later claim lineage can follow that source record through the move.
The original link and every move remain in history.

## Lineage lookup

`kn lineage REFERENCE [--field FIELD_ID] [--audience NAME] [--permit RIGHTS ...]` traces an object
or one field to every record and decision behind it. `REFERENCE` is a KN ID or a qualified
identifier `NAMESPACE:VALUE`, such as `inventree:vl-itree:part:42`; every colon is tried as the
separator, and an identifier held by more than one object, or by none, reports `E_INPUT`. The
command reads the identity journal, resolves the reference before it opens the database, and then
reads the evidence schema in a PostgreSQL read-only transaction. It needs `KN_DATABASE_URL` and
its password or password file; an unavailable database reports `E_DATABASE`. `--data-dir`,
and `--json` behave as for `kn identity`. The text output gives English section headings with
counts followed by canonical JSON rows.

A lookup covers the reference's terminal successors and every object that redirects to them, so a
merged ID shows its survivor's lineage with the merge event, and a split ID shows both
successors. The view lists, in this order:

| Key | Content |
| --- | --- |
| `objects` | Class, state, anchor, mint event, successors and terminal IDs of each covered object |
| `history` | Mint, unlink, merge, split, reclassify, retire and restore events with actor, reason, evidence and decision reference |
| `identifiers`, `attributes`, `links` | Holdings of covered objects: the original `kn_id`, the current `owner`, the recording event and, for links, the record, method, score, match ID and closing event |
| `matches` | Match records for linked records or naming a covered object, with candidates, features, decision and trace |
| `records` | Linked and claimed source records with `last_seen` and every version: fetch ID, archive record ID, code digest, field hashes, change set and later sightings |
| `claims`, `confirmations`, `evidence` | Claims about covered objects in field and recording order, their confirmations, and the evidence rows both cite |
| `facts`, `outcomes`, `review_items`, `review_decisions` | Current fact versions of the audience, the selection outcome of each evaluated claim, and the review items and decisions the facts name |
| `withheld`, `gaps` | Counts of rows withheld by rights, and broken references in the chain |

A claim about a split object belongs to the successor that now holds its source record, so each
successor shows only the records and claims it received. `--field` keeps one stable field ID in
claims, facts, attributes, field hashes and change sets; versions that did not state the field
stay listed. JSON columns appear parsed, without their `_json` suffix, exact decimals as plain
strings and times in UTC.

The default audience is `internal`, and without `--permit` every rights statement is visible.
With `--permit`, a claim or confirmation whose evidence rights are not listed is withheld, and so
is every fact, outcome, review item or decision that would reveal it. A claim whose evidence row
is missing, or a fact naming a claim the view does not hold, is shown only to an audience that
permits every rights statement. An excerpt whose `excerpt_rights` are not permitted is removed
from evidence the audience may see. Identity attributes and match features carry no rights
statement, so a restricted audience sees none of their values. `withheld` counts each kind of
withheld row and never shows its content.

`gaps` reports `claim_record_missing`, `claim_version_missing` and `claim_change_set_missing` for a
visible claim the identity journal cannot place, `evidence_missing`, `fact_claim_missing`, and
`fact_subject_superseded` for a current fact stored under an object that was later merged or split.
For an audience that permits every rights statement, `claim_successor_missing` names a claim about a
split object whose record no successor holds, such as a weak-key fragment's claim. A complete chain
runs from the fact through its claim and change set to the version's fetch and archive record ID.
Outbound exchange receipts join the view with the exchange ledger.

`kn.identity.lineage.lineage(state, rows, reference, field_id=..., audience=...)` builds the same
view for other read-only callers. `rows` implements `kn.evidence.lineage.EvidenceRows`;
`SqlEvidenceRows(connection)` reads the registered evidence tables in the caller's transaction.

## Storage and wire contracts

Registered ODCS contract `kn.core.identity` lives in
`src/kn/contracts/resources/identity/1.0.0.json`. It adds ten tables and 71 stable fields to the
editable `1.0.0` development baseline. `make contract-compile` derives the SQLAlchemy/PostgreSQL,
Pydantic, wire and engine artifacts under `generated/contracts/kn.core.identity/`.

| Table | Content |
| --- | --- |
| `objects` | KN UUIDv7, entity class, lifecycle state, anchoring source record, mint event and current single redirect |
| `identifiers` | Namespace/native value, issuer, authority level, half-open validity and evidence |
| `attributes` | Original and normalized values, field ID, normalizer, profile digest and evidence |
| `source_records` | Source-qualified key digest, original source/key and last-seen instant |
| `source_versions` | Opaque version, content/per-field hashes, source/observed times, fetch/archive references and code digest |
| `links` | Historical and current record ownership, method, score/probability, profile version/digest, match/decision and closing event |
| `matches` | Candidate set, features, comparator outcomes/weights, scores/probabilities, selected candidate and decision/profile references |
| `change_sets` | Record-version reference and per-field added/changed/unchanged/emptied/not-stated classifications and hashes |
| `lifecycle_events` | Ordered immutable event projection with actor, reason, evidence, time, decision reference and complete canonical payload |
| `redirects` | Flattened terminal successors; a split can have several |

A `record_seen` event has no table of its own. Its `lifecycle_events` row keeps the sighting, and
`source_records.last_seen` is the latest observed time of the record's versions and sightings.

The [wire contracts](../../../contracts/core/identity/README.md) bind immutable Pydantic payloads,
a closed versioned event envelope and match profiles. New match events carry an optional trace
field for compatibility with existing v1 event hashes. It records the source version, request
digest, route, prior, expected follow-up count and minted KN ID when applicable. Attribute events
that the matcher writes name their contributing source record in another optional field. The SQL
`attributes` table does not project it; `lifecycle_events.event_json` keeps it. The SQL match ID
identifies the corresponding `lifecycle_events` row. `kn identity history KN_ID` includes matches
involving that object as a candidate or mint target.

Objects and source records declare `kn.identity`; the local `identity.anchor-v1` reference describes
exact anchor uniqueness, without supplying a class's scored profile. Every table declares shared
`kn.humanVerification` coverage. External version-bound review uses the shared resolver; lifecycle
events declare decision-log coverage. No review timestamp is fabricated by replay, and a lifecycle
`decision_ref` does not itself prove a human acceptance. Current verification joins and invalidation
remain owned by `human-verification-projections`.

## Match resolution

Use `kn.identity.matching.ingest.submit(connection, journal, profile, observation, actor=...,
evidence=...)` from a trusted source adapter in a caller-owned PostgreSQL transaction. The
`Observation` carries a `SourceKey`, opaque version, time with offset, mapped field readings,
optional authoritative keys and optional alias KN IDs. The adapter supplies the authority
classification and exact namespace, issuer and native value for authoritative keys, such as an
LEI or a reviewed manufacturer-plus-MPN key. The adapter also supplies the trusted actor and
archive evidence reference. Include the issuing jurisdiction in `organization.tax_id`.

Load the reviewed class JSON with `Profile.model_validate_json`. The four profiles cover
organizations, manufacturer parts, orderable variants and supplier offers. Organizations block on
LEI, jurisdiction-qualified tax ID with country, registrable domain, or normalized legal name.
Parts block on manufacturer plus normalized MPN and score the original MPN exactly. Variants
block on part plus packaging or ordering suffix. Offers block on supplier, SKU and orderable
variant together. Use resolved KN IDs for manufacturer, parent part, supplier and orderable
references. Domains use the pinned local Public Suffix List, including private suffixes, and
IDNA normalization without network access. [Match profile files](../../../contracts/core/identity/README.md).

The resolver checks exact current authoritative identifiers first, then the record's existing
ownership. An identifier interval starts at its first observation, so an observation earlier than
every recorded interval of the identifier belongs to the earliest holder; one that falls between two
holders goes to review. Contradictory authoritative targets, an occupied identifier with a
mismatched issuer or class, and a conflict with current ownership go to review. A new binding or
mint stores the match reference in `identity.links`. Existing links retain their original IDs.
Successful decisions record declared attribute readings and previously unregistered authoritative
keys. At an observation instant each candidate has one view per contributing source record, holding
that record's latest reading of each field at or before the instant. A record whose readings all
come later contributes its earliest reading, so an older observation that arrives late still finds
the candidate. A record keeps its view through merges and splits, and one record's newer reading
never hides another record's. Conflicting readings of one record at the same latest time leave that
field missing in its view. Readings recorded without a source record form one view of their own.

Scoring blocks on complete normalized keys in any view, scores each blocked view and keeps the first
highest-scoring one. It records that view's comparator input values, outcome and natural-log
likelihood weight `ln(m/u)`. Missing or unusable values contribute zero. The posterior combines the
sum and the profile prior. Candidates are ordered by descending score and ascending KN ID. A scored
link requires a calibrated profile, the link threshold, agreement on a discriminating attribute with
no discriminating attribute disagreeing, and a unique lead that meets the margin in posterior
probability. Candidates reaching the review threshold go to review when these gates fail. Alias-only
candidates can prompt review. An alias KN ID follows merge and split redirects to its active
successors of the profile's class; unknown alias IDs are ignored. In the absence of a qualifying
candidate the resolver mints a new UUIDv7. All four supplied profiles are uncalibrated. Name and
description fields cannot discriminate, and profile validation rejects a link threshold reachable by
nondiscriminating evidence alone.

A receipt returns the match digest, stored match and bound KN ID, with an empty KN ID for
review. A retried observation returns its original receipt, whose KN ID can since have been
merged or split; resolve it before storing it outside KN. Review decisions are durable match rows
available to `review-queue-cli` when that workflow ships. For verification,
`kn.identity.matching.scoring.verify_match(profile, match)` checks the profile digest and
version, reruns the comparators on the recorded inputs, and reproduces the score and probability.
Exact shortcuts record the matched identifier or source key, with a weight and score of zero and
a probability of one. The pure `matching.resolve.resolve` API computes a decision over a supplied
state without writing.

## Partial-update tracking

Use `kn.identity.tracking.writer.track(connection, journal, delivery, actor=..., clock=...)` from a
trusted source adapter in a caller-owned PostgreSQL READ COMMITTED transaction, after the record
or its parent is linked. A `Delivery` names the `SourceKey`, an optional parent record of the same
source, the source version and updated time, the `ordering`, the fetch ID, archive record ID,
fetch time, origin URI, locator kind, rights, code and contract digests, assertion type, evidence
class and one `Statement` per stated field. A statement holds a typed claim value, or null when the
source stated the field empty, with the original value and unit, conditions and its locator. A
field the delivery omits is not stated. Blank text and `source_empty` are refused as values,
because tracking owns emptiness.

`kn.identity.tracking.mapping` reads a reviewed crawler mapping. `record_key` keeps one key field's
exact text, or joins several as a canonical JSON array, and reports `record_key_missing`.
`version` and `updated_at` read the version field and the `updated_at` time field; a naive time
needs the field's declared zone and otherwise reports `time_invalid`. `stated` returns the mapped
fields a record states, with null, blank, empty list and empty object values marked empty.
`ordering` chooses `version` for a version field that is not the updated time, `updated` for an
updated time field, and `fetch` otherwise.

Versions of one record order by the numeric source version or the source updated time, then fetch
time, then version text. A source without a version gets one version per fetch. Each field hash
covers the typed value, original value, original unit and conditions; an empty statement hashes
alike whatever its original text. Each field compares with the record's latest claim for it, so a
partial version changes only what it states:

| Class | Condition | Evidence rows |
| --- | --- | --- |
| `added` | No earlier claim for the field | New claim |
| `changed` | A different value, or a value after an emptied claim | New claim superseding the record's previous claim |
| `unchanged` | The same hash as the previous claim | Confirmation of that claim with the new version, fetch and observed time |
| `emptied` | Stated empty after a value | New `source_empty` claim superseding the previous one; nothing is cleared |
| `not_stated` | Omitted, or first stated empty with nothing to clear | None |

The change set lists every field the record has claimed or the delivery states. It is a journal
event citing its version, which carries the fetch ID, archive record ID and code digest; claims
cite the version and change set. A delivery whose content equals the current version without a
new source version, or a repeat of a recorded source version in another fetch, appends a
`record_seen` event instead of a version. It advances `last_seen` and confirms the current claims.
A version that orders before the current one is kept as history: it records its hashes and
advances `last_seen`, but has no change set, claims or confirmations. A record that stops
appearing keeps its claims, its `last_seen` stops advancing and nothing is deleted.

A record with an active link claims about its owner, following merges and splits; a weak-key
fragment without one uses its parent record's link. Tracking never runs the matcher, and an
unlinked record is refused. Claims and confirmations are validated before the journal append. The
same delivery retried after a rollback reuses its journaled version and change set and completes
the evidence rows. A rerun writes nothing new and keeps claims the version already made, even after
a merge. A recorded source version delivered again with different content is refused, as is a
missing previous claim.

Replay checks that change-set hashes are consistent with their class and equal their version's
field hashes, and that a sighting cites a known version in a new fetch.
`kn.identity.tracking.changes.prepare` plans a delivery against a locked journal without writing.

## Durable journal and minting

`kn.identity.journal.Journal(data_dir)` owns `$DATA_DIR/identity/events-v1.jsonl`. Files and directories
are private, appends use an exclusive file lock, and the file and directory entries are fsynced
before SQL projection. Entries use canonical ASCII JSON with escaped source text. The envelope
hash binds a contiguous sequence and predecessor digest. Torn lines, malformed events, altered
content, unknown versions, sequence gaps and symlink paths refuse without rewriting history.
Only an operator-owned local journal is a trusted replay input; importers must not copy external
logs or untrusted actor strings into it.

Inside `Journal.locked()`, `LockedJournal.mint(anchor, entity_class, occurred_at=..., actor=...,
reason=..., evidence=...)` mints a random UUIDv7 once per exact `SourceKey(source, key)`. The ID is
stored in the event before it is returned. Retries, including concurrent callers, return the
original ID; a changed class for the same anchor refuses. IDs display as `kn:<uuid>`, preserve the
first-sight UTC milliseconds and use 74 random bits. IDs are never derived from labels. Numeric
looking record keys retain leading zeroes, and the source is part of their identity.

## Replay and integrity

`kn.identity.store.apply(connection, journal, write)` acquires the identity transaction advisory
lock, validates the SQL event prefix, invokes the append or mint callback, and projects the
durable suffix in a savepoint. Ordinary writes append event rows and update the affected objects,
source records, ownership, links and redirects. The writer closes old links before inserting
replacement active links. Tracking uses the same incremental write path.

Reuse a `Journal` instance across submissions. It retains validated state and matching indexes
under the file lock. A changed file identity, size or modification stamp triggers full validation
before reuse. An invalid batch leaves the durable prefix intact. Matching selects candidates
through indexed authoritative keys, source links, aliases and historical blocking values. It
checks each candidate's current owner, class and as-of values per contributing record before
scoring. Retry validation uses the link and identifier history as of the original decision.

Callers own short PostgreSQL READ COMMITTED transactions and commit after application. Appends
and fsync precede SQL, so a rollback can leave a pending suffix. The next successful write projects
that suffix with its original IDs, actor, time and decision. The disposable
`identity.projection_checkpoint` records the validated SQL event prefix in the same transaction.
SQL updates, deletes and truncation of event rows invalidate it. Unverified SQL rows are compared
with the journal before a new append. Divergent or ahead SQL history refuses.

`store.replay(connection, journal)` validates the whole journal and SQL event prefix, then
replaces the disposable projection and checks deferred references. It returns the validated
`State`. `State.resolve(id)` returns terminal successors, including retired IDs or multiple split
successors. Unknown IDs fail. Replaying the same history produces identical rows.

The pure replay validator in `state.py` and `transitions.py` enforces:

- No reused KN ID or anchoring record, even after retirement, merging or splitting.
- One active link per source record, with new links only to active objects. PostgreSQL also enforces
  active-record uniqueness through the compiled `whereNull: ended_event` partial unique index.
- Identifier namespace/value intervals never overlap; validity is half-open, so adjacent intervals
  can use the same identifier. Authority levels stay distinct.
- Merge targets are active, distinct objects of the same class. Merged and split states are
  terminal. Replay maintains flattened terminal successors for a single lookup, including
  converging split branches.
- A split names at least two distinct active objects of the same class and assigns every current
  link, identifier and attribute to exactly one successor. Reclassification retires the old object
  and mints a new-class successor in one event, retaining ownership lineage.
- Retirement closes active links. Restore permits a retired object without a successor. Links can
  then be added explicitly. Operator events cite the accepted review. Trusted ingestion can
  instead append a `Merge` with an `authoritative` observation, using the opposing object's
  recorded identifier with the same namespace, issuer and exact value. Both identifiers must be
  authoritative and valid at the event instant. The merge carries the new evidence without
  inserting a duplicate identifier interval.
- Record versions are unique per source key. Older observations remain history without reducing
  `last_seen`. Change sets cite an existing version once with consistent field hashes. Sightings
  cite a known version once per other fetch. Scored links cite a stored match with the same record,
  selected candidate, score, probability and profile version/digest.

SQL primary/foreign keys, enums, unique anchors/versions and the active-link index supplement these
checks. Temporal overlap and lifecycle semantics are enforced at the journal/application boundary;
loaders must use that boundary. The local journal and database administration remain trusted.
Explicit replay repairs disposable rows from the durable history. Anchor, ownership, identifier,
record version, change set and match request indexes support validation during replay.

Matching validates its full event batch before appending. Retry the same observation and profile
to reuse the original event digest and KN ID after a SQL rollback. A complete journal prefix of
an interrupted match can be finished by the same retry. New match requests, lifecycle mutations,
registry mints and other journal appends return a pending match error until that retry completes.
A journal written before this check could contain another operation after the incomplete batch;
its retry then refuses as a diverged suffix. The usual torn-line integrity checks apply.

## Reviewed writes and recovery

`kn.identity.lifecycle.submit` takes a trusted authenticator and applies the shared
[review protocol](evidence-model.md#trusted-decision-application) inside the identity writer lock.
The accepted `workflow` decision binds the normalized transition, the preceding identity event
digest, and the reviewer, reason, evidence and exact performed time. The decision journal is
fsynced first. The identity journal event then cites `identity-review:<decision_id>` and is
fsynced before SQL state is committed. Replay checks both journals and restores the referenced
decisions alongside identity rows. Rebuild takes the identity lock, then the review lock, before
replacing schemas. Keep both journals together for rebuilds.

Retry with the same reviewer, request ID, operation, performed time, reason and evidence. An
applied request returns the original event even after later transitions. If only the decision was
written, the same request can finish against the same identity head. If the head has advanced,
inspect the current state and submit a newly reviewed request. A decision by itself never changes
ownership. A changed identity head between terminal confirmation and submission refuses the
operation. Historical opaque references from earlier v1 journal entries remain readable.

## Rebuild and verification

`kn db rebuild` replays identity before reviewed seeds and any later raw-record replay. It uses
`DATA_DIR` from the environment, resolving relative paths from the project root, or `.data` by
default. `make db-rebuild` first loads `.env` through the shared shell helpers. Python callers can
pass `rebuild(connection, data_dir=path)`. Rebuild takes the identity lock before dropping schemas;
a replay or seed failure restores the complete previous SQL state. Raw replay remains planned.

`tests/identity/` covers every event kind, invalid transitions, namespace validity, typed schemas,
profile structure, source key preservation, authoritative merge proof, terminal authorization,
journal damage, retries and concurrent minting.
`tests/integration/test_identity.py` and `test_identity_database.py` check repeated replay, complete
database-drop recovery through the CLI, concurrent SQL writers, caught SQL errors,
pending replay, malformed-log rebuild rollback, SQL/log disagreement and the partial index.
`tests/integration/test_identity_lifecycle*.py` check CLI writes, cross-class refusal, interrupted
appends, stale requests and repeat rebuilds with the original decision IDs. `make test-bilingual`
compares identity lookups and command help with the English goldens.
`tests/identity/test_match*.py` cover the labeled match fixtures, profile safety, comparators,
exact and scored precedence, retries and concurrent writes. `test_match_order.py` submits the
organization, part and variant fixtures in every order and compares objects and decision counts,
and checks late observations, an identifier seen before or between its holders, and the
discriminator veto. `test_match_registry.py` covers
per-record views after merges, splits and identifier links, and aliases of merged objects. The
PostgreSQL matching fixture checks projection, rollback recovery and rebuild of recorded match
receipts. `tests/integration/test_identity_resolution.py` merges, splits and submits a name-only
match, then compares every identity row and review decision across two rebuilds and a schema drop.
It also refuses a lifecycle mutation while a match batch is incomplete. The `heavy`
`tests/identity/test_replay_scale.py` check, run by `make ci-local`, fails when replay and row
projection grow faster than linearly.
`tests/identity/test_tracking*.py` cover every change class, partial, emptied, omitted and
first-empty fields, records that stop appearing, identical re-deliveries, late versions, numeric
and updated ordering, fragments, retries, interrupted versions, reruns after a merge, mapping
inputs and replay checks. `tests/integration/test_identity_tracking.py` tracks a delivery sequence
through PostgreSQL after a rolled-back first attempt, checks current claims, confirmations,
`last_seen` and change-set rows, and compares identity rows after a schema drop and rebuild.
`tests/identity/test_lineage*.py` check complete chains to archive record IDs for every fixture
object, a late version and an omitted field through the selected fact, a fragment claim after a
split, a merged ID against its survivor, a partial update with a sighting, a two-source conflict,
split successors, withheld claims, facts, excerpts, attributes and match features, qualified and
ambiguous identifiers, reported gaps, and the CLI refusals before any database access.
`tests/e2e/test_lineage_cli.py` compares four lookups with the
[English lineage goldens](../../../tests/e2e/fixtures/lineage-cli.json).
`tests/integration/test_lineage_cli.py` stores the same fixture in PostgreSQL and checks that the
CLI matches the text goldens and structured results through a read-only transaction.
`make model-baseline` now includes identity history before SATCOM import and compares every
registered column after two rebuilds. Run `make ci` and `make test-integration` against local
PostGIS. The integration suite times warmed PostgreSQL submits against 5,000 and 50,000 synthetic
organizations and compares incremental writes to two rebuilds after database drops. It covers
untouched rows, SQL prefix corruption, interrupted writes, retries and concurrent writers. See the
[incremental writes record](../records/0048-object-identity-identity-incremental-writes.md) for
commands and measurements. `make ci-local` also includes the local SKOS gate.

## Known limitations

These are accepted or scheduled findings of the
[identity resolution audit](../records/0042-object-identity-identity-resolution-implementation-audit.md#findings)
and the [object identity audit](../records/0049-object-identity-object-identity-implementation-audit.md#findings).

- A new `Journal` instance or a write by another instance requires full file validation. The
  first scored request for each field and normalizer builds its blocking index. Broad blocking
  keys and long attribute histories can still produce expensive candidate sets. Reviewed history
  still validates and checks its decision projection when a write runs.
- An object minted without a source link, such as a reclassification successor, sends its
  re-delivered anchor record to review after a merge instead of following the redirect. Reopen
  this when an adapter mints objects without links.
- Legal-name normalization removes only common trailing legal forms such as `Ltd`, `Inc` and
  `GmbH`. A leading form, such as the Ukrainian abbreviation for a limited liability company,
  stays in the name. Names never discriminate, so this affects only review recall. Reopen this
  when an organization calibration report shows missed held-out pairs that differ only by legal
  form.
- Claims and confirmations live in the evidence tables, which rebuild drops and does not restore
  from the identity journal. Tracking the same deliveries again in their original order reproduces
  the same claims and confirmations from the journaled change sets. Until the raw replay of
  `rebuild-from-raw` does this, a delivery whose previous claim is missing refuses.
- A late version stays history even for fields that newer partial versions never stated. Its
  hashes and raw record remain, and replay in version order would claim them.
- Ordering by source version requires numeric versions. A source with an opaque version string
  orders by its updated time or by fetch time.
- Lineage shows only current fact versions, and matches are found by a scan of the whole journal.
  Reopen this when an analyst view needs fact history or lookups slow at registry scale.
- Identity rows, record versions and archive record IDs carry no rights statement; a restricted
  lineage audience still sees record keys and archive IDs, but no attribute or feature values.
- The matcher never merges by itself. A shared authoritative identifier on two records goes to
  review. A trusted adapter or review workflow appends the merge.
- Resolution is sequential. Of two similar records without a shared key, the first mints and the
  second opens review, so arrival order decides which one waits. A record in review registers no
  identifiers or attributes, and a later record with the same unregistered key can mint. Accepted
  matches will register them through `review-queue-cli`. Reopen this if reviewed duplicates grow
  with source count.
- An alias that names a retired object is ignored, and the record resolves as if it carried no
  alias. Reopen this when a counterpart import returns retired KN IDs.
- A weak-key fragment has no link of its own, so a split cannot assign the claims it made before
  the split. Lineage reports them as `claim_successor_missing`, and the fact projection leaves
  them unattributed until `fragment-claims-follow-splits`.

Acceptance evidence is retained in
[record 0033](../records/0033-object-identity-identity-registry-contracts.md),
[record 0039](../records/0039-object-identity-object-lifecycle-operations.md),
[record 0040](../records/0040-object-identity-identity-match-engine.md),
[record 0042](../records/0042-object-identity-identity-resolution-implementation-audit.md),
[record 0045](../records/0045-object-identity-partial-update-tracking.md),
[record 0046](../records/0046-object-identity-canonical-fact-selection.md),
[record 0047](../records/0047-object-identity-object-lineage-lookup.md),
[record 0048](../records/0048-object-identity-identity-incremental-writes.md) and
[record 0049](../records/0049-object-identity-object-identity-implementation-audit.md).
