# Microelectronics Domain Design

This page details the [microelectronics ELT](../spec.md#microelectronics-elt) and
[microelectronics dashboards](../spec.md#microelectronics-dashboards) capabilities.

## Scope and priorities

The domain covers global technology intelligence, with EU, UK, and Canadian actors first. US and
other vendors appear as benchmarks or documented exceptions. Research signals are never excluded
by geography alone. Prospective technology that could improve energy use and autonomy comes first,
with product baselines in parallel.

## Classification axes

From the proposals in `domains/microelectronics/seeds/proposals/`:

| Axis | Proposal sheet | Use | Verification |
| --- | --- | --- | --- |
| Product classifier | `03_Product_Classifier` (76 nodes) | One primary class per product. SoC, MEMS, SiP, material, and integration style are facets, not root classes. | OECD "Chips, nodes and wafers" Figure 9 backbone (`OECD_NODE`, with local codes, not official OECD codes) plus `KB_EXTENSION` and `KB_NON_CHIP` nodes |
| Technology chapters | `04_ECS_Technology` (8) | Many-to-many | ECS SRIA 2026 chapter tags |
| Technology tags | `05_Technology_Tags` (40, `T.*`) | Many-to-many; demonstrated versus claimed kept apart | Local; the ECS chapter mapping is an analyst mapping |
| Application tags | `06_Application_Tags` (12) | Many-to-many | ECS segments 3.1-3.6 plus local `APP.X*` |
| Service vocabulary | `07_Service_Vocabulary` (S01-S14) | Industrial services | Local; namespaced (collides with space and GDELT `S*`) |
| Ontology | `01_Entity_Ontology` (27 classes), `02_Relations` (29) | Entity classes and typed relations | Local |
| Attribute dictionary | `08_Attribute_Dictionary` (195 fields in 18 profiles) | Field IDs, canonical units, required conditions; `M` = required for comparison, `R` = recommended | Local field IDs. The IEC CDD, ECLASS, and JEDEC JEP30 references are not imported property IDs. |
| Observation schema | `09_Observation_Schema` | Fact-level provenance and condition sets | Local; reconciled with the core evidence model |
| Comparison profiles | `10_Comparison_Profiles` (C01-C07) | Matched-condition comparison gates | Local |
| Scouting rubric | `12_Scouting_Rubric` | Analyst policy with weights (energy 35, autonomy 20, maturity 20, access 15, integration 10); not a prediction | Local; editable policy data |
| Examples | `11_Tagging_Examples`, `13_Energy_Template` | Fixtures only; the energy template values are synthetic and its formulas are recorded, not evaluated | Not facts |

## Modeling rules

- Product family, product model, orderable MPN, die or chiplet, IP block, development kit, and
  module are distinct classes. Identity requires the legal manufacturer plus the exact MPN, with
  package and version where appropriate. Nothing merges on a family label. Family, model,
  manufacturer part, orderable variant, and supplier offer are the shared
  [part and supply model](../spec.md#part-and-supply-model) classes, matched through the
  [object identity](../spec.md#object-identity) profiles.
- Legal manufacturer, brand, design location, wafer fab, assembly site, final test site, parent
  ownership or control, and export classification are separate facts. Unknown stays unknown, and
  origin is never assumed from headquarters.
- Each observation keeps its raw value; normalized min, typical, and max; units with logged
  conversion; and a qualifier (measured, vendor typical, guaranteed limit, simulated, or analyst
  derived). It also keeps its condition set (rails, temperature, clock, mode, workload, precision,
  boundary, firmware or model hash), source and locator, and bitemporal times.
- Comparison happens only within a comparison group with matched conditions. TOPS alone is never
  ranked. Advertised peaks are never compared with measured results without a label. A record
  with unknown required fields is excluded from matched ranking but stays visible.
- Energy normalizes per task or inference, with duty cycle and battery boundary, and explicit
  units and conversion provenance.
- Imaging records resolution, ROI, bit depth, shutter, readout, and interface with FPS. FPGA records
  device, speed grade, utilization, post-route clock, constraints, and measurement method.

## Target-market policy

An analyst selects a destination market and an as-of date to inspect published trade measures
alongside a technical comparison. Model countries such as Ukraine, the US, and Canada separately
from blocs such as the EU. Record dated bloc membership when applying a bloc measure to a member
market. Keep the issuing jurisdiction and authority separate from the destination: an export
control issued in one country can concern goods shipped to another.

One observation describes one published measure or revision and its stated scope. Capture the
instrument and provision, policy type, origin and destination scope, goods or classification
codes, stated conditions, effective interval, publication date, and evidence locator and fetch
time. Link a product only through a supported classification or other cited scope match.
Present the source wording and conditions. Missing coverage or a missing classification is
reported as unknown. A market observation describes a measure, without deciding a transaction.

Compute technical ranks before retrieving policy details. The market panel can show several
measures for one product. A product with zero matches keeps its technical score and position.
The source catalogue tracks official publications, permitted fetch methods, and coverage dates
by jurisdiction. Prior proposal flags about vendors remain unreviewed inputs.

## Sources

The catalogue holds 65 candidate rows from `01_Data_Sources`, with original IDs (D, V, and C
series) kept. Many are web-only vendor or research pages, where permitted collection is uncertain.
The first onboarding uses structured sources and the curated method:

| Order | Source | Why first |
| --- | --- | --- |
| 1 | MLPerf Tiny results (D16) | Published results with versions, divisions, and measurement boundaries; anchors the benchmark layer |
| 2 | CORDIS projects (D04) | Official bulk datasets; R&D projects, participants, funding |
| 3 | Curated vendor datasheet observations | Watchlist families (`05_Vendor_Watchlist`) recorded with datasheet revision, page, and table |

Later candidates include OpenAlex (D12), arXiv (D14), Crossref (D15), EPO OPS (D13, account), GLEIF
(C07), TED (C08), and distributor APIs (C01-C03, accounts and terms). Each follows the same workflow.
The priority watch topics W01-W07 (`04_Prospective_Signals`) become GDELT and source watch
definitions after review.
