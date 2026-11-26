CREATE TABLE evidence.aliases (
	alias_id TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	alias TEXT NOT NULL,
	language TEXT NOT NULL,
	normalized_key TEXT NOT NULL,
	normalizer TEXT NOT NULL,
	claim_key TEXT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_aliases PRIMARY KEY (alias_id)
);

CREATE TABLE evidence.canonical_facts (
	fact_version_id TEXT NOT NULL,
	fact_key TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	field_id TEXT NOT NULL,
	conditions_json TEXT NOT NULL,
	audience TEXT NOT NULL,
	claim_key TEXT,
	unresolved_reason TEXT,
	mode TEXT NOT NULL,
	policy_digest TEXT NOT NULL,
	outcome TEXT NOT NULL,
	deciding_criterion TEXT NOT NULL,
	winner_criteria_json TEXT NOT NULL,
	runner_up_criteria_json TEXT,
	verification_state TEXT NOT NULL,
	owner_override BOOLEAN NOT NULL,
	review_item_id TEXT,
	valid_from TIMESTAMP WITH TIME ZONE,
	valid_from_precision TEXT,
	valid_to TIMESTAMP WITH TIME ZONE,
	valid_to_precision TEXT,
	knowledge_from TIMESTAMP WITH TIME ZONE NOT NULL,
	knowledge_to TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_canonical_facts PRIMARY KEY (fact_version_id),
	CONSTRAINT ck_canonical_facts_unresolved_reason_enum CHECK (unresolved_reason IN ('no_eligible_claim', 'conflict', 'review_pending', 'cleared')),
	CONSTRAINT ck_canonical_facts_mode_enum CHECK (mode IN ('priority', 'latest_observed', 'accumulate', 'fixed')),
	CONSTRAINT ck_canonical_facts_outcome_enum CHECK (outcome IN ('filled', 'replaced', 'corroborated', 'conflict')),
	CONSTRAINT ck_canonical_facts_deciding_criterion_enum CHECK (deciding_criterion IN ('first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision')),
	CONSTRAINT ck_canonical_facts_verification_state_enum CHECK (verification_state IN ('unreviewed', 'corroborated', 'verified', 'disputed')),
	CONSTRAINT ck_canonical_facts_valid_from_precision_enum CHECK (valid_from_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_canonical_facts_valid_to_precision_enum CHECK (valid_to_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_canonical_facts_claim_or_reason_presence CHECK (num_nonnulls(claim_key, unresolved_reason) = 1),
	CONSTRAINT ck_canonical_facts_valid_from_time_presence CHECK (num_nonnulls(valid_from, valid_from_precision) IN (0, 2)),
	CONSTRAINT ck_canonical_facts_valid_to_time_presence CHECK (num_nonnulls(valid_to, valid_to_precision) IN (0, 2))
);

CREATE TABLE evidence.claim_confirmations (
	confirmation_id TEXT NOT NULL,
	claim_key TEXT NOT NULL,
	source_version_id TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	fetch_id TEXT NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_claim_confirmations PRIMARY KEY (confirmation_id)
);

CREATE TABLE evidence.claims (
	claim_key TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	field_id TEXT NOT NULL,
	conditions_json TEXT NOT NULL,
	source_id TEXT NOT NULL,
	record_id TEXT NOT NULL,
	source_version_id TEXT NOT NULL,
	change_set_id TEXT,
	change_kind TEXT NOT NULL,
	supersedes TEXT,
	decision_ref TEXT,
	evidence_id TEXT NOT NULL,
	fetch_id TEXT NOT NULL,
	origin_uri TEXT NOT NULL,
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
	original_value TEXT,
	original_unit TEXT,
	value_text TEXT,
	value_language TEXT,
	value_number NUMERIC(38, 18),
	value_boolean BOOLEAN,
	value_date TEXT,
	value_concept TEXT,
	value_kn_id TEXT,
	missing_reason TEXT,
	normalized_unit TEXT,
	conversion_rule TEXT,
	assertion_type TEXT NOT NULL,
	evidence_class TEXT NOT NULL,
	extraction_confidence NUMERIC(5, 4),
	source_verification_label TEXT,
	event_at TIMESTAMP WITH TIME ZONE,
	event_precision TEXT,
	published_at TIMESTAMP WITH TIME ZONE,
	published_precision TEXT,
	valid_from TIMESTAMP WITH TIME ZONE,
	valid_from_precision TEXT,
	valid_to TIMESTAMP WITH TIME ZONE,
	valid_to_precision TEXT,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_claims PRIMARY KEY (claim_key),
	CONSTRAINT ck_claims_change_kind_enum CHECK (change_kind IN ('added', 'changed', 'emptied', 'decided')),
	CONSTRAINT ck_claims_value_date_precision CHECK (value_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_claims_missing_reason_enum CHECK (missing_reason IN ('source_empty', 'not_found', 'not_disclosed', 'requires_vendor_quote', 'cannot_verify', 'not_applicable')),
	CONSTRAINT ck_claims_assertion_type_enum CHECK (assertion_type IN ('declared', 'observed', 'derived', 'reported')),
	CONSTRAINT ck_claims_evidence_class_enum CHECK (evidence_class IN ('primary', 'secondary', 'derived', 'extracted_candidate')),
	CONSTRAINT ck_claims_event_precision_enum CHECK (event_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_claims_published_precision_enum CHECK (published_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_claims_valid_from_precision_enum CHECK (valid_from_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_claims_valid_to_precision_enum CHECK (valid_to_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_claims_value_or_reason_presence CHECK (num_nonnulls(value_text, value_number, value_boolean, value_date, value_concept, value_kn_id, missing_reason) = 1),
	CONSTRAINT ck_claims_text_language_presence CHECK (num_nonnulls(value_text, value_language) IN (0, 2)),
	CONSTRAINT ck_claims_unit_conversion_presence CHECK (num_nonnulls(normalized_unit, conversion_rule) IN (0, 2)),
	CONSTRAINT ck_claims_event_time_presence CHECK (num_nonnulls(event_at, event_precision) IN (0, 2)),
	CONSTRAINT ck_claims_published_time_presence CHECK (num_nonnulls(published_at, published_precision) IN (0, 2)),
	CONSTRAINT ck_claims_valid_from_time_presence CHECK (num_nonnulls(valid_from, valid_from_precision) IN (0, 2)),
	CONSTRAINT ck_claims_valid_to_time_presence CHECK (num_nonnulls(valid_to, valid_to_precision) IN (0, 2))
);

CREATE TABLE evidence.evidence_records (
	evidence_id TEXT NOT NULL,
	source_id TEXT NOT NULL,
	fetch_id TEXT NOT NULL,
	archive_record_id TEXT,
	origin_uri TEXT NOT NULL,
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
	locator_kind TEXT NOT NULL,
	locator TEXT NOT NULL,
	excerpt TEXT,
	excerpt_rights TEXT,
	rights TEXT NOT NULL,
	code_digest TEXT NOT NULL,
	contract_digest TEXT NOT NULL,
	curator TEXT,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_evidence_records PRIMARY KEY (evidence_id),
	CONSTRAINT ck_evidence_records_locator_kind_enum CHECK (locator_kind IN ('json_pointer', 'row', 'page', 'offset')),
	CONSTRAINT ck_evidence_records_licensed_excerpt_presence CHECK (num_nonnulls(excerpt, excerpt_rights) IN (0, 2))
);

CREATE TABLE evidence.relation_assertions (
	assertion_id TEXT NOT NULL,
	relation_key TEXT NOT NULL,
	subject_kn_id TEXT NOT NULL,
	relation_type TEXT NOT NULL,
	object_kn_id TEXT NOT NULL,
	qualifiers_json TEXT NOT NULL,
	valid_from TIMESTAMP WITH TIME ZONE,
	valid_from_precision TEXT,
	valid_to TIMESTAMP WITH TIME ZONE,
	valid_to_precision TEXT,
	review_state TEXT NOT NULL,
	decision_ref TEXT,
	opened_by TEXT NOT NULL,
	opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
	closed_at TIMESTAMP WITH TIME ZONE,
	close_reason TEXT,
	CONSTRAINT pk_relation_assertions PRIMARY KEY (assertion_id),
	CONSTRAINT ck_relation_assertions_valid_from_precision_enum CHECK (valid_from_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_relation_assertions_valid_to_precision_enum CHECK (valid_to_precision IN ('year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond')),
	CONSTRAINT ck_relation_assertions_review_state_enum CHECK (review_state IN ('unreviewed', 'accepted', 'disputed', 'rejected')),
	CONSTRAINT ck_relation_assertions_close_reason_enum CHECK (close_reason IN ('rejected', 'retracted', 'superseded')),
	CONSTRAINT ck_relation_assertions_closure_presence CHECK (num_nonnulls(closed_at, close_reason) IN (0, 2)),
	CONSTRAINT ck_relation_assertions_valid_from_time_presence CHECK (num_nonnulls(valid_from, valid_from_precision) IN (0, 2)),
	CONSTRAINT ck_relation_assertions_valid_to_time_presence CHECK (num_nonnulls(valid_to, valid_to_precision) IN (0, 2))
);

CREATE TABLE evidence.relation_supports (
	assertion_id TEXT NOT NULL,
	claim_key TEXT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_relation_supports PRIMARY KEY (assertion_id, claim_key)
);

CREATE TABLE evidence.review_decisions (
	decision_id TEXT NOT NULL,
	item_id TEXT NOT NULL,
	outcome TEXT NOT NULL,
	selected_claim_key TEXT,
	predecessor TEXT,
	reviewer TEXT NOT NULL,
	reason TEXT NOT NULL,
	performed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	human_verification_decision_id TEXT,
	event_json TEXT NOT NULL,
	CONSTRAINT pk_review_decisions PRIMARY KEY (decision_id),
	CONSTRAINT ck_review_decisions_outcome_enum CHECK (outcome IN ('select', 'reject', 'accept', 'defer', 'dismiss'))
);

CREATE TABLE evidence.review_items (
	item_id TEXT NOT NULL,
	kind TEXT NOT NULL,
	kn_id TEXT,
	field_id TEXT,
	fact_key TEXT,
	candidates_json TEXT NOT NULL,
	reason_code TEXT NOT NULL,
	opened_by TEXT NOT NULL,
	opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_review_items PRIMARY KEY (item_id),
	CONSTRAINT ck_review_items_kind_enum CHECK (kind IN ('fact_conflict', 'fixed_value_change', 'empty_claim', 'high_impact', 'owner_override', 'relation_candidate', 'quarantine', 'identity_match', 'identity_drift'))
);

CREATE TABLE evidence.selection_outcomes (
	outcome_id TEXT NOT NULL,
	fact_key TEXT NOT NULL,
	claim_key TEXT NOT NULL,
	fact_version_id TEXT NOT NULL,
	outcome TEXT NOT NULL,
	criterion TEXT NOT NULL,
	criteria_json TEXT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_selection_outcomes PRIMARY KEY (outcome_id),
	CONSTRAINT ck_selection_outcomes_outcome_enum CHECK (outcome IN ('filled', 'replaced', 'ignored', 'corroborated', 'conflict')),
	CONSTRAINT ck_selection_outcomes_criterion_enum CHECK (criterion IN ('first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision'))
);

CREATE TABLE evidence.text_translations (
	translation_id TEXT NOT NULL,
	claim_key TEXT NOT NULL,
	language TEXT NOT NULL,
	text TEXT NOT NULL,
	method TEXT NOT NULL,
	provenance TEXT NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_text_translations PRIMARY KEY (translation_id),
	CONSTRAINT ck_text_translations_method_enum CHECK (method IN ('source', 'human', 'machine'))
);

ALTER TABLE evidence.aliases ADD CONSTRAINT fk_aliases_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX aliases_key_idx ON evidence.aliases USING btree (normalized_key);

COMMENT ON TABLE evidence.aliases IS 'Weak, non-unique alias identifiers of objects.';

COMMENT ON COLUMN evidence.aliases.alias_id IS 'SHA-256 of the object, text, language and claim';

COMMENT ON COLUMN evidence.aliases.kn_id IS 'Object the alias weakly identifies';

COMMENT ON COLUMN evidence.aliases.alias IS 'Alias text exactly as stated';

COMMENT ON COLUMN evidence.aliases.language IS 'BCP-47 tag of the alias; und when unknown';

COMMENT ON COLUMN evidence.aliases.normalized_key IS 'Normalized lookup key; not unique';

COMMENT ON COLUMN evidence.aliases.normalizer IS 'Normalizer that produced the key';

COMMENT ON COLUMN evidence.aliases.claim_key IS 'Claim that states the alias';

COMMENT ON COLUMN evidence.aliases.recorded_at IS 'UTC time KN recorded the alias';

ALTER TABLE evidence.canonical_facts ADD CONSTRAINT fk_canonical_facts_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.canonical_facts ADD CONSTRAINT fk_canonical_facts_review_item_id FOREIGN KEY(review_item_id) REFERENCES evidence.review_items (item_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX facts_current_idx ON evidence.canonical_facts USING btree (fact_key) WHERE knowledge_to IS NULL;

CREATE INDEX facts_subject_idx ON evidence.canonical_facts USING btree (kn_id, field_id);

COMMENT ON TABLE evidence.canonical_facts IS 'Bitemporal projection of selected claims and unresolved fields.';

COMMENT ON COLUMN evidence.canonical_facts.fact_version_id IS 'SHA-256 of the fact key, selection content and knowledge start';

COMMENT ON COLUMN evidence.canonical_facts.fact_key IS 'SHA-256 of object, field, conditions and audience';

COMMENT ON COLUMN evidence.canonical_facts.kn_id IS 'Object of the fact; a survivor after merges';

COMMENT ON COLUMN evidence.canonical_facts.field_id IS 'Stable contract field ID';

COMMENT ON COLUMN evidence.canonical_facts.conditions_json IS 'Canonical JSON condition set; {} when unconditioned';

COMMENT ON COLUMN evidence.canonical_facts.audience IS 'Audience whose eligible evidence was selected';

COMMENT ON COLUMN evidence.canonical_facts.claim_key IS 'Selected claim; null when unresolved';

COMMENT ON COLUMN evidence.canonical_facts.unresolved_reason IS 'Why no claim is selected';

COMMENT ON COLUMN evidence.canonical_facts.mode IS 'Update policy mode';

COMMENT ON COLUMN evidence.canonical_facts.policy_digest IS 'SHA-256 of the canonical update policy';

COMMENT ON COLUMN evidence.canonical_facts.outcome IS 'Outcome of the change that produced this version; ignored claims leave no version';

COMMENT ON COLUMN evidence.canonical_facts.deciding_criterion IS 'Criterion that decided the outcome';

COMMENT ON COLUMN evidence.canonical_facts.winner_criteria_json IS 'Canonical criteria values of the winner';

COMMENT ON COLUMN evidence.canonical_facts.runner_up_criteria_json IS 'Canonical criteria values of the runner-up';

COMMENT ON COLUMN evidence.canonical_facts.verification_state IS 'Derived verification label';

COMMENT ON COLUMN evidence.canonical_facts.owner_override IS 'An owner-entered value outranks a differing first-party value';

COMMENT ON COLUMN evidence.canonical_facts.review_item_id IS 'Open review item for this version';

COMMENT ON COLUMN evidence.canonical_facts.valid_from IS 'Inclusive start of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.canonical_facts.valid_from_precision IS 'Precision of valid_from; present exactly when it is';

COMMENT ON COLUMN evidence.canonical_facts.valid_to IS 'Exclusive end of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.canonical_facts.valid_to_precision IS 'Precision of valid_to; present exactly when it is';

COMMENT ON COLUMN evidence.canonical_facts.knowledge_from IS 'Inclusive UTC knowledge time of this version';

COMMENT ON COLUMN evidence.canonical_facts.knowledge_to IS 'Exclusive UTC knowledge end; null while current';

ALTER TABLE evidence.claim_confirmations ADD CONSTRAINT fk_claim_confirmations_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.claim_confirmations ADD CONSTRAINT fk_claim_confirmations_evidence_id FOREIGN KEY(evidence_id) REFERENCES evidence.evidence_records (evidence_id) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX confirmations_claim_idx ON evidence.claim_confirmations USING btree (claim_key);

COMMENT ON TABLE evidence.claim_confirmations IS 'Re-observations of unchanged claim values.';

COMMENT ON COLUMN evidence.claim_confirmations.confirmation_id IS 'SHA-256 of the claim key, source version and fetch';

COMMENT ON COLUMN evidence.claim_confirmations.claim_key IS 'Unchanged claim that was observed again';

COMMENT ON COLUMN evidence.claim_confirmations.source_version_id IS 'Source record version that repeated the value';

COMMENT ON COLUMN evidence.claim_confirmations.evidence_id IS 'Evidence of the re-observation';

COMMENT ON COLUMN evidence.claim_confirmations.fetch_id IS 'Fetch ID of the re-observation';

COMMENT ON COLUMN evidence.claim_confirmations.observed_at IS 'UTC time of the re-observation';

COMMENT ON COLUMN evidence.claim_confirmations.recorded_at IS 'UTC time KN recorded the confirmation';

ALTER TABLE evidence.claims ADD CONSTRAINT fk_claims_evidence_id FOREIGN KEY(evidence_id) REFERENCES evidence.evidence_records (evidence_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.claims ADD CONSTRAINT fk_claims_supersedes FOREIGN KEY(supersedes) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX claims_evidence_idx ON evidence.claims USING btree (evidence_id);

CREATE INDEX claims_subject_idx ON evidence.claims USING btree (kn_id, field_id);

CREATE INDEX claims_version_idx ON evidence.claims USING btree (source_version_id);

COMMENT ON TABLE evidence.claims IS 'Immutable claims about KN objects with claim-level provenance.';

COMMENT ON COLUMN evidence.claims.claim_key IS 'Deterministic SHA-256 of the claim content and its evidence';

COMMENT ON COLUMN evidence.claims.kn_id IS 'KN ID of the object the claim is about';

COMMENT ON COLUMN evidence.claims.field_id IS 'Stable contract field ID the claim states';

COMMENT ON COLUMN evidence.claims.conditions_json IS 'Canonical JSON object of conditions; {} when unconditioned';

COMMENT ON COLUMN evidence.claims.source_id IS 'Qualified source catalogue ID';

COMMENT ON COLUMN evidence.claims.record_id IS 'Identity source record that stated the value';

COMMENT ON COLUMN evidence.claims.source_version_id IS 'Identity source record version that stated the value';

COMMENT ON COLUMN evidence.claims.change_set_id IS 'Identity change set that produced the claim, when tracked';

COMMENT ON COLUMN evidence.claims.change_kind IS 'Change that produced the claim';

COMMENT ON COLUMN evidence.claims.supersedes IS 'Earlier claim of the same record and field';

COMMENT ON COLUMN evidence.claims.decision_ref IS 'Review decision that produced an owner-entered claim';

COMMENT ON COLUMN evidence.claims.evidence_id IS 'Evidence that carries the full provenance';

COMMENT ON COLUMN evidence.claims.fetch_id IS 'Fetch ID of the evidence';

COMMENT ON COLUMN evidence.claims.origin_uri IS 'Redacted origin URI of the evidence';

COMMENT ON COLUMN evidence.claims.fetched_at IS 'UTC fetch time of the evidence';

COMMENT ON COLUMN evidence.claims.original_value IS 'Value exactly as the source states it';

COMMENT ON COLUMN evidence.claims.original_unit IS 'Unit exactly as the source states it';

COMMENT ON COLUMN evidence.claims.value_text IS 'Normalized text value in its original language';

COMMENT ON COLUMN evidence.claims.value_language IS 'BCP-47 tag of value_text; und when unknown';

COMMENT ON COLUMN evidence.claims.value_number IS 'Exact normalized decimal value';

COMMENT ON COLUMN evidence.claims.value_boolean IS 'Normalized boolean value';

COMMENT ON COLUMN evidence.claims.value_date IS 'Partial ISO date value';

COMMENT ON COLUMN evidence.claims.value_concept IS 'Qualified semantic concept ID value';

COMMENT ON COLUMN evidence.claims.value_kn_id IS 'KN ID of a referenced object';

COMMENT ON COLUMN evidence.claims.missing_reason IS 'Why no value is stated; exclusive with every value';

COMMENT ON COLUMN evidence.claims.normalized_unit IS 'Unit of value_number after conversion';

COMMENT ON COLUMN evidence.claims.conversion_rule IS 'Rule that converted the original unit';

COMMENT ON COLUMN evidence.claims.assertion_type IS 'How the source asserts the value';

COMMENT ON COLUMN evidence.claims.evidence_class IS 'Evidence class used by selection';

COMMENT ON COLUMN evidence.claims.extraction_confidence IS 'Extraction confidence from 0 to 1, never a truth probability';

COMMENT ON COLUMN evidence.claims.source_verification_label IS 'Imported source verification label; never human verification';

COMMENT ON COLUMN evidence.claims.event_at IS 'Time the described event happened (UTC); null when unknown';

COMMENT ON COLUMN evidence.claims.event_precision IS 'Precision of event_at; present exactly when it is';

COMMENT ON COLUMN evidence.claims.published_at IS 'Time the source published the value (UTC); null when unknown';

COMMENT ON COLUMN evidence.claims.published_precision IS 'Precision of published_at; present exactly when it is';

COMMENT ON COLUMN evidence.claims.valid_from IS 'Inclusive start of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.claims.valid_from_precision IS 'Precision of valid_from; present exactly when it is';

COMMENT ON COLUMN evidence.claims.valid_to IS 'Exclusive end of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.claims.valid_to_precision IS 'Precision of valid_to; present exactly when it is';

COMMENT ON COLUMN evidence.claims.observed_at IS 'UTC time the value was observed';

COMMENT ON COLUMN evidence.claims.recorded_at IS 'UTC knowledge time KN recorded the claim';

CREATE INDEX evidence_fetch_idx ON evidence.evidence_records USING btree (fetch_id);

COMMENT ON TABLE evidence.evidence_records IS 'Fetch-level provenance of claims: origin, locator, rights and digests.';

COMMENT ON COLUMN evidence.evidence_records.evidence_id IS 'SHA-256 of the canonical provenance content';

COMMENT ON COLUMN evidence.evidence_records.source_id IS 'Qualified source catalogue ID';

COMMENT ON COLUMN evidence.evidence_records.fetch_id IS 'Fetch run that retrieved the bytes';

COMMENT ON COLUMN evidence.evidence_records.archive_record_id IS 'Raw archive record; null only for review decisions and curated entries';

COMMENT ON COLUMN evidence.evidence_records.origin_uri IS 'Origin URI after credential redaction';

COMMENT ON COLUMN evidence.evidence_records.fetched_at IS 'UTC fetch or capture time';

COMMENT ON COLUMN evidence.evidence_records.locator_kind IS 'Kind of native record locator';

COMMENT ON COLUMN evidence.evidence_records.locator IS 'Native locator inside the archived record';

COMMENT ON COLUMN evidence.evidence_records.excerpt IS 'Original excerpt, stored only when its rights permit';

COMMENT ON COLUMN evidence.evidence_records.excerpt_rights IS 'Rights reference that permits the stored excerpt';

COMMENT ON COLUMN evidence.evidence_records.rights IS 'Rights or license policy reference of the evidence';

COMMENT ON COLUMN evidence.evidence_records.code_digest IS 'SHA-256 of the parser or mapping code';

COMMENT ON COLUMN evidence.evidence_records.contract_digest IS 'Digest of the contract the parser applied';

COMMENT ON COLUMN evidence.evidence_records.curator IS 'Curator of a curated observation';

COMMENT ON COLUMN evidence.evidence_records.recorded_at IS 'UTC time KN recorded the evidence';

ALTER TABLE evidence.relation_assertions ADD CONSTRAINT fk_relation_assertions_opened_by FOREIGN KEY(opened_by) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX relations_active_idx ON evidence.relation_assertions USING btree (relation_key) WHERE closed_at IS NULL;

CREATE INDEX relations_subject_idx ON evidence.relation_assertions USING btree (subject_kn_id, relation_type);

COMMENT ON TABLE evidence.relation_assertions IS 'Typed relations between objects with no active duplicates.';

COMMENT ON COLUMN evidence.relation_assertions.assertion_id IS 'SHA-256 of the relation key and the claim that opened it';

COMMENT ON COLUMN evidence.relation_assertions.relation_key IS 'SHA-256 of subject, type, object, qualifiers and validity';

COMMENT ON COLUMN evidence.relation_assertions.subject_kn_id IS 'Subject object';

COMMENT ON COLUMN evidence.relation_assertions.relation_type IS 'Ontology relation type ID';

COMMENT ON COLUMN evidence.relation_assertions.object_kn_id IS 'Object at the other endpoint';

COMMENT ON COLUMN evidence.relation_assertions.qualifiers_json IS 'Canonical JSON object of qualifiers; {} when none';

COMMENT ON COLUMN evidence.relation_assertions.valid_from IS 'Inclusive start of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.relation_assertions.valid_from_precision IS 'Precision of valid_from; present exactly when it is';

COMMENT ON COLUMN evidence.relation_assertions.valid_to IS 'Exclusive end of validity (UTC); null when unknown';

COMMENT ON COLUMN evidence.relation_assertions.valid_to_precision IS 'Precision of valid_to; present exactly when it is';

COMMENT ON COLUMN evidence.relation_assertions.review_state IS 'Review state of the assertion';

COMMENT ON COLUMN evidence.relation_assertions.decision_ref IS 'Review decision behind the review state';

COMMENT ON COLUMN evidence.relation_assertions.opened_by IS 'Claim that first asserted the relation';

COMMENT ON COLUMN evidence.relation_assertions.opened_at IS 'UTC knowledge time the assertion became active';

COMMENT ON COLUMN evidence.relation_assertions.closed_at IS 'UTC knowledge time the assertion stopped being active';

COMMENT ON COLUMN evidence.relation_assertions.close_reason IS 'Why the assertion closed';

ALTER TABLE evidence.relation_supports ADD CONSTRAINT fk_relation_supports_assertion_id FOREIGN KEY(assertion_id) REFERENCES evidence.relation_assertions (assertion_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.relation_supports ADD CONSTRAINT fk_relation_supports_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE evidence.relation_supports IS 'Claims that support a relation assertion.';

COMMENT ON COLUMN evidence.relation_supports.assertion_id IS 'Supported relation assertion';

COMMENT ON COLUMN evidence.relation_supports.claim_key IS 'Claim that supports the assertion';

COMMENT ON COLUMN evidence.relation_supports.recorded_at IS 'UTC time KN recorded the support';

ALTER TABLE evidence.review_decisions ADD CONSTRAINT fk_review_decisions_item_id FOREIGN KEY(item_id) REFERENCES evidence.review_items (item_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.review_decisions ADD CONSTRAINT fk_review_decisions_predecessor FOREIGN KEY(predecessor) REFERENCES evidence.review_decisions (decision_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.review_decisions ADD CONSTRAINT fk_review_decisions_selected_claim_key FOREIGN KEY(selected_claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX review_decisions_item_idx ON evidence.review_decisions USING btree (item_id);

COMMENT ON TABLE evidence.review_decisions IS 'Append-only review decisions with reviewer, reason and times.';

COMMENT ON COLUMN evidence.review_decisions.decision_id IS 'SHA-256 of the canonical decision event';

COMMENT ON COLUMN evidence.review_decisions.item_id IS 'Decided review item';

COMMENT ON COLUMN evidence.review_decisions.outcome IS 'Append-only decision outcome';

COMMENT ON COLUMN evidence.review_decisions.selected_claim_key IS 'Claim selected by a select decision';

COMMENT ON COLUMN evidence.review_decisions.predecessor IS 'Earlier decision this one supersedes';

COMMENT ON COLUMN evidence.review_decisions.reviewer IS 'Authenticated reviewer principal';

COMMENT ON COLUMN evidence.review_decisions.reason IS 'Reviewer''s reason';

COMMENT ON COLUMN evidence.review_decisions.performed_at IS 'UTC time of the human decision';

COMMENT ON COLUMN evidence.review_decisions.recorded_at IS 'Separate UTC journal recording time';

COMMENT ON COLUMN evidence.review_decisions.human_verification_decision_id IS 'Shared human verification decision, when the decision also verifies';

COMMENT ON COLUMN evidence.review_decisions.event_json IS 'Canonical decision event; authoritative replay payload';

CREATE INDEX review_items_subject_idx ON evidence.review_items USING btree (kn_id, field_id);

COMMENT ON TABLE evidence.review_items IS 'Candidates, conflicts and quarantine awaiting human review.';

COMMENT ON COLUMN evidence.review_items.item_id IS 'SHA-256 of the kind, subject and sorted candidates';

COMMENT ON COLUMN evidence.review_items.kind IS 'Registered review item kind';

COMMENT ON COLUMN evidence.review_items.kn_id IS 'Object under review, when the item has one';

COMMENT ON COLUMN evidence.review_items.field_id IS 'Field under review, when the item has one';

COMMENT ON COLUMN evidence.review_items.fact_key IS 'Fact under review, when the item has one';

COMMENT ON COLUMN evidence.review_items.candidates_json IS 'Canonical sorted array of candidate claim keys or references';

COMMENT ON COLUMN evidence.review_items.reason_code IS 'Stable reason code';

COMMENT ON COLUMN evidence.review_items.opened_by IS 'Selection, run or match record that opened the item';

COMMENT ON COLUMN evidence.review_items.opened_at IS 'UTC time the item opened';

ALTER TABLE evidence.selection_outcomes ADD CONSTRAINT fk_selection_outcomes_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE evidence.selection_outcomes ADD CONSTRAINT fk_selection_outcomes_fact_version_id FOREIGN KEY(fact_version_id) REFERENCES evidence.canonical_facts (fact_version_id) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX outcomes_fact_idx ON evidence.selection_outcomes USING btree (fact_key);

COMMENT ON TABLE evidence.selection_outcomes IS 'Explained outcome of each claim evaluated by selection.';

COMMENT ON COLUMN evidence.selection_outcomes.outcome_id IS 'SHA-256 of the fact version and evaluated claim';

COMMENT ON COLUMN evidence.selection_outcomes.fact_key IS 'Fact whose selection evaluated the claim';

COMMENT ON COLUMN evidence.selection_outcomes.claim_key IS 'Evaluated claim';

COMMENT ON COLUMN evidence.selection_outcomes.fact_version_id IS 'Fact version current after the evaluation';

COMMENT ON COLUMN evidence.selection_outcomes.outcome IS 'Explained outcome for the claim';

COMMENT ON COLUMN evidence.selection_outcomes.criterion IS 'Deciding criterion';

COMMENT ON COLUMN evidence.selection_outcomes.criteria_json IS 'Canonical criteria values of the evaluated claim';

COMMENT ON COLUMN evidence.selection_outcomes.recorded_at IS 'UTC time of the evaluation';

ALTER TABLE evidence.text_translations ADD CONSTRAINT fk_text_translations_claim_key FOREIGN KEY(claim_key) REFERENCES evidence.claims (claim_key) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX translations_language_idx ON evidence.text_translations USING btree (claim_key, language);

COMMENT ON TABLE evidence.text_translations IS 'Derived translations of text claims; originals stay unchanged.';

COMMENT ON COLUMN evidence.text_translations.translation_id IS 'SHA-256 of the claim, language, text and provenance';

COMMENT ON COLUMN evidence.text_translations.claim_key IS 'Text claim whose original stays unchanged';

COMMENT ON COLUMN evidence.text_translations.language IS 'BCP-47 tag of the translation';

COMMENT ON COLUMN evidence.text_translations.text IS 'Derived translated text';

COMMENT ON COLUMN evidence.text_translations.method IS 'Who produced the translation';

COMMENT ON COLUMN evidence.text_translations.provenance IS 'Source record, review or model and prompt reference';

COMMENT ON COLUMN evidence.text_translations.recorded_at IS 'UTC time KN recorded the translation';
