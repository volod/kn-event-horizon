# Source Onboarding Workflow

## Work contract

````markdown
#### source-onboarding-workflow

Coding-agent source investigation needs a fixed, safe procedure before the first real source.

- Serves: `source-management` -- [Source management](../design/spec.md#source-management)
- Agent status: CLEAR
- Dependencies: The [crawler configuration and enablement checks](current/source-management.md#validate-crawler-configurations).
- User-visible outcome: Contributors follow a documented workflow with templates for the terms
  dossier, investigation report, fixture sanitization, and review checklist. `AGENTS.md` states the
  untrusted-content rule for agents reading source material.
- Scope boundary: Documentation and templates only, plus a fixture-sanitization check that rejects
  credentials and personal data in fixtures.
- Data and artifact paths: `docs/guide/source-onboarding.md`, `docs/guide/templates/`,
  `AGENTS.md`, `tests/fixtures/`, `tests/quality/`.
- Execution path: Write the guide from the specification's steps, and add the sanitization check to
  `make ci`.
- Acceptance gates: The guide links resolve. The sanitization check fails on a planted secret
  fixture. `make ci` passes.
- Documentation target: `current/source-management.md` listed in the
  [areas index](current.md#areas).
```

## Implementation and decisions

The [contributor guide](../../guide/source-onboarding.md) follows the seven specification
steps and links four templates. The repository rules treat source content as untrusted data.
Sampling and enablement both use the existing approval workflow and crawler validation.

`make fixture-check` runs offline in the shared CI gate. It scans regular UTF-8 files in
fixture directories anywhere under `tests/`. It uses bounded reads, preserves parser fixture
syntax, and reports locations and rule categories. Manual review covers rights, unlabeled
personal data, and custom encodings and fields. The check uses the standard library.

- **ONBOARD-01 (major, fixed).** Initial focused tests allowed multiline and percent-escaped
  credential values and a partial redaction marker. Source fixture review consumes the check.
  Source management fixed the rules with regression tests for all four cases.

## Acceptance evidence

Status: accepted.

- `make plan-status` initially reported 123 tasks, 110 agent tasks, 13 human tasks,
  109 DELIVERY and 14 MODEL.
- `make fixture-check` accepted the checkout's 21 fixture files.
- With a synthetic Authorization value in a temporary HTTP fixture, `make ci` stopped at
  `fixture-check` with exit status 2 from Make. The diagnostic reported the path and
  credential rule. The log contained zero copies of the planted value.
- The focused run passed 157 tests, including the 29 fixture-check cases.

  ```bash
  .venv/bin/python -m pytest -o "cache_dir=$DATA_DIR/cache/pytest" \
    tests/sources tests/quality/test_fixture_sanitization.py \
    --junitxml "$onboarding_run/fixtures.xml"
  ```

- `kn --json source validate` accepted the candidate fixture and an enabled copy referencing
  the passing JUnit report. It exited 1 with `E_SOURCE_CONFIG` at `$/approval/reference`
  when that reference was removed.
- Clean `make ci` passed all checks and 1,083 tests, with 92 local-only tests deselected.
  `make lint-md` and `git diff --check` passed. The acceptance run used offline fixtures.
- Evidence is under `$DATA_DIR/source-onboarding/check-6BCKgJzf/`.

## Handoff

The source admission audit consumes this record and the
[current workflow](../current/source-management.md#onboard-a-source). Source run status
remains planned under `ingestion-state-contracts`.

`make plan-status` changed from 123 to 122 tasks, 110 to 109 in the agent lane, and 109 to
108 in DELIVERY. The human lane stays at 13 and MODEL at 14. The next ready agent task is
`source-admission-implementation-audit`.
