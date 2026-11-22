# Space Domain Design

This page details the [space ELT](../spec.md#space-elt) and
[space dashboards](../spec.md#space-dashboards) capabilities. The
[knowledge integrity rules](../spec.md#knowledge-integrity-rules) apply throughout.

## Pilot scope: global SATCOM awareness

The pilot gives public industrial and commercial awareness of satellite communications: past and
planned launch activity, spacecraft, operators, services, commercial availability, and prices.
The candidate operator and system families are Starlink, Eutelsat OneWeb, SES O3b mPOWER, and
Telesat Lightspeed. Being named as a candidate says nothing about operational status or coverage.
Other systems, such as Amazon's constellation, are added only as source access and scope permit.

The pilot implements only the tables below. The full space dictionaries are still loaded. The
system must work with sparse evidence and clearly labeled unknowns. The map is a market and
geographic awareness tool, not a tracking system.

## Initial source dataset

The owner-provided `satcom_enriched_package` is a source dataset within space, not a separate
cosmos or SATCOM domain. Its 28 CSV tables preserve textual source IDs, claims, contextual
observations, finance and deployment bases, missing reasons and field dictionaries. The initial
source projection and immutable package archive are described in the
[current data-contract documentation](../../impl/current/data-contracts.md).

Source rows keep their own identity namespace and snapshot ID. Mapping them into the canonical
space tables below requires reviewed identity and ontology decisions; importing them does not
assert that a source spacecraft model is an individual spacecraft, a plan is a deployment, or
an opportunity is a verified contract. The workbook remains archived with its formulas and charts.

## Classification axes

The seed proposals in `domains/space/seeds/proposals/` use three independent axes plus the
ontology:

| Axis | Proposal sheet | Use | Verification |
| --- | --- | --- | --- |
| Product hierarchy | `03_ESA_GPT_Classifier` (44 nodes) | One primary path per product; secondary mappings allowed | ESA Generic Product Tree Issue 1 Rev 1. Nodes marked `OFFICIAL_SYSTEM` must be checked against ESA originals. `KB_NORMALIZED`, `KB_EXTENSION`, and `SERVICE_EXTENSION` nodes are analyst extensions. |
| Technology tags | `04_NASA_TX_Tags` (17 level-1 areas), `05_ESA_Tech_Tags` (26 domains, 107 subdomains) | Many-to-many | NASA 2024 Technology Taxonomy and ESA Technology Tree v4.1 (STM-277). Leaf technology groups are not included. |
| Application tags | `06_EUSPA_App_Tags` (16 segments) | Many-to-many downstream markets | EUSPA EU Space Market Report 2026 |
| Service types | `07_Service_Types` (S01-S17) | Independent service vocabulary, never forced into the product tree | Local vocabulary |
| Ontology | `01_Entity_Ontology` (21 classes), `02_Relations` (19 relations) | Entity classes and typed relations | Local; normalized on import |
| Examples | `08_Tagging_Examples` | Fixtures only | Not facts |

Seed import notes:

- The ESA GPT sheet has an empty `Parent node` column, so the hierarchy comes from the segment code
  and node code. The import adds structural root and parent links.
- Relations are stored in one canonical direction with an inverse label. The proposal mixes
  directions (for example `operates` and `operated_by`, `member_of_constellation` and
  `contains_spacecraft`).
- The pilot needs classes the ontology proposal lacks: tariff plan, tariff observation, coverage
  observation, service metric, orbital element set, orbital shell, and launch performance. They are
  added as reviewed `kb_extension` classes.

## Domain model

Every extension table has `entity_id uuid` as its primary key and a foreign key to the canonical
entity, unless stated otherwise. Every selected fact carries its claim provenance. When a price,
metric, or time depends on conditions, it becomes a contextual observation rather than an
overwritten attribute. `NULL` with a missing reason means unknown, never zero.

| Table | Minimum fields beyond shared fields |
| --- | --- |
| `organization` | Legal name, aliases (separate table), jurisdiction (ISO alpha-2 if known), legal identifier scheme and value, actor roles, website, lifecycle |
| `launch_vehicle` | Family, variant or configuration, manufacturer and provider as separate relations, status, stages, reuse capability, length, diameter, launch mass, fairing dimensions, first launch |
| `launch_performance` | Vehicle, target orbit class, altitude or perigee/apogee, inclination, payload capacity, recovery mode, conditions, documented price, claim; one observation per scenario |
| `launch_event` | Native event IDs, vehicle configuration, provider, site, scheduled time and precision, actual time and precision, result, mission name, last observed. Planned and actual stay separate. |
| `launch_payload` | Event, spacecraft or unresolved manifest entry, relationship status, claim; no invented spacecraft identity |
| `constellation` | System name, operator relation (temporal), service tags, lifecycle, orbit class, parent program, planned and authorized counts as dated claims separate from observed counts |
| `orbital_shell` | Constellation, native shell ID, altitude, inclination, planned planes, spacecraft per plane, regulatory or deployed basis, validity |
| `spacecraft_model` | Manufacturer relation, platform or bus, dry and launch mass, dimensions, design life, payload type, RF bands, throughput basis, propulsion type |
| `spacecraft` | Model (nullable), qualified identifiers, constellation membership as a relation, launch event, operator and owner relations, lifecycle, commissioning and decay dates where evidenced |
| `orbital_element_set` | Catalog identifier, spacecraft (nullable), epoch (UTC), received time, OMM numeric fields, frame, time system, theory; append-only and source-policy restricted |
| `facility` | Class (spaceport, pad, teleport, ground station, AIT), organization relation, country, optional public point `geometry(Point,4326)` with precision and source, lifecycle |
| `terminal_model` | Model or MPN, manufacturer, compatible systems, fixed or mobile, RF bands, antenna type, peak and typical power with conditions, data rates, dimensions, mass, environment, lifecycle |
| `service` | Provider relation, service type, enabling constellations, customer class, mobility class, named offer, lifecycle |
| `tariff_plan` | Named offer with immutable identity across price changes; service foreign key |
| `tariff_observation` | Plan, service, market country or region, customer class, original currency (ISO 4217), recurring amount and cadence, data allowance and fair-use policy, rate limits and priority, activation and equipment cost, tax inclusion, promotion and term, availability conditions, validity, claim |
| `service_metric` | Service, plan, or model; metric ID; min, typical, and max or percentile; value and unit; test or advertised conditions; geography; validity; claim |
| `coverage_observation` | Service or system, geometry or country, `coverage_kind`, `availability_status`, source method, precision, observation and validity times, claim; geometry nullable when unknown |
| `regulatory_record` | Administration, filing or licence ID, holder, network, category and exact status, date, jurisdiction; never a deployed capability |
| `program`, `contract_award` | Identity, parties and roles, stated value with currency and basis, milestone and status, binding status, date; MoU and LoI kept distinct |

Identity rules:

- COSPAR international designator and NORAD catalog number are distinct qualified identifiers, and
  neither is a manufacturer ID.
- Program, spacecraft model, physical spacecraft, constellation, and service are never conflated.
- Active, cataloged, and operational are different states. Operational status is never derived
  from orbit existence alone.
- Membership counts come from qualified spacecraft IDs as of a time, never from page headlines or
  duplicated entries.
- Orbit elements are neither an ephemeris nor coverage.

## Coverage, geography, and pricing rules

- `coverage_kind` is mandatory: `provider_declared_geometric`, `provider_declared_commercial`,
  `regulatory_authorization`, `derived_model` (reserved for a future reviewed method), or
  `unknown`.
- `availability_status` is separately controlled: `available`, `restricted`, `planned`,
  `waitlist`, `unavailable`, or `unknown`. Regulatory records use their own status vocabulary.
- Market availability is never inferred from an orbit footprint or an ITU filing. No service-region
  polygons are generated from orbital elements.
- A country polygon represents a reported market condition, not measured RF coverage, and is
  labeled so. When no authorized machine-readable geometry exists, the provider map link is kept.
- Geometry uses EPSG:4326 with type, range, and `ST_IsValid` checks. Repairs are audited and the
  original is kept. The antimeridian is handled. Simplified geometry for BI never replaces the
  original. Reference boundaries are versioned and licence-reviewed, and the neutral-boundary
  policy is documented.
- Tariff comparisons match customer class, country, tax basis, currency, billing interval,
  included equipment and allowance, and observation period. The original price is always stored.
  Optional FX conversion uses an approved reference rate with its date and source.
- Promotions and one-off hardware costs stay separate. Unlimited plans, fair-use limits, and
  priority tiers are distinct.
- A provider page without a price is a valid record of missing data, with a reason (login,
  country not offered, no advertised value, source blocked). An advertised rate is not a measured
  speed.
- Launcher capacities are compared only for the same destination orbit and recovery assumptions.

## Sources

Every source starts as a catalogue candidate from `01_Data_Sources` (37 rows). Each follows the
[onboarding workflow](../spec.md#source-management) and stays disabled until approved. The
schedules below are proposals to verify, not permissions.

| Source | Outputs | Proposed cadence | Gate notes |
| --- | --- | --- | --- |
| CelesTrak GP | Selected constellation GP records (OMM JSON): catalog ID, epoch, group membership candidates, snapshot counts | At most every 6 h per selected group, one request per update | Honor the usage policy. Use JSON, OMM, or CSV, not fixed-width TLE, for 6-digit catalog numbers. |
| Launch Library 2 | Agencies, launcher configurations, launch events, pads, manifests | Upcoming launches every 6 h; configurations daily to weekly | The free tier is rate limited (historically about 15 requests per hour); verify. The archive makes history a one-time fetch. |
| Natural Earth | Reference country polygons with edition | Manual, on new edition | Terms review; required for maps |
| Operator disclosures | Public system specs, plans, market availability, dated announcements per provider | Curated; daily to weekly checks only after review | Curated method. Terms usually forbid automated access to commercial sites, and pricing is often address-based, which is excluded. |
| Space-Track | Catalog identity and status corroboration | Daily if a lawful account is provided | Optional; account required |
| ESA DISCOS | Launcher and object metadata cross-check | Weekly | Optional; account and terms |
| UNOOSA register | State registration evidence (not ownership) | Monthly | Optional; document extraction |
| ITU Space Explorer | Network filing and status evidence (not deployment) | Weekly or manual export | Optional |

Wider catalogue sources (CEOS, Copernicus STAC, NASA CMR, TechPort, CORDIS, TED, USAspending,
SAM.gov, EPO OPS, SatNOGS) remain candidates. Commercial databases (Space Insider, Novaspace,
Seradata) and web-only references (Gunter's Space Page, Orbital Radar) stay catalogue entries
unless the owner provides a licence or approves an analyst workflow.

Live acceptance needs actual permitted samples for launches, catalog snapshots, and at least two
provider disclosure scopes. Synthetic records alone never pass it.

## Analytical marts

| Mart (minimum grain) | Consumer |
| --- | --- |
| `satcom_constellation_snapshot` (system x date x source scope) | Counts and trends by operator, orbit, status; planned and observed separate |
| `satcom_service_comparison` (service x market x snapshot x customer class) | Advertised rate, latency, capacity with units, conditions, completeness, provenance |
| `satcom_tariff_history` (plan x market x observed date x applicability) | Recurring and upfront cost, currency, interval, terms; incomparable values filtered |
| `launch_vehicle_comparison` (variant x target orbit x condition) | Manufacturer, provider, performance, status, launch record |
| `launch_event_daily` (date x provider x family x result) | Counts and trends; planned and actual filters |
| `satcom_market_geo` (service x market or geometry x as-of x coverage kind) | Validated GeoJSON with source, validity, semantic category |
| `public_facilities_geo` (facility x observed time) | Optional map points with public precision |
| `data_freshness`, `run_quality`, `fact_evidence_lookup` | Last success, staleness, coverage, conflicts, evidence drill-down |

Dashboards:

1. **Global SATCOM Overview.** Known and planned counts, operator and system comparison, catalog
   trend, launch activity, freshness, and missing-data metrics.
2. **Service and Tariff Comparison.** Filters for country, customer segment, system, date, and
   currency. A sortable table of rates, stated latency and throughput, subscription and terminal
   costs, data caps, and evidence date. Incompatible conditions are never ranked together.
3. **Market Coverage and Availability.** Country and region polygons, with optional public facility
   points on a separate layer. An as-of filter, a legend for coverage kind and status, source
   tooltips, and distinct unknowns. Static time filtering suffices.
4. **Launchers, Launches and Satellite Models.** Configuration comparisons with orbit assumptions,
   launch history, and a spacecraft model table with cited evidence.
5. **Acquisition and Operations.** Source status, lag, run success and rejection, and the review
   queue. GDELT trends are added later.

The map tile provider is chosen at deployment with lawful terms and attribution, and no secret
reaches the browser. A no-basemap fallback still shows polygons. Fixture acceptance never requires
a paid API key.
