# kn.core.semantic

Version: 1.0.0

Digest: `0fb9971b4b55742d2c3855f206bc7a8e25de93ea6beb0ba9be80f6c17e566944`

Storage schema: `semantic`

## alternative_labels

Additional original-language labels; never replace preferred labels.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| term_id | semantic.alternative_labels.term_id | string | True | True | Reference to terms |
| locale | semantic.alternative_labels.locale | string | True | True | BCP 47 language tag |
| label | semantic.alternative_labels.label | string | True | True | Alternative label |
| review_reference | semantic.alternative_labels.review_reference | string | False | False | Durable terminology review reference for derived text |
| reviewed_identical | semantic.alternative_labels.reviewed_identical | boolean | False | False | Review explicitly confirms identical English and Ukrainian text |

## attribute_definitions

Typed observation attributes with original unit and quantity type.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.attribute_definitions.id | string | True | True | Stable qualified identifier |
| entity_class_id | semantic.attribute_definitions.entity_class_id | string | True | False | Reference to entity_classes |
| value_type | semantic.attribute_definitions.value_type | string | True | False | Attribute value type |
| unit | semantic.attribute_definitions.unit | string | False | False | Original unit identifier |
| quantity_type | semantic.attribute_definitions.quantity_type | string | False | False | Quantity type identifier |

## comparison_profiles

Condition-bound comparison definitions, not ranking execution.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.comparison_profiles.id | string | True | True | Stable qualified identifier |
| entity_class_id | semantic.comparison_profiles.entity_class_id | string | True | False | Reference to entity_classes |
| condition_set_id | semantic.comparison_profiles.condition_set_id | string | True | False | Reference to condition_sets |

## concept_mappings

SKOS mappings and separate analyst crosswalks with method and evidence.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.concept_mappings.id | string | True | True | Stable qualified identifier |
| source_id | semantic.concept_mappings.source_id | string | True | False | Reference to concepts |
| target_id | semantic.concept_mappings.target_id | string | True | False | Reference to concepts |
| mapping_type | semantic.concept_mappings.mapping_type | string | True | False | Directional or symmetric mapping |
| method | semantic.concept_mappings.method | string | True | False | Mapping method |
| evidence_id | semantic.concept_mappings.evidence_id | string | True | False | Evidence reference resolved by caller |

## concept_schemes

Origin and edition verification; extensions retain their distinct origin.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.concept_schemes.id | string | True | True | Stable qualified identifier |
| origin | semantic.concept_schemes.origin | string | True | False | Scheme provenance class |
| publisher | semantic.concept_schemes.publisher | string | False | False | Publishing body |
| edition | semantic.concept_schemes.edition | string | False | False | Publication edition |
| source_uri | semantic.concept_schemes.source_uri | string | False | False | Publication URI |
| source_sha256 | semantic.concept_schemes.source_sha256 | string | False | False | Checked publication checksum |
| verification_state | semantic.concept_schemes.verification_state | string | True | False | Official publication verification |
| verification_reason | semantic.concept_schemes.verification_reason | string | True | False | Evidence or reason verification is unavailable |

## concepts

String concept codes, primary hierarchy, and retained replacement links.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.concepts.id | string | True | True | Stable qualified identifier |
| scheme_id | semantic.concepts.scheme_id | string | True | False | Reference to concept_schemes |
| parent_id | semantic.concepts.parent_id | string | False | False | Reference to concepts |
| replacement_id | semantic.concepts.replacement_id | string | False | False | Reference to concepts |

## condition_sets

Named reusable observation condition sets.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.condition_sets.id | string | True | True | Stable qualified identifier |

## condition_values

One explicit value per attribute in a condition set.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| condition_set_id | semantic.condition_values.condition_set_id | string | True | True | Reference to condition_sets |
| attribute_id | semantic.condition_values.attribute_id | string | True | True | Reference to attribute_definitions |
| value | semantic.condition_values.value | string | True | False | Exact original condition value |
| unit | semantic.condition_values.unit | string | False | False | Original unit identifier |

## entity_classes

Domain-qualified entity classes with a primary parent.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.entity_classes.id | string | True | True | Stable qualified identifier |
| parent_id | semantic.entity_classes.parent_id | string | False | False | Reference to entity_classes |

## entity_tags

Evidence-backed entity concepts with half-open validity.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.entity_tags.id | string | True | True | Stable qualified identifier |
| entity_id | semantic.entity_tags.entity_id | string | True | False | KN object reference resolved by caller |
| concept_id | semantic.entity_tags.concept_id | string | True | False | Reference to concepts |
| method | semantic.entity_tags.method | string | True | False | Tagging method |
| evidence_id | semantic.entity_tags.evidence_id | string | True | False | Evidence reference resolved by caller |
| verification_state | semantic.entity_tags.verification_state | string | True | False | Tag review state |
| valid_from | semantic.entity_tags.valid_from | timestamp | False | False | Inclusive validity start |
| valid_to | semantic.entity_tags.valid_to | timestamp | False | False | Exclusive validity end |

## labels

One preferred label per term and locale, with localized definition and inverse relation label.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| term_id | semantic.labels.term_id | string | True | True | Reference to terms |
| locale | semantic.labels.locale | string | True | True | BCP 47 language tag |
| label | semantic.labels.label | string | True | False | Preferred label |
| definition | semantic.labels.definition | string | False | False | Localized definition |
| inverse_label | semantic.labels.inverse_label | string | False | False | Inverse relation label |
| review_reference | semantic.labels.review_reference | string | False | False | Durable terminology review reference for derived text |
| reviewed_identical | semantic.labels.reviewed_identical | boolean | False | False | Review explicitly confirms identical English and Ukrainian text |

## namespace_labels

Localized namespace names.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| namespace_id | semantic.namespace_labels.namespace_id | string | True | True | Reference to namespaces |
| locale | semantic.namespace_labels.locale | string | True | True | BCP 47 language tag |
| label | semantic.namespace_labels.label | string | True | False | Preferred namespace label |
| review_reference | semantic.namespace_labels.review_reference | string | False | False | Durable terminology review reference for derived text |
| reviewed_identical | semantic.namespace_labels.reviewed_identical | boolean | False | False | Review explicitly confirms identical English and Ukrainian text |

## namespaces

Domain and scheme/edition qualification boundaries.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.namespaces.id | string | True | True | Domain-qualified namespace |
| domain | semantic.namespaces.domain | string | True | False | Domain identifier |
| code | semantic.namespaces.code | string | True | False | Scheme or edition namespace code |
| definition | semantic.namespaces.definition | string | True | False | Namespace definition |

## profile_attributes

Declared comparison attributes and required-field eligibility.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| profile_id | semantic.profile_attributes.profile_id | string | True | True | Reference to comparison_profiles |
| attribute_id | semantic.profile_attributes.attribute_id | string | True | True | Reference to attribute_definitions |
| required | semantic.profile_attributes.required | boolean | True | False | Whether absence excludes matched ranking |

## relation_types

Typed directional relations and their evidence requirements.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.relation_types.id | string | True | True | Stable qualified identifier |
| source_class_id | semantic.relation_types.source_class_id | string | True | False | Reference to entity_classes |
| target_class_id | semantic.relation_types.target_class_id | string | True | False | Reference to entity_classes |
| cardinality | semantic.relation_types.cardinality | string | True | False | Allowed endpoint multiplicity |
| minimum_evidence | semantic.relation_types.minimum_evidence | string | True | False | Minimum evidence class |
| guarded_errors | semantic.relation_types.guarded_errors | string | True | False | Common errors this relation prevents |

## rubric_criteria

Explicit attribute weights and direction for an analyst rubric.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| rubric_id | semantic.rubric_criteria.rubric_id | string | True | True | Reference to rubrics |
| attribute_id | semantic.rubric_criteria.attribute_id | string | True | True | Reference to attribute_definitions |
| weight | semantic.rubric_criteria.weight | number | True | False | Positive exact decimal weight |
| direction | semantic.rubric_criteria.direction | string | True | False | Preferred value direction |

## rubrics

Named analyst policies; scores are not predictions.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.rubrics.id | string | True | True | Stable qualified identifier |
| profile_id | semantic.rubrics.profile_id | string | True | False | Reference to comparison_profiles |

## terms

One identifier registry for every semantic kind; IDs never depend on load order.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| id | semantic.terms.id | string | True | True | Namespace plus native code |
| namespace_id | semantic.terms.namespace_id | string | True | False | Reference to namespaces |
| code | semantic.terms.code | string | True | False | Original string code, including leading zeroes |
| kind | semantic.terms.kind | string | True | False | Semantic dataset kind |
| status | semantic.terms.status | string | True | False | Lifecycle status; deprecated terms remain resolvable |
| definition | semantic.terms.definition | string | False | False | Prose definition when supplied; proposal metadata belongs in provenance |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
