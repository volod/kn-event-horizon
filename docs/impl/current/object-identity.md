# Object Identity

The identity storage contract, durable event journal and deterministic replay are available.
Operator lifecycle commands, matching execution, change detection, lineage queries and calibration
remain in the [plan](../plan.md).

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

The [wire contracts](../../../contracts/core/identity/README.md) bind immutable Pydantic payloads
and a closed, versioned event envelope. Structural match profiles declare blocking keys,
attributes/normalizers/comparators, agreement m/u probabilities, prior, thresholds, margin and
calibration reference. Their schema validates shape and references within the profile. Scoring,
name-only safety and evaluation of calibration evidence belong to `identity-match-engine` and
`identity-match-calibration`.

Objects and source records declare `kn.identity`; the local `identity.anchor-v1` reference describes
exact anchor uniqueness, without supplying a class's scored profile. Every table declares shared
`kn.humanVerification` coverage. External version-bound review uses the shared resolver; lifecycle
events declare decision-log coverage. No review timestamp is fabricated by replay, and a lifecycle
`decision_ref` does not itself prove a human acceptance. Current verification joins and invalidation
remain owned by `human-verification-projections`.

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
  terminal. Redirect projections collapse chains to terminal successors.
- A split names at least two distinct active objects of the same class and assigns every current
  link, identifier and attribute to exactly one successor. Reclassification retires the old object
  and mints a new-class successor in one event, retaining ownership lineage.
- Retirement closes active links. Restore permits a retired object without a successor; links can
  then be added explicitly. Merge, split, restore and reclassification require decision references.
- Record versions are unique per source key. Older observations remain history without reducing
  `last_seen`. Change sets cite an existing version once. Scored links cite a stored match with the
  same record, selected candidate, score, probability and profile version/digest.

SQL primary/foreign keys, enums, unique anchors/versions and the active-link index supplement these
checks. Temporal overlap and lifecycle semantics are enforced at the journal/application boundary;
loaders must use that boundary. Arbitrary direct SQL or filesystem administrator tampering is
outside the trusted protocol. Match profiles and stored features are structural data here; no
resolver executes matching or classifies updates yet. Replay currently validates the whole local
log and replaces disposable state; it has no large-log performance claim.

## Rebuild and verification

`kn db rebuild` replays identity before reviewed seeds and any later raw-record replay. It uses
`DATA_DIR` from the environment, resolving relative paths from the project root, or `.data` by
default. `make db-rebuild` first loads `.env` through the shared shell helpers. Python callers can
pass `rebuild(connection, data_dir=path)`. Rebuild takes the identity lock before dropping schemas;
a replay or seed failure restores the complete previous SQL state. Raw replay remains planned.

`tests/identity/` covers every event kind, invalid transitions, namespace validity, typed schemas,
profile structure, source key preservation, journal damage, retries and concurrent minting.
`tests/integration/test_identity.py` and `test_identity_database.py` check repeated replay, complete
database-drop recovery through the CLI in both locales, concurrent SQL writers, caught SQL errors,
pending replay, malformed-log rebuild rollback, SQL/log disagreement and the partial index.
`make model-baseline` now includes identity history before SATCOM import and compares every
registered column after two rebuilds. Run `make ci` and `make test-integration` against local PostGIS;
`make ci-local` also includes the existing local SKOS gate.

Acceptance evidence is retained in
[record 0033](../records/0033-object-identity-identity-registry-contracts.md).
