# 0004 InvenTree Interchange and Object Identity Specification

## Work contract

Direct request from the owner, with no plan task. Update `spec.md` and `plan.md` with a solution
and tasks for exchanging information with [InvenTree](https://inventree.org/) instances:

1. A data contract, plus schema-evolution support for changes between InvenTree versions.
2. Data exchange between the knowledge system and the owner's `vl-itree` instance
   (<https://github.com/volod/vl-itree>), which will be upgraded to the latest InvenTree release.
3. Knowledge base features as complete as the information vendors can supply.
4. Matching of the same object's data across sources: unique object IDs, identity attributes with a
   probability level, and data lineage.
5. Identity and matching as the core data model from the start, with object lifecycle and
   partial-update matching and tracking.
6. Data interchange and compatibility as initial requirements.

## Implementation and decisions

Specification changes: new sections for [object identity](../../design/spec.md#object-identity),
the [part and supply model](../../design/spec.md#part-and-supply-model),
[data interchange](../../design/spec.md#data-interchange), and
[InvenTree exchange](../../design/spec.md#inventree-exchange). Also new: integrity rules 11-13,
principles, the architecture diagram, layout, durable inputs, source-management blocks, engine
steps, rights rules for counterpart instances, backups, security, release freeze, and four
registry rows. The new [InvenTree design page](../../design/integrations/inventree.md) holds the
resource mapping and the API changes observed so far.

| Finding | Resolution |
| --- | --- |
| Requirement 5 of [record 0002](0002-adhoc-knowledge-platform-specification.md) (no versioned schemas or compatibility code before release) conflicts with requirement 6 here | Requirement 5 stays in force for KN storage. The external boundary (interchange contract from `0.1.0`, upgrade steps, adapter profiles) is versioned from its first task. The owner can narrow this exception. |
| Rebuild-from-archive would re-mint entity UUIDs, which breaks IDs stored in InvenTree | An append-only identity event log becomes a durable input and is replayed before raw records. Rebuild reports identity drift and does not regroup silently. |
| The prior resolution order (key, native ID, alias) had no probability level | Fellegi-Sunter style match profiles per class, match records with features and probability, and a calibration gate. Scored matches stay review-only until calibrated. The "no merge by name alone" rule is kept. |
| Identity sat inside the evidence model task `identity-and-fact-selection` | Identity moved to the new `object-identity` capability. The task became `canonical-fact-selection`, and its two dependents were updated. |
| Partial vendor feeds could clear or overwrite unrelated fields | Declared delivery semantics and field-level change sets. Unchanged re-deliveries become confirmations, which never count as independent support. |
| "As complete as vendors supply" had no testable form | A vendor information coverage matrix with a test. Every delivered field is mapped, raw-only, or excluded with a reason. |
| Parts and MPNs existed only in the microelectronics domain, while InvenTree needs them in the core | A shared `supply` schema. The microelectronics domain extends it and does not redefine it. |
| Writing into an owner system is a new outward action | Approved dry-run plans, field ownership, three-way conflict detection, read-back, no deletion, licence filtering, and a human approval task. |
| InvenTree API changes break naive clients | API version probe, OpenAPI capture and normalized snapshots, the snapshot diff classifier, and profiles per API range. The test service pins two releases on either side of the generic parameter change. |

Research inputs, read on 2026-11-21:

- The InvenTree documentation (`latest`) reported API version 582. Breaking or notable entries used
  as fixture cases are listed in the design page.
- The release blog confirms that 1.2.0 replaced the part parameter models with generic parameter
  models. Release notes for 1.6.0 were not found. The newest stable release is therefore pinned by
  `inventree-test-service` at pin time.
- `https://github.com/volod/vl-itree` returned 404 to anonymous requests, and no local checkout was
  found. Its current version and deployment shape are unknown, and
  `provide-inventree-instance-access` asks the owner for them.

Defaults the owner may change: the calibration gate (precision 0.99 on 200 held-out positive
pairs), that part and category creation in InvenTree is off by default, the default field owners
in the design page, and `owner_private` rights for instance data.

## Acceptance evidence

Status: accepted for the documentation change. No production code changed.

- `make lint-spec-plan`: 0 findings, including the research register.
- `make lint-doc-links`: 0 broken links.
- `make lint-md`: exit 0, after three overlong prose lines were rewrapped.
- `make ci`: exit 0 (format, lint, typing, 65 tests, complexity, shell lint, links, spec-plan).
- `git diff --check`: clean.

## Handoff

Plan counts went from 72 tasks (64 agent, 8 human) to 95 tasks (84 agent, 11 human). Statuses went
from CLEAR 60, RUN NEEDED 4, HUMAN-GATED 7, BLOCKED BY HUMAN 1 to CLEAR 77, RUN NEEDED 7,
HUMAN-GATED 9, BLOCKED BY HUMAN 2. The new capabilities are `object-identity` (6 tasks),
`part-supply-model` (2), `data-interchange` (4), and `inventree-exchange` (8 agent tasks, one
optional, plus 3 human tasks). Registry rows were renumbered from 22 to 26.

Changed prerequisites: `evidence-claim-contracts`, `canonical-fact-selection`, `review-queue-cli`,
`engine-skeleton`, `mapping-and-quality-rules`, `obsidian-export-core`,
`analyst-fact-explanation`, `microelectronics-domain-contracts`, `bilingual-acceptance-suite`,
`security-test-suite`, and `approve-release`. The priority human task is now
`provide-inventree-instance-access`.

## Revision after owner feedback

The owner reviewed the first version and decided:

1. Sources declare nothing about completeness or delivery semantics. KN decides how a value updates
   an object: it fills an absent attribute, and it updates or ignores a present one by a priority
   rule (source rank, data timestamp, data reliability).
2. Repository access to `vl-itree` is granted.
3. `vl-itree` is released together with KN on the latest InvenTree release, so no historical
   InvenTree schemas are tracked. InvenTree is still an uncontrolled third-party application.
4. Every other decision keeps the defaults above.

Resolutions:

| Feedback | Change |
| --- | --- |
| Sources declare nothing | `kn.delivery`, the crawler `delivery` block, and the `snapshot`, `delta`, and `patch` semantics are removed. Change sets compare a record with its previous version (`added`, `changed`, `unchanged`, `emptied`, `not_stated`). Records keep a `last_seen` time, and absence never clears or deletes. |
| Priority rule | A new [update policy](../../design/spec.md#update-policy) with the `kn.updatePolicy` extension. Modes are `priority`, `latest_observed`, `accumulate`, and `fixed`. Criteria are reliability, then source rank, then data time, then a tie that becomes a conflict. Outcomes are filled, replaced, ignored, corroborated, and conflict. A reviewed source rank table uses the classes `first_party`, `authorized_channel`, `owner_entered`, `third_party`, and `unranked`. The result does not depend on arrival order. `canonical-fact-selection` owns it. |
| Repository access | The repository was read at commit `4775dcd`: the standard InvenTree Compose stack (PostgreSQL 17, Redis, Caddy) with no plugins, the floating `stable` tag, automatic migrations, plain HTTP on host port 8080, and a backup script. The [design page](../../design/integrations/inventree.md#the-vl-itree-deployment) records these facts. |
| No historical schemas | One target release, pinned by exact tag in KN and `vl-itree`. Legacy parameter support and the two-release matrix are removed. Historical API changes remain only as diff-classifier fixtures. The runtime probe compares the schema digest with the target. Drift allows compatible reads and blocks writes. `inventree-upgrade-check` checks each candidate release before adoption. |

Plan changes: `vl-itree-baseline-capture` and `vl-itree-upgrade-compatibility` are removed.
`inventree-upgrade-check`, `vl-itree-read-acceptance`, and `vl-itree-write-acceptance` are added.
`upgrade-vl-itree-instance` becomes `align-vl-itree-release`, where an agent prepares the exact tag
pin in `vl-itree` and the owner deploys it. `partial-update-tracking`, `canonical-fact-selection`,
and the InvenTree tasks are rewritten. Prerequisites change for `identity-match-calibration`,
`approve-inventree-write-exchange`, `inventree-change-feed`, and `approve-release`. The release
approval now also requires the upgrade check on any newer stable release.

Plan counts went from 95 tasks (84 agent, 11 human) to 96 tasks (85 agent, 11 human). Statuses are
CLEAR 78, RUN NEEDED 7, HUMAN-GATED 9, BLOCKED BY HUMAN 2. `make lint-spec-plan`,
`make lint-doc-links`, `make lint-md`, and `make ci` passed on the revised tree.

## Second revision after owner feedback

The owner answered the open questions:

1. The owner's entries rank higher than vendor data.
2. "Verified" was undefined. If it means human review, ranking should simply prefer verification
   by a higher-ranked source.
3. Prepare a prompt that upgrades `vl-itree` to the latest InvenTree release. The owner then
   creates the exact release tag to pin.
4. `vl-itree` may run on another machine. The prompt must require TLS, and the `.env` template must
   fail when a working instance keeps an unchanged password.

Resolutions:

| Feedback | Change |
| --- | --- |
| Owner entries rank higher | `owner_entered` becomes the highest rank class, above `first_party`. An owner value that differs from a first-party value is flagged `owner_override` and listed by `kn review list --overrides`. Echo suppression in the exchange ledger keeps values KN wrote from coming back as owner entries. An owner edit in InvenTree to a KN-owned field becomes an owner claim, not a conflict. |
| "Verified" undefined | Verification states are now derived labels, defined in the [update policy](../../design/spec.md#update-policy), and are not ranking criteria. A review decision is an `owner_entered` assertion. A candidate value ranks by its best supporting claim: source rank, then evidence class, then data time within one source. Equal-rank disagreement between different sources is a conflict. Repetition never adds rank. |
| Upgrade prompt | [vl-itree upgrade prompt](../../design/integrations/vl-itree-upgrade-prompt.md): pin every image by tag and digest, vendor the `Caddyfile`, and document the upgrade and restore procedure, including the secret key. The prompt reports the tag and digest for the owner's release tag. `deploy/versions.yaml` records the InvenTree tag, digest, and `vl-itree` release tag. |
| TLS and password guard | [vl-itree requirements](../../design/integrations/inventree.md#vl-itree-requirements): HTTPS for any non-loopback listener, an owner certificate or an internal CA with an exported root, and a bind address defaulting to loopback. Secrets live in an untracked local file. The launcher refuses missing, placeholder, default, or short passwords outside a loopback-only development mode, and existing databases get a scripted rotation. KN refuses plain HTTP and failed certificate verification for non-loopback instances. |

Plan changes: `canonical-fact-selection`, `exchange-binding-ledger`, `inventree-test-service` (now
with a test CA), `inventree-read-import`, `inventree-write-export`, `vl-itree-read-acceptance`,
`provide-inventree-instance-access`, and `align-vl-itree-release` are revised. Task counts are
unchanged at 96 (85 agent, 11 human).
