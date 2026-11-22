CREATE TABLE semantic.alternative_labels (
	term_id TEXT NOT NULL,
	locale TEXT NOT NULL,
	label TEXT NOT NULL,
	CONSTRAINT pk_alternative_labels PRIMARY KEY (term_id, locale, label)
);

CREATE TABLE semantic.attribute_definitions (
	id TEXT NOT NULL,
	entity_class_id TEXT NOT NULL,
	value_type TEXT NOT NULL,
	unit TEXT,
	quantity_type TEXT,
	CONSTRAINT pk_attribute_definitions PRIMARY KEY (id),
	CONSTRAINT ck_attribute_definitions_value_type_enum CHECK (value_type IN ('string', 'integer', 'number', 'boolean', 'date', 'timestamp'))
);

CREATE TABLE semantic.comparison_profiles (
	id TEXT NOT NULL,
	entity_class_id TEXT NOT NULL,
	condition_set_id TEXT NOT NULL,
	CONSTRAINT pk_comparison_profiles PRIMARY KEY (id)
);

CREATE TABLE semantic.concept_mappings (
	id TEXT NOT NULL,
	source_id TEXT NOT NULL,
	target_id TEXT NOT NULL,
	mapping_type TEXT NOT NULL,
	method TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	CONSTRAINT pk_concept_mappings PRIMARY KEY (id),
	CONSTRAINT ck_concept_mappings_mapping_type_enum CHECK (mapping_type IN ('exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'analyst_crosswalk'))
);

CREATE TABLE semantic.concept_schemes (
	id TEXT NOT NULL,
	origin TEXT NOT NULL,
	publisher TEXT,
	edition TEXT,
	source_uri TEXT,
	source_sha256 TEXT,
	verification_state TEXT NOT NULL,
	verification_reason TEXT NOT NULL,
	CONSTRAINT pk_concept_schemes PRIMARY KEY (id),
	CONSTRAINT ck_concept_schemes_origin_enum CHECK (origin IN ('official', 'kb_normalized', 'kb_extension', 'service_extension', 'native')),
	CONSTRAINT ck_concept_schemes_verification_state_enum CHECK (verification_state IN ('unverified', 'verified'))
);

CREATE TABLE semantic.concepts (
	id TEXT NOT NULL,
	scheme_id TEXT NOT NULL,
	parent_id TEXT,
	replacement_id TEXT,
	CONSTRAINT pk_concepts PRIMARY KEY (id)
);

CREATE TABLE semantic.condition_sets (
	id TEXT NOT NULL,
	CONSTRAINT pk_condition_sets PRIMARY KEY (id)
);

CREATE TABLE semantic.condition_values (
	condition_set_id TEXT NOT NULL,
	attribute_id TEXT NOT NULL,
	value TEXT NOT NULL,
	unit TEXT,
	CONSTRAINT pk_condition_values PRIMARY KEY (condition_set_id, attribute_id)
);

CREATE TABLE semantic.entity_classes (
	id TEXT NOT NULL,
	parent_id TEXT,
	CONSTRAINT pk_entity_classes PRIMARY KEY (id)
);

CREATE TABLE semantic.entity_tags (
	id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	concept_id TEXT NOT NULL,
	method TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	verification_state TEXT NOT NULL,
	valid_from TIMESTAMP WITH TIME ZONE,
	valid_to TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_entity_tags PRIMARY KEY (id),
	CONSTRAINT ck_entity_tags_verification_state_enum CHECK (verification_state IN ('unreviewed', 'corroborated', 'verified', 'disputed', 'rejected'))
);

CREATE TABLE semantic.labels (
	term_id TEXT NOT NULL,
	locale TEXT NOT NULL,
	label TEXT NOT NULL,
	definition TEXT,
	inverse_label TEXT,
	CONSTRAINT pk_labels PRIMARY KEY (term_id, locale)
);

CREATE TABLE semantic.namespace_labels (
	namespace_id TEXT NOT NULL,
	locale TEXT NOT NULL,
	label TEXT NOT NULL,
	CONSTRAINT pk_namespace_labels PRIMARY KEY (namespace_id, locale)
);

CREATE TABLE semantic.namespaces (
	id TEXT NOT NULL,
	domain TEXT NOT NULL,
	code TEXT NOT NULL,
	definition TEXT NOT NULL,
	CONSTRAINT pk_namespaces PRIMARY KEY (id)
);

CREATE TABLE semantic.profile_attributes (
	profile_id TEXT NOT NULL,
	attribute_id TEXT NOT NULL,
	required BOOLEAN NOT NULL,
	CONSTRAINT pk_profile_attributes PRIMARY KEY (profile_id, attribute_id)
);

CREATE TABLE semantic.relation_types (
	id TEXT NOT NULL,
	source_class_id TEXT NOT NULL,
	target_class_id TEXT NOT NULL,
	cardinality TEXT NOT NULL,
	minimum_evidence TEXT NOT NULL,
	guarded_errors TEXT NOT NULL,
	CONSTRAINT pk_relation_types PRIMARY KEY (id),
	CONSTRAINT ck_relation_types_cardinality_enum CHECK (cardinality IN ('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many')),
	CONSTRAINT ck_relation_types_minimum_evidence_enum CHECK (minimum_evidence IN ('primary', 'secondary', 'derived', 'extracted'))
);

CREATE TABLE semantic.rubric_criteria (
	rubric_id TEXT NOT NULL,
	attribute_id TEXT NOT NULL,
	weight NUMERIC(38, 18) NOT NULL,
	direction TEXT NOT NULL,
	CONSTRAINT pk_rubric_criteria PRIMARY KEY (rubric_id, attribute_id),
	CONSTRAINT ck_rubric_criteria_direction_enum CHECK (direction IN ('minimize', 'maximize'))
);

CREATE TABLE semantic.rubrics (
	id TEXT NOT NULL,
	profile_id TEXT NOT NULL,
	CONSTRAINT pk_rubrics PRIMARY KEY (id)
);

CREATE TABLE semantic.terms (
	id TEXT NOT NULL,
	namespace_id TEXT NOT NULL,
	code TEXT NOT NULL,
	kind TEXT NOT NULL,
	status TEXT NOT NULL,
	definition TEXT NOT NULL,
	CONSTRAINT pk_terms PRIMARY KEY (id),
	CONSTRAINT ck_terms_kind_enum CHECK (kind IN ('entity_class', 'relation_type', 'concept_scheme', 'concept', 'concept_mapping', 'entity_tag', 'attribute_definition', 'condition_set', 'comparison_profile', 'rubric')),
	CONSTRAINT ck_terms_status_enum CHECK (status IN ('draft', 'active', 'deprecated', 'replaced'))
);

ALTER TABLE semantic.alternative_labels ADD CONSTRAINT fk_alternative_labels_term_id FOREIGN KEY(term_id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.alternative_labels IS 'Additional original-language labels; never replace preferred labels.';

COMMENT ON COLUMN semantic.alternative_labels.term_id IS 'Reference to terms';

COMMENT ON COLUMN semantic.alternative_labels.locale IS 'BCP 47 language tag';

COMMENT ON COLUMN semantic.alternative_labels.label IS 'Alternative label';

ALTER TABLE semantic.attribute_definitions ADD CONSTRAINT fk_attribute_definitions_entity_class_id FOREIGN KEY(entity_class_id) REFERENCES semantic.entity_classes (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.attribute_definitions ADD CONSTRAINT fk_attribute_definitions_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.attribute_definitions IS 'Typed observation attributes with original unit and quantity type.';

COMMENT ON COLUMN semantic.attribute_definitions.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.attribute_definitions.entity_class_id IS 'Reference to entity_classes';

COMMENT ON COLUMN semantic.attribute_definitions.value_type IS 'Attribute value type';

COMMENT ON COLUMN semantic.attribute_definitions.unit IS 'Original unit identifier';

COMMENT ON COLUMN semantic.attribute_definitions.quantity_type IS 'Quantity type identifier';

ALTER TABLE semantic.comparison_profiles ADD CONSTRAINT fk_comparison_profiles_condition_set_id FOREIGN KEY(condition_set_id) REFERENCES semantic.condition_sets (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.comparison_profiles ADD CONSTRAINT fk_comparison_profiles_entity_class_id FOREIGN KEY(entity_class_id) REFERENCES semantic.entity_classes (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.comparison_profiles ADD CONSTRAINT fk_comparison_profiles_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.comparison_profiles IS 'Condition-bound comparison definitions, not ranking execution.';

COMMENT ON COLUMN semantic.comparison_profiles.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.comparison_profiles.entity_class_id IS 'Reference to entity_classes';

COMMENT ON COLUMN semantic.comparison_profiles.condition_set_id IS 'Reference to condition_sets';

ALTER TABLE semantic.concept_mappings ADD CONSTRAINT fk_concept_mappings_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.concept_mappings ADD CONSTRAINT fk_concept_mappings_source_id FOREIGN KEY(source_id) REFERENCES semantic.concepts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.concept_mappings ADD CONSTRAINT fk_concept_mappings_target_id FOREIGN KEY(target_id) REFERENCES semantic.concepts (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.concept_mappings IS 'SKOS mappings and separate analyst crosswalks with method and evidence.';

COMMENT ON COLUMN semantic.concept_mappings.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.concept_mappings.source_id IS 'Reference to concepts';

COMMENT ON COLUMN semantic.concept_mappings.target_id IS 'Reference to concepts';

COMMENT ON COLUMN semantic.concept_mappings.mapping_type IS 'Directional or symmetric mapping';

COMMENT ON COLUMN semantic.concept_mappings.method IS 'Mapping method';

COMMENT ON COLUMN semantic.concept_mappings.evidence_id IS 'Evidence reference resolved by caller';

ALTER TABLE semantic.concept_schemes ADD CONSTRAINT fk_concept_schemes_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.concept_schemes IS 'Origin and edition verification; extensions retain their distinct origin.';

COMMENT ON COLUMN semantic.concept_schemes.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.concept_schemes.origin IS 'Scheme provenance class';

COMMENT ON COLUMN semantic.concept_schemes.publisher IS 'Publishing body';

COMMENT ON COLUMN semantic.concept_schemes.edition IS 'Publication edition';

COMMENT ON COLUMN semantic.concept_schemes.source_uri IS 'Publication URI';

COMMENT ON COLUMN semantic.concept_schemes.source_sha256 IS 'Checked publication checksum';

COMMENT ON COLUMN semantic.concept_schemes.verification_state IS 'Official publication verification';

COMMENT ON COLUMN semantic.concept_schemes.verification_reason IS 'Evidence or reason verification is unavailable';

ALTER TABLE semantic.concepts ADD CONSTRAINT fk_concepts_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.concepts ADD CONSTRAINT fk_concepts_parent_id FOREIGN KEY(parent_id) REFERENCES semantic.concepts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.concepts ADD CONSTRAINT fk_concepts_replacement_id FOREIGN KEY(replacement_id) REFERENCES semantic.concepts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.concepts ADD CONSTRAINT fk_concepts_scheme_id FOREIGN KEY(scheme_id) REFERENCES semantic.concept_schemes (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.concepts IS 'String concept codes, primary hierarchy, and retained replacement links.';

COMMENT ON COLUMN semantic.concepts.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.concepts.scheme_id IS 'Reference to concept_schemes';

COMMENT ON COLUMN semantic.concepts.parent_id IS 'Reference to concepts';

COMMENT ON COLUMN semantic.concepts.replacement_id IS 'Reference to concepts';

ALTER TABLE semantic.condition_sets ADD CONSTRAINT fk_condition_sets_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.condition_sets IS 'Named reusable observation condition sets.';

COMMENT ON COLUMN semantic.condition_sets.id IS 'Stable qualified identifier';

ALTER TABLE semantic.condition_values ADD CONSTRAINT fk_condition_values_attribute_id FOREIGN KEY(attribute_id) REFERENCES semantic.attribute_definitions (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.condition_values ADD CONSTRAINT fk_condition_values_condition_set_id FOREIGN KEY(condition_set_id) REFERENCES semantic.condition_sets (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.condition_values IS 'One explicit value per attribute in a condition set.';

COMMENT ON COLUMN semantic.condition_values.condition_set_id IS 'Reference to condition_sets';

COMMENT ON COLUMN semantic.condition_values.attribute_id IS 'Reference to attribute_definitions';

COMMENT ON COLUMN semantic.condition_values.value IS 'Exact original condition value';

COMMENT ON COLUMN semantic.condition_values.unit IS 'Original unit identifier';

ALTER TABLE semantic.entity_classes ADD CONSTRAINT fk_entity_classes_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.entity_classes ADD CONSTRAINT fk_entity_classes_parent_id FOREIGN KEY(parent_id) REFERENCES semantic.entity_classes (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.entity_classes IS 'Domain-qualified entity classes with a primary parent.';

COMMENT ON COLUMN semantic.entity_classes.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.entity_classes.parent_id IS 'Reference to entity_classes';

ALTER TABLE semantic.entity_tags ADD CONSTRAINT fk_entity_tags_concept_id FOREIGN KEY(concept_id) REFERENCES semantic.concepts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.entity_tags ADD CONSTRAINT fk_entity_tags_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.entity_tags IS 'Evidence-backed entity concepts with half-open validity.';

COMMENT ON COLUMN semantic.entity_tags.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.entity_tags.entity_id IS 'KN object reference resolved by caller';

COMMENT ON COLUMN semantic.entity_tags.concept_id IS 'Reference to concepts';

COMMENT ON COLUMN semantic.entity_tags.method IS 'Tagging method';

COMMENT ON COLUMN semantic.entity_tags.evidence_id IS 'Evidence reference resolved by caller';

COMMENT ON COLUMN semantic.entity_tags.verification_state IS 'Tag review state';

COMMENT ON COLUMN semantic.entity_tags.valid_from IS 'Inclusive validity start';

COMMENT ON COLUMN semantic.entity_tags.valid_to IS 'Exclusive validity end';

ALTER TABLE semantic.labels ADD CONSTRAINT fk_labels_term_id FOREIGN KEY(term_id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.labels IS 'One preferred label per term and locale, with localized definition and inverse relation label.';

COMMENT ON COLUMN semantic.labels.term_id IS 'Reference to terms';

COMMENT ON COLUMN semantic.labels.locale IS 'BCP 47 language tag';

COMMENT ON COLUMN semantic.labels.label IS 'Preferred label';

COMMENT ON COLUMN semantic.labels.definition IS 'Localized definition';

COMMENT ON COLUMN semantic.labels.inverse_label IS 'Inverse relation label';

ALTER TABLE semantic.namespace_labels ADD CONSTRAINT fk_namespace_labels_namespace_id FOREIGN KEY(namespace_id) REFERENCES semantic.namespaces (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.namespace_labels IS 'Localized namespace names.';

COMMENT ON COLUMN semantic.namespace_labels.namespace_id IS 'Reference to namespaces';

COMMENT ON COLUMN semantic.namespace_labels.locale IS 'BCP 47 language tag';

COMMENT ON COLUMN semantic.namespace_labels.label IS 'Preferred namespace label';

CREATE UNIQUE INDEX semantic_namespaces_0_uq ON semantic.namespaces USING btree (domain, code);

COMMENT ON TABLE semantic.namespaces IS 'Domain and scheme/edition qualification boundaries.';

COMMENT ON COLUMN semantic.namespaces.id IS 'Domain-qualified namespace';

COMMENT ON COLUMN semantic.namespaces.domain IS 'Domain identifier';

COMMENT ON COLUMN semantic.namespaces.code IS 'Scheme or edition namespace code';

COMMENT ON COLUMN semantic.namespaces.definition IS 'Namespace definition';

ALTER TABLE semantic.profile_attributes ADD CONSTRAINT fk_profile_attributes_attribute_id FOREIGN KEY(attribute_id) REFERENCES semantic.attribute_definitions (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.profile_attributes ADD CONSTRAINT fk_profile_attributes_profile_id FOREIGN KEY(profile_id) REFERENCES semantic.comparison_profiles (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.profile_attributes IS 'Declared comparison attributes and required-field eligibility.';

COMMENT ON COLUMN semantic.profile_attributes.profile_id IS 'Reference to comparison_profiles';

COMMENT ON COLUMN semantic.profile_attributes.attribute_id IS 'Reference to attribute_definitions';

COMMENT ON COLUMN semantic.profile_attributes.required IS 'Whether absence excludes matched ranking';

ALTER TABLE semantic.relation_types ADD CONSTRAINT fk_relation_types_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.relation_types ADD CONSTRAINT fk_relation_types_source_class_id FOREIGN KEY(source_class_id) REFERENCES semantic.entity_classes (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.relation_types ADD CONSTRAINT fk_relation_types_target_class_id FOREIGN KEY(target_class_id) REFERENCES semantic.entity_classes (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.relation_types IS 'Typed directional relations and their evidence requirements.';

COMMENT ON COLUMN semantic.relation_types.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.relation_types.source_class_id IS 'Reference to entity_classes';

COMMENT ON COLUMN semantic.relation_types.target_class_id IS 'Reference to entity_classes';

COMMENT ON COLUMN semantic.relation_types.cardinality IS 'Allowed endpoint multiplicity';

COMMENT ON COLUMN semantic.relation_types.minimum_evidence IS 'Minimum evidence class';

COMMENT ON COLUMN semantic.relation_types.guarded_errors IS 'Common errors this relation prevents';

ALTER TABLE semantic.rubric_criteria ADD CONSTRAINT fk_rubric_criteria_attribute_id FOREIGN KEY(attribute_id) REFERENCES semantic.attribute_definitions (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.rubric_criteria ADD CONSTRAINT fk_rubric_criteria_rubric_id FOREIGN KEY(rubric_id) REFERENCES semantic.rubrics (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.rubric_criteria IS 'Explicit attribute weights and direction for an analyst rubric.';

COMMENT ON COLUMN semantic.rubric_criteria.rubric_id IS 'Reference to rubrics';

COMMENT ON COLUMN semantic.rubric_criteria.attribute_id IS 'Reference to attribute_definitions';

COMMENT ON COLUMN semantic.rubric_criteria.weight IS 'Positive exact decimal weight';

COMMENT ON COLUMN semantic.rubric_criteria.direction IS 'Preferred value direction';

ALTER TABLE semantic.rubrics ADD CONSTRAINT fk_rubrics_id FOREIGN KEY(id) REFERENCES semantic.terms (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE semantic.rubrics ADD CONSTRAINT fk_rubrics_profile_id FOREIGN KEY(profile_id) REFERENCES semantic.comparison_profiles (id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE semantic.rubrics IS 'Named analyst policies; scores are not predictions.';

COMMENT ON COLUMN semantic.rubrics.id IS 'Stable qualified identifier';

COMMENT ON COLUMN semantic.rubrics.profile_id IS 'Reference to comparison_profiles';

ALTER TABLE semantic.terms ADD CONSTRAINT fk_terms_namespace_id FOREIGN KEY(namespace_id) REFERENCES semantic.namespaces (id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX semantic_terms_0_uq ON semantic.terms USING btree (namespace_id, code);

COMMENT ON TABLE semantic.terms IS 'One identifier registry for every semantic kind; IDs never depend on load order.';

COMMENT ON COLUMN semantic.terms.id IS 'Namespace plus native code';

COMMENT ON COLUMN semantic.terms.namespace_id IS 'Reference to namespaces';

COMMENT ON COLUMN semantic.terms.code IS 'Original string code, including leading zeroes';

COMMENT ON COLUMN semantic.terms.kind IS 'Semantic dataset kind';

COMMENT ON COLUMN semantic.terms.status IS 'Lifecycle status; deprecated terms remain resolvable';

COMMENT ON COLUMN semantic.terms.definition IS 'Definition in original language';
