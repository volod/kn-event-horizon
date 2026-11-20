# 0002 Knowledge Platform Specification

## Work contract

Direct request from the owner, with no plan task. Critically review the draft package
`docs/design/Knowledge_Awareness_Platform_Codex_Package/` (a draft specification and five taxonomy
and source workbooks) together with the owner's requirements. Suggest improvements and better
practices or ready-made frameworks, and ask questions where needed. Then write the project
`spec.md` and `plan.md` under this repository's rules, without writing code, and delete the draft
package.

The owner's requirements, summarized:

1. Read the full draft and workbooks. Do not turn example rows into facts. Check the exact official
   taxonomy editions, API terms, and schemas before enabling collection.
2. Ontology, taxonomy, and tagging are data, imported as data migrations, and kept under data
   contract and schema control like domain data.
3. Import the initial source list as a data migration. Manage crawlers mainly through configuration
   (ontology mapping, error mapping, monitoring). Write configuration and transformations after
   coding-agent investigation.
4. Build a core engine skeleton first, then improve it with TDD source by source, improving both
   the core and earlier sources.
5. No versioned schemas or backward-compatibility code before release.
6. A compact raw store during development: fetch once, transform many, and wipe and reload on
   schema change.
7. The integrity, safety, provenance, AI, localization, and Obsidian rules of the draft, plus a
   fully qualified origin URI and fetch timestamp on every piece of data.
8. Build contracts, the extraction and transformation engine, and export and import first, then
   improve them with TDD per source.
9. Order: space ("cosmos") ELT, then space dashboards, then GDELT and microelectronics ELT and
   visualizations.

Owner decisions taken during the session:

- Workbooks become well-formed JSON under Git, for use as future migration sources.
- One database, `kn`, with a schema per domain (not a database per domain).
- Kestra's native UI is an approved English-only engineering tool, and operator workflows stay
  bilingual through the CLI and Superset.
- The raw store is WARC plus a Parquet fetch ledger.

## Implementation and decisions

Review findings and their resolutions:

| Finding | Resolution in the specification |
| --- | --- |
| Requirement 5 (no versioned schemas before release) contradicts the draft's semantic versions, Atlas migrations, release ledger, and the v1 -> v1.1 migration test | [Development and release phases](../../design/spec.md#development-and-release-phases): rebuild mode until release; migration mode, tool selection, and versioning move to `release-readiness` |
| Requirement 7 ("refuse destructive migrations") conflicts with requirement 6 ("delete old data and reload") | Rebuild is allowed only in development, never touches the raw archive, and is refused once the environment is released |
| Claim provenance needs a "contract version" while schemas carry no versions | `contract_digest` and `code_digest` replace version numbers until release |
| A rebuild would lose human review decisions and curated data that cannot be re-derived from raw | Decisions go to append-only logs in `DATA_DIR` and curated observations to Git files; rebuild replays both and reports orphans |
| "Data migrations" for ontology and sources do not fit an unversioned phase | Idempotent seed loads with deterministic IDs on every rebuild; versioned data migrations begin after release |
| "Git-managed YAML/SKOS is authoritative" conflicts with the request for JSON seeds | Reviewed JSON seed files are authoritative for vocabulary content, SKOS is a generated export, and YAML holds contracts and crawler configuration |
| Draft source YAML in Git versus "import the source list as a data migration" | Two layers: a catalogue (data, all candidates, never enabled) and reviewed crawler configuration (Git), where enablement needs approval |
| Separate databases per domain force postgres_fdw, an outbox, multiple dbt targets, and Superset connections | Owner chose one database with schema-per-domain roles; one `REPEATABLE READ` snapshot now serves exports |
| Kestra UI had no Ukrainian in its last published language list (12 languages, as of 0.19) | Owner approved an English-only engineering waiver, and operator workflows are bilingual elsewhere |
| "UI translated to EN/US" in the request | Read as `en` and `uk`, the codes used throughout |
| The draft MVP included GDELT DOC and a GDELT dashboard section before microelectronics, which differs from requirement 9 | Registry order follows requirement 9: GDELT after space dashboards, then microelectronics |
| Operator websites (Starlink and others) have terms that commonly forbid automated access, and pricing is often address-based | A curated source method with cited URIs and permitted page captures replaces scraping |
| "Fully qualified origin URI" versus credentials in query strings | URIs are stored after redaction of declared secret parameters |
| Derived rows cannot have a single origin URI | Derived rows carry lineage (model, inputs, window) instead |
| Workbook identifier collisions: `S01`-`S17` (space), `S01`-`S14` (microelectronics), `S01`-`S13` (GDELT); `APP.*` in GDELT and microelectronics | All identifiers are qualified by domain and scheme at import |
| Space relation directions are inconsistent (`operates` and `operated_by`, `member_of_constellation` and `contains_spacecraft`); the ESA GPT sheet has no parent values | Normalized on import with inverse labels and structural parents |
| The pilot tables need classes absent from the space ontology workbook (tariff plan and observation, coverage, orbital element set and shell, launch performance, service metric) | Added as reviewed `kb_extension` classes in `space-domain-contracts` |
| The GDELT workbook states that the CAMEO, actor, and GCAM dictionaries are incomplete | The full official dictionaries are imported as sources (`gdelt-source-dictionaries`) |
| Microelectronics workbooks imply an origin and foreign-control screening policy that no requirement defines | A human-gated task, `define-microelectronics-origin-policy`; origin facts are stored but never gate anything until then |
| The draft's 32 GB memory budgets total close to 32 GB with inference and tools running together | Budgets kept as starting values, with a rule against concurrent heavy jobs and a measured performance gate |
| The draft suggests PostgreSQL 17 | Pin the newest major with an official PostGIS image at pin time |
| Ready-made extraction frameworks | dlt's REST client may be adopted for pagination if raw bytes stay archived; dlt schema inference is rejected because contracts are authoritative; the decision is recorded in `crawler-config-schema` |

External facts checked during the review, at documentation level:

- ODCS: v3.1.0 is the current official version on the Bitol site and GitHub. A v3.2.0 release
  (September 2026) is reported by one third-party source but was not confirmed.
  [ODCS releases](https://github.com/bitol-io/open-data-contract-standard/releases)
- Kestra 0.19 added UI localization in 12 languages, without Ukrainian. Newer releases were not
  confirmed. [Kestra 0.19 release](https://kestra.io/blogs/release-0-19)
- Superset bundles a `uk` translation catalog in `superset/translations/`.
  [Superset translations](https://superset.apache.org/docs/contributing/translations)
- dlt schema contracts support `freeze` and `discard_value` modes.
  [dlt schema contracts](https://dlthub.com/docs/general-usage/schema-contracts)
- `warcio` reads and writes WARC 1.0 and 1.1 (ISO 28500).
  [warcio](https://pypi.org/project/warcio/)

Seed conversion: the five workbooks were converted to `domains/<domain>/seeds/proposals/` (47 sheet
files plus 5 `workbook.json` manifests). The converter used only the Python standard library and
was not committed. Every one of the 8,232 non-empty cells was checked against the JSON, and every
manifest checksum matched. No macros or external links were present. Six formulas in the
hypothetical `13_Energy_Template` were recorded but never evaluated. The format is described in
[domains/README.md](../../../domains/README.md).

Draft package disposition: deleted at the owner's request after absorption into the
[specification](../../design/spec.md) and the domain pages for
[space](../../design/domains/space.md), [GDELT](../../design/domains/gdelt.md), and
[microelectronics](../../design/domains/microelectronics.md). Deleted files and their SHA-256:

| File | SHA-256 |
| --- | --- |
| `Knowledge_Awareness_Platform_Specification.md` | `4ff2f330548be06a6bfa062a6b239df1f03a9cb4585947f9f6017757bc99e266` |
| `ontology-taxonomy/gdelt_ontology_and_tags_v1.xlsx` | `c31bba2aad40336c620044c6df5332744aebdce70b415e56bc121096845881a2` |
| `ontology-taxonomy/space_sector_data_sources_v1.xlsx` | `83958f6df5f3e5b0cd969a4fe3206197fe4bf4cee396df62f02dbe394a3040f0` |
| `ontology-taxonomy/space_sector_ontology_and_tags_v1.xlsx` | `26e7468ee372e9c606ff08910756b2066ef30ac9fea7524e646b52d8529eec28` |
| `ontology-taxonomy/microelectronics_ontology_and_tags_v1.xlsx` | `7166aa06791998c692cc6a2ac377692a6687f15e3353ffa70a1c159f2e63c34f` |
| `ontology-taxonomy/microelectronics_data_sources_v1.xlsx` | `ab7837e18fc1907a2b977def23d03de78e608787d3125011ab3b38bda2536fba` |
| `ontology-taxonomy/SHA256SUMS.txt` | `c8cc0f54f4dbbff31a380cff2d309720564578023fce9ba4556f723385d01d18` |

The workbook checksums match the package's own `SHA256SUMS.txt`, which listed the files under a
`packages/input/` path that did not exist.

## Acceptance evidence

Status: accepted.

| Check | Result |
| --- | --- |
| `make lint-spec-plan` | 0 spec-plan findings, 0 register findings |
| `make lint-doc-links` | 0 broken links |
| `pymarkdown scan` on the specification, domain pages, plan, records, and `domains/README.md` | pass |
| `make ci` after deleting the draft package | pass (59 tests) |
| `make quality` after deleting the draft package | pass, including Markdown lint, coverage, and build |
| ASCII scan of the new documentation | no non-ASCII characters |
| Seed round trip | 8,232 of 8,232 non-empty cells reproduced; 47 sheet checksums verified |

## Handoff

Plan counts before: 0 tasks, as left by
[record 0001](0001-project-identity-personalize-template-project.md). After: 71 tasks. The agent
lane has 62 (CLEAR 58, RUN NEEDED 4); the human lane has 9 (HUMAN-GATED 8, BLOCKED BY HUMAN 1).
The highest-priority agent task is `compose-database-service`, and the highest-priority human task
is `define-microelectronics-origin-policy`.

Registry changes: 19 new `planned` capabilities, from `runtime-platform` to `ai-extraction`. The
three foundation capabilities stay `shipped`. No current-state page changed, because no behavior
changed.
