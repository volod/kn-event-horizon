# Vocabulary URI Namespace Decision

## Work contract

```markdown
#### decide-vocabulary-uri-namespace

Exported vocabulary terms use `urn:kn:term:<id>`, but `kn` is not a registered URN namespace, and
the URIs become references in other systems once an export is shared.

- Serves: `ontology-taxonomy` -- [Ontology and taxonomy](../design/spec.md#ontology-and-taxonomy)
- Agent status: HUMAN-GATED
- Execution stage: MODEL
- Dependencies: The owner chooses a base that the owner controls: an HTTPS path on a domain the
  owner holds, or a `tag:` URI (RFC 4151) with an authority the owner holds. An agent prepares the
  options with their consequences, as described in finding ON-09 of the
  [ontology audit](records/0025-ontology-taxonomy-ontology-taxonomy-implementation-audit.md#findings).
- User-visible outcome: A recorded URI base, applied by the agent to the SKOS export while no
  consumer stores the old URIs.
- Scope boundary: The decision and the export change only. Qualified term IDs stay unchanged; no
  web service is published.
- Data and artifact paths: `src/kn/semantic/skos.py`, `tests/semantic/`, and the task record.
- Execution path: The owner picks the base. The agent changes the URI function and its tests and
  re-exports every scheme.
- Acceptance gates: Every exported term URI uses the recorded base, the IDs inside them are
  unchanged, and the export still parses and round-trips its labels.
- Documentation target: `current/ontology-taxonomy.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The owner reported registering `summa.dev` and requested a registered URN namespace using it.
That selects a domain authority and a URN scheme for this task. The implementation uses the
existing [IANA `publicid` namespace](https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml#urn-namespaces-1)
and the domain-based owner identifier specified by [RFC 3151](https://www.rfc-editor.org/rfc/rfc3151.html#section-2).

The formal public identifier `+//IDN summa.dev//NONSGML KN Event Horizon Vocabulary//EN`
gives the exporter the default base `urn:publicid:%2B:IDN+summa.dev:NONSGML+KN+Event+Horizon+Vocabulary:EN`.
The owner also requested a configurable domain. `KN_VOCABULARY_DOMAIN` supplies the authority for
each export through the process environment or the shared `.env` loader. The same processed
domain is used for terms, metadata, and label selections. Malformed domains fail before writing
an export.
Use distinct RDF fragments for vocabulary terms, metadata, and label selections. The fragments
identify RDF resources within a single vocabulary, so compare the complete IRI for RDF identity.
Under [RFC 8141 URN equivalence](https://www.rfc-editor.org/rfc/rfc8141.html#section-3.1), these
IRIs share the same assigned name. The project relies on continued control of the domain to
maintain the owner identifier. The export requires no DNS lookup or resolver.

The term fragment and `dcterms:identifier` retain the stored qualified ID verbatim.
The [SKOS export reference](../current/ontology-taxonomy/skos.md#interchange-mapping) defines
the fragments. Repository references to the earlier export IRIs appeared in the exporter and
documentation. The semantic model and CLI both use qualified IDs as inputs.

## Acceptance evidence

Accepted. `make ci` passed all checks and 1164 tests, with 99 integration or heavy tests
deselected by the standard gate.

- `.venv/bin/python -m pytest -q -x tests/semantic/test_skos_reviewed.py` reproduced the old
  `urn:kn:term:` IRI before the fix.
- `.venv/bin/python -m pytest -q -x tests/semantic/test_skos_cli.py -k configured_namespace`
  reproduced the ignored domain override before the configuration change.
- `.venv/bin/python -m pytest --override-ini addopts='' -q tests/semantic tests/e2e/test_skos.py tests/quality/test_skos_reference.py`
  passed 283 tests. RDFLib and Oxigraph agreed on the parsed triples for all 16 schemes. The
  regression check matched exported term IRIs to the stored qualified IDs and verified the two
  display selections, and the fixtures verified English and Ukrainian label round trips. CLI
  cases verified normalization and rejection of invalid domains before output.
- `make skos-reference-check` and `KN_VOCABULARY_DOMAIN=Vocabulary.Example.Test. make skos-reference-check`
  each passed all 16 schemes with Apache Jena RIOT 6.3.0. Both used
  `JVM_ARGS=-Djdk.net.hosts.file=<temporary-loopback-hosts-file>` to provide a loopback entry
  for the local hostname after Java's default lookup failed in the sandbox. The summaries and
  exports are under `$DATA_DIR/skos-reference/3453907a876f4a2484ab908ba98ffc4e/` for the default
  domain and `$DATA_DIR/skos-reference/72dcfc4d6aac47e6bfa0f19de878daf2/` for the override.
  RDFLib graph comparison confirmed that the 16 pairs differ only in the URI authority.
- A CLI smoke test loaded the override from a temporary `.env` with `kn_load_env` and exported
  `gdelt.services.scheme`. The resulting `$DATA_DIR/skos/490e8cbd3dff4d42b63e5cf7168b42f9/vocabulary.ttl`
  used the normalized authority and reported 13 concepts and 14 Ukrainian fallbacks.

## Handoff

`make plan-status` changed from 119 tasks (106 agent, 13 human) to 118 (106 agent, 12 human).
The ontology-taxonomy capability stays planned. The `vocabulary-namespace-implementation-audit`
task now points to this decision and can proceed.
