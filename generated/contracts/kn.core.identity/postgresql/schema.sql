CREATE TABLE identity.attributes (
	attribute_id TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	field_id TEXT NOT NULL,
	original TEXT NOT NULL,
	normalized TEXT NOT NULL,
	normalizer TEXT NOT NULL,
	profile_digest TEXT NOT NULL,
	evidence TEXT NOT NULL,
	CONSTRAINT pk_attributes PRIMARY KEY (attribute_id)
);

CREATE TABLE identity.change_sets (
	change_set_id TEXT NOT NULL,
	version_id TEXT NOT NULL,
	changes_json TEXT NOT NULL,
	CONSTRAINT pk_change_sets PRIMARY KEY (change_set_id)
);

CREATE TABLE identity.identifiers (
	identifier_id TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	namespace TEXT NOT NULL,
	value TEXT NOT NULL,
	issuer TEXT NOT NULL,
	authority TEXT NOT NULL,
	valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
	valid_to TIMESTAMP WITH TIME ZONE,
	evidence TEXT NOT NULL,
	CONSTRAINT pk_identifiers PRIMARY KEY (identifier_id),
	CONSTRAINT ck_identifiers_authority_enum CHECK (authority IN ('authoritative', 'source_qualified', 'weak'))
);

CREATE TABLE identity.lifecycle_events (
	event_id TEXT NOT NULL,
	sequence BIGINT NOT NULL,
	previous TEXT,
	kind TEXT NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
	actor TEXT NOT NULL,
	reason TEXT NOT NULL,
	evidence TEXT NOT NULL,
	decision_ref TEXT,
	event_json TEXT NOT NULL,
	CONSTRAINT pk_lifecycle_events PRIMARY KEY (event_id),
	CONSTRAINT ck_lifecycle_events_kind_enum CHECK (kind IN ('minted', 'linked', 'unlinked', 'merged', 'split', 'reclassified', 'retired', 'restored', 'identifier_recorded', 'attribute_recorded', 'version_recorded', 'match_recorded', 'changes_recorded', 'record_seen'))
);

CREATE TABLE identity.links (
	link_id TEXT NOT NULL,
	record_id TEXT NOT NULL,
	kn_id TEXT NOT NULL,
	method TEXT NOT NULL,
	score NUMERIC(38, 18),
	probability NUMERIC(38, 18),
	profile_digest TEXT,
	profile_version TEXT,
	match_id TEXT,
	decision_ref TEXT,
	ended_event TEXT,
	CONSTRAINT pk_links PRIMARY KEY (link_id),
	CONSTRAINT ck_links_method_enum CHECK (method IN ('authoritative_key', 'existing_link', 'scored_match', 'review_decision', 'minted'))
);

CREATE TABLE identity.matches (
	match_id TEXT NOT NULL,
	record_id TEXT NOT NULL,
	profile_digest TEXT NOT NULL,
	profile_version TEXT NOT NULL,
	candidates_json TEXT NOT NULL,
	decision TEXT NOT NULL,
	selected TEXT,
	decision_ref TEXT,
	CONSTRAINT pk_matches PRIMARY KEY (match_id),
	CONSTRAINT ck_matches_decision_enum CHECK (decision IN ('link', 'review', 'mint'))
);

CREATE TABLE identity.objects (
	kn_id TEXT NOT NULL,
	entity_class TEXT NOT NULL,
	state TEXT NOT NULL,
	anchor_record_id TEXT NOT NULL,
	mint_event TEXT NOT NULL,
	current_redirect TEXT,
	revision_event TEXT NOT NULL,
	CONSTRAINT pk_objects PRIMARY KEY (kn_id),
	CONSTRAINT ck_objects_state_enum CHECK (state IN ('active', 'merged', 'split', 'retired'))
);

CREATE TABLE identity.redirects (
	kn_id TEXT NOT NULL,
	successor TEXT NOT NULL,
	CONSTRAINT pk_redirects PRIMARY KEY (kn_id, successor)
);

CREATE TABLE identity.source_records (
	record_id TEXT NOT NULL,
	source TEXT NOT NULL,
	native_key TEXT NOT NULL,
	last_seen TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_source_records PRIMARY KEY (record_id)
);

CREATE TABLE identity.source_versions (
	version_id TEXT NOT NULL,
	record_id TEXT NOT NULL,
	version TEXT NOT NULL,
	content_digest TEXT NOT NULL,
	field_hashes_json TEXT NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	source_updated_at TIMESTAMP WITH TIME ZONE,
	fetch_id TEXT NOT NULL,
	archive_record_id TEXT NOT NULL,
	code_digest TEXT NOT NULL,
	CONSTRAINT pk_source_versions PRIMARY KEY (version_id)
);

ALTER TABLE identity.attributes ADD CONSTRAINT fk_attributes_attribute_id FOREIGN KEY(attribute_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.attributes ADD CONSTRAINT fk_attributes_kn_id FOREIGN KEY(kn_id) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE identity.attributes IS 'Disposable projection of identity events: attributes.';

COMMENT ON COLUMN identity.attributes.attribute_id IS 'attributes: attribute id.';

COMMENT ON COLUMN identity.attributes.kn_id IS 'attributes: kn id.';

COMMENT ON COLUMN identity.attributes.field_id IS 'attributes: field id.';

COMMENT ON COLUMN identity.attributes.original IS 'attributes: original.';

COMMENT ON COLUMN identity.attributes.normalized IS 'attributes: normalized.';

COMMENT ON COLUMN identity.attributes.normalizer IS 'attributes: normalizer.';

COMMENT ON COLUMN identity.attributes.profile_digest IS 'attributes: profile digest.';

COMMENT ON COLUMN identity.attributes.evidence IS 'attributes: evidence.';

ALTER TABLE identity.change_sets ADD CONSTRAINT fk_change_sets_change_set_id FOREIGN KEY(change_set_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.change_sets ADD CONSTRAINT fk_change_sets_version_id FOREIGN KEY(version_id) REFERENCES identity.source_versions (version_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX identity_changes_version_idx ON identity.change_sets USING btree (version_id);

COMMENT ON TABLE identity.change_sets IS 'Disposable projection of identity events: change sets.';

COMMENT ON COLUMN identity.change_sets.change_set_id IS 'change_sets: change set id.';

COMMENT ON COLUMN identity.change_sets.version_id IS 'change_sets: version id.';

COMMENT ON COLUMN identity.change_sets.changes_json IS 'change_sets: changes json.';

ALTER TABLE identity.identifiers ADD CONSTRAINT fk_identifiers_identifier_id FOREIGN KEY(identifier_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.identifiers ADD CONSTRAINT fk_identifiers_kn_id FOREIGN KEY(kn_id) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE identity.identifiers IS 'Disposable projection of identity events: identifiers.';

COMMENT ON COLUMN identity.identifiers.identifier_id IS 'identifiers: identifier id.';

COMMENT ON COLUMN identity.identifiers.kn_id IS 'identifiers: kn id.';

COMMENT ON COLUMN identity.identifiers.namespace IS 'identifiers: namespace.';

COMMENT ON COLUMN identity.identifiers.value IS 'identifiers: value.';

COMMENT ON COLUMN identity.identifiers.issuer IS 'identifiers: issuer.';

COMMENT ON COLUMN identity.identifiers.authority IS 'identifiers: authority.';

COMMENT ON COLUMN identity.identifiers.valid_from IS 'identifiers: valid from.';

COMMENT ON COLUMN identity.identifiers.valid_to IS 'identifiers: valid to.';

COMMENT ON COLUMN identity.identifiers.evidence IS 'identifiers: evidence.';

ALTER TABLE identity.lifecycle_events ADD CONSTRAINT fk_lifecycle_events_previous FOREIGN KEY(previous) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX identity_event_sequence_idx ON identity.lifecycle_events USING btree (sequence);

COMMENT ON TABLE identity.lifecycle_events IS 'Disposable projection of identity events: lifecycle events.';

COMMENT ON COLUMN identity.lifecycle_events.event_id IS 'lifecycle_events: event id.';

COMMENT ON COLUMN identity.lifecycle_events.sequence IS 'lifecycle_events: sequence.';

COMMENT ON COLUMN identity.lifecycle_events.previous IS 'lifecycle_events: previous.';

COMMENT ON COLUMN identity.lifecycle_events.kind IS 'lifecycle_events: kind.';

COMMENT ON COLUMN identity.lifecycle_events.occurred_at IS 'lifecycle_events: occurred at.';

COMMENT ON COLUMN identity.lifecycle_events.actor IS 'lifecycle_events: actor.';

COMMENT ON COLUMN identity.lifecycle_events.reason IS 'lifecycle_events: reason.';

COMMENT ON COLUMN identity.lifecycle_events.evidence IS 'lifecycle_events: evidence.';

COMMENT ON COLUMN identity.lifecycle_events.decision_ref IS 'lifecycle_events: decision ref.';

COMMENT ON COLUMN identity.lifecycle_events.event_json IS 'lifecycle_events: event json.';

ALTER TABLE identity.links ADD CONSTRAINT fk_links_ended_event FOREIGN KEY(ended_event) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.links ADD CONSTRAINT fk_links_kn_id FOREIGN KEY(kn_id) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.links ADD CONSTRAINT fk_links_link_id FOREIGN KEY(link_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.links ADD CONSTRAINT fk_links_match_id FOREIGN KEY(match_id) REFERENCES identity.matches (match_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.links ADD CONSTRAINT fk_links_record_id FOREIGN KEY(record_id) REFERENCES identity.source_records (record_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX identity_active_link_idx ON identity.links USING btree (record_id) WHERE ended_event IS NULL;

COMMENT ON TABLE identity.links IS 'Disposable projection of identity events: links.';

COMMENT ON COLUMN identity.links.link_id IS 'links: link id.';

COMMENT ON COLUMN identity.links.record_id IS 'links: record id.';

COMMENT ON COLUMN identity.links.kn_id IS 'links: kn id.';

COMMENT ON COLUMN identity.links.method IS 'links: method.';

COMMENT ON COLUMN identity.links.score IS 'links: score.';

COMMENT ON COLUMN identity.links.probability IS 'links: probability.';

COMMENT ON COLUMN identity.links.profile_digest IS 'links: profile digest.';

COMMENT ON COLUMN identity.links.profile_version IS 'links: profile version.';

COMMENT ON COLUMN identity.links.match_id IS 'links: match id.';

COMMENT ON COLUMN identity.links.decision_ref IS 'links: decision ref.';

COMMENT ON COLUMN identity.links.ended_event IS 'links: ended event.';

ALTER TABLE identity.matches ADD CONSTRAINT fk_matches_match_id FOREIGN KEY(match_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.matches ADD CONSTRAINT fk_matches_record_id FOREIGN KEY(record_id) REFERENCES identity.source_records (record_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.matches ADD CONSTRAINT fk_matches_selected FOREIGN KEY(selected) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE identity.matches IS 'Disposable projection of identity events: matches.';

COMMENT ON COLUMN identity.matches.match_id IS 'matches: match id.';

COMMENT ON COLUMN identity.matches.record_id IS 'matches: record id.';

COMMENT ON COLUMN identity.matches.profile_digest IS 'matches: profile digest.';

COMMENT ON COLUMN identity.matches.profile_version IS 'matches: profile version.';

COMMENT ON COLUMN identity.matches.candidates_json IS 'matches: candidates json.';

COMMENT ON COLUMN identity.matches.decision IS 'matches: decision.';

COMMENT ON COLUMN identity.matches.selected IS 'matches: selected.';

COMMENT ON COLUMN identity.matches.decision_ref IS 'matches: decision ref.';

ALTER TABLE identity.objects ADD CONSTRAINT fk_objects_anchor_record_id FOREIGN KEY(anchor_record_id) REFERENCES identity.source_records (record_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.objects ADD CONSTRAINT fk_objects_current_redirect FOREIGN KEY(current_redirect) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.objects ADD CONSTRAINT fk_objects_mint_event FOREIGN KEY(mint_event) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.objects ADD CONSTRAINT fk_objects_revision_event FOREIGN KEY(revision_event) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX identity_anchor_idx ON identity.objects USING btree (anchor_record_id);

COMMENT ON TABLE identity.objects IS 'Disposable projection of identity events: objects.';

COMMENT ON COLUMN identity.objects.kn_id IS 'objects: kn id.';

COMMENT ON COLUMN identity.objects.entity_class IS 'objects: entity class.';

COMMENT ON COLUMN identity.objects.state IS 'objects: state.';

COMMENT ON COLUMN identity.objects.anchor_record_id IS 'objects: anchor record id.';

COMMENT ON COLUMN identity.objects.mint_event IS 'objects: mint event.';

COMMENT ON COLUMN identity.objects.current_redirect IS 'objects: current redirect.';

COMMENT ON COLUMN identity.objects.revision_event IS 'Lifecycle event defining the current object revision.';

ALTER TABLE identity.redirects ADD CONSTRAINT fk_redirects_kn_id FOREIGN KEY(kn_id) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.redirects ADD CONSTRAINT fk_redirects_successor FOREIGN KEY(successor) REFERENCES identity.objects (kn_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE identity.redirects IS 'Disposable projection of identity events: redirects.';

COMMENT ON COLUMN identity.redirects.kn_id IS 'redirects: kn id.';

COMMENT ON COLUMN identity.redirects.successor IS 'redirects: successor.';

CREATE UNIQUE INDEX identity_source_key_idx ON identity.source_records USING btree (source, native_key);

COMMENT ON TABLE identity.source_records IS 'Disposable projection of identity events: source records.';

COMMENT ON COLUMN identity.source_records.record_id IS 'source_records: record id.';

COMMENT ON COLUMN identity.source_records.source IS 'source_records: source.';

COMMENT ON COLUMN identity.source_records.native_key IS 'source_records: native key.';

COMMENT ON COLUMN identity.source_records.last_seen IS 'source_records: last seen.';

ALTER TABLE identity.source_versions ADD CONSTRAINT fk_source_versions_record_id FOREIGN KEY(record_id) REFERENCES identity.source_records (record_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE identity.source_versions ADD CONSTRAINT fk_source_versions_version_id FOREIGN KEY(version_id) REFERENCES identity.lifecycle_events (event_id) DEFERRABLE INITIALLY DEFERRED;

CREATE UNIQUE INDEX identity_record_version_idx ON identity.source_versions USING btree (record_id, version);

COMMENT ON TABLE identity.source_versions IS 'Disposable projection of identity events: source versions.';

COMMENT ON COLUMN identity.source_versions.version_id IS 'source_versions: version id.';

COMMENT ON COLUMN identity.source_versions.record_id IS 'source_versions: record id.';

COMMENT ON COLUMN identity.source_versions.version IS 'source_versions: version.';

COMMENT ON COLUMN identity.source_versions.content_digest IS 'source_versions: content digest.';

COMMENT ON COLUMN identity.source_versions.field_hashes_json IS 'source_versions: field hashes json.';

COMMENT ON COLUMN identity.source_versions.observed_at IS 'source_versions: observed at.';

COMMENT ON COLUMN identity.source_versions.source_updated_at IS 'source_versions: source updated at.';

COMMENT ON COLUMN identity.source_versions.fetch_id IS 'source_versions: fetch id.';

COMMENT ON COLUMN identity.source_versions.archive_record_id IS 'source_versions: archive record id.';

COMMENT ON COLUMN identity.source_versions.code_digest IS 'source_versions: code digest.';
