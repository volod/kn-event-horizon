# Source Investigation Report

Use this template after an [authorized capture](../source-onboarding.md#3-capture-and-investigate).

## Capture and coverage

- Qualified source ID, investigator, configuration revision, and sampling approval reference.
- Run ID, UTC capture time, archive record locators, and schema or codebook edition and fingerprint.
- Endpoints or dataset subsets covered and actual requests, time and bytes against the budget.
- Stop conditions encountered, missing pages or intervals, and other coverage gaps.

## Native data and proposed mappings

- Native record key, version field, cursor behavior, and how samples support each choice.
- Native fields, units, time semantics and codes, with proposed contract field IDs and ontology
  mappings.
- Duplicate, missing, malformed and schema drift examples, with proposed quality checks, error
  codes and retry classes.
- Rights and mapping risks, open questions, and follow-up owners.
- Candidate fixture cases, corresponding archive locators and sanitization worksheet location.
