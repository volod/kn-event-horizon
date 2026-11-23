# Human Verification Metadata

This is a required extension of the [evidence model](spec.md#human-verification-metadata).
The [shared decision protocol](../impl/current/evidence-model.md) is implemented; dataset-wide
coverage and read projections remain planned. The operator problem is to distinguish data that a
person checked from data merely imported, corroborated, or accepted by automated validation, while
leaving unchecked data usable. Future verification workflows consume this metadata instead of
inventing a new
meaning for each domain.

## Coverage and granularity

Every registered data record and independently addressable value can expose an optional
`human_verified_at`. Record and field scopes are independent: checking a terminal's mass does not
verify its availability, manufacturer or complete record. A record approval binds its declared
contents but does not manufacture separate field-review events. A field approval never sets the
whole-record stamp. Existing immutable claims provide a natural field-level target; other tables
use their contract field IDs and typed primary keys.

| Current or planned data | Verification target |
| --- | --- |
| Semantic namespaces, terms, concepts, classes and relation definitions | Qualified ID plus exact reviewed content; relations and mappings are independent records |
| Preferred/alternative labels and localized definitions | Full key, including locale, and the relevant field ID; English review never verifies Ukrainian text |
| Scheme/publication and terminology reviews | The compared content and review purpose; existing verification states remain distinct |
| SATCOM organizations, programs, equipment, observations, links and other domain rows | Snapshot-qualified primary key and record or field scope |
| Sources, claims, classifications, dictionaries, evidence and missing-data assertions | Their own stable key/version and optional field scope; source approval does not certify its claims |
| Imports, file manifests, raw rows and contract markers | Exact artifact or record version; integrity review does not certify all enclosed facts |
| Future identities, claims, canonical facts, offers, documents and derived values | Stable identity/claim/observation keys and reviewed content version; lineage alone grants no verification |

All 50 tables in the original review inventory need explicit coverage, including the 18 semantic,
28 SATCOM domain, three SATCOM bookkeeping and one governance tables. Newly registered contracts,
including the shared decision log, need coverage too. Immutable source bytes, CSV headers and
publication manifests are preserved; verification metadata is attached externally or through KN
projections. Audit decisions retain
their own actor and event times; recording a decision does not recursively approve that decision
or its payload. No technical record or data group silently defaults to verified.

## Public metadata

The minimum read surface is consistent for both record and field targets:

| Field | Meaning |
| --- | --- |
| `human_verified_at` | Nullable UTC `timestamptz`: when a human accepted this exact target/version/scope |
| `human_verified_by` | Nullable stable reviewer/principal reference; resolved by the trusted review boundary |
| `human_verification_decision_id` | Nullable reference to the durable acceptance decision |

The three values are all absent or all present in an active verification projection. The time is
not a default, creation time, fetch time, observation time, publisher timestamp, SQL migration time,
or the time an agent processed a file. Null means there is no active, timestamped human acceptance
for that exact target. It does not imply the value is false or that a reviewer rejected it.
Missing translations and missing-value assertions can be reviewed without replacing their values.

Automatic checks, source-provided `verified` text, provenance references, source rank, content
hashes, scheme origin, and an AI/agent decision cannot set the stamp. A principal claiming to be
human in imported data is not sufficient. Future human-facing review entry points establish the
actor and authorization independently of payload text. Accepting a workflow item such as a source
enablement or identity operation is not automatically a factual verification of every linked row.

Existing verification states keep their domain meanings. Publication comparison, terminology
review, source assertions and human factual acceptance must be distinguishable by target and
purpose. A generic timestamp never bypasses canonical selection, rights, evidence or safety rules.
Historical `verified` labels and date-only `reviewed_on` values do not justify a timestamp:
migration
leaves it null until an attributable review with an exact time exists.

## Durable decisions and version binding

Use one append-only verification decision model and its read projections. This avoids separate
timestamp writers and incompatible meanings across dozens of tables. A nullable database field or
a joined view may expose the read metadata; a central history is authoritative, and API/analytics
consumers must see the same result. Field metadata is a bounded mapping keyed by approved field
IDs, or a claim projection, rather than a separate timestamp column for every source cell.

A typed decision binds:

- a deterministic decision ID and schema version;
- contract ID, dataset, typed complete primary key, record/field scope and stable field ID when
  applicable; the key encoding preserves strings, leading zeroes and composite keys;
- an immutable target version or content digest, including the reviewed value, units, conditions,
  missing reason, locale and relevant evidence/context;
- the explicit verification purpose, so a publication or integrity check cannot become a different
  kind of factual approval;
- authenticated human reviewer reference, performed time, separate recorded time, outcome, reason
  and supporting review/evidence reference;
- the prior decision it supersedes or revokes when applicable.

Accept, reject, revoke and supersede are recorded events. A rejection or revocation leaves no
active acceptance stamp while retaining its history. Re-review of the same content records a new
decision; replay of the same decision is idempotent. Historical queries retain what was accepted
and when, rather than rewriting prior decisions.
Conflicting concurrent outcomes are surfaced as a conflict with no active acceptance until an
explicit superseding human decision resolves it; wall-clock order alone does not hide the conflict.

Times require explicit offsets, normalize to UTC and retain the actual instant. Naive, invalid or
future performed times relative to the recorded event are refused using a controlled clock.
Imported historical decisions need an attributable exact time; a date is never expanded to an
invented midnight. No timestamp or reviewer identity is fabricated during backfill.

A substantive edit creates a different reviewed version and the current stamp becomes null or
explicitly stale; the old decision remains attached to the old version. Restoring an old value,
merging an identity, translating text, changing a field's unit, or selecting a different claim
does not silently transfer approval. An unchanged re-delivery may retain approval only when the
same target version remains. Contract-declared review projections define meaningful content and
exclude the verification annotations themselves, interface presentation choices, and transport
counters such as `last_seen`; excluded fields cannot alter the fact's meaning. Writing a stamp
must not invalidate its own content digest. A derived value's target version includes its model,
input versions, window and filters, rather than only the displayed number.
Referential integrity uses registered typed target resolvers, consistent with the existing rule
against cross-contract SQL foreign keys.

## Rebuild, ingestion and exchange

Durable human decisions live under `$DATA_DIR/decisions/` independently of disposable SQL schemas.
Rebuild replays them against durable targets and recreates projections with the original times,
reviewers and decision IDs. Decisions whose targets are not restored yet remain pending; missing,
changed or incompatible targets produce an orphan/stale report rather than invented approval or
lost history. Source re-import preserves matching decisions without duplicate events. A failed
transaction cannot publish a partial verification projection.

Source archives and raw cells remain byte-identical. Incoming metadata from another system is an
attributed external assessment until its reviewer authority, subject/version, purpose and time
can be validated under an explicit trust policy. Unsupported outbound metadata appears in a loss
report. Restricted values, reviewer identities and evidence references are filtered together;
an export must not leak a private review through its timestamp or count.

## Boundary and evaluation

The initial work supplies contracts, coverage, validation, durable history and read projections.
Queue screens, scheduling, notifications, reviewer assignment and approvals are later workflow
work. No current datum is automatically marked human-verified, and ingestion never requires a
human to have reviewed it.

Acceptance covers all existing contract tables, row and field scopes, real human acceptance,
untouched nulls, attempted automation spoofing, source-only verification labels, composite keys,
labels/locales, units/conditions, changed and unchanged deliveries, rejection/revocation,
duplicate/concurrent decisions, UTC and invalid clocks, rights filtering, missing targets,
transaction rollback, exchange loss reports, and two rebuilds with identical decision projections.
The registration gate rejects missing coverage so a new domain cannot omit this requirement.
When a target or old assessment lacks enough identity, time or authority, the valid result is a
null timestamp plus an explicit unsupported/legacy/stale reason, with original data retained.

The [review record](../impl/records/0028-adhoc-human-verification-model-review.md) maps current gaps
to the implementation tasks in the [forward plan](../impl/plan.md).
