# Current Implementation

This index describes behavior available now. For product intent read the
[specification](../design/spec.md); for work that remains read the [forward plan](plan.md). For
research questions that stopped, and what would reopen them, read the
[closed-research register](future-research.md).

## Documentation shape

Small areas stay as one page. When an area grows, its page becomes a short orientation and index,
and focused topics move under `current/<area>/`. New pages must be linked from their area in the same
change. Write behavior, modules, commands, and durable findings at the narrowest level.
[Task records](records/README.md) preserve acceptance evidence.

## Areas

Each page under [`current/`](current/README.md) is listed here with what it owns. The tooling and
documentation checks that came with the template are described in the
[development guide](../guide/development.md).

| Page | Owns |
| --- | --- |
| [Product core](current/product-core.md) | Distribution, `kn` import package, `kn` and `kn-plan` commands, and identity verification |
| [Runtime platform](current/runtime-platform.md) | Compose stack, the PostgreSQL and PostGIS service, `make db-*` targets, schemas, roles, and the version manifest |
