# Identity Contracts

The editable ODCS source is
[`src/kn/contracts/resources/identity/1.0.0.json`](../../../src/kn/contracts/resources/identity/1.0.0.json).
Its local reference catalog defines exact source-anchor comparison. Class profiles use the
[profile schema](match-profile.schema.json) and the semantic validation in
`kn.identity.profiles.Profile`. Load a reviewed profile by class.

| Entity class | Profile |
| --- | --- |
| `core.organization` | [Organization](match-profiles/organization.json) |
| `core.manufacturer_part` | [Manufacturer part](match-profiles/manufacturer_part.json) |
| `core.orderable_variant` | [Orderable variant](match-profiles/orderable_variant.json) |
| `core.supplier_offer` | [Supplier offer](match-profiles/supplier_offer.json) |

The profiles ship uncalibrated. Keep the exact version and digest of profiles used for durable
records so the comparator results and probabilities can be reproduced. A calibrated revision
requires a held-out evaluation reference.

The [event schema](event.schema.json) is generated from `kn.identity.events.Event`. Every JSON
Lines entry carries its sequence, predecessor digest, event digest, UTC instant, actor, reason,
evidence, optional decision reference and discriminated payload. A match event also records the
profile digest and version, candidates, comparator evidence, weights, score, probability and
decision. New matches carry a trace with the request digest, source version, route, prior,
expected follow-up count and minted ID if applicable. Attribute events written by the matcher
name their contributing source record, so matching keeps one view of evidence per record. Earlier
events without either optional field keep their canonical bytes and hashes. Tests compare both
schemas with their Python models.

Partial-update tracking appends a version and its change set, or a `record_seen` sighting of an
already recorded version in a later fetch. Each field change's hashes must agree with its class:
`added` has only a current hash, `changed` and `emptied` have two different hashes, `unchanged`
has two equal hashes and `not_stated` has no current hash. Replay also checks current hashes
against the version's field hashes.

A forced merge can carry a second authoritative identifier observation in its payload. The
existing matching identifier must belong to the other active participant and be valid at the
merge time. Reviewed merge payloads preserve the original v1 representation.

The storage contract declares `kn.identity` on objects and source records and the shared
`kn.humanVerification` trait on every dataset. Decision references and imported verification text
grant no human verification stamp. See the [available registry and replay
interfaces](../../../docs/impl/current/object-identity.md) for trust and transaction boundaries.
