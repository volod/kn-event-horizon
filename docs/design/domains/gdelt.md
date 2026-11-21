# GDELT Domain Design

This page details the [GDELT ELT](../spec.md#gdelt-elt) and
[GDELT dashboards](../spec.md#gdelt-dashboards) capabilities. GDELT is a discovery signal, never a
factual authority ([rule 8](../spec.md#knowledge-integrity-rules)).

## Native semantics

Native GDELT semantics are stored separately from local claims and ontology tags.

- **Grain.** An Event is a machine-coded event record. A Mention is one occurrence of an event in a
  source document. A GKG record holds the metadata of one processed document.
- **Joins.** Events join to Mentions on `GlobalEventID`. Mentions join to GKG on
  `MentionIdentifier` plus `MentionType` and `DocumentIdentifier` plus `SourceCollectionIdentifier`,
  which can be one-to-many. Joins never rely on URL alone.
- **Time.** Event day, `DATEADDED`, mention time, GKG batch time, publication time (when
  independently known), and retrieval time stay separate. None is an article publication time by
  default.
- **Values.** Codes are strings: CAMEO codes keep their leading zeros and actor codes are 3-character
  tokens. Actor and geography country codes are CAMEO or FIPS, never assumed to be ISO.
- **Scores.** Confidence (10-100) measures extraction, not truth. Tone, GCAM, and Goldstein values
  keep their native scale and scope and are never severity or verification.
- **Sensitive attributes.** CAMEO ethnic and religion codes are restricted dictionary attributes and
  are never projected onto people.

## Seed proposal status

The proposals in `domains/gdelt/seeds/proposals/` are partial by their own statement.

- `03_CAMEO_Classifier` holds the 20 root codes and two codebook examples only.
- `05_GKG_Theme_Tags` holds 43 codes observed in the 2021 lookup snapshot.
- `06_GCAM_Tone_Tags` holds codebook examples; the GCAM master codebook was not decoded.
- Actor and geography dictionaries are linked, not copied.

The full official lookups (CAMEO event codes, actor types, countries, known groups, GKG themes,
GCAM codebook) must therefore be imported as sources with edition and checksum before production
tagging. Unmapped native codes stay strings in an `unmapped` state, and no mapping is invented.
Technology tags (`TECH.*`), application tags (`APP.*`), and services (`S01`-`S13`) are local
extensions. They are namespaced as `gdelt.*` because `APP.*` and `S*` collide with the
microelectronics proposals.

## First slice: DOC 2.0 API watches

- **Watch manifests.** Each manifest holds approved query strings, `en` and `uk` aliases, a purpose,
  and an owner. Topics are space (satellite communications, constellations, launch services) and
  microelectronics (low-power sensors, MCU/SoC, FPGA, edge AI, energy harvesting), plus vendors and
  R&D institutions from the microelectronics watchlist. These are technology and market queries,
  never tracking of people.
- **Records.** DOC results are article-list metadata: URL, title, source domain, language, and seen
  time. They are not native Events, Mentions, or GKG records, and no native IDs are manufactured
  for them.
- **Windows.** Queries run hourly over a rolling window with overlap. Proposed defaults are a
  24-hour lookback and a 2-hour overlap; verify them against current API limits, which historically
  were about 250 records per query, a rolling window of about 3 months, and a minimum interval
  between requests. A window is split when a cap is reached. Truncation and partial results are
  recorded, and coverage is never declared exhaustive.
- **Errors.** An HTTP 200 response without JSON is a failure.
- **Storage.** Documents are deduplicated by normalized URL plus revision hash, and syndication
  grouping is kept separately. Only metadata, links, and permitted excerpts are stored, never
  paywalled full text.

## Later refinement: selective native streams

Selective GKG, Events, and Mentions import works in two ways. It can stream the official 15-minute
files and keep only rows that match the watch, actor, theme, or geography criteria. It can also run
BigQuery queries with a dry run, partition filters, and an approved budget. Either way, the file
list, checksums, and selected-row counts are recorded. Unselected files are not kept, and no
complete archive is mirrored. Historical requests are bounded by time, rows, and bytes, and
coverage statistics name the filters and the missing intervals.

## Cross-domain use

A GDELT document can propose a candidate link to a space or microelectronics entity, for example an
announcement mentioning a known operator. The candidate goes to review. Promotion to a claim needs
source verification. News never updates truth, ownership, or lifecycle automatically.
Independent-source counts deduplicate syndicated stories by story cluster.
