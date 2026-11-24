# Object Identity

The identity storage contract, durable journal, deterministic replay, reviewed lifecycle commands
and profile-driven matcher are available. Change detection, claim lineage and real-record
calibration remain in the [plan](../plan.md).

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
`kn_load_env` before running the CLI. Use `--locale en` or `--locale uk` for localized headings,
help, confirmation and diagnostics. `--json` returns the same keys and values in either locale.
Success for a mutation returns the full identity event and `decision_id`. Input or transition
errors report `E_INPUT`, terminal or owner refusals report `E_IDENTITY_AUTH`, and SQL errors report
`E_DATABASE`.

Merge, split and reclassification preserve the original link ID and source record ID while
changing link ownership. Later claim lineage can follow that source record through the move.
The original link and every move remain in history.

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

The [wire contracts](../../../contracts/core/identity/README.md) bind immutable Pydantic payloads,
a closed versioned event envelope and match profiles. New match events carry an optional trace
field for compatibility with existing v1 event hashes. It records the source version, request
digest, route, prior, expected follow-up count and minted KN ID when applicable. The SQL match ID
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
ownership. Contradictory authoritative targets, an occupied identifier with a mismatched issuer
or class, and a conflict with current ownership go to review. A new binding or mint stores the
match reference in `identity.links`. Existing links retain their original IDs. Successful
decisions record declared attribute readings and previously unregistered authoritative keys.
At an observation instant the scorer uses the latest eligible reading for each candidate field.
Conflicting readings at the same latest time leave that field missing for scoring.

Scoring uses complete normalized blocking keys and records each comparator's input values,
outcome and natural-log likelihood weight `ln(m/u)`. Missing or unusable values contribute
zero. The posterior combines the sum and the profile prior. Candidates are ordered by
descending score and ascending KN ID. A scored link requires a calibrated profile, the link
threshold, agreement on a discriminating attribute, and a unique lead that meets the margin
in posterior probability. Candidates reaching the review threshold go to review when these
gates fail. Alias-only candidates can prompt review. In the absence of a qualifying candidate the
resolver mints a new UUIDv7. All four supplied profiles are uncalibrated. Name and description
fields cannot discriminate, and profile validation rejects a link threshold reachable by
nondiscriminating evidence alone.

A receipt returns the match digest, stored match and bound KN ID, with an empty KN ID for
review. Review decisions are durable match rows available to `review-queue-cli` when that workflow
ships. For verification, `kn.identity.matching.scoring.verify_match(profile, match)` checks the
profile digest and version, reruns the comparators on the recorded inputs, and reproduces the
score and probability. Exact shortcuts record the matched identifier or source key, with a
weight and score of zero and a probability of one. The pure `matching.resolve.resolve` API
computes a decision over a supplied state without writing.

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
lock, validates the SQL event prefix, invokes a journal append/mint callback, then projects its
history in a savepoint. The callback only writes the locked journal. `store.replay(connection,
journal)` recovers durable pending history and returns the validated `State`; `State.resolve(id)`
returns terminal successors, including retired IDs or multiple split successors. Unknown IDs fail.

Callers own short PostgreSQL READ COMMITTED transactions and commit after application. Append and
fsync precede SQL, so a caught SQL error or rollback can leave a durable pending event. Replay
recovers its original ID, actor, time and decision. SQL history that differs from the journal or
runs ahead of it refuses; replay never silently overwrites conflicting event history. Disposable
state rows are rebuilt from the validated history, and deferred references are checked before
return. Replaying the same history produces identical rows.

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
  `last_seen`. Change sets cite an existing version once. Scored links cite a stored match with the
  same record, selected candidate, score, probability and profile version/digest.

SQL primary/foreign keys, enums, unique anchors/versions and the active-link index supplement these
checks. Temporal overlap and lifecycle semantics are enforced at the journal/application boundary;
loaders must use that boundary. Arbitrary direct SQL or filesystem administrator tampering is
outside the trusted protocol. Replay validates the whole local log and replaces disposable state.
Candidate lookup scans the active registry holdings.

Matching validates its full event batch before appending. Retry the same observation and profile
to reuse the original event digest and KN ID after a SQL rollback. A complete journal prefix of
an interrupted match can be finished by the same retry. New match requests return a pending
match error until that retry completes. If another identity operation has already advanced
the journal, a diverged suffix refuses the retry. The usual torn-line integrity checks apply.

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
database-drop recovery through the CLI in both locales, concurrent SQL writers, caught SQL errors,
pending replay, malformed-log rebuild rollback, SQL/log disagreement and the partial index.
`tests/integration/test_identity_lifecycle*.py` check CLI writes, cross-class refusal, interrupted
appends, stale requests and repeat rebuilds with the original decision IDs. `make test-bilingual`
compares identity lookups and command help with both locale goldens.
`tests/identity/test_match*.py` cover the labeled match fixtures, profile safety, comparators,
exact and scored precedence, retries and concurrent writes. The PostgreSQL matching fixture
checks projection, rollback recovery and rebuild of recorded match receipts.
`make model-baseline` now includes identity history before SATCOM import and compares every
registered column after two rebuilds. Run `make ci` and `make test-integration` against local PostGIS;
`make ci-local` also includes the existing local SKOS gate.

Acceptance evidence is retained in
[record 0033](../records/0033-object-identity-identity-registry-contracts.md) and
[record 0039](../records/0039-object-identity-object-lifecycle-operations.md) and
[record 0040](../records/0040-object-identity-identity-match-engine.md).
