# Record 0026: adhoc independent RDF parsers and host prerequisites

## Work contract

Direct requests from the owner while closing the open gate of
[record 0025](0025-ontology-taxonomy-ontology-taxonomy-implementation-audit.md), "The SKOS export
parses with an independent tool": investigate whether `pyoxigraph`, Raptor (`rapper`) or Apache
Jena is the better independent parser, then use both recommended tools. Document the decision, and
make `make venv` ensure that the system prerequisites exist.

## Implementation and decisions

### Parser choice

All three candidates are independent of RDFLib, which writes the export. They were compared on
conformance evidence, maintenance, reproducibility under the project rules, and whether the check
can stay permanent rather than being run once.

| Candidate | Evidence found | Decision |
| --- | --- | --- |
| `pyoxigraph` 0.5.13 (Oxigraph, Rust; MIT or Apache-2.0) | Released 2026-10-22; wheels for CPython 3.12 and 3.13 on Linux x86-64, about 8 MB; its README calls the implementations "nearly fully conformant"; not in the W3C report, which predates it | Used as the permanent check: pinned in the `dev` extra and `uv.lock`, so a network-free unit test runs it in `make ci` and on GitHub |
| Apache Jena RIOT 6.3.0 (Java, Apache-2.0) | Every row read of the [W3C Turtle implementation report](https://w3c.github.io/rdf-tests/rdf/rdf11/rdf-turtle/reports/) passes; a Jena maintainer co-edited the test suite; `riot --validate` is strict; Jena 6 needs Java 21, which the host has | Used as the reference check: installed by `make bootstrap` from a pinned archive and run by `make skos-reference-check`, locally only |
| Raptor 2.0.16 (C) | Last release 2023-03-01; passes the report rows read; available as `raptor2-utils` in Ubuntu 24.04 | Not used: no newer evidence than the other two, older, and not pinnable through the lock file |

The owner allowed installing system packages. None was needed: Java 21 was already present, and
Jena is a release archive rather than a system package.

### Host prerequisites

`deploy/versions.yaml` gained `host_prerequisites` (Git, Make, uv, Docker Compose v2 or newer, Java
21 or newer, each with a purpose and an install hint) and `downloaded_tools` (Apache Jena 6.3.0
with its `archive.apache.org` URL, SHA-512, signing-key fingerprint and install directory).
`archive.apache.org` keeps every release, so the URL survives newer Jena releases.

`kn.quality.prerequisites` reads that manifest. `make bootstrap` and its alias `make venv` sync the
locked environment, then check every prerequisite and fail with one message per missing command
or too-old version. They never install system packages, as the
[reproducible environment](../../design/spec.md#reproducible-environment) section states. Each
downloaded tool is installed under `DATA_DIR/tools/` only when the archive matches the pinned
SHA-512; extraction uses the tar `data` filter in a staging directory followed by one rename, and
a marker records the checksum. A directory without the marker is never reused. `make doctor` runs
the same checks without installing. GitHub Actions installs with `uv sync` and runs the unit gate,
so it needs neither Docker nor Java. The specification section now describes the manifest, the
checks and the tool archives.

`kn.quality.skos_reference` exports every reviewed scheme into
`DATA_DIR/skos-reference/<run-id>/`, runs `riot --validate` on each, and fails on a non-zero exit
or any warning. `make skos-reference-check` runs it, and `make ci-local` includes it.

The manifest also named the old `0001_satcom` baseline, which record 0019 had replaced with
`0001_baseline`; it is corrected.

## Acceptance evidence

Status: accepted on 2026-11-22. Logs are in
`$DATA_DIR/acceptance/ontology-taxonomy-implementation-audit-20261122/`.

- Jena 6.3.0 download: SHA-512 `828ac4bc...805f0ce` matched the published `.sha512`, and the
  `.asc` signature was good from key `D99038A1731B8B31B71549EF04C95136D236A58F` (Andy Seaborne,
  code signing key) in the Jena `KEYS` file. The archive had 296 entries, no absolute or parent
  paths and no links. The download is kept under `DATA_DIR/tools/downloads/jena-6.3.0/`.
- `make venv` installed Jena from `archive.apache.org` and reported the host ready; `make doctor`
  agreed.
- `make skos-reference-check`: 16 schemes, 0 failures (`skos-reference-check.log`).
- `jena-validate.log` and `parser-counts.log`: the audit's 16 exports pass `riot --validate`, and
  RDFLib, Oxigraph and Jena agree on every triple count, from 97 to 1,720 triples.
- `tests/semantic/test_skos_independent.py`: 17 passed; Oxigraph's triple sets equal RDFLib's for
  every scheme, and Oxigraph refuses an IRI with a space.
- `tests/quality/test_prerequisites.py` and `test_skos_reference.py`: 17 passed, network-free,
  covering missing and too-old commands, a once-only install, checksum mismatch, parent paths,
  absolute links, a missing executable, an HTTP URL, an unverified directory, and RIOT errors and
  warnings.

## Handoff

No plan task was added or removed by this record. Record 0025 closes its open gate with this
evidence. A later tool archive is one more `downloaded_tools` entry; a later host command is one
more `host_prerequisites` entry.
