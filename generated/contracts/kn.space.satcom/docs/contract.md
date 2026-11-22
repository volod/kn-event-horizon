# kn.space.satcom

Version: 1.0.0

Digest: `498e717814a2eb29e44756f256fd3dab4277b069812f4b54e2bb42a496d2ec10`

Storage schema: `space`

## aliases_crosswalk



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.aliases_crosswalk.import_id | string | True | True |  |
| alias_id | space.satcom.aliases_crosswalk.alias_id | string | True | True |  |
| entity_id | space.satcom.aliases_crosswalk.entity_id | string | True | False |  |
| alias | space.satcom.aliases_crosswalk.alias | string | True | False |  |
| alias_type | space.satcom.aliases_crosswalk.alias_type | string | True | False | former_name / brand / abbreviation / local_name / catalog_name / legacy_catalog_id / merger_predecessor |
| valid_from | space.satcom.aliases_crosswalk.valid_from | string | False | False |  |
| valid_to | space.satcom.aliases_crosswalk.valid_to | string | False | False |  |
| source_id | space.satcom.aliases_crosswalk.source_id | string | False | False |  |
| notes | space.satcom.aliases_crosswalk.notes | string | False | False |  |

## classifications



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.classifications.import_id | string | True | True |  |
| class_id | space.satcom.classifications.class_id | string | True | True | \u0421\u0442\u0430\u0431\u0456\u043b\u044c\u043d\u0438\u0439 \u043a\u043e\u0434 \u043a\u043b\u0430\u0441\u0443 (scheme:code) |
| scheme | space.satcom.classifications.scheme | string | True | False | \u0421\u0445\u0435\u043c\u0430 \u043a\u043b\u0430\u0441\u0438\u0444\u0456\u043a\u0430\u0446\u0456\u0457 (orbit_class, segment, band, ontology_entity, esa_gpt, nasa_tx, esa_tech, euspa, service_tag, opportunity_type, tech_category \u0442\u043e\u0449\u043e) |
| code | space.satcom.classifications.code | string | True | False | \u041a\u043e\u0434 \u0443 \u043c\u0435\u0436\u0430\u0445 \u0441\u0445\u0435\u043c\u0438 |
| label_uk | space.satcom.classifications.label_uk | string | False | False | \u041d\u0430\u0437\u0432\u0430 \u0443\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u043e\u044e |
| label_en | space.satcom.classifications.label_en | string | False | False | \u041d\u0430\u0437\u0432\u0430 \u0430\u043d\u0433\u043b\u0456\u0439\u0441\u044c\u043a\u043e\u044e |
| parent_class_id | space.satcom.classifications.parent_class_id | string | False | False | \u0411\u0430\u0442\u044c\u043a\u0456\u0432\u0441\u044c\u043a\u0438\u0439 \u043a\u043b\u0430\u0441 |
| definition_uk | space.satcom.classifications.definition_uk | string | False | False | \u0412\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f |
| origin | space.satcom.classifications.origin | string | False | False | \u041f\u043e\u0445\u043e\u0434\u0436\u0435\u043d\u043d\u044f \u043a\u043e\u0434\u0443: input-\u043e\u043d\u0442\u043e\u043b\u043e\u0433\u0456\u044f (\u0444\u0430\u0439\u043b/\u0430\u0440\u043a\u0443\u0448/\u0440\u044f\u0434\u043e\u043a) \u0430\u0431\u043e \u043a\u0430\u0442\u0430\u043b\u043e\u0433 |

## compatibility



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.compatibility.import_id | string | True | True |  |
| compatibility_id | space.satcom.compatibility.compatibility_id | string | True | True | ID (CMP-\u2026) |
| subject_id | space.satcom.compatibility.subject_id | string | True | False | \u0422\u0435\u0440\u043c\u0456\u043d\u0430\u043b / \u0442\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0456\u044f / \u0441\u0435\u0440\u0432\u0456\u0441 |
| program_id | space.satcom.compatibility.program_id | string | True | False | \u041c\u0435\u0440\u0435\u0436\u0430 |
| compatibility_type | space.satcom.compatibility.compatibility_type | string | True | False | native / certified / announced / multi_network / via_partner |
| status | space.satcom.compatibility.status | string | False | False | active / announced / legacy |
| claim_id | space.satcom.compatibility.claim_id | string | False | False |  |

## constellations_programs



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.constellations_programs.import_id | string | True | True |  |
| program_id | space.satcom.constellations_programs.program_id | string | True | True | ID \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u0438 / \u0444\u043b\u043e\u0442\u0443 / \u0441\u0435\u0440\u0432\u0456\u0441\u043d\u043e\u0433\u043e \u0431\u0440\u0435\u043d\u0434\u0443 (PRG-\u2026) |
| name | space.satcom.constellations_programs.name | string | True | False | \u041d\u0430\u0437\u0432\u0430 |
| entity_kind | space.satcom.constellations_programs.entity_kind | string | True | False | \u0422\u0438\u043f \u0441\u0443\u0442\u043d\u043e\u0441\u0442\u0456 |
| orbit_class | space.satcom.constellations_programs.orbit_class | string | True | False | \u041e\u0440\u0431\u0456\u0442\u0430\u043b\u044c\u043d\u0438\u0439 \u043a\u043b\u0430\u0441 |
| primary_segment | space.satcom.constellations_programs.primary_segment | string | True | False | \u041e\u0441\u043d\u043e\u0432\u043d\u0438\u0439 \u0441\u0435\u0433\u043c\u0435\u043d\u0442 |
| lifecycle_status | space.satcom.constellations_programs.lifecycle_status | string | True | False | \u0421\u0442\u0430\u043d \u043d\u0430 \u0434\u0430\u0442\u0443 status_as_of |
| status_as_of | space.satcom.constellations_programs.status_as_of | string | False | False | \u0414\u0430\u0442\u0430, \u043d\u0430 \u044f\u043a\u0443 \u0432\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e \u0441\u0442\u0430\u043d |
| operator_org_id | space.satcom.constellations_programs.operator_org_id | string | False | False | \u041e\u043f\u0435\u0440\u0430\u0442\u043e\u0440 |
| owner_org_id | space.satcom.constellations_programs.owner_org_id | string | False | False | \u0412\u043b\u0430\u0441\u043d\u0438\u043a (\u044f\u043a\u0449\u043e \u0432\u0456\u0434\u0440\u0456\u0437\u043d\u044f\u0454\u0442\u044c\u0441\u044f) |
| country_iso2 | space.satcom.constellations_programs.country_iso2 | string | False | False | \u041a\u0440\u0430\u0457\u043d\u0430 \u044e\u0440\u0438\u0441\u0434\u0438\u043a\u0446\u0456\u0457 / \u043b\u0456\u0446\u0435\u043d\u0437\u0443\u0432\u0430\u043d\u043d\u044f |
| user_class | space.satcom.constellations_programs.user_class | string | False | False | commercial / government / military / mixed |
| coverage_scope | space.satcom.constellations_programs.coverage_scope | string | False | False | \u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u0438\u0439 / \u0440\u0435\u0433\u0456\u043e\u043d\u0430\u043b\u044c\u043d\u0438\u0439 / \u043d\u0430\u0446\u0456\u043e\u043d\u0430\u043b\u044c\u043d\u0438\u0439 / \u043f\u043e\u043b\u044f\u0440\u043d\u0438\u0439 |
| planned_spacecraft_total | space.satcom.constellations_programs.planned_spacecraft_total | integer | False | False | \u0417\u0430\u044f\u0432\u043b\u0435\u043d\u0430 / \u043b\u0456\u0446\u0435\u043d\u0437\u043e\u0432\u0430\u043d\u0430 \u0446\u0456\u043b\u044c\u043e\u0432\u0430 \u043a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u041a\u0410 (\u043a\u0430\u043d\u043e\u043d\u0456\u0447\u043d\u0435 \u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043d\u044f) [\u041a\u0410] |
| first_launch_date | space.satcom.constellations_programs.first_launch_date | string | False | False | \u041f\u0435\u0440\u0448\u0438\u0439 \u0437\u0430\u043f\u0443\u0441\u043a \u041a\u0410 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u0438 |
| service_start_date | space.satcom.constellations_programs.service_start_date | string | False | False | \u041f\u043e\u0447\u0430\u0442\u043e\u043a \u043a\u043e\u043c\u0435\u0440\u0446\u0456\u0439\u043d\u043e\u0433\u043e / \u0448\u0442\u0430\u0442\u043d\u043e\u0433\u043e \u0441\u0435\u0440\u0432\u0456\u0441\u0443 |
| altitude_km_nominal | space.satcom.constellations_programs.altitude_km_nominal | number | False | False | \u041d\u043e\u043c\u0456\u043d\u0430\u043b\u044c\u043d\u0430 \u0432\u0438\u0441\u043e\u0442\u0430 \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0457 \u043e\u0431\u043e\u043b\u043e\u043d\u043a\u0438 [\u043a\u043c] |
| inclination_deg_nominal | space.satcom.constellations_programs.inclination_deg_nominal | number | False | False | \u041d\u043e\u043c\u0456\u043d\u0430\u043b\u044c\u043d\u0438\u0439 \u043d\u0430\u0445\u0438\u043b \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0457 \u043e\u0431\u043e\u043b\u043e\u043d\u043a\u0438 [\xb0] |
| isl_type | space.satcom.constellations_programs.isl_type | string | False | False | \u041c\u0456\u0436\u0441\u0443\u043f\u0443\u0442\u043d\u0438\u043a\u043e\u0432\u0456 \u043b\u0456\u043d\u0456\u0457: none / RF / optical / unknown |
| ukraine_service_status | space.satcom.constellations_programs.ukraine_service_status | string | False | False | \u0421\u0442\u0430\u0442\u0443\u0441 \u0441\u0435\u0440\u0432\u0456\u0441\u0443 \u0432 \u0423\u043a\u0440\u0430\u0457\u043d\u0456 \u0437\u0430 \u0434\u0436\u0435\u0440\u0435\u043b\u0430\u043c\u0438 |
| website_url | space.satcom.constellations_programs.website_url | string | False | False | \u041e\u0444\u0456\u0446\u0456\u0439\u043d\u0430 \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0430 |
| notes | space.satcom.constellations_programs.notes | string | False | False | \u041f\u043e\u044f\u0441\u043d\u0435\u043d\u043d\u044f \u043c\u0435\u0436 \u0441\u0443\u0442\u043d\u043e\u0441\u0442\u0456 |

## countries



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.countries.import_id | string | True | True |  |
| country_iso2 | space.satcom.countries.country_iso2 | string | True | True | \u041a\u043e\u0434 ISO 3166-1 alpha-2; XX \u2014 \u043c\u0456\u0436\u043d\u0430\u0440\u043e\u0434\u043d\u0430 / \u0431\u0430\u0433\u0430\u0442\u043e\u043d\u0430\u0446\u0456\u043e\u043d\u0430\u043b\u044c\u043d\u0430 \u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456\u044f, EU \u2014 \u0404\u0421 |
| name_uk | space.satcom.countries.name_uk | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u0443\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u043e\u044e |
| name_en | space.satcom.countries.name_en | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u0430\u043d\u0433\u043b\u0456\u0439\u0441\u044c\u043a\u043e\u044e |
| region | space.satcom.countries.region | string | True | False | \u041c\u0430\u043a\u0440\u043e\u0440\u0435\u0433\u0456\u043e\u043d \u0434\u043b\u044f \u0430\u0433\u0440\u0435\u0433\u0430\u0442\u0456\u0432 |
| is_ukraine_neighbor | space.satcom.countries.is_ukraine_neighbor | boolean | False | False | \u0421\u0443\u0441\u0456\u0434\u043d\u044f \u0437 \u0423\u043a\u0440\u0430\u0457\u043d\u043e\u044e \u0434\u0435\u0440\u0436\u0430\u0432\u0430 (\u0434\u043b\u044f \u043e\u0446\u0456\u043d\u043a\u0438 \u0440\u0438\u043d\u043a\u043e\u0432\u043e\u0433\u043e \u0434\u043e\u0441\u0442\u0443\u043f\u0443) |

## deployment_observations



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.deployment_observations.import_id | string | True | True |  |
| observation_id | space.satcom.deployment_observations.observation_id | string | True | True | ID \u0441\u043f\u043e\u0441\u0442\u0435\u0440\u0435\u0436\u0435\u043d\u043d\u044f (DEP-\u2026) |
| program_id | space.satcom.deployment_observations.program_id | string | True | False |  |
| spacecraft_model_id | space.satcom.deployment_observations.spacecraft_model_id | string | False | False |  |
| status_metric | space.satcom.deployment_observations.status_metric | string | True | False | \u0421\u0442\u0430\u0442\u0443\u0441\u043d\u0430 \u0432\u0435\u043b\u0438\u0447\u0438\u043d\u0430 (\u043d\u0435 \u043f\u0456\u0434\u0441\u0443\u043c\u043e\u0432\u0443\u044e\u0442\u044c\u0441\u044f \u043c\u0456\u0436 \u0441\u043e\u0431\u043e\u044e) |
| count | space.satcom.deployment_observations.count | integer | True | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u041a\u0410 [\u041a\u0410] |
| observation_date | space.satcom.deployment_observations.observation_date | string | True | False | \u0414\u0430\u0442\u0430 \u0437\u0440\u0456\u0437\u0443 |
| definition_uk | space.satcom.deployment_observations.definition_uk | string | False | False | \u0412\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u043f\u043e\u043a\u0430\u0437\u043d\u0438\u043a\u0430 \u0432 \u0434\u0436\u0435\u0440\u0435\u043b\u0456 |
| information_character | space.satcom.deployment_observations.information_character | string | False | False | \u0425\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0456\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0456\u0457 |
| claim_id | space.satcom.deployment_observations.claim_id | string | True | False |  |

## enabling_devices_technologies



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.enabling_devices_technologies.import_id | string | True | True |  |
| tech_id | space.satcom.enabling_devices_technologies.tech_id | string | True | True | ID (TEC-\u2026) |
| name | space.satcom.enabling_devices_technologies.name | string | True | False |  |
| category | space.satcom.enabling_devices_technologies.category | string | True | False | \u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0456\u044f |
| vendor_org_id | space.satcom.enabling_devices_technologies.vendor_org_id | string | False | False | \u041f\u043e\u0441\u0442\u0430\u0447\u0430\u043b\u044c\u043d\u0438\u043a (NULL \u2014 \u043a\u043b\u0430\u0441 \u0442\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0456\u0457) |
| example_products | space.satcom.enabling_devices_technologies.example_products | string | False | False | \u041f\u0440\u0438\u043a\u043b\u0430\u0434\u0438 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0456\u0432 / \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0456\u0432 |
| function_uk | space.satcom.enabling_devices_technologies.function_uk | string | False | False | \u0424\u0443\u043d\u043a\u0446\u0456\u044f |
| expected_effect_uk | space.satcom.enabling_devices_technologies.expected_effect_uk | string | False | False | \u041e\u0447\u0456\u043a\u0443\u0432\u0430\u043d\u0438\u0439 \u0435\u0444\u0435\u043a\u0442 |
| effect_evidence_type | space.satcom.enabling_devices_technologies.effect_evidence_type | string | False | False | measured / vendor_claim / standard_spec / research_hypothesis |
| application_conditions_uk | space.satcom.enabling_devices_technologies.application_conditions_uk | string | False | False | \u0423\u043c\u043e\u0432\u0438 \u0437\u0430\u0441\u0442\u043e\u0441\u0443\u0432\u0430\u043d\u043d\u044f |
| maturity | space.satcom.enabling_devices_technologies.maturity | string | False | False | \u0417\u0440\u0456\u043b\u0456\u0441\u0442\u044c |
| compatibility_uk | space.satcom.enabling_devices_technologies.compatibility_uk | string | False | False | \u0421\u0443\u043c\u0456\u0441\u043d\u0456\u0441\u0442\u044c |
| dependencies_uk | space.satcom.enabling_devices_technologies.dependencies_uk | string | False | False | \u0417\u0430\u043b\u0435\u0436\u043d\u043e\u0441\u0442\u0456 |
| customer_relevance_uk | space.satcom.enabling_devices_technologies.customer_relevance_uk | string | False | False | \u0417\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u0434\u043b\u044f \u0437\u0430\u043c\u043e\u0432\u043d\u0438\u043a\u0430 |
| claim_id | space.satcom.enabling_devices_technologies.claim_id | string | False | False |  |

## entity_classifications



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.entity_classifications.import_id | string | True | True |  |
| entity_id | space.satcom.entity_classifications.entity_id | string | True | True |  |
| class_id | space.satcom.entity_classifications.class_id | string | True | True |  |
| basis | space.satcom.entity_classifications.basis | string | False | False | claim_id \u0430\u0431\u043e analyst_mapping |

## entity_registry



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.entity_registry.import_id | string | True | True |  |
| entity_id | space.satcom.entity_registry.entity_id | string | True | True | \u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u043e \u0443\u043d\u0456\u043a\u0430\u043b\u044c\u043d\u0438\u0439 ID \u0441\u0443\u0442\u043d\u043e\u0441\u0442\u0456 \u0431\u0443\u0434\u044c-\u044f\u043a\u043e\u0457 \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u043d\u043e\u0457 \u0442\u0430\u0431\u043b\u0438\u0446\u0456 |
| entity_table | space.satcom.entity_registry.entity_table | string | True | False | \u0422\u0430\u0431\u043b\u0438\u0446\u044f, \u0434\u0435 \u0432\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043e \u0441\u0443\u0442\u043d\u0456\u0441\u0442\u044c |
| display_name | space.satcom.entity_registry.display_name | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u0434\u043b\u044f \u0432\u0456\u0434\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u043d\u044f |

## evidence_claims



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.evidence_claims.import_id | string | True | True |  |
| claim_id | space.satcom.evidence_claims.claim_id | string | True | True | \u0421\u0442\u0430\u0431\u0456\u043b\u044c\u043d\u0438\u0439 ID (CLM-\u2026; \u0445\u0435\u0448 entity/field/source/value) |
| entity_id | space.satcom.evidence_claims.entity_id | string | True | False |  |
| field_key | space.satcom.evidence_claims.field_key | string | True | False | \u041a\u043b\u044e\u0447 \u043f\u043e\u043b\u044f (\u0434\u0438\u0432. field_dictionary) |
| raw_value | space.satcom.evidence_claims.raw_value | string | True | False | \u0417\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u044f\u043a \u0443 \u0434\u0436\u0435\u0440\u0435\u043b\u0456 |
| value_num | space.satcom.evidence_claims.value_num | number | False | False | \u041d\u043e\u0440\u043c\u0430\u043b\u0456\u0437\u043e\u0432\u0430\u043d\u0435 \u0447\u0438\u0441\u043b\u043e |
| value_text | space.satcom.evidence_claims.value_text | string | False | False | \u041d\u043e\u0440\u043c\u0430\u043b\u0456\u0437\u043e\u0432\u0430\u043d\u0435 \u0442\u0435\u043a\u0441\u0442\u043e\u0432\u0435 / \u043a\u043b\u0430\u0441\u043e\u0432\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f |
| unit | space.satcom.evidence_claims.unit | string | False | False | \u041e\u0434\u0438\u043d\u0438\u0446\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u0456\u0437\u043e\u0432\u0430\u043d\u043e\u0433\u043e \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f |
| qualifier | space.satcom.evidence_claims.qualifier | string | True | False | \u041a\u0432\u0430\u043b\u0456\u0444\u0456\u043a\u0430\u0442\u043e\u0440 |
| value_min | space.satcom.evidence_claims.value_min | number | False | False |  |
| value_max | space.satcom.evidence_claims.value_max | number | False | False |  |
| fact_date | space.satcom.evidence_claims.fact_date | string | False | False | \u0414\u0430\u0442\u0430 \u0444\u0430\u043a\u0442\u0443 |
| valid_from | space.satcom.evidence_claims.valid_from | string | False | False |  |
| valid_to | space.satcom.evidence_claims.valid_to | string | False | False |  |
| access_date | space.satcom.evidence_claims.access_date | date | True | False |  |
| source_id | space.satcom.evidence_claims.source_id | string | True | False |  |
| locator | space.satcom.evidence_claims.locator | string | False | False | \u0421\u0442\u043e\u0440\u0456\u043d\u043a\u0430 / \u0442\u0430\u0431\u043b\u0438\u0446\u044f / \u0440\u043e\u0437\u0434\u0456\u043b |
| quote | space.satcom.evidence_claims.quote | string | False | False | \u0414\u043e\u0441\u043b\u0456\u0432\u043d\u0438\u0439 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0434\u0436\u0435\u0440\u0435\u043b\u0430 |
| information_character | space.satcom.evidence_claims.information_character | string | True | False | \u0425\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0456\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0456\u0457 |
| comment | space.satcom.evidence_claims.comment | string | False | False | \u041e\u0431\u043c\u0435\u0436\u0435\u043d\u043d\u044f |
| contradiction_group | space.satcom.evidence_claims.contradiction_group | string | False | False | \u0413\u0440\u0443\u043f\u0430 \u0430\u043b\u044c\u0442\u0435\u0440\u043d\u0430\u0442\u0438\u0432\u043d\u0438\u0445 \u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u044c \u0442\u043e\u0433\u043e \u0436 \u043f\u043e\u043b\u044f |
| is_canonical | space.satcom.evidence_claims.is_canonical | boolean | True | False | \u041a\u0430\u043d\u043e\u043d\u0456\u0447\u043d\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u043f\u043e\u043b\u044f |
| selection_rule | space.satcom.evidence_claims.selection_rule | string | False | False | \u041f\u0440\u0430\u0432\u0438\u043b\u043e \u0432\u0438\u0431\u043e\u0440\u0443 \u043a\u0430\u043d\u043e\u043d\u0456\u0447\u043d\u043e\u0433\u043e \u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f |
| formula | space.satcom.evidence_claims.formula | string | False | False | \u0424\u043e\u0440\u043c\u0443\u043b\u0430 \u0434\u043b\u044f \u0440\u043e\u0437\u0440\u0430\u0445\u0443\u043d\u043a\u0443 |
| input_claim_ids | space.satcom.evidence_claims.input_claim_ids | string | False | False | \u0412\u0445\u0456\u0434\u043d\u0456 claim_id \u0440\u043e\u0437\u0440\u0430\u0445\u0443\u043d\u043a\u0443 (\u0447\u0435\u0440\u0435\u0437 ';') |
| verification_status | space.satcom.evidence_claims.verification_status | string | True | False | quote_verified / value_found / token_found / fetch_blocked / unreachable / not_rechecked / calculated |
| origin | space.satcom.evidence_claims.origin | string | False | False | \u041f\u043e\u0445\u043e\u0434\u0436\u0435\u043d\u043d\u044f \u0437\u0430\u043f\u0438\u0441\u0443: catalog_research / prior_catalog_import / orbital_catalog_parser |

## field_dictionary



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.field_dictionary.import_id | string | True | True |  |
| field_key | space.satcom.field_dictionary.field_key | string | True | True |  |
| entity_table | space.satcom.field_dictionary.entity_table | string | False | False | \u0422\u0430\u0431\u043b\u0438\u0446\u044f, \u0434\u043e \u044f\u043a\u043e\u0457 \u043d\u0430\u043b\u0435\u0436\u0438\u0442\u044c \u043f\u043e\u043b\u0435 |
| field_group | space.satcom.field_dictionary.field_group | string | False | False | \u0413\u0440\u0443\u043f\u0430 \u0434\u043b\u044f \u0437\u0430\u043f\u043e\u0432\u043d\u0435\u043d\u043e\u0441\u0442\u0456 |
| unit | space.satcom.field_dictionary.unit | string | False | False |  |
| description_uk | space.satcom.field_dictionary.description_uk | string | False | False |  |
| applies_to | space.satcom.field_dictionary.applies_to | string | False | False | \u041f\u0440\u0430\u0432\u0438\u043b\u043e \u0437\u0430\u0441\u0442\u043e\u0441\u043e\u0432\u043d\u043e\u0441\u0442\u0456 |

## financial_observations



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.financial_observations.import_id | string | True | True |  |
| fin_id | space.satcom.financial_observations.fin_id | string | True | True | ID (FIN-\u2026) |
| entity_id | space.satcom.financial_observations.entity_id | string | True | False | \u0421\u0443\u0442\u043d\u0456\u0441\u0442\u044c (\u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456\u044f, \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u0430, \u0441\u0435\u0440\u0432\u0456\u0441, \u0442\u0435\u0440\u043c\u0456\u043d\u0430\u043b, \u043d\u043e\u0441\u0456\u0439) |
| basis | space.satcom.financial_observations.basis | string | True | False | \u0424\u0456\u043d\u0430\u043d\u0441\u043e\u0432\u0430 \u0431\u0430\u0437\u0430 (\u043d\u0435 \u0437\u043c\u0456\u0448\u0443\u044e\u0442\u044c\u0441\u044f \u0432 \u0440\u0435\u0439\u0442\u0438\u043d\u0433\u0430\u0445) |
| comparison_group | space.satcom.financial_observations.comparison_group | string | False | False | A \u2014 \u0437\u0430\u043b\u0443\u0447\u0435\u043d\u0438\u0439 \u043a\u0430\u043f\u0456\u0442\u0430\u043b; B \u2014 \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u043d\u043e \u0437\u043e\u0431\u043e\u0432'\u044f\u0437\u0430\u043d\u0435 \u0444\u0456\u043d\u0430\u043d\u0441\u0443\u0432\u0430\u043d\u043d\u044f (\u043a\u0440\u0435\u0434\u0438\u0442\u043d\u0456 \u043b\u0456\u043d\u0456\u0457, \u0433\u0440\u0430\u043d\u0442\u0438, \u0437\u043e\u0431\u043e\u0432'\u044f\u0437\u0430\u043d\u043d\u044f \u0430\u043a\u0446\u0456\u043e\u043d\u0435\u0440\u0456\u0432); C \u2014 \u0431\u044e\u0434\u0436\u0435\u0442 / \u0432\u0430\u0440\u0442\u0456\u0441\u0442\u044c \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u0438; D \u2014 \u0432\u0438\u0442\u0440\u0430\u0442\u0438 \u0433\u0440\u0443\u043f\u0438 (CAPEX); K \u2014 \u0432\u0430\u0440\u0442\u0456\u0441\u0442\u044c \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u0443 \u0437\u0430\u043c\u043e\u0432\u043b\u0435\u043d\u043d\u044f (\u0437\u0430\u043a\u0443\u043f\u0456\u0432\u043b\u044f \u041a\u0410/\u043f\u043e\u0441\u043b\u0443\u0433); M \u2014 \u043e\u0446\u0456\u043d\u043a\u0430 \u0443\u0433\u043e\u0434\u0438 M&A; P \u2014 \u0446\u0456\u043d\u0438 |
| amount | space.satcom.financial_observations.amount | number | True | False | \u0421\u0443\u043c\u0430 \u0443 \u0432\u0430\u043b\u044e\u0442\u0456 \u0434\u0436\u0435\u0440\u0435\u043b\u0430 |
| currency | space.satcom.financial_observations.currency | string | True | False | ISO 4217 |
| amount_usd_nominal | space.satcom.financial_observations.amount_usd_nominal | number | False | False | \u041d\u043e\u043c\u0456\u043d\u0430\u043b\u044c\u043d\u0430 \u043a\u043e\u043d\u0432\u0435\u0440\u0442\u0430\u0446\u0456\u044f (\u0444\u043e\u0440\u043c\u0443\u043b\u0430: amount \xd7 fx_rates.usd_per_unit) [USD] |
| fx_id | space.satcom.financial_observations.fx_id | string | False | False |  |
| fact_date | space.satcom.financial_observations.fact_date | string | False | False | \u0414\u0430\u0442\u0430 \u0444\u0430\u043a\u0442\u0443 / \u043e\u0433\u043e\u043b\u043e\u0448\u0435\u043d\u043d\u044f |
| period_start | space.satcom.financial_observations.period_start | string | False | False |  |
| period_end | space.satcom.financial_observations.period_end | string | False | False |  |
| counterparty_org_id | space.satcom.financial_observations.counterparty_org_id | string | False | False | \u041a\u0440\u0435\u0434\u0438\u0442\u043e\u0440 / \u0456\u043d\u0432\u0435\u0441\u0442\u043e\u0440 / \u0437\u0430\u043c\u043e\u0432\u043d\u0438\u043a |
| price_region | space.satcom.financial_observations.price_region | string | False | False | \u0420\u0435\u0433\u0456\u043e\u043d \u0446\u0456\u043d\u0438 |
| package_scope | space.satcom.financial_observations.package_scope | string | False | False | \u041a\u043e\u043c\u043f\u043b\u0435\u043a\u0442\u0430\u0446\u0456\u044f / \u043f\u043e\u0434\u0430\u0442\u043a\u0438 / \u043f\u0435\u0440\u0456\u043e\u0434 |
| claim_id | space.satcom.financial_observations.claim_id | string | True | False |  |
| notes | space.satcom.financial_observations.notes | string | False | False |  |

## fx_rates



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.fx_rates.import_id | string | True | True |  |
| fx_id | space.satcom.fx_rates.fx_id | string | True | True |  |
| currency | space.satcom.fx_rates.currency | string | True | False | ISO 4217 |
| usd_per_unit | space.satcom.fx_rates.usd_per_unit | number | True | False | USD \u0437\u0430 1 \u043e\u0434\u0438\u043d\u0438\u0446\u044e \u0432\u0430\u043b\u044e\u0442\u0438 |
| rate_date | space.satcom.fx_rates.rate_date | date | True | False |  |
| source_id | space.satcom.fx_rates.source_id | string | True | False |  |
| notes | space.satcom.fx_rates.notes | string | False | False |  |

## ground_infrastructure



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.ground_infrastructure.import_id | string | True | True |  |
| ground_id | space.satcom.ground_infrastructure.ground_id | string | True | True | ID (GND-\u2026) |
| name | space.satcom.ground_infrastructure.name | string | True | False |  |
| infra_type | space.satcom.ground_infrastructure.infra_type | string | True | False | \u0422\u0438\u043f |
| operator_org_id | space.satcom.ground_infrastructure.operator_org_id | string | False | False |  |
| program_id | space.satcom.ground_infrastructure.program_id | string | False | False |  |
| country_iso2 | space.satcom.ground_infrastructure.country_iso2 | string | False | False |  |
| location_text | space.satcom.ground_infrastructure.location_text | string | False | False | \u0420\u043e\u0437\u0442\u0430\u0448\u0443\u0432\u0430\u043d\u043d\u044f \u044f\u043a \u0443 \u0434\u0436\u0435\u0440\u0435\u043b\u0456 |
| sites_count | space.satcom.ground_infrastructure.sites_count | integer | False | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u043c\u0430\u0439\u0434\u0430\u043d\u0447\u0438\u043a\u0456\u0432 / \u0430\u043d\u0442\u0435\u043d (\u0434\u043b\u044f \u043c\u0435\u0440\u0435\u0436) |
| bands_text | space.satcom.ground_infrastructure.bands_text | string | False | False | \u0414\u0456\u0430\u043f\u0430\u0437\u043e\u043d\u0438 |
| status | space.satcom.ground_infrastructure.status | string | False | False | operational / planned / construction / retired |
| claim_id | space.satcom.ground_infrastructure.claim_id | string | False | False |  |
| notes | space.satcom.ground_infrastructure.notes | string | False | False |  |

## launch_configurations



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.launch_configurations.import_id | string | True | True |  |
| config_id | space.satcom.launch_configurations.config_id | string | True | True | ID \u043a\u043e\u043d\u0444\u0456\u0433\u0443\u0440\u0430\u0446\u0456\u0457 (LVC-\u2026) |
| lv_id | space.satcom.launch_configurations.lv_id | string | True | False |  |
| config_name | space.satcom.launch_configurations.config_name | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u043a\u043e\u043d\u0444\u0456\u0433\u0443\u0440\u0430\u0446\u0456\u0457 (\u043a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u043f\u0440\u0438\u0441\u043a\u043e\u0440\u044e\u0432\u0430\u0447\u0456\u0432, \u0440\u0435\u0436\u0438\u043c \u043f\u043e\u0432\u0435\u0440\u043d\u0435\u043d\u043d\u044f) |
| recovery_mode | space.satcom.launch_configurations.recovery_mode | string | False | False | expendable / droneship / rtls / partial / n/a |
| orbit_type | space.satcom.launch_configurations.orbit_type | string | True | False | LEO / SSO / GTO / GEO / MEO / TLI / TMI |
| altitude_km | space.satcom.launch_configurations.altitude_km | number | False | False | \u0412\u0438\u0441\u043e\u0442\u0430 \u043e\u043f\u043e\u0440\u043d\u043e\u0457 \u043e\u0440\u0431\u0456\u0442\u0438 (\u0430\u0431\u043e \u043f\u0435\u0440\u0438\u0433\u0435\u0439) [\u043a\u043c] |
| apogee_km | space.satcom.launch_configurations.apogee_km | number | False | False |  |
| inclination_deg | space.satcom.launch_configurations.inclination_deg | number | False | False |  |
| payload_kg | space.satcom.launch_configurations.payload_kg | number | True | False | \u0412\u0430\u043d\u0442\u0430\u0436\u043d\u0456\u0441\u0442\u044c \u043d\u0430 \u0432\u043a\u0430\u0437\u0430\u043d\u0443 \u043e\u0440\u0431\u0456\u0442\u0443 [\u043a\u0433] |
| qualifier | space.satcom.launch_configurations.qualifier | string | False | False | exact / approx / max / min |
| claim_id | space.satcom.launch_configurations.claim_id | string | True | False |  |
| notes | space.satcom.launch_configurations.notes | string | False | False | \u0423\u043c\u043e\u0432\u0438 |

## launch_events_contracts



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.launch_events_contracts.import_id | string | True | True |  |
| event_id | space.satcom.launch_events_contracts.event_id | string | True | True | ID (LEC-\u2026) |
| event_type | space.satcom.launch_events_contracts.event_type | string | True | False | contract / launch / option / rideshare_booking / milestone |
| program_id | space.satcom.launch_events_contracts.program_id | string | False | False |  |
| lv_id | space.satcom.launch_events_contracts.lv_id | string | False | False |  |
| customer_org_id | space.satcom.launch_events_contracts.customer_org_id | string | False | False |  |
| provider_org_id | space.satcom.launch_events_contracts.provider_org_id | string | False | False |  |
| announced_date | space.satcom.launch_events_contracts.announced_date | string | False | False | \u0414\u0430\u0442\u0430 \u043e\u0433\u043e\u043b\u043e\u0448\u0435\u043d\u043d\u044f / \u043f\u0456\u0434\u043f\u0438\u0441\u0430\u043d\u043d\u044f |
| event_date | space.satcom.launch_events_contracts.event_date | string | False | False | \u0414\u0430\u0442\u0430 \u043f\u043e\u0434\u0456\u0457 (\u0434\u043b\u044f \u043f\u0443\u0441\u043a\u0443) |
| window_start | space.satcom.launch_events_contracts.window_start | string | False | False | \u041f\u043e\u0447\u0430\u0442\u043e\u043a \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u043d\u043e\u0433\u043e \u0432\u0456\u043a\u043d\u0430 |
| window_end | space.satcom.launch_events_contracts.window_end | string | False | False | \u041a\u0456\u043d\u0435\u0446\u044c \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u043d\u043e\u0433\u043e \u0432\u0456\u043a\u043d\u0430 |
| launches_count | space.satcom.launch_events_contracts.launches_count | integer | False | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u043f\u0443\u0441\u043a\u0456\u0432 \u0443 \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u0456 / \u043f\u043e\u0434\u0456\u0457 |
| spacecraft_count | space.satcom.launch_events_contracts.spacecraft_count | integer | False | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u041a\u0410 |
| status | space.satcom.launch_events_contracts.status | string | False | False | contracted / completed / in_progress / cancelled / option_unexercised |
| claim_id | space.satcom.launch_events_contracts.claim_id | string | False | False |  |
| notes | space.satcom.launch_events_contracts.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## launch_vehicles



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.launch_vehicles.import_id | string | True | True |  |
| lv_id | space.satcom.launch_vehicles.lv_id | string | True | True | ID \u043d\u043e\u0441\u0456\u044f (LV-\u2026) |
| name | space.satcom.launch_vehicles.name | string | True | False | \u041d\u0430\u0437\u0432\u0430 |
| family | space.satcom.launch_vehicles.family | string | False | False | \u0421\u0456\u043c\u0435\u0439\u0441\u0442\u0432\u043e |
| provider_org_id | space.satcom.launch_vehicles.provider_org_id | string | False | False | \u041f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440 \u043f\u0443\u0441\u043a\u0443 |
| country_iso2 | space.satcom.launch_vehicles.country_iso2 | string | False | False |  |
| status | space.satcom.launch_vehicles.status | string | True | False | \u0421\u0442\u0430\u043d |
| first_flight_date | space.satcom.launch_vehicles.first_flight_date | string | False | False | \u041f\u0435\u0440\u0448\u0438\u0439 \u043f\u043e\u043b\u0456\u0442 |
| stages | space.satcom.launch_vehicles.stages | integer | False | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u0441\u0442\u0443\u043f\u0435\u043d\u0456\u0432 |
| reusability | space.satcom.launch_vehicles.reusability | string | False | False | none / first_stage_recovery / full_reuse_planned / booster_recovery / unknown |
| height_m | space.satcom.launch_vehicles.height_m | number | False | False |  |
| diameter_m | space.satcom.launch_vehicles.diameter_m | number | False | False |  |
| liftoff_mass_t | space.satcom.launch_vehicles.liftoff_mass_t | number | False | False |  |
| fairing_diameter_m | space.satcom.launch_vehicles.fairing_diameter_m | number | False | False | \u0417\u043e\u0432\u043d\u0456\u0448\u043d\u0456\u0439 \u0434\u0456\u0430\u043c\u0435\u0442\u0440 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u043e\u0433\u043e \u043e\u0431\u0442\u0456\u0447\u043d\u0438\u043a\u0430 [\u043c] |
| fairing_height_m | space.satcom.launch_vehicles.fairing_height_m | number | False | False | \u0412\u0438\u0441\u043e\u0442\u0430 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u043e\u0433\u043e \u043e\u0431\u0442\u0456\u0447\u043d\u0438\u043a\u0430 [\u043c] |
| flights_total | space.satcom.launch_vehicles.flights_total | integer | False | False | \u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u0437\u0430\u043f\u0443\u0441\u043a\u0456\u0432 \u043d\u0430 \u0434\u0430\u0442\u0443 flights_as_of |
| flights_successful | space.satcom.launch_vehicles.flights_successful | integer | False | False | \u0423\u0441\u043f\u0456\u0448\u043d\u0456 \u0437\u0430\u043f\u0443\u0441\u043a\u0438 |
| flights_as_of | space.satcom.launch_vehicles.flights_as_of | date | False | False | \u0414\u0430\u0442\u0430 \u043b\u0456\u0447\u0438\u043b\u044c\u043d\u0438\u043a\u0430 |
| export_access_note | space.satcom.launch_vehicles.export_access_note | string | False | False | \u041e\u0431\u043c\u0435\u0436\u0435\u043d\u043d\u044f \u0434\u043e\u0441\u0442\u0443\u043f\u0443 (\u0441\u0430\u043d\u043a\u0446\u0456\u0457, \u043b\u0438\u0448\u0435 \u0443\u0440\u044f\u0434\u043e\u0432\u0456 \u0437\u0430\u043c\u043e\u0432\u043d\u0438\u043a\u0438 \u0442\u043e\u0449\u043e) |
| notes | space.satcom.launch_vehicles.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## opportunity_evidence



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.opportunity_evidence.import_id | string | True | True |  |
| opportunity_id | space.satcom.opportunity_evidence.opportunity_id | string | True | True |  |
| claim_id | space.satcom.opportunity_evidence.claim_id | string | True | True |  |

## organization_relationships



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.organization_relationships.import_id | string | True | True |  |
| relationship_id | space.satcom.organization_relationships.relationship_id | string | True | True | ID \u0437\u0432'\u044f\u0437\u043a\u0443 (REL-\u2026) |
| from_org_id | space.satcom.organization_relationships.from_org_id | string | True | False | \u0421\u0443\u0431'\u0454\u043a\u0442 \u0437\u0432'\u044f\u0437\u043a\u0443 |
| to_org_id | space.satcom.organization_relationships.to_org_id | string | True | False | \u041e\u0431'\u0454\u043a\u0442 \u0437\u0432'\u044f\u0437\u043a\u0443 |
| relationship_type | space.satcom.organization_relationships.relationship_type | string | True | False | \u0422\u0438\u043f \u0437\u0432'\u044f\u0437\u043a\u0443 |
| share_pct | space.satcom.organization_relationships.share_pct | number | False | False | \u0427\u0430\u0441\u0442\u043a\u0430 \u0443\u0447\u0430\u0441\u0442\u0456, \u044f\u043a\u0449\u043e \u0440\u043e\u0437\u043a\u0440\u0438\u0442\u0430 [%] |
| start_date | space.satcom.organization_relationships.start_date | string | False | False | \u041f\u043e\u0447\u0430\u0442\u043e\u043a \u0434\u0456\u0457 |
| end_date | space.satcom.organization_relationships.end_date | string | False | False | \u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043d\u044f \u0434\u0456\u0457 |
| program_id | space.satcom.organization_relationships.program_id | string | False | False | \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u0430, \u044f\u043a\u043e\u0457 \u0441\u0442\u043e\u0441\u0443\u0454\u0442\u044c\u0441\u044f \u0437\u0432'\u044f\u0437\u043e\u043a |
| claim_id | space.satcom.organization_relationships.claim_id | string | False | False | \u0414\u043e\u043a\u0430\u0437 |
| notes | space.satcom.organization_relationships.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## organizations



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.organizations.import_id | string | True | True |  |
| org_id | space.satcom.organizations.org_id | string | True | True | ID \u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456\u0457 (ORG-\u2026) |
| name | space.satcom.organizations.name | string | True | False | \u041f\u043e\u0448\u0438\u0440\u0435\u043d\u0430 \u043d\u0430\u0437\u0432\u0430 |
| legal_name | space.satcom.organizations.legal_name | string | False | False | \u042e\u0440\u0438\u0434\u0438\u0447\u043d\u0430 \u043d\u0430\u0437\u0432\u0430 (\u044f\u043a\u0449\u043e \u0432\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430) |
| country_iso2 | space.satcom.organizations.country_iso2 | string | False | False | \u041a\u0440\u0430\u0457\u043d\u0430 \u0456\u043d\u043a\u043e\u0440\u043f\u043e\u0440\u0430\u0446\u0456\u0457 / \u0448\u0442\u0430\u0431-\u043a\u0432\u0430\u0440\u0442\u0438\u0440\u0438 |
| org_type | space.satcom.organizations.org_type | string | True | False | \u041e\u0441\u043d\u043e\u0432\u043d\u0430 \u0440\u043e\u043b\u044c |
| ownership_type | space.satcom.organizations.ownership_type | string | False | False | \u0422\u0438\u043f \u0432\u043b\u0430\u0441\u043d\u043e\u0441\u0442\u0456 |
| parent_org_id | space.satcom.organizations.parent_org_id | string | False | False | \u041c\u0430\u0442\u0435\u0440\u0438\u043d\u0441\u044c\u043a\u0430 \u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456\u044f (\u044f\u043a\u0449\u043e \u0432\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430 \u0434\u0436\u0435\u0440\u0435\u043b\u043e\u043c) |
| status | space.satcom.organizations.status | string | False | False | active / merged / acquired / defunct / renamed |
| website_url | space.satcom.organizations.website_url | string | False | False | \u041e\u0444\u0456\u0446\u0456\u0439\u043d\u0438\u0439 \u0441\u0430\u0439\u0442 (\u0456\u0434\u0435\u043d\u0442\u0438\u0444\u0456\u043a\u0430\u0446\u0456\u044f, \u043d\u0435 \u0434\u043e\u043a\u0430\u0437 \u0447\u0438\u0441\u043b\u043e\u0432\u0438\u0445 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u0456\u0432) |
| public_contact_channel | space.satcom.organizations.public_contact_channel | string | False | False | \u041f\u0443\u0431\u043b\u0456\u0447\u043d\u0438\u0439 \u043a\u0430\u043d\u0430\u043b \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u0443 \u0434\u043b\u044f \u043f\u0430\u0440\u0442\u043d\u0435\u0440\u0441\u0442\u0432\u0430 / \u0437\u0430\u043a\u0443\u043f\u0456\u0432\u043b\u0456 (URL \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0438) |
| competencies | space.satcom.organizations.competencies | string | False | False | \u041a\u043b\u044e\u0447\u043e\u0432\u0456 \u0442\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0456\u0447\u043d\u0456 \u043a\u043e\u043c\u043f\u0435\u0442\u0435\u043d\u0446\u0456\u0457 (\u043a\u043e\u0440\u043e\u0442\u043a\u043e) |
| notes | space.satcom.organizations.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## parameter_gaps



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.parameter_gaps.import_id | string | True | True |  |
| gap_id | space.satcom.parameter_gaps.gap_id | string | True | True |  |
| entity_id | space.satcom.parameter_gaps.entity_id | string | True | False |  |
| field_key | space.satcom.parameter_gaps.field_key | string | True | False |  |
| field_group | space.satcom.parameter_gaps.field_group | string | False | False |  |
| null_reason | space.satcom.parameter_gaps.null_reason | string | True | False | not_found / not_disclosed / requires_vendor_quote / cannot_verify / not_applicable |
| decision_impact | space.satcom.parameter_gaps.decision_impact | string | False | False | high / medium / low |
| next_step_uk | space.satcom.parameter_gaps.next_step_uk | string | False | False | \u0429\u043e \u0437\u0430\u043f\u0438\u0442\u0430\u0442\u0438 / \u0434\u0435 \u0448\u0443\u043a\u0430\u0442\u0438 |

## partnerships_opportunities



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.partnerships_opportunities.import_id | string | True | True |  |
| opportunity_id | space.satcom.partnerships_opportunities.opportunity_id | string | True | True | ID (OPP-\u2026) |
| opportunity_type | space.satcom.partnerships_opportunities.opportunity_type | string | True | False | \u0422\u0438\u043f \u043c\u043e\u0436\u043b\u0438\u0432\u043e\u0441\u0442\u0456 |
| title_uk | space.satcom.partnerships_opportunities.title_uk | string | True | False | \u041a\u043e\u0440\u043e\u0442\u043a\u0430 \u043d\u0430\u0437\u0432\u0430 |
| counterparty_org_id | space.satcom.partnerships_opportunities.counterparty_org_id | string | False | False |  |
| program_id | space.satcom.partnerships_opportunities.program_id | string | False | False |  |
| factual_basis_uk | space.satcom.partnerships_opportunities.factual_basis_uk | string | True | False | \u0424\u0430\u043a\u0442\u0438\u0447\u043d\u0430 \u043f\u0456\u0434\u0441\u0442\u0430\u0432\u0430 (\u0437 \u0434\u0436\u0435\u0440\u0435\u043b\u043e\u043c) |
| required_competencies_uk | space.satcom.partnerships_opportunities.required_competencies_uk | string | False | False | \u041d\u0435\u043e\u0431\u0445\u0456\u0434\u043d\u0456 \u043a\u043e\u043c\u043f\u0435\u0442\u0435\u043d\u0446\u0456\u0457 \u0437\u0430\u043c\u043e\u0432\u043d\u0438\u043a\u0430 |
| dependencies_uk | space.satcom.partnerships_opportunities.dependencies_uk | string | False | False | \u0417\u0430\u043b\u0435\u0436\u043d\u043e\u0441\u0442\u0456 / \u0440\u0438\u0437\u0438\u043a\u0438 |
| open_questions_uk | space.satcom.partnerships_opportunities.open_questions_uk | string | False | False | \u0412\u0456\u0434\u043a\u0440\u0438\u0442\u0456 \u043f\u0438\u0442\u0430\u043d\u043d\u044f \u0434\u043e \u043f\u043e\u0441\u0442\u0430\u0447\u0430\u043b\u044c\u043d\u0438\u043a\u0430 |
| analyst_assumption_uk | space.satcom.partnerships_opportunities.analyst_assumption_uk | string | False | False | \u041f\u0440\u0438\u043f\u0443\u0449\u0435\u043d\u043d\u044f \u0430\u043d\u0430\u043b\u0456\u0442\u0438\u043a\u0430 (\u043e\u043a\u0440\u0435\u043c\u043e \u0432\u0456\u0434 \u0444\u0430\u043a\u0442\u0456\u0432) |
| readiness | space.satcom.partnerships_opportunities.readiness | string | False | False | available_now / requires_negotiation / emerging / watchlist |
| ukraine_access_note | space.satcom.partnerships_opportunities.ukraine_access_note | string | False | False | \u0420\u0435\u0433\u0443\u043b\u044f\u0442\u043e\u0440\u043d\u0456 \u0439 \u0435\u043a\u0441\u043f\u043e\u0440\u0442\u043d\u0456 \u0443\u043c\u043e\u0432\u0438 \u0434\u043b\u044f \u0423\u043a\u0440\u0430\u0457\u043d\u0438 |
| basis_claim_id | space.satcom.partnerships_opportunities.basis_claim_id | string | False | False | \u041e\u0441\u043d\u043e\u0432\u043d\u0435 \u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043d\u044f-\u043f\u0456\u0434\u0441\u0442\u0430\u0432\u0430 |

## program_organizations



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.program_organizations.import_id | string | True | True |  |
| program_id | space.satcom.program_organizations.program_id | string | True | True |  |
| org_id | space.satcom.program_organizations.org_id | string | True | True |  |
| role | space.satcom.program_organizations.role | string | True | True | \u0420\u043e\u043b\u044c |
| claim_id | space.satcom.program_organizations.claim_id | string | False | False | \u0414\u043e\u043a\u0430\u0437 |

## satcom_files



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.satcom_files.import_id | string | True | True |  |
| path | space.satcom.satcom_files.path | string | True | True |  |
| sha256 | space.satcom.satcom_files.sha256 | string | True | False |  |
| size_bytes | space.satcom.satcom_files.size_bytes | integer | True | False |  |

## satcom_imports



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.satcom_imports.import_id | string | True | True |  |
| contract_version | space.satcom.satcom_imports.contract_version | string | True | False |  |
| contract_digest | space.satcom.satcom_imports.contract_digest | string | True | False |  |
| adapter_version | space.satcom.satcom_imports.adapter_version | string | True | False |  |

## satcom_rows



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.satcom_rows.import_id | string | True | True |  |
| table_name | space.satcom.satcom_rows.table_name | string | True | True |  |
| row_number | space.satcom.satcom_rows.row_number | integer | True | True |  |
| cells_json | space.satcom.satcom_rows.cells_json | string | True | False |  |

## search_coverage



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.search_coverage.import_id | string | True | True |  |
| coverage_id | space.satcom.search_coverage.coverage_id | string | True | True |  |
| category | space.satcom.search_coverage.category | string | True | False |  |
| region | space.satcom.search_coverage.region | string | True | False |  |
| sources_checked | space.satcom.search_coverage.sources_checked | string | False | False | \u041f\u0435\u0440\u0435\u0432\u0456\u0440\u0435\u043d\u0456 \u043f\u0440\u043e\u0444\u0456\u043b\u044c\u043d\u0456 \u0434\u0436\u0435\u0440\u0435\u043b\u0430 |
| entities_found | space.satcom.search_coverage.entities_found | integer | False | False |  |
| open_gaps_uk | space.satcom.search_coverage.open_gaps_uk | string | False | False |  |
| saturation | space.satcom.search_coverage.saturation | string | False | False | saturated / continuing_yield / not_started |
| check_date | space.satcom.search_coverage.check_date | date | False | False |  |

## services_offerings



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.services_offerings.import_id | string | True | True |  |
| service_id | space.satcom.services_offerings.service_id | string | True | True | ID (SVC-\u2026) |
| name | space.satcom.services_offerings.name | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u0441\u0435\u0440\u0432\u0456\u0441\u0443 / \u0442\u0430\u0440\u0438\u0444\u043d\u043e\u0457 \u043b\u0456\u043d\u0456\u0439\u043a\u0438 |
| provider_org_id | space.satcom.services_offerings.provider_org_id | string | False | False | \u041f\u043e\u0441\u0442\u0430\u0447\u0430\u043b\u044c\u043d\u0438\u043a |
| program_id | space.satcom.services_offerings.program_id | string | False | False | \u041c\u0435\u0440\u0435\u0436\u0430 |
| service_type | space.satcom.services_offerings.service_type | string | True | False | \u0422\u0438\u043f \u0441\u0435\u0440\u0432\u0456\u0441\u0443 |
| channel | space.satcom.services_offerings.channel | string | False | False | direct / reseller / wholesale / partner / government |
| region_scope | space.satcom.services_offerings.region_scope | string | False | False | \u0413\u0435\u043e\u0433\u0440\u0430\u0444\u0456\u044f \u043f\u0440\u043e\u043f\u043e\u0437\u0438\u0446\u0456\u0457 |
| ukraine_availability | space.satcom.services_offerings.ukraine_availability | string | False | False | \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u0456\u0441\u0442\u044c \u0432 \u0423\u043a\u0440\u0430\u0457\u043d\u0456 \u0437\u0430 \u0434\u0436\u0435\u0440\u0435\u043b\u0430\u043c\u0438 |
| dl_mbps_claimed | space.satcom.services_offerings.dl_mbps_claimed | number | False | False | \u0417\u0430\u044f\u0432\u043b\u0435\u043d\u0430 \u0448\u0432\u0438\u0434\u043a\u0456\u0441\u0442\u044c DL (\u043d\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0456\u044f) [\u041c\u0431\u0456\u0442/\u0441] |
| ul_mbps_claimed | space.satcom.services_offerings.ul_mbps_claimed | number | False | False |  |
| latency_ms_claimed | space.satcom.services_offerings.latency_ms_claimed | number | False | False |  |
| sla_note | space.satcom.services_offerings.sla_note | string | False | False | CIR / SLA / \u043f\u0440\u0456\u043e\u0440\u0438\u0442\u0435\u0442 \u2014 \u044f\u043a \u0441\u0444\u043e\u0440\u043c\u0443\u043b\u044c\u043e\u0432\u0430\u043d\u043e \u0434\u0436\u0435\u0440\u0435\u043b\u043e\u043c |
| terms_note | space.satcom.services_offerings.terms_note | string | False | False | \u041e\u0431\u043c\u0435\u0436\u0435\u043d\u043d\u044f \u0442\u0440\u0430\u0444\u0456\u043a\u0443, \u043c\u043e\u0431\u0456\u043b\u044c\u043d\u0456\u0441\u0442\u044c, \u0443\u043c\u043e\u0432\u0438 |
| claim_id | space.satcom.services_offerings.claim_id | string | False | False |  |
| notes | space.satcom.services_offerings.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## sources



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.sources.import_id | string | True | True |  |
| source_id | space.satcom.sources.source_id | string | True | True | \u0421\u0442\u0430\u0431\u0456\u043b\u044c\u043d\u0438\u0439 ID \u0434\u0436\u0435\u0440\u0435\u043b\u0430 (SRC-\u2026; \u0445\u0435\u0448 URL) |
| url | space.satcom.sources.url | string | True | False | \u041f\u0440\u044f\u043c\u0438\u0439 URL \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 |
| title | space.satcom.sources.title | string | False | False | \u041d\u0430\u0437\u0432\u0430 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 / \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0438 |
| publisher | space.satcom.sources.publisher | string | False | False | \u0412\u0438\u0434\u0430\u0432\u0435\u0446\u044c / \u0430\u0432\u0442\u043e\u0440 |
| document_date | space.satcom.sources.document_date | string | False | False | \u0414\u0430\u0442\u0430 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 \u0430\u0431\u043e \u043e\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044f (\u044f\u043a\u0449\u043e \u0432\u043a\u0430\u0437\u0430\u043d\u0430) |
| document_revision | space.satcom.sources.document_revision | string | False | False | \u0420\u0435\u0432\u0456\u0437\u0456\u044f / \u0432\u0435\u0440\u0441\u0456\u044f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 |
| document_type | space.satcom.sources.document_type | string | False | False | \u0422\u0438\u043f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 |
| language | space.satcom.sources.language | string | False | False | \u041c\u043e\u0432\u0430 (ISO 639-1) |
| access_date | space.satcom.sources.access_date | date | False | False | \u0414\u0430\u0442\u0430 \u043e\u0441\u0442\u0430\u043d\u043d\u044c\u043e\u0433\u043e \u0434\u043e\u0441\u0442\u0443\u043f\u0443 |
| http_status | space.satcom.sources.http_status | integer | False | False | HTTP-\u043a\u043e\u0434 \u043f\u0440\u0438 \u043e\u0441\u0442\u0430\u043d\u043d\u0456\u0439 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u0446\u0456 |
| content_kind | space.satcom.sources.content_kind | string | False | False | html / pdf / csv / local |
| content_sha256 | space.satcom.sources.content_sha256 | string | False | False | SHA-256 \u0437\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0435\u043d\u043e\u0433\u043e \u0432\u043c\u0456\u0441\u0442\u0443 (\u043a\u0435\u0448 output/cache/sources) |
| verification_status | space.satcom.sources.verification_status | string | True | False | \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438 \u0432\u043c\u0456\u0441\u0442\u0443 |
| archive_url | space.satcom.sources.archive_url | string | False | False | \u0410\u0440\u0445\u0456\u0432\u043d\u0430 \u043a\u043e\u043f\u0456\u044f, \u0432\u0438\u043a\u043e\u0440\u0438\u0441\u0442\u0430\u043d\u0430 \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0432\u0456\u0440\u043a\u0438, \u044f\u043a\u0449\u043e \u043e\u0440\u0438\u0433\u0456\u043d\u0430\u043b \u0431\u043b\u043e\u043a\u0443\u0454 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u043d\u0438\u0439 \u0434\u043e\u0441\u0442\u0443\u043f |
| notes | space.satcom.sources.notes | string | False | False | \u041e\u0431\u043c\u0435\u0436\u0435\u043d\u043d\u044f \u0434\u0436\u0435\u0440\u0435\u043b\u0430 |

## spacecraft_models



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.spacecraft_models.import_id | string | True | True |  |
| spacecraft_model_id | space.satcom.spacecraft_models.spacecraft_model_id | string | True | True | ID \u043c\u043e\u0434\u0435\u043b\u0456 / \u043f\u043e\u043a\u043e\u043b\u0456\u043d\u043d\u044f \u041a\u0410 (SCM-\u2026) |
| program_id | space.satcom.spacecraft_models.program_id | string | False | False | \u041f\u0440\u043e\u0433\u0440\u0430\u043c\u0430 |
| name | space.satcom.spacecraft_models.name | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u043c\u043e\u0434\u0435\u043b\u0456 / \u041a\u0410 |
| generation | space.satcom.spacecraft_models.generation | string | False | False | \u041f\u043e\u043a\u043e\u043b\u0456\u043d\u043d\u044f / \u0441\u0435\u0440\u0456\u044f |
| manufacturer_org_id | space.satcom.spacecraft_models.manufacturer_org_id | string | False | False | \u0413\u043e\u043b\u043e\u0432\u043d\u0438\u0439 \u0432\u0438\u0440\u043e\u0431\u043d\u0438\u043a |
| bus_platform | space.satcom.spacecraft_models.bus_platform | string | False | False | \u041f\u043b\u0430\u0442\u0444\u043e\u0440\u043c\u0430 |
| launch_mass_kg | space.satcom.spacecraft_models.launch_mass_kg | number | False | False | \u0421\u0442\u0430\u0440\u0442\u043e\u0432\u0430 \u043c\u0430\u0441\u0430 [\u043a\u0433] |
| dry_mass_kg | space.satcom.spacecraft_models.dry_mass_kg | number | False | False | \u0421\u0443\u0445\u0430 \u043c\u0430\u0441\u0430 [\u043a\u0433] |
| power_kw | space.satcom.spacecraft_models.power_kw | number | False | False | \u041f\u043e\u0442\u0443\u0436\u043d\u0456\u0441\u0442\u044c (\u0431\u0430\u0437\u0430 \u0432 \u043f\u0440\u0438\u043c\u0456\u0442\u0446\u0456) [\u043a\u0412\u0442] |
| design_life_years | space.satcom.spacecraft_models.design_life_years | number | False | False | \u041f\u0440\u043e\u0454\u043a\u0442\u043d\u0438\u0439 \u0440\u0435\u0441\u0443\u0440\u0441 [\u0440\u043e\u043a\u0456\u0432] |
| payload_architecture | space.satcom.spacecraft_models.payload_architecture | string | False | False | bent_pipe / regenerative / digital_processor / unknown |
| design_capacity_gbps | space.satcom.spacecraft_models.design_capacity_gbps | number | False | False | \u041f\u0440\u043e\u0454\u043a\u0442\u043d\u0430 / \u0437\u0430\u044f\u0432\u043b\u0435\u043d\u0430 \u043c\u0456\u0441\u0442\u043a\u0456\u0441\u0442\u044c \u043e\u0434\u043d\u043e\u0433\u043e \u041a\u0410 [\u0413\u0431\u0456\u0442/\u0441] |
| isl_type | space.satcom.spacecraft_models.isl_type | string | False | False | none / RF / optical / unknown |
| first_launch_date | space.satcom.spacecraft_models.first_launch_date | string | False | False | \u041f\u0435\u0440\u0448\u0438\u0439 \u0437\u0430\u043f\u0443\u0441\u043a \u043c\u043e\u0434\u0435\u043b\u0456 |
| norad_id | space.satcom.spacecraft_models.norad_id | integer | False | False | NORAD (\u0434\u043b\u044f \u043e\u0434\u0438\u043d\u0438\u0447\u043d\u043e\u0433\u043e \u041a\u0410) |
| cospar_id | space.satcom.spacecraft_models.cospar_id | string | False | False | COSPAR (\u0434\u043b\u044f \u043e\u0434\u0438\u043d\u0438\u0447\u043d\u043e\u0433\u043e \u041a\u0410) |
| orbital_position | space.satcom.spacecraft_models.orbital_position | string | False | False | \u041e\u0440\u0431\u0456\u0442\u0430\u043b\u044c\u043d\u0430 \u043f\u043e\u0437\u0438\u0446\u0456\u044f GEO \u0430\u0431\u043e \u043e\u0431\u043e\u043b\u043e\u043d\u043a\u0430 |
| notes | space.satcom.spacecraft_models.notes | string | False | False | \u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438 |

## terminal_models



| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| import_id | space.satcom.terminal_models.import_id | string | True | True |  |
| terminal_id | space.satcom.terminal_models.terminal_id | string | True | True | ID \u043c\u043e\u0434\u0435\u043b\u0456 (TRM-\u2026) |
| name | space.satcom.terminal_models.name | string | True | False | \u041d\u0430\u0437\u0432\u0430 \u043c\u043e\u0434\u0435\u043b\u0456 |
| family | space.satcom.terminal_models.family | string | False | False | \u0421\u0456\u043c\u0435\u0439\u0441\u0442\u0432\u043e / \u043b\u0456\u043d\u0456\u0439\u043a\u0430 |
| revision | space.satcom.terminal_models.revision | string | False | False | \u0420\u0435\u0432\u0456\u0437\u0456\u044f / \u043f\u043e\u043a\u043e\u043b\u0456\u043d\u043d\u044f |
| manufacturer_org_id | space.satcom.terminal_models.manufacturer_org_id | string | False | False |  |
| primary_program_id | space.satcom.terminal_models.primary_program_id | string | False | False | \u041e\u0441\u043d\u043e\u0432\u043d\u0430 \u043c\u0435\u0440\u0435\u0436\u0430 (NULL \u2014 \u043c\u0443\u043b\u044c\u0442\u0438\u043c\u0435\u0440\u0435\u0436\u0435\u0432\u0438\u0439) |
| form_factor | space.satcom.terminal_models.form_factor | string | True | False | \u0424\u043e\u0440\u043c-\u0444\u0430\u043a\u0442\u043e\u0440 |
| service_class | space.satcom.terminal_models.service_class | string | True | False | \u041a\u043b\u0430\u0441 \u0441\u0435\u0440\u0432\u0456\u0441\u0443 |
| antenna_type | space.satcom.terminal_models.antenna_type | string | False | False | ESA / phased_array / parabolic_mech / flat_panel_mech / omni / patch / hybrid / metasurface |
| multi_orbit | space.satcom.terminal_models.multi_orbit | boolean | False | False | \u041f\u0456\u0434\u0442\u0440\u0438\u043c\u043a\u0430 \u043a\u0456\u043b\u044c\u043a\u043e\u0445 \u043e\u0440\u0431\u0456\u0442 / \u043c\u0435\u0440\u0435\u0436 |
| aperture_w_mm | space.satcom.terminal_models.aperture_w_mm | number | False | False |  |
| aperture_h_mm | space.satcom.terminal_models.aperture_h_mm | number | False | False |  |
| depth_mm | space.satcom.terminal_models.depth_mm | number | False | False |  |
| mass_antenna_kg | space.satcom.terminal_models.mass_antenna_kg | number | False | False | \u041c\u0430\u0441\u0430 \u0430\u043d\u0442\u0435\u043d\u0438 / ODU \u0431\u0435\u0437 \u043a\u0440\u0456\u043f\u043b\u0435\u043d\u043d\u044f, \u043a\u0430\u0431\u0435\u043b\u044e, \u0411\u0416 [\u043a\u0433] |
| mass_with_mount_kg | space.satcom.terminal_models.mass_with_mount_kg | number | False | False | \u0410\u043d\u0442\u0435\u043d\u0430 \u0437 \u043f\u0456\u0434\u0441\u0442\u0430\u0432\u043a\u043e\u044e / \u043a\u0440\u0456\u043f\u043b\u0435\u043d\u043d\u044f\u043c [\u043a\u0433] |
| mass_device_with_battery_kg | space.satcom.terminal_models.mass_device_with_battery_kg | number | False | False | \u041f\u043e\u0440\u0442\u0430\u0442\u0438\u0432\u043d\u0438\u0439 \u043f\u0440\u0438\u0441\u0442\u0440\u0456\u0439 \u0437\u0456 \u0448\u0442\u0430\u0442\u043d\u043e\u044e \u0431\u0430\u0442\u0430\u0440\u0435\u0454\u044e [\u043a\u0433] |
| mass_idu_kg | space.satcom.terminal_models.mass_idu_kg | number | False | False | \u0412\u043d\u0443\u0442\u0440\u0456\u0448\u043d\u0456\u0439 \u0431\u043b\u043e\u043a / \u0440\u043e\u0443\u0442\u0435\u0440 / \u043c\u043e\u0434\u0435\u043c [\u043a\u0433] |
| mass_psu_kg | space.satcom.terminal_models.mass_psu_kg | number | False | False | \u0411\u043b\u043e\u043a \u0436\u0438\u0432\u043b\u0435\u043d\u043d\u044f [\u043a\u0433] |
| mass_with_mount_cable_kg | space.satcom.terminal_models.mass_with_mount_cable_kg | number | False | False | \u0410\u043d\u0442\u0435\u043d\u0430 \u0437 \u043a\u0440\u0456\u043f\u043b\u0435\u043d\u043d\u044f\u043c / \u043a\u0430\u0431\u0435\u043b\u0435\u043c (\u044f\u043a \u0443 \u043f\u0430\u0441\u043f\u043e\u0440\u0442\u0456) [\u043a\u0433] |
| mass_installed_kg | space.satcom.terminal_models.mass_installed_kg | number | False | False | \u0412\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u0430 (\u0443\u0441\u0456 \u0430\u043d\u0442\u0435\u043d\u0438/\u0440\u0430\u0434\u043e\u043c\u0438 \u0430\u0431\u043e \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0442 \u0456\u0437 \u0411\u0416, \u043a\u0430\u0431\u0435\u043b\u044f\u043c\u0438, \u0442\u0440\u0438\u043d\u043e\u0433\u043e\u044e \u2014 \u0434\u0438\u0432. mass_basis_note) [\u043a\u0433] |
| mass_packaged_kg | space.satcom.terminal_models.mass_packaged_kg | number | False | False | \u041c\u0430\u0441\u0430 \u0432 \u0443\u043f\u0430\u043a\u043e\u0432\u0446\u0456 [\u043a\u0433] |
| mass_unspecified_kg | space.satcom.terminal_models.mass_unspecified_kg | number | False | False | \u041c\u0430\u0441\u0430 \u0431\u0435\u0437 \u0440\u043e\u0437\u043a\u0440\u0438\u0442\u043e\u0457 \u0431\u0430\u0437\u0438 [\u043a\u0433] |
| mass_basis_note | space.satcom.terminal_models.mass_basis_note | string | False | False | \u0429\u043e \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u043e \u0432 \u043c\u0430\u0441\u0443 |
| power_idle_w | space.satcom.terminal_models.power_idle_w | number | False | False |  |
| power_typical_w | space.satcom.terminal_models.power_typical_w | number | False | False |  |
| power_avg_min_w | space.satcom.terminal_models.power_avg_min_w | number | False | False |  |
| power_avg_max_w | space.satcom.terminal_models.power_avg_max_w | number | False | False |  |
| power_peak_w | space.satcom.terminal_models.power_peak_w | number | False | False |  |
| dc_input_min_v | space.satcom.terminal_models.dc_input_min_v | number | False | False |  |
| dc_input_max_v | space.satcom.terminal_models.dc_input_max_v | number | False | False |  |
| dl_peak_mbps | space.satcom.terminal_models.dl_peak_mbps | number | False | False | \u041f\u0430\u0441\u043f\u043e\u0440\u0442\u043d\u0430 / \u0437\u0430\u044f\u0432\u043b\u0435\u043d\u0430 \u043f\u0456\u043a\u043e\u0432\u0430 DL [\u041c\u0431\u0456\u0442/\u0441] |
| ul_peak_mbps | space.satcom.terminal_models.ul_peak_mbps | number | False | False |  |
| speed_basis | space.satcom.terminal_models.speed_basis | string | False | False | datasheet_peak / marketing_up_to / measured / guaranteed |
| eirp_dbw | space.satcom.terminal_models.eirp_dbw | number | False | False |  |
| gt_dbk | space.satcom.terminal_models.gt_dbk | number | False | False |  |
| fov_deg | space.satcom.terminal_models.fov_deg | number | False | False |  |
| min_elevation_deg | space.satcom.terminal_models.min_elevation_deg | number | False | False |  |
| ip_rating | space.satcom.terminal_models.ip_rating | string | False | False | IP-\u043a\u043b\u0430\u0441 |
| temp_min_c | space.satcom.terminal_models.temp_min_c | number | False | False |  |
| temp_max_c | space.satcom.terminal_models.temp_max_c | number | False | False |  |
| interfaces | space.satcom.terminal_models.interfaces | string | False | False | \u0406\u043d\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0438 |
| availability_status | space.satcom.terminal_models.availability_status | string | True | False | \u0421\u0442\u0430\u043d \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e\u0441\u0442\u0456 \u0432\u0438\u0440\u043e\u0431\u0443 |
| availability_as_of | space.satcom.terminal_models.availability_as_of | date | False | False |  |
| notes | space.satcom.terminal_models.notes | string | False | False | \u041e\u0431\u043c\u0435\u0436\u0435\u043d\u043d\u044f \u0442\u0430 \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0442\u0430\u0446\u0456\u044f |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
