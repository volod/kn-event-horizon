# Evidence Model

The shared human verification protocol is implemented. Claims, canonical selection, review queues
and dataset-wide verification projections remain planned. Existing source verification labels
retain their meanings and grant no human timestamp.

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

## Verification

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
[record 0032](../records/0032-evidence-model-human-verification-contracts.md).
