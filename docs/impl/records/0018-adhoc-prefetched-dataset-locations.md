# Record 0018: adhoc prefetched dataset locations

## Work contract

Direct request from the owner, after the
[data contracts audit](0017-data-contracts-data-contracts-implementation-audit.md): the SATCOM
package may be published on Google Drive, so that it can be re-imported periodically. Investigate
the best approach, for example a `.env` variable that holds a local path or a Google Drive link,
then write the specification and plan tasks. No production code changes.

## Implementation and decisions

The [ingestion engine](../../design/spec.md#ingestion-engine) section gained a prefetched datasets
design. An owner-supplied package is a `bulk_file` source. Its location comes from an environment
variable that its configuration names: a local directory, a local ZIP, or `gdrive:<file-id>` read
through the Drive API v3 with a read-only service-account key. The section also states its boundary,
evaluation items and negative result, and registry row 12 names the new evaluation. The
[data contracts](../../design/spec.md#data-contracts) section links the design from its SATCOM
paragraph.

Decisions and the alternatives they replace:

- The project fetches, not the coding agent. The Google Drive connector of a Claude session is
  available only inside a live session. Make, CI and the planned orchestration cannot use it, a
  cloud agent cannot reach the local `DATA_DIR` or database, and the package bytes would pass
  through the model context instead of the raw archive. It stays usable for a one-off copy.
- One ZIP per release instead of a Drive folder. Drive can convert uploaded CSV and workbook files
  to Google formats, a folder can hold two items with one name, and a folder is not one snapshot.
  The snapshot identity covers the unpacked files, so a rebuilt ZIP of the same files imports
  nothing.
- The Drive API with a service account instead of a link-sharing URL. The public download endpoint
  is undocumented, adds a virus-scan interstitial and a redirect to another host, returns no
  checksum to verify, and lets anyone with the ID read the data. The API returns the SHA-256 and the
  head revision, so an unchanged file costs one metadata request, the documented equivalent of a
  conditional request. The file ID may be committed, because only the shared account can read it.
- One runtime dependency, `google-auth`, signs the service-account token. `requests` is already in
  the lock file through other packages.
- Periodic runs belong to [orchestration](../../design/spec.md#orchestration). Until its flows
  exist, an operating-system timer may run `make satcom-fetch satcom-import`.

Plan changes:

- `dataset-package-locations` (agent lane, ingestion engine): the location resolver, the Drive
  client, verification, safe unpacking, and the raw run directory, first used by the SATCOM
  commands. It has no prerequisite.
- `publish-satcom-drive-package` (human lane, ingestion engine): the owner publishes the ZIP,
  shares it with a service account, sets `.env`, and approves the rights and periodic fetches; the
  agent then runs the live fetch. It requires `dataset-package-locations`.
- `prefetched-dataset-method` now requires `dataset-package-locations` and takes the location
  variable from the source configuration.

## Acceptance evidence

Status: accepted on 2026-11-22. `make lint-spec-plan` reports 0 findings, `make lint-md` passes
with 0 broken links, and `make plan-status` shows the new counts below. No code changed, so no test
ran for this record.

## Handoff

Plan counts before: 113 tasks (102 agent, 11 human); statuses BLOCKED BY HUMAN 2, CLEAR 94,
HUMAN-GATED 9, RUN NEEDED 8. Plan counts after: 115 tasks (103 agent, 12 human); statuses BLOCKED BY
HUMAN 3, CLEAR 95, HUMAN-GATED 9, RUN NEEDED 8. Priority tasks unchanged:
`storage-contract-registry` and `provide-inventree-instance-access`.

Capability affected: `ingestion-engine`, which stays `planned`. The next action is
`dataset-package-locations`; the owner's inputs are listed in `publish-satcom-drive-package`.
