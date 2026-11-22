"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class AlternativeLabels(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    term_id: _kn_builtins.str = _kn_pydantic.Field(alias='term_id', description='Reference to terms', json_schema_extra={'x-kn': {'fieldId': 'semantic.alternative_labels.term_id', 'foreignKey': {'fields': ['term_id'], 'table': 'terms', 'targetFields': ['id']}}})
    locale: _kn_builtins.str = _kn_pydantic.Field(alias='locale', description='BCP 47 language tag', json_schema_extra={'x-kn': {'fieldId': 'semantic.alternative_labels.locale'}})
    label: _kn_builtins.str = _kn_pydantic.Field(alias='label', description='Alternative label', json_schema_extra={'x-kn': {'fieldId': 'semantic.alternative_labels.label'}})

class AttributeDefinitions(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.attribute_definitions.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    entity_class_id: _kn_builtins.str = _kn_pydantic.Field(alias='entity_class_id', description='Reference to entity_classes', json_schema_extra={'x-kn': {'fieldId': 'semantic.attribute_definitions.entity_class_id', 'foreignKey': {'fields': ['entity_class_id'], 'table': 'entity_classes', 'targetFields': ['id']}}})
    value_type: _kn_typing.Literal['string', 'integer', 'number', 'boolean', 'date', 'timestamp'] = _kn_pydantic.Field(alias='value_type', description='Attribute value type', json_schema_extra={'x-kn': {'enum': ['string', 'integer', 'number', 'boolean', 'date', 'timestamp'], 'fieldId': 'semantic.attribute_definitions.value_type'}})
    unit: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='unit', description='Original unit identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.attribute_definitions.unit'}})
    quantity_type: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='quantity_type', description='Quantity type identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.attribute_definitions.quantity_type'}})

class ComparisonProfiles(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.comparison_profiles.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    entity_class_id: _kn_builtins.str = _kn_pydantic.Field(alias='entity_class_id', description='Reference to entity_classes', json_schema_extra={'x-kn': {'fieldId': 'semantic.comparison_profiles.entity_class_id', 'foreignKey': {'fields': ['entity_class_id'], 'table': 'entity_classes', 'targetFields': ['id']}}})
    condition_set_id: _kn_builtins.str = _kn_pydantic.Field(alias='condition_set_id', description='Reference to condition_sets', json_schema_extra={'x-kn': {'fieldId': 'semantic.comparison_profiles.condition_set_id', 'foreignKey': {'fields': ['condition_set_id'], 'table': 'condition_sets', 'targetFields': ['id']}}})

class ConceptMappings(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_mappings.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Reference to concepts', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_mappings.source_id', 'foreignKey': {'fields': ['source_id'], 'table': 'concepts', 'targetFields': ['id']}}})
    target_id: _kn_builtins.str = _kn_pydantic.Field(alias='target_id', description='Reference to concepts', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_mappings.target_id', 'foreignKey': {'fields': ['target_id'], 'table': 'concepts', 'targetFields': ['id']}}})
    mapping_type: _kn_typing.Literal['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'analyst_crosswalk'] = _kn_pydantic.Field(alias='mapping_type', description='Directional or symmetric mapping', json_schema_extra={'x-kn': {'enum': ['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'analyst_crosswalk'], 'fieldId': 'semantic.concept_mappings.mapping_type'}})
    method: _kn_builtins.str = _kn_pydantic.Field(alias='method', description='Mapping method', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_mappings.method'}})
    evidence_id: _kn_builtins.str = _kn_pydantic.Field(alias='evidence_id', description='Evidence reference resolved by caller', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_mappings.evidence_id'}})

class ConceptSchemes(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    origin: _kn_typing.Literal['official', 'kb_normalized', 'kb_extension', 'service_extension', 'native'] = _kn_pydantic.Field(alias='origin', description='Scheme provenance class', json_schema_extra={'x-kn': {'enum': ['official', 'kb_normalized', 'kb_extension', 'service_extension', 'native'], 'fieldId': 'semantic.concept_schemes.origin'}})
    publisher: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='publisher', description='Publishing body', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.publisher'}})
    edition: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='edition', description='Publication edition', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.edition'}})
    source_uri: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='source_uri', description='Publication URI', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.source_uri'}})
    source_sha256: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='source_sha256', description='Checked publication checksum', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.source_sha256'}})
    verification_state: _kn_typing.Literal['unverified', 'verified'] = _kn_pydantic.Field(alias='verification_state', description='Official publication verification', json_schema_extra={'x-kn': {'enum': ['unverified', 'verified'], 'fieldId': 'semantic.concept_schemes.verification_state'}})
    verification_reason: _kn_builtins.str = _kn_pydantic.Field(alias='verification_reason', description='Evidence or reason verification is unavailable', json_schema_extra={'x-kn': {'fieldId': 'semantic.concept_schemes.verification_reason'}})

class Concepts(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.concepts.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    scheme_id: _kn_builtins.str = _kn_pydantic.Field(alias='scheme_id', description='Reference to concept_schemes', json_schema_extra={'x-kn': {'fieldId': 'semantic.concepts.scheme_id', 'foreignKey': {'fields': ['scheme_id'], 'table': 'concept_schemes', 'targetFields': ['id']}}})
    parent_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='parent_id', description='Reference to concepts', json_schema_extra={'x-kn': {'fieldId': 'semantic.concepts.parent_id', 'foreignKey': {'fields': ['parent_id'], 'table': 'concepts', 'targetFields': ['id']}}})
    replacement_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='replacement_id', description='Reference to concepts', json_schema_extra={'x-kn': {'fieldId': 'semantic.concepts.replacement_id', 'foreignKey': {'fields': ['replacement_id'], 'table': 'concepts', 'targetFields': ['id']}}})

class ConditionSets(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.condition_sets.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})

class ConditionValues(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    condition_set_id: _kn_builtins.str = _kn_pydantic.Field(alias='condition_set_id', description='Reference to condition_sets', json_schema_extra={'x-kn': {'fieldId': 'semantic.condition_values.condition_set_id', 'foreignKey': {'fields': ['condition_set_id'], 'table': 'condition_sets', 'targetFields': ['id']}}})
    attribute_id: _kn_builtins.str = _kn_pydantic.Field(alias='attribute_id', description='Reference to attribute_definitions', json_schema_extra={'x-kn': {'fieldId': 'semantic.condition_values.attribute_id', 'foreignKey': {'fields': ['attribute_id'], 'table': 'attribute_definitions', 'targetFields': ['id']}}})
    value: _kn_builtins.str = _kn_pydantic.Field(alias='value', description='Exact original condition value', json_schema_extra={'x-kn': {'fieldId': 'semantic.condition_values.value'}})
    unit: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='unit', description='Original unit identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.condition_values.unit'}})

class EntityClasses(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_classes.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    parent_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='parent_id', description='Reference to entity_classes', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_classes.parent_id', 'foreignKey': {'fields': ['parent_id'], 'table': 'entity_classes', 'targetFields': ['id']}}})

class EntityTags(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    entity_id: _kn_builtins.str = _kn_pydantic.Field(alias='entity_id', description='KN object reference resolved by caller', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.entity_id'}})
    concept_id: _kn_builtins.str = _kn_pydantic.Field(alias='concept_id', description='Reference to concepts', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.concept_id', 'foreignKey': {'fields': ['concept_id'], 'table': 'concepts', 'targetFields': ['id']}}})
    method: _kn_builtins.str = _kn_pydantic.Field(alias='method', description='Tagging method', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.method'}})
    evidence_id: _kn_builtins.str = _kn_pydantic.Field(alias='evidence_id', description='Evidence reference resolved by caller', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.evidence_id'}})
    verification_state: _kn_typing.Literal['unreviewed', 'corroborated', 'verified', 'disputed', 'rejected'] = _kn_pydantic.Field(alias='verification_state', description='Tag review state', json_schema_extra={'x-kn': {'enum': ['unreviewed', 'corroborated', 'verified', 'disputed', 'rejected'], 'fieldId': 'semantic.entity_tags.verification_state'}})
    valid_from: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_from', description='Inclusive validity start', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.valid_from'}})
    valid_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_to', description='Exclusive validity end', json_schema_extra={'x-kn': {'fieldId': 'semantic.entity_tags.valid_to'}})

class Labels(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    term_id: _kn_builtins.str = _kn_pydantic.Field(alias='term_id', description='Reference to terms', json_schema_extra={'x-kn': {'fieldId': 'semantic.labels.term_id', 'foreignKey': {'fields': ['term_id'], 'table': 'terms', 'targetFields': ['id']}}})
    locale: _kn_builtins.str = _kn_pydantic.Field(alias='locale', description='BCP 47 language tag', json_schema_extra={'x-kn': {'fieldId': 'semantic.labels.locale'}})
    label: _kn_builtins.str = _kn_pydantic.Field(alias='label', description='Preferred label', json_schema_extra={'x-kn': {'fieldId': 'semantic.labels.label'}})
    definition: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='definition', description='Localized definition', json_schema_extra={'x-kn': {'fieldId': 'semantic.labels.definition'}})
    inverse_label: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='inverse_label', description='Inverse relation label', json_schema_extra={'x-kn': {'fieldId': 'semantic.labels.inverse_label'}})

class NamespaceLabels(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    namespace_id: _kn_builtins.str = _kn_pydantic.Field(alias='namespace_id', description='Reference to namespaces', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespace_labels.namespace_id', 'foreignKey': {'fields': ['namespace_id'], 'table': 'namespaces', 'targetFields': ['id']}}})
    locale: _kn_builtins.str = _kn_pydantic.Field(alias='locale', description='BCP 47 language tag', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespace_labels.locale'}})
    label: _kn_builtins.str = _kn_pydantic.Field(alias='label', description='Preferred namespace label', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespace_labels.label'}})

class Namespaces(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Domain-qualified namespace', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespaces.id'}})
    domain: _kn_builtins.str = _kn_pydantic.Field(alias='domain', description='Domain identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespaces.domain'}})
    code: _kn_builtins.str = _kn_pydantic.Field(alias='code', description='Scheme or edition namespace code', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespaces.code'}})
    definition: _kn_builtins.str = _kn_pydantic.Field(alias='definition', description='Namespace definition', json_schema_extra={'x-kn': {'fieldId': 'semantic.namespaces.definition'}})

class ProfileAttributes(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    profile_id: _kn_builtins.str = _kn_pydantic.Field(alias='profile_id', description='Reference to comparison_profiles', json_schema_extra={'x-kn': {'fieldId': 'semantic.profile_attributes.profile_id', 'foreignKey': {'fields': ['profile_id'], 'table': 'comparison_profiles', 'targetFields': ['id']}}})
    attribute_id: _kn_builtins.str = _kn_pydantic.Field(alias='attribute_id', description='Reference to attribute_definitions', json_schema_extra={'x-kn': {'fieldId': 'semantic.profile_attributes.attribute_id', 'foreignKey': {'fields': ['attribute_id'], 'table': 'attribute_definitions', 'targetFields': ['id']}}})
    required: _kn_builtins.bool = _kn_pydantic.Field(alias='required', description='Whether absence excludes matched ranking', json_schema_extra={'x-kn': {'fieldId': 'semantic.profile_attributes.required'}})

class RelationTypes(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.relation_types.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    source_class_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_class_id', description='Reference to entity_classes', json_schema_extra={'x-kn': {'fieldId': 'semantic.relation_types.source_class_id', 'foreignKey': {'fields': ['source_class_id'], 'table': 'entity_classes', 'targetFields': ['id']}}})
    target_class_id: _kn_builtins.str = _kn_pydantic.Field(alias='target_class_id', description='Reference to entity_classes', json_schema_extra={'x-kn': {'fieldId': 'semantic.relation_types.target_class_id', 'foreignKey': {'fields': ['target_class_id'], 'table': 'entity_classes', 'targetFields': ['id']}}})
    cardinality: _kn_typing.Literal['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'] = _kn_pydantic.Field(alias='cardinality', description='Allowed endpoint multiplicity', json_schema_extra={'x-kn': {'enum': ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'], 'fieldId': 'semantic.relation_types.cardinality'}})
    minimum_evidence: _kn_typing.Literal['primary', 'secondary', 'derived', 'extracted'] = _kn_pydantic.Field(alias='minimum_evidence', description='Minimum evidence class', json_schema_extra={'x-kn': {'enum': ['primary', 'secondary', 'derived', 'extracted'], 'fieldId': 'semantic.relation_types.minimum_evidence'}})
    guarded_errors: _kn_builtins.str = _kn_pydantic.Field(alias='guarded_errors', description='Common errors this relation prevents', json_schema_extra={'x-kn': {'fieldId': 'semantic.relation_types.guarded_errors'}})

class RubricCriteria(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    rubric_id: _kn_builtins.str = _kn_pydantic.Field(alias='rubric_id', description='Reference to rubrics', json_schema_extra={'x-kn': {'fieldId': 'semantic.rubric_criteria.rubric_id', 'foreignKey': {'fields': ['rubric_id'], 'table': 'rubrics', 'targetFields': ['id']}}})
    attribute_id: _kn_builtins.str = _kn_pydantic.Field(alias='attribute_id', description='Reference to attribute_definitions', json_schema_extra={'x-kn': {'fieldId': 'semantic.rubric_criteria.attribute_id', 'foreignKey': {'fields': ['attribute_id'], 'table': 'attribute_definitions', 'targetFields': ['id']}}})
    weight: _kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits=38, decimal_places=18, allow_inf_nan=False)] = _kn_pydantic.Field(alias='weight', description='Positive exact decimal weight', json_schema_extra={'x-kn': {'fieldId': 'semantic.rubric_criteria.weight'}})
    direction: _kn_typing.Literal['minimize', 'maximize'] = _kn_pydantic.Field(alias='direction', description='Preferred value direction', json_schema_extra={'x-kn': {'enum': ['minimize', 'maximize'], 'fieldId': 'semantic.rubric_criteria.direction'}})

class Rubrics(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Stable qualified identifier', json_schema_extra={'x-kn': {'fieldId': 'semantic.rubrics.id', 'foreignKey': {'fields': ['id'], 'table': 'terms', 'targetFields': ['id']}}})
    profile_id: _kn_builtins.str = _kn_pydantic.Field(alias='profile_id', description='Reference to comparison_profiles', json_schema_extra={'x-kn': {'fieldId': 'semantic.rubrics.profile_id', 'foreignKey': {'fields': ['profile_id'], 'table': 'comparison_profiles', 'targetFields': ['id']}}})

class Terms(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    id: _kn_builtins.str = _kn_pydantic.Field(alias='id', description='Namespace plus native code', json_schema_extra={'x-kn': {'fieldId': 'semantic.terms.id'}})
    namespace_id: _kn_builtins.str = _kn_pydantic.Field(alias='namespace_id', description='Reference to namespaces', json_schema_extra={'x-kn': {'fieldId': 'semantic.terms.namespace_id', 'foreignKey': {'fields': ['namespace_id'], 'table': 'namespaces', 'targetFields': ['id']}}})
    code: _kn_builtins.str = _kn_pydantic.Field(alias='code', description='Original string code, including leading zeroes', json_schema_extra={'x-kn': {'fieldId': 'semantic.terms.code'}})
    kind: _kn_typing.Literal['entity_class', 'relation_type', 'concept_scheme', 'concept', 'concept_mapping', 'entity_tag', 'attribute_definition', 'condition_set', 'comparison_profile', 'rubric'] = _kn_pydantic.Field(alias='kind', description='Semantic dataset kind', json_schema_extra={'x-kn': {'enum': ['entity_class', 'relation_type', 'concept_scheme', 'concept', 'concept_mapping', 'entity_tag', 'attribute_definition', 'condition_set', 'comparison_profile', 'rubric'], 'fieldId': 'semantic.terms.kind'}})
    status: _kn_typing.Literal['draft', 'active', 'deprecated', 'replaced'] = _kn_pydantic.Field(alias='status', description='Lifecycle status; deprecated terms remain resolvable', json_schema_extra={'x-kn': {'enum': ['draft', 'active', 'deprecated', 'replaced'], 'fieldId': 'semantic.terms.status'}})
    definition: _kn_builtins.str = _kn_pydantic.Field(alias='definition', description='Definition in original language', json_schema_extra={'x-kn': {'fieldId': 'semantic.terms.definition'}})
