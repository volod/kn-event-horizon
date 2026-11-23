# Schema-First Development

The [forward plan](../impl/plan.md) prioritizes model implementation before runtime features.
The goal is to settle shared keys, histories, timestamps, verification metadata and domain
boundaries while fixture rebuilds are cheap, reducing later breaking changes and repeated backfill.
This is an executable scheduling policy, not a claim that the model is already implemented or
that no later additive schema work will be needed.

## Selection rule

Tasks may declare `Execution stage: MODEL`; otherwise their stage is `DELIVERY`.
`make plan-status` first excludes tasks with open `Requires`, then selects required before
optional, MODEL before DELIVERY, and registry/document order within those classes. The summary
reports stage counts. Stages never grant source access or remove external/manual prerequisites.

The integrity gate accepts only MODEL and DELIVERY. A MODEL task cannot depend on an open
DELIVERY task. Split mixed contract/runtime work or retain DELIVERY with an explicit dependency;
do not hide a producer task in `Dependencies` to obtain priority. Capability groups stay in
registry order in both lanes for navigation. The evidence-model group precedes identity so the
shared verification contract can be selected first without adding false technical dependencies.

## Model sequence

These are dependency waves, not permission to skip the declared checks of an individual task.

| Wave | Model work | Dependency reason |
| --- | --- | --- |
| 1 | `human-verification-contracts` | Shared optional review time, actor, decision, target/version and coverage trait must exist before more tables are authored |
| 2 | `identity-registry-contracts`, `source-catalogue-import`, `vendor-information-coverage`, `warc-raw-store` | Establish stable object/source keys, the target vendor field set and durable archive/log formats |
| 3 | `evidence-claim-contracts`, `crawler-config-schema`, `supply-model-contracts`, `ingestion-state-contracts` | Use those identities and sources to fix provenance, change/selection/review state, shared measurements, and run/checkpoint storage |
| 4 | `space-domain-contracts`, `gdelt-domain-contracts`, `microelectronics-domain-contracts`, `interchange-contract`, `interchange-schema-evolution`, `exchange-ledger-contracts` | Extend the common shapes and fix domain and external compatibility boundaries using synthetic/archived fixtures |
| 5 | `human-verification-projections` | Apply uniform coverage to the complete early registry, including new core/domain tables, rather than retrofit each successive table |
| 6 | `development-model-baseline` | Compile, load and rebuild all owners as one integrated set before persistent runtime consumers |

Within a wave, actual prerequisites and registry order determine the next task. For example,
source catalogue IDs must precede evidence contracts, and evidence contracts precede supply and
ingestion-state contracts. Crawler configuration can be validated before there is an HTTP engine.
WARC storage is in MODEL because its durable record IDs and ledger format are later references;
its acceptance needs only local fixture I/O, not a live source.

The human `decide-vocabulary-uri-namespace` task is also MODEL. The owner can settle that external
identifier boundary early. It does not block typed internal keys or core schema acceptance; its
approval requirements remain in the human lane.

## Model ownership and splits

| Owner/task | Shapes fixed early | Behavior left to DELIVERY |
| --- | --- | --- |
| Identity registry | Object/identifier/link keys, source versions, per-field hashes/change sets, match features/profile versions, lifecycle events and redirects | Lifecycle CLI, matching algorithm, change detection, lineage lookup and calibration |
| Evidence contracts | Claims, confirmations, evidence, review/decision records, selection outcome/history and source-rank/update-policy formats | Fact selection, conflict handling and review workflows |
| Supply contracts | Organizations, parts/variants/offers, typed observations, attributes, units, conditions, compliance and match-profile interfaces | Vendor parsers and executable scored matching |
| Source catalogue/configuration | Qualified source IDs, lifecycle states, method blocks, error vocabulary and approval references | Onboarding investigation, live collection and source enablement |
| `ingestion-state-contracts` | Attempts, batches, status/errors, cursor/checkpoint versions, archive references, health fields and transactional constraints | Engine execution, retry orchestration and status display |
| `interchange-contract` | Record/manifest/full/delta/loss metadata schemas and versioned typed examples | New `interchange-package-export` owns snapshot queries, ZIP creation, filters, hashes and CLI validation |
| `exchange-ledger-contracts` | Bindings, field ownership, three-way versions, plans, approvals, receipts and idempotency keys | Existing `exchange-binding-ledger` owns synchronization, counterpart calls and crash recovery |
| Domain contracts | Domain types, claim links, vocabularies, measurement extensions and loader boundaries | Authorized source parsers, loaders and full pipeline replay |

`supply-model-contracts` owns the shared measurement/attribute/condition model. Microelectronics
extends it; it does not become a prerequisite for defining the base used by supply itself.
The scored matching engine and full raw replay are not necessary to compile domain contracts.
Their earlier dependencies on these runtime tasks are replaced with the actual model providers.
All prior runtime acceptance remains on its owning task or the explicit split task.
The first GDELT dictionary and microelectronics benchmark loaders explicitly require
`rebuild-from-raw`, preserving the runtime prerequisite moved off their domain model tasks.

## Integrated baseline and later changes

`development-model-baseline` requires the model projections and interchange evolution checks;
their transitive dependencies cover the whole MODEL set. It accepts the combined registry through
compilation, real database constraints, representative fixture round trips and repeated rebuilds.
It includes stable identifiers, review provenance, multilingual source text, units/conditions,
all contract markers and the lossless SATCOM fixture. Domain replay acceptance uses fixtures and
the durable model/log protocols; the complete source engine and its later replay suite remain
separate work.
Existing SATCOM tables are snapshot-shaped source projections, while the new space model contains
canonical facts with KN identities and claim links. Resolve table ownership, names and field-ID
mapping during the space model task; the shared baseline rejects collisions or silent changes in
meaning. A source projection never becomes a canonical fact merely because it shares a name.

Use isolated or transaction-scoped fixture rebuilds during individual model tasks. Apply the
combined model to the shared development database explicitly at the checkpoint, with recovery
evidence and backfill, rather than treating every intermediate definition as a separate rollout.
Until adoption, the existing digest-drift refusal remains intentional.

The first lifecycle, selection, ingestion and exchange runtime writers require this checkpoint,
directly or transitively. Optional audits do not gate required work. Infrastructure and tools
that do not write the core model may remain independent, but do not outrank eligible required
MODEL work.

After this checkpoint, later tasks consume the established definitions. Classify any schema work:

| Later work | Expected impact |
| --- | --- |
| dbt marts, analytics views and human-facing read models | Additive projections over core contracts; keep identifiers and semantic meaning |
| Source dictionaries and domain source adapters | Data, mappings and profiles over early schemas; new source-specific tables may be additive |
| InvenTree API snapshots and adapter profiles | External schema/configuration artifacts; use shared interchange and ledger models |
| Optional native GDELT streams | Explicit additive native tables; no change to the meaning of core claims or object IDs |
| Obsidian/AI/workflow profiles | Typed adapters and artifacts using the common provenance/review extension points |
| Kestra, Superset, proxy and host setup | Service-owned storage/configuration, separate from KN's canonical data model |
| Release migration mode | Freeze and migration discipline after release approval, not an early release compatibility promise |

An unexpected change to a core key, type, unit, null meaning, ownership, review scope or record
version requires explicit plan work and revalidation of the affected baseline. Do not add a
parallel table or weaken a constraint to make a runtime feature pass. An honest new dependency
on live evidence stays visible; the model stage cannot make unknown source requirements vanish.
New domains and fields remain possible through reviewed additive contracts and extension points.

Development still edits contract `1.0.0` and the baseline in place, then explicitly rebuilds and
backfills. The checkpoint consolidates known model work before those consumers proliferate; it
does not replace the [release migration switch](../design/spec.md#release-readiness).

The [prioritization record](../impl/records/0029-adhoc-schema-first-plan-priorities.md) retains the
complete before/after task inventory and dry scheduling evidence.
