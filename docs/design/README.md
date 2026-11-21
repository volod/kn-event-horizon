# Design

The [product specification](spec.md) is the living source of truth for product behavior. It includes
the capability registry, the evaluation contract for each capability, explicit boundaries, and the
process for adding capabilities discovered during implementation.

Domain detail lives in the [space](domains/space.md), [GDELT](domains/gdelt.md), and
[microelectronics](domains/microelectronics.md) design pages. The seed proposals that those pages
reference are described in [domains/README.md](../../domains/README.md). Counterpart-system detail
lives in the [InvenTree exchange](integrations/inventree.md) design page.

The registry order is the implementation line followed by the
[forward plan](../impl/plan.md). `make lint-spec-plan` makes disagreement between those documents a
build failure.

Current behavior is indexed by [current implementation](../impl/current.md).
