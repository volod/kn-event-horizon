# Official Publication Verification

All 16 reviewed schemes have a publication comparison or an explicit local-vocabulary decision.
The reviewed metadata is in `domains/<domain>/seeds/verification.json`, linked to packaged
`src/kn/semantic/resources/<domain>-verification.json`. Source installations and wheels use the
same review bytes. These reviews were performed on 2026-11-22; they are evidence for the pinned
publication bytes and selected seed content, not a claim that a mutable URL never changes.

Four schemes or scoped subsets are verified. Twelve schemes remain unverified.
A verified subset does not
claim a complete dictionary, reviewed Ukrainian terminology, or official publisher-assigned KN
identifiers. The original concept terms retain their codes, labels, hierarchy and `draft` status. The
[separate OECD scheme and product crosswalks](oecd.md) add verified categories without moving
existing product references.

## Decisions and boundaries

| Scheme | State | Compared scope and result |
| --- | --- | --- |
| `space.esa_tt_4_1` | verified | All 26 domains and 107 subdomains match the ESA abbreviated TD/TS table. TDxx codes and domain-qualified labels are local encodings. The full version also contains TD 3 / TS D, absent from the abbreviated table and seed. All TG leaves are outside this subset. |
| `space.euspa_2026` | verified | All 16 market-segment labels match the report's page 6 list. KN codes are generated from labels, not assigned by EUSPA. Application and use-case dictionaries are outside scope. |
| `gdelt.gkg_themes_2021` | verified | All 43 native codes occur verbatim in the November 2021 linked lookup. Its other 59,272 codes are absent; no hierarchy is inferred from underscores. |
| `space.nasa_tx_2024` | unverified | Sixteen root labels match; TX17 is officially `GN&C`, while the proposal expands it. Subareas and technologies are absent. |
| `microelectronics.ecs_sria_2026` | unverified | Seven chapter headings match ignoring case. Chapter 2.3's PDF heading uses `Methods`; the proposal and publisher web navigation use `Method`. The PDF heading controls this comparison. |
| `gdelt.cameo_v2` | unverified | Twenty-one selected labels agree ignoring case. Code `20` is `USE UNCONVENTIONAL MASS VIOLENCE` in the lookup and `Engage in unconventional mass violence` in the seed. Another 288 distinct numeric codes are absent. |
| `space.esa_gpt_1_1` | unverified | The normalized mixture includes four official segment labels, renamed systems, local codes and extensions. Product leaves are absent; the mixed scheme stays `kb_normalized`. |
| `microelectronics.oecd_2024` | verified | All 29 Figure 9 categories and 25 parent edges match the supplied PDF. KN identifiers and display disambiguation of the two Others labels are explicit; verbatim source labels are retained. |
| `microelectronics.product_v1` | unverified | Figure 9 is uncoded; the normalized seed adds engineering specializations. The user-supplied August 2024 PDF was inspected and checksum-pinned after the initial HTTP 403. The mixed scheme remains normalized. |
| `microelectronics.applications` | unverified | Six ECS areas are mixed with six local application extensions and local APP codes; the scheme stays `kb_normalized`. |
| Other six schemes | unverified | Space, GDELT and microelectronics services, GDELT technology and applications, and microelectronics technology are local vocabularies with no official edition claimed. |

Mismatches are findings, not silent corrections. Every concept in a mismatched scheme remains
under its scheme's `unverified` state, including otherwise matching members. A later correction
requires a reviewed seed edit and a new publication comparison. Original proposal provenance is
retained independently from publication evidence.

The GCAM master codebook was also downloaded, checksum-pinned and decoded as Windows-1252.
Its selected examples `c2.21`, `c10.1`, and `v10.1` match Bodypt, Positive, and Positive (Scored Value).
`wc` and `nwc` are structural fields rather than dictionary dimensions. No GCAM scheme exists in
the reviewed seeds. Its 14 mixed GCAM/tone proposal rows still need mapping; the related-publication
review in the GDELT manifest does not import a dictionary. `gdelt-source-dictionaries` owns that work.

## Primary publications

The manifests record edition, publisher, exact publication URI, SHA-256 when downloadable,
comparison scope, findings with locators, and a checksum of the reviewed seed projection.

- [ESA GPT Issue 1 Rev 1](https://esastar-emr.sso.esa.int/Account/DownloadCompetencesFile?fileType=P),
  July 2011, especially pages 4-17.
- [ESA Technology Tree 4.1, STM-277](https://esamultimedia.esa.int/multimedia/publications/STM-277/STM-277.pdf),
  abbreviated table on printed pages 10-12 and full table from page 13.
- [NASA Technology Taxonomy 2024](https://www.nasa.gov/wp-content/uploads/2024/10/nasa-2024-technology-taxonomy-report-low-resolution-final-20240730-tagged.pdf),
  contents page ii and root chapters, including TX17 on printed page 211.
- [EUSPA EU Space Market Report 2026](https://www.euspa.europa.eu/sites/default/files/documents/EU_Space_Market_Report_2026.pdf),
  Issue 1, page 6.
- [ECS SRIA 2026](https://ecssria.eu/ECS-SRIA-2026.pdf), Figure 0.9 on page 42 and chapter 2.3
  on page 268. The singular cross-reference on page 310 does not change that chapter heading.
- [OECD Chips, nodes and wafers](https://www.oecd.org/content/dam/oecd/en/publications/reports/2024/08/chips-nodes-and-wafers_1189c2a2/f68de895-en.pdf),
  August 2024, Figure 9 on page 30; the user-supplied PDF was rendered and inspected.
- [GDELT CAMEO event lookup](https://www.gdeltproject.org/data/lookups/CAMEO.eventcodes.txt),
  for GDELT 1.0/2.0; the retrieval date identifies these unversioned lookup bytes.
- [November 2021 GKG lookup announcement](https://blog.gdeltproject.org/new-november-2021-gkg-2-0-themes-lookup/)
  and its [linked lookup](https://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT).
- [GCAM master codebook](https://data.gdeltproject.org/documentation/GCAM-MASTER-CODEBOOK.TXT),
  unversioned publication bytes identified by retrieval date and checksum.

The OECD download supplied as `.data/f68de895-en.pdf` matches the report title, DOI
`10.1787/f68de895-en`, August 2024 edition and Figure 9 on page 30. Its original bytes have SHA-256:

```text
25f7ec43f76d5fc1ddac65d1a16b179262aa8b68371545eef87ccac384d40083
```

The initial HTTP 403 receipt is retained as history. The supplied PDF, acquisition receipt, text
extraction and Figure 9 render are archived under
`$DATA_DIR/taxonomy-verification/oecd-user-2026-11-22/`. The checksum identifies the supplied PDF
bytes; obtaining those bytes does not change the local origin of engineering extensions.

## Enforcement and reproduction

`kn.semantic.verification` validates strict review envelopes, one decision per scheme, unchanged
origin, and a canonical content digest covering IDs, codes, statuses, parents, replacements and
all preferred/alternative labels. Row ordering does not affect it. Proposal-row definitions are
provenance rather than official definitions and are excluded from this comparison digest.
Publication definitions and Ukrainian translations have not been reviewed.

Verified decisions require official origin, publisher, edition, publication URI and checksum, and
cannot carry mismatches, access limits or local extensions. Missing leaves are allowed only as
an explicitly recorded subset boundary. The existing semantic validator checks the publication
URI and checksum shape. These offline checks preserve a human-readable review; they do not fetch
or automatically certify an official publication.

`reconcile()` applies reviewed scheme metadata before validation and staging. A scheme whose content
digest no longer matches its review is staged `unverified` with a request for a new comparison and
reported under `stale_reviews`, so a proposal change can be reviewed without ever keeping an old
verification. The packaged loader requires stored scheme metadata to equal that review and refuses
stale content before database writes. It never overwrites labels, codes or origins. A changed
projection requires a new comparison and digest; updating only the seed cannot retain an old
verification. Reviewed states and reasons are available in both locale runs' staged snapshots and in
rebuilt `concept_schemes` rows. Future interfaces must carry these states and subset boundaries.
[SKOS export](skos.md) carries them for every included scheme, including crosswalk counterparts.

- `make seed-check` repeats the normal CLI path and checks reviewed snapshots and proposal fixtures.
- `make ci` compares 268 selected publication rows offline, pins the three label mismatches, checks
  review completeness, rejects stale content and unsupported verification, and exercises both
  CLI locales and reordered proposals. No network is used by tests.
- `make test-integration` checks exact reviewed metadata through the existing transactional seed
  loader and repeated rebuild tests.
- `make build` includes seed snapshots and review manifests for use outside the repository.

Raw publications, retrieval metadata, extracted text and selected page renders are preserved under
`$DATA_DIR/taxonomy-verification/official-2026-11-22/`. The full GDELT lookup bytes there are review
artifacts, not imported semantic dictionaries. The [task record](../../records/0022-ontology-taxonomy-verify-official-taxonomies.md)
contains run evidence and the [closed research decision](../../future-research.md#verify-official-taxonomies----full-official-status-for-mixed-seeds).
