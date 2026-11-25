# 0043 SKOS Reference Tools

## Work contract

Direct request: add a Make target that installs every dependency of the SKOS reference check,
including Java 21 and Apache Jena.

## Implementation and decisions

`make skos-reference-tools` installs the pinned Eclipse Temurin JRE 21.0.13.1+2 and Apache Jena
6.3.0 under `DATA_DIR/tools/`. It uses the checksum-verified archive installer that already
installed Jena. `kn.quality.prerequisites --tool NAME` selects downloaded tools and skips the host
checks. A tool that declares a `platform` refuses to install elsewhere, and the JRE is pinned for
`linux/amd64`. `make skos-reference-check` sets `JAVA` to the pinned runtime, which the `riot`
launcher prefers over `JAVA_HOME` and `PATH`. Its summary names both versions.

The target does not install a system package. The [reproducible
environment](../../design/spec.md#reproducible-environment) section keeps system packages outside
the project's control, and a package would need root and would change the host's default Java.
Record [0026](0026-adhoc-independent-rdf-parsers-and-host-prerequisites.md) had made Java 21 a host
prerequisite because the host had it at the time. This host now has only Java 1.8, and Jena was
its only user, so `java` left `host_prerequisites`. `make bootstrap` installs both archives,
because it installs every declared tool.

The JRE came from the Adoptium API's latest Temurin 21 JRE for Linux x64. Its SHA-256 matched
the API and the release's `.sha256.txt` file. `gpg --verify` reported a good signature from the
Adoptium GPG key `3B04D753C9050D9A5D343F39843C48A565F8F04B`, checked in a temporary keyring. The
archive has one top-level directory and only relative links inside it. The manifest pins its
SHA-512.

## Acceptance evidence

Status: accepted on 2026-11-25.

- `make skos-reference-tools` installed both archives in 93 seconds, and a rerun returned at once.
  The installed runtime reports `Temurin-21.0.13.1+2`.
- `make skos-reference-check` passed: all 16 schemes validated on the pinned runtime with no
  error or warning. The summary is under `$DATA_DIR/skos-reference/48c6f291150846bea8c1ca7e5d3b9398/`.
- `make bootstrap` and `make doctor` now pass on this host.
- `tests/quality/test_prerequisites.py` and `tests/quality/test_skos_reference.py` cover the
  manifest pins, tool selection without host checks, unknown tool names, a platform mismatch, the
  `JAVA` setting and a missing runtime or Jena.
- `make ci` and `make lint-md` passed.

## Handoff

No plan task changed. Moving the JRE to a newer update follows the steps in the
[development guide](../../guide/development.md#setup).
