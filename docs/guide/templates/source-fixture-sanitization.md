# Source Fixture Sanitization Worksheet

Use this template while [preparing fixtures](../source-onboarding.md#4-build-and-sanitize-fixtures).
Record archive locators only where the intended reader may access them.

- Fixture path, test case, configuration revision, and source ID.
- Approved archive locator or indication that the fixture was generated from a synthetic example.
- Rights for committing the fixture and any required attribution.
- Fields, encodings, key relationships and failure modes the fixture preserves.
- Categories omitted or replaced, covering credentials, authorization and cookie headers,
  secret query values, personal data, restricted records and embedded metadata. Record field
  names and categories only.
- Confirmation that filenames, free text, nested records and encoded values were reviewed.
- `make fixture-check` and parser test results, reviewer and review date.
