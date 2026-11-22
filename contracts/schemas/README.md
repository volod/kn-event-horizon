# Contract Schemas

The canonical schemas live in the Python package so the same bytes work in a source checkout
and an installed wheel. There are no generated or separately maintained copies in this directory.

- [ODCS 3.1.0](../../src/kn/contracts/resources/odcs-3.1.0.json): the official standard, with only
  non-ASCII characters escaped for the repository's ASCII policy.
- [KN extension values](../../src/kn/contracts/resources/kn-extensions.json): closed JSON Schemas
  for every specification family and the existing SATCOM profile. `x-kn-scopes` declares valid
  contract, table, and field locations. References are structural strings; lint does not resolve
  ontology, policy, field, or mapping references.
- [Checksums and upstream source](../../src/kn/contracts/resources/pins.json): both schema hashes
  are mandatory and verified on every lint and compile. The upstream checksum records the original
  ODCS bytes before ASCII escaping.

See [current behavior](../../docs/impl/current/data-contracts.md#contract-lint-and-toolchain)
for commands, diagnostics, supported extension shapes, and compiler boundaries.
