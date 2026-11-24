# 0040 Identity match engine

## Work contract

```markdown
#### identity-match-engine

Data about one object from different sources must meet at one KN ID through explained, scored
decisions.

- Serves: `object-identity` -- [Object identity](../design/spec.md#object-identity)
- Agent status: CLEAR
- Dependencies: [Identity lifecycle and replay](current/object-identity.md#replay-and-integrity).
  The smallest justified string-similarity dependency, or a local comparator with tests.
- User-visible outcome: The resolver applies exact authoritative identifiers, existing
  source-qualified links, scored matching over declared identity attributes, and alias candidates,
  in that order. Each decision writes a match record with features, comparator outcomes, weights,
  score, probability, profile digest, and the outcome: auto-link, review, or new object.
- Scope boundary: Matching behavior and validation against the
  [early profile schema](../../contracts/core/identity/match-profile.schema.json), including
  rejection of name-only link paths.
  Normalizers for MPNs, organization names, web domains, and identifiers. Blocking, comparators,
  Fellegi-Sunter weights, thresholds and margin, the `calibrated` flag that keeps uncalibrated
  profiles review-only, and deterministic tie-breaking. Profiles for organization, manufacturer
  part, orderable variant, and supplier offer. Calibration on real records comes in
  `identity-match-calibration`.
- Data and artifact paths: `src/kn/identity/matching/`, `contracts/core/identity/match-profiles/`,
  `tests/identity/`, `tests/fixtures/identity/`.
- Execution path: Write labeled synthetic fixtures first, then the resolver.
- Acceptance gates: Fixtures with one MPN from two manufacturers, packaging variants, a renamed
  organization with a stable LEI, name-only similarity, and two close candidates produce their
  declared decisions. Permuted input order gives identical decisions. A match record reproduces its
  score and probability. A profile whose link threshold names alone can reach fails validation.
- Documentation target: `current/object-identity.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The [lifecycle acceptance record](0039-object-identity-object-lifecycle-operations.md) and the
registry replay API satisfied the prerequisite. The Python source-adapter entry point applies
the authoritative, existing-link, scored and alias paths under the existing writer lock. It
stores decisions, creates bindings where appropriate, and registers accepted identity
observations for subsequent resolution. Exact conflicts become review decisions with existing
ownership intact. A reviewed profile and receipt together reproduce the comparator outcomes
and posterior.

The organization, manufacturer part, orderable variant and supplier offer profiles ship
uncalibrated. The string comparator uses the Python standard library. Web domain normalization
uses the pinned Public Suffix List and IDNA support offline. New matching trace fields are
optional for compatibility with historical event hashes.

| Finding | Severity | Evidence, owner and disposition |
| --- | --- | --- |
| IDMATCH-01 | Major | Early profile validation allowed a threshold whose nondiscriminating evidence could reach it. The matching profile validator now checks the maximum possible nondiscriminating score and rejects discriminating name fields. Fixed in the resolver scope. Evidence is in `test_names_cannot_reach_link_threshold` and `test_camel_case_name_cannot_be_declared_discriminating`. |
| IDMATCH-02 | Major | Built-in IDNA encoding can fold distinct domains to one key. The organization profile now uses IDNA normalization that preserves the distinct fixture domains. Fixed in the normalizer. Evidence is in `test_normalizers`. |
| IDMATCH-03 | Major | A partial match append could leave a decision before its binding. The matching writer now stores the expected follow-up count, validates the full batch before append and resumes a complete prefix on identical retry. New matcher requests wait for that retry. Fixed in the matching writer. The interruption and divergent-history tests cover recovery and refusal. |

## Acceptance evidence

Status: accepted. Final `make ci` passed with 1,157 tests and 99 local-only tests
deselected. The log is in `$DATA_DIR/identity/matching-cRY2dC6l/ci.log`.

- The fixture-first run failed during collection before the matcher existed. The completed
  `.venv/bin/python -m pytest tests/identity` run passed 107 tests. Labeled cases distinguish
  manufacturers and packaging, link a renamed organization through its LEI, review name
  similarity and competing high scores, and preserve decisions under input permutation. The
  tests compare the numeric score and probability with explicit likelihood and posterior
  calculations.
- The local PostGIS run of `tests/integration/test_identity*.py`,
  `tests/integration/test_rebuild*.py` and `tests/integration/test_model_baseline.py` passed
  31 tests. Evidence is in `$DATA_DIR/identity/matching-cRY2dC6l/postgres-results.xml`.
- The final PostGIS rerun of `tests/integration/test_identity_matching.py` and
  `tests/integration/test_identity.py` passed eight tests with the follow-up count and pending
  request check. Evidence is in `$DATA_DIR/identity/matching-cRY2dC6l/postgres-final.xml`.
  Both local services were stopped and their temporary databases removed.
- `make test-bilingual` passed 100 tests. Evidence is in
  `$DATA_DIR/e2e/bilingual-L9Kf8ZFe/manifest.json`.
- `make lint-md` and `uv lock --check --offline` passed.
- An interim `make ci` run overlapped event schema regeneration. The schema comparison used the
  pre-change imported model and failed. The focused identity suite passed against the regenerated
  schema before the final CI rerun.

## Handoff

The plan changed from 120 to 119 tasks, with 107 to 106 agent tasks and 13 human tasks.
`identity-resolution-implementation-audit` uses this record and is the next agent task.
`identity-match-calibration` owns real-record calibration and `review-queue-cli` owns applying
review decisions. The object-identity capability remains planned while its other evaluation
gates remain open.
