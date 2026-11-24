# Identity Contracts

The editable ODCS source is
[`src/kn/contracts/resources/identity/1.0.0.json`](../../../src/kn/contracts/resources/identity/1.0.0.json).
Its local reference catalog defines exact source-anchor comparison only. Entity-class matching
profiles use the structural [profile schema](match-profile.schema.json); the matching engine and
calibration gates remain separate tasks.

The [event schema](event.schema.json) is generated from `kn.identity.events.Event`. Every JSON
Lines entry carries its sequence, predecessor digest, event digest, UTC instant, actor, reason,
evidence, optional decision reference and discriminated payload. Both schemas are compared with
their Python models in `tests/identity/`.

A forced merge can carry a second authoritative identifier observation in its payload. The
existing matching identifier must belong to the other active participant and be valid at the
merge time. Reviewed merge payloads preserve the original v1 representation.

The storage contract declares `kn.identity` on objects and source records and the shared
`kn.humanVerification` trait on every dataset. Decision references and imported verification text
grant no human verification stamp. See the [available registry and replay
interfaces](../../../docs/impl/current/object-identity.md) for trust and transaction boundaries.
