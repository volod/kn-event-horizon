# 0057 Raw archive implementation audit

## Work contract

```markdown
#### raw-archive-implementation-audit

The archive is the durable input that every rebuild replays, so a format or integrity defect would
force a re-fetch that a source may no longer allow.

- Serves: `raw-archive` -- [Raw archive](../design/spec.md#raw-archive)
- Agent status: CLEAR
- Dependencies: The accepted [raw store](records/0055-raw-archive-warc-raw-store.md) and
  [fetch ledger](records/0056-raw-archive-raw-fetch-ledger.md) task records and the
  [implementation audit](../guide/planning-workflow.md#implementation-audits) checks.
- User-visible outcome: Every rebuild replays from a verified archive. The audit record gives every
  check a result and every finding a disposition. The current-state page lists known limitations,
  and each scheduled finding is a plan task.
- Scope boundary: Focus: WARC 1.1 conformance and readability with independent tools; block and
  payload digests; large and streamed payloads; compressed, truncated and partial files; repeated
  payloads; archive commit and index publication recovery; capture-version compatibility; agreement
  between the ledger and the files; retention, backup and licence boundaries. Fixes only; new
  behavior becomes plan tasks. Target-host scale measurements belong to `performance-gate`.
- Data and artifact paths: `src/kn/archive/`, `$KN_RAW_ARCHIVE_DIR`, `$KN_RAW_INDEX_DIR`,
  `tests/archive/`, `docs/impl/plan.md`, and the task record.
- Execution path: Rerun the group's acceptance commands, then work through the audit checks. Read
  WARC with an independent tool, truncate a file, stop a write midway, then restore to a different
  archive root with the index missing and replay a run from the committed archive alone.
- Acceptance gates: An independent WARC reader accepts every file. A truncated or partial file is
  detected and never replayed silently. Digests verify on every replay. A restored tombstoned
  capture stays suppressed, including via a revisit reference. Every finding has a
  severity, evidence, and a disposition, no `blocker` is accepted, and every fix starts from a
  failing regression test. `make ci` passes with the scheduled tasks in the plan.
- Documentation target: `current/raw-archive.md` listed in the [areas index](current.md#areas).
```

## Implementation and decisions

The audit reran the member gates of records 0055 and 0056 on the base tree, then probed each focus
area of the scope boundary with nine probes kept under the evidence directory. Probe 1 builds an
archive with every record kind, including a 16 MiB WARC payload. Probe 2 truncates, empties,
extends or corrupts each committed file kind. Probe 3 sends SIGKILL to a writer midway through a
streamed WARC and blob body, to a reindex and to a purge. Probe 4 backs up, restores to another
root with the index missing, replays through the CLI, and restores an older backup with only the
current tombstones. Probe 5 loses a whole batch. Probe 6 damages another source's manifest.
Probe 7 covers fractional WARC dates, a tombstone copied without its batch and a tightened
redaction rule. Probe 8 reads the archives committed by records 0055 and 0056. Probe 9 checks the
WARC payload ceiling. Every fix started from a failing test (`red-*.log`, `mutant-suite-before.log`).

The independent reader is FastWARC 2.0.1 (Resiliparse, C++, Apache-2.0), pinned in the `dev` extra
with brotli and tqdm as new locked packages. As with Oxigraph in
[record 0026](0026-adhoc-independent-rdf-parsers-and-host-prerequisites.md), it runs in
`make ci`. Version 2.1.0 was published on the day of the audit, so the lock holds 2.0.1.
GNU gzip 1.14 checked gzip member framing separately. A strict validator, warchaeology 5.0.0 from
the National Library of Norway, was downloaded and checked against its published SHA-256. The
session did not permit running the downloaded binary, so it was not run.

The fixes keep every on-disk format: manifest 1, capture metadata 1 and 2, tombstone 1 and fetch
ledger 1. The new reason code is `capture_lost`. A lookup of a detached tombstone's record ID now
reports `capture_tombstoned` instead of `capture_not_found`. `retention.withdraw` gained an
optional batch hint. Staging for commits and tombstones moved from `staging/` to
`staging/_sources/<domain>/<source-id>/`. A leading `_` cannot start a domain name, so the path
never meets the package stager's `staging/<domain>/<source-id>/<run-id>/`.

## Findings

| ID | Severity | Evidence and affected consumer | Owner and disposition |
| --- | --- | --- | --- |
| RAA-01 | major | `probe5-before.log`: after a committed batch directory disappeared, `kn raw verify` passed and both scoped and full reindex published views without it. Its ID then read `capture_not_found`, like an ID that never existed. The specification requires reindex to tell a tombstoned removal from lost evidence. Affects rebuild, restore and evidence resolution. | Raw archive, fixed. Reindex compares the previous view's covered IDs in its scope with the archive and its tombstones, and refuses with `capture_lost` while keeping that view (`ledger.py:155`). Deleting the index accepts the loss. A full reindex over an unreadable view skips the comparison so it can still repair it. Tests: `test_reindex_refuses_to_forget_a_lost_batch`, `test_a_damaged_view_cannot_block_the_full_rebuild_that_replaces_it`. |
| RAA-02 | major | `probe7.log`: a restored backup with a current tombstone whose batch the backup lacks refused every read and verification with `tombstone_capture`. The specified restore applies the current tombstones to the backup, so any withdrawal after a backup broke the restore. A revisit of a target that was not restored failed with `revisit_target` (`red-detached-revisit.log`). Affects `backup-restore-drill` and `rebuild-from-raw`. | Raw archive, fixed. A tombstone whose batch is absent stays detached: it counts, suppresses the capture and its revisits if the batch returns, and lets lookups report `capture_tombstoned` (`catalog.py:169`). A tombstone that names a capture its present batch lacks is still refused. Verification and reindex treat a revisit of a detached target as withdrawn (`catalog.py:237`). Tests: the four cases in `tests/archive/test_restore.py`. |
| RAA-03 | major | `probe6-before.log`: a damaged manifest of one source refused a revisit commit and a withdrawal in another source with `manifest_schema`. Writers for different sources must publish independently. Each revisit batch also read every manifest in the archive. Affects every engine run that revisits unchanged payloads. | Raw archive, fixed. Revisit commits and withdrawals under the source lock read only that source (`writer.py:92`, `retention.py:38`). A withdrawal finds the source through the index when one is configured. Without an index, finding the capture still scans every manifest (`probe6-after.log`), as other ID lookups do (RAA-12). Test: `test_a_damaged_batch_of_another_source_blocks_neither_revisits_nor_withdrawals`. |
| RAA-04 | major | `mutant-suite-before.log`: a release that wrote and expected `WARC-Date` with `+00:00` passed all 35 archive tests, while both archives committed by records 0055 and 0056 became unreadable with `warc_record_fields`. A tightened redaction rule did the same with `capture_redaction` (`probe8.log`). Every compatibility test wrote its archive with the current writer, and no archive fixture was committed. | Raw archive, fixed. `tests/fixtures/archive/committed-v1/` freezes uncompressed records, descriptors, a v1 descriptor, a revisit, a purged capture and its tombstone, with the expected metadata and replay digests. `test_records_committed_by_an_earlier_release_still_read` fails under both mutants (`mutant-suite-after.log`). |
| RAA-05 | minor | Record 0055 ran `warcio check`, from the library that writes the files. No permanent check read the WARC output with an independent parser. | Raw archive, fixed. `test_independent.py` and the committed-fixture test read every record kind with FastWARC in `make ci`. |
| RAA-06 | minor | `probe3.log`: SIGKILL during a streamed body left 4.2 MB and 4.1 MB `pending-*` directories in the archive and 24 KB in the index root. Nothing reclaimed them, and an interrupted bulk blob leaves its partial size. Affects disk quotas under unattended runs. | Raw archive, fixed. The next commit or withdrawal under a source lock removes that source's `pending-*` directories, and reindex does so under its lock (`files.py:82`). Leftovers of other sources and the package stager are untouched. Tests: `test_process_exit_leaves_only_previous_commits`, `test_writers_reclaim_only_what_their_own_lock_left`. |
| RAA-07 | major | `probe4.log`: restoring a backup taken before a purge and applying the current tombstones kept the capture suppressed, but its WARC segment was back on disk and verification reported success. The tombstone does not record whether a purge happened, so nothing can apply it again. Affects deletion obligations after any restore. | Ingestion engine, scheduled feature `capture-retention-enforcement`. Listed under known limitations. |
| RAA-08 | major | `Retention.expires_at` is stored and never acted on, and no forward task marks claims that cite a withdrawn capture `evidence_tombstoned`, which the [retention rules](../../design/spec.md#capture-schema-and-fetch-ledger) require. The current page left them to engine integration without a task. | Ingestion engine, scheduled feature `capture-retention-enforcement`, which `rebuild-from-raw` now requires. |
| RAA-09 | minor | `probe1`: `fastwarc check -p` reported payload failures for every resource, metadata and revisit record. FastWARC defines a payload only for HTTP messages. KN writes a payload digest equal to the block digest for non-HTTP blocks, and the target's payload digest on a revisit, which WARC 1.1 allows. | Raw archive, accepted and documented. The independent test asserts both relations. Reopen if a consumer's WARC reader rejects these fields. |
| RAA-10 | minor | Request records hold the request line and the approved headers. They have no `Host` header, which an HTTP/1.1 request needs. The target is in `WARC-Target-URI`. Adding it would change the bytes that verification compares for existing captures. | Raw archive, accepted and documented. Reopen if an external replay tool needs it. |
| RAA-11 | minor | `probe7.log`: reads reapply the current default redaction, so a later rule that treats another query parameter as a credential makes older captures holding one unreadable. | Raw archive, accepted as fail-closed and documented: such a capture holds what the new rules call a credential, so withdraw, purge and fetch it again. RAA-04's fixture makes any such change fail CI. |
| RAA-12 | minor | `probe2.log` (`unrelated_manifest_truncated`): one truncated manifest stops verification, metadata iteration, reindex and lookups that scan the archive. | Raw archive, accepted and documented: the archive fails closed, the index keeps lookups of other batches working, and the batch is restored from a backup. Reopen if recovery needs partial replay while a batch is lost. |
| RAA-13 | minor | The current page said only to back up captures and tombstones together. Copying `tombstones/` before `captures/` from a live archive can capture a purge midway without its tombstone, which verification refuses. | Raw archive, fixed in the current-state page. With RAA-02, copying `captures/` before `tombstones/` gives a consistent backup. `backup-restore-drill` links the order. |
| RAA-14 | minor | `current/raw-archive.md` linked this audit's plan anchor for conformance and restore, had no known limitations, and named no owner for withdrawn-evidence claims. Records 0055 and 0056 linked the same anchor. | Raw archive, fixed in the current-state page and both records. |

## Six audit checks

1. **Implementation validation.** The member gates pass on the base tree: 35 archive tests
   (`member-unit.xml`). They cover both backends and exact digests, decoded limits, metadata-only
   reads, two sources, idempotency, a writer exit before publication, v1 and v2 metadata,
   corruption, redaction, revisits, relocation, interrupted withdrawal, ledger recovery, scoped
   rebuilds, failed publication, pinned readers and tombstones. `warcio check` and both
   `kn raw verify` formats pass (`member-operator.log`). The archives of records 0055 and 0056
   still verify and reindex (`probe8.log`). The current-state page matched the commands,
   interfaces, paths and error codes except RAA-14, now fixed.
2. **Specification conformance.** Each storage-root, capture, commit, schema, ledger, retention
   and evaluation promise of the [raw archive section](../../design/spec.md#raw-archive) maps to a
   test in `tests/archive/`. The departures were RAA-01, RAA-02 and RAA-03, all fixed, and RAA-04,
   the uncommitted fixture, fixed. Two remain gaps: claims are not yet marked
   `evidence_tombstoned` and expiry is not enforced (RAA-08), and a purge is not re-applied after
   a restore (RAA-07). No behavior exists outside the boundary: no replay UI, shared catalog or
   object store. The consumers `engine-skeleton`, `prefetched-dataset-method`, `rebuild-from-raw`
   and `backup-restore-drill` use `Archive.commit`, `replay`, `metadata`, `iter_metadata` and
   `withdraw` and the ledger queries, whose signatures are unchanged apart from the optional hint.
3. **Design scope.** These decisions would be expensive to change later and were kept. Record and
   fetch IDs are UUID 5 values of the batch key, capture key and role, independent of paths,
   offsets and schema versions. The layout is `captures/<domain>/<source-id>/<run-id>/<batch-id>/`,
   one directory per capture, and `tombstones/<record-uuid>.json`. The KN WARC profile has one
   gzip member per record, in the order payload, request and metadata, with SHA-256 Base32 digests.
   The versions are manifest 1, metadata 2 with version 1 projected, tombstone 1 and ledger schema
   1. The CLI surface is `E_RAW_ARCHIVE` with a reason code. Read-time redaction makes the default
   rules a compatibility surface that may widen but not tighten without a new metadata version
   (RAA-11). New metadata versions extend `decode_metadata`, a new index derives from the archive,
   and object storage needs an equivalent manifest contract. Purge records (RAA-07) are a new file
   kind that leaves version 1 tombstones readable.
4. **Corner cases.** Empty batches and keys outside the identifier pattern are refused. Empty
   bodies, 204 and 304 responses, a status without a reason phrase, CRLF and WARC text inside a
   payload, UTF-8 bodies and fractional seconds round-trip and pass FastWARC (`probe1-build.log`,
   `probe7.log`). Duplicate keys in a batch and duplicate IDs across manifests are refused.
   Captures with equal times replay in fetch ID order, and a revisit cannot precede its target.
   A WARC payload of exactly 16 MiB commits; one byte more is refused before publication, while a
   blob of that size commits (`probe9.log`). Truncated, emptied, extended and corrupted objects,
   descriptors and manifests are refused by verification and replay, and replay writes no bytes
   (`probe2.log`). Metadata-only reads and reindex check presence and size by design. Kills midway
   leave no visible batch, keep the previous index coverage, and finish on retry
   (`probe3-after.log`). Symlinks and parent paths in locators are refused. Credentials are removed
   from URIs, headers and diagnostics. Times are normalized to UTC, and scopes accept any offset.
   The fetch time is the caller's clock; the archive never compares it with wall time, so clock
   skew can only reorder captures, and a revisit must not precede its target. Origin URIs must be
   printable ASCII, so the caller percent-encodes an IRI. The archive stores bytes, so it has no
   bilingual text, and its CLI messages are English by
   [record 0050](0050-adhoc-cli-localization-scope.md). Concurrent sources, retried batches,
   repeated withdrawals and rebuilds from the committed archive alone give identical IDs, rows and
   replay digests (`probe4.log`, `test_committed.py`).
5. **Best practices.** Production code stays typed and passes mypy, Ruff and the complexity gate.
   The archive modules stay at about 250 lines; `inputs.py` and `warc.py` were already slightly
   over. The new dependency is dev-only and pinned in `uv.lock`. Tests are deterministic and
   network-free and keep pyarrow out of forked tests. The fixtures are ASCII and pass
   `make fixture-check`. Diagnostics carry reason codes, never paths or values.
6. **Debt.** The cross-source revisit check in `_affected` became unreachable with the source-scoped
   catalog and was removed; verification and replay still refuse such a reference. The time filter
   of the Parquet reader is shared by both readers. Two withdrawal checks remain by design: the
   catalog check for scans and the tombstone-file check for index lookups. The ledger test that
   counts `read_member` calls asserts an internal; it measures the metadata-only read property
   directly. No TODO, skipped test or weakened check was added.

## Acceptance evidence

Status: accepted on 2026-11-27. Initial `make plan-status`: 110 tasks, 98 agent, 12 human;
BLOCKED BY HUMAN=3, CLEAR=85, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=100, MODEL=10.

The evidence directory is `$DATA_DIR/raw-archive/audit-kPtPdhv8/`, with the probe scripts under
`probes/`. `probes/freeze_fixture.py` produced `committed-v1` from `fixture-source/`. Commands ran
from the project root after `source scripts/shared/common.sh && kn_load_env`.

| Gate | Run and result |
| --- | --- |
| An independent WARC reader accepts every file | FastWARC block digests and GNU `gzip -t` passed 19 of 19 segments, from probe 1, the fixture source and the archives of records 0055 and 0056 (`independent-readers.log`). FastWARC reads every record kind with correct types, IDs and offsets and verifies HTTP payload digests (`test_independent.py`, `test_committed.py`). The strict warchaeology validator was not run (see above). |
| A truncated or partial file is detected and never replayed silently | Verification and replay refuse every mutation in `probe2.log` and write no bytes. Kills midway leave no visible batch (`probe3-after.log`). A lost batch is reported by reindex (RAA-01). |
| Digests verify on every replay | Replay checks the container digest, WARC block digest, payload digest and size before writing. Same-size blob damage is refused (`probe2.log`). |
| A restored tombstoned capture stays suppressed, including via a revisit | A restore to another root with the index missing verifies through the CLI. It suppresses the target, its revisit and a logical withdrawal before and after reindex, and replays the remaining capture by ID from the archive alone (`probe4.log`). With RAA-02, an older backup with current tombstones reads, and a batch restored later stays suppressed (`test_restore.py`). |
| Findings | Each of the 14 findings has a severity, evidence and a disposition. No `blocker` was found. Each fix started from a failing test: `red-loss.log`, `red-isolation.log`, `red-restore.log`, `red-detached-revisit.log`, `red-staging.log` and `mutant-suite-before.log`. |
| `make ci` | Passed on the final tree with the scheduled task in the plan: 1,487 tests with 141 local-only tests deselected, and every format, lint, typing, complexity, contract, shell, fixture, documentation and spec-plan check (`ci.log`). No archive test is local-only. |

`make lint-md`, `make lint-spec-plan` and `git diff --check` passed. The probes created no
service; the archives and indexes they wrote stay under the evidence directory.

## Handoff

The audit left the plan, and its group heading went with it. `capture-retention-enforcement`
(RAA-07 and RAA-08) joined the ingestion-engine group before `rebuild-from-raw`, which now requires
it. It requires `source-management-implementation-audit`. The plan stays at 110 tasks, 98 agent and
12 human; BLOCKED BY HUMAN=3, CLEAR=85, HUMAN-GATED=9, RUN NEEDED=13; DELIVERY=100, MODEL=10.
`ingestion-state-contracts`, `engine-skeleton` and `prefetched-dataset-method` no longer require
this audit. `engine-skeleton` links the commit and replay interface, and `backup-restore-drill`
links the backup order. The `raw-archive` capability is now `shipped`. Its remaining gaps are
listed under its known limitations and owned by `capture-retention-enforcement`. The next agent
task is `ingestion-state-contracts`. No commit or push was made.
