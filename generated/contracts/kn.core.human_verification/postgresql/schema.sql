CREATE TABLE evidence.human_verification_decisions (
	decision_id TEXT NOT NULL,
	target_id TEXT NOT NULL,
	request_key TEXT NOT NULL,
	reviewer TEXT NOT NULL,
	performed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	outcome TEXT NOT NULL,
	event_json TEXT NOT NULL,
	CONSTRAINT pk_human_verification_decisions PRIMARY KEY (decision_id),
	CONSTRAINT ck_human_verification_decisions_outcome_enum CHECK (outcome IN ('accept', 'reject', 'revoke', 'supersede'))
);

CREATE UNIQUE INDEX human_verification_request_idx ON evidence.human_verification_decisions USING btree (request_key);

CREATE INDEX human_verification_target_idx ON evidence.human_verification_decisions USING btree (target_id);

COMMENT ON TABLE evidence.human_verification_decisions IS 'Append-only SQL projection of the trusted durable human decision journal.';

COMMENT ON COLUMN evidence.human_verification_decisions.decision_id IS 'Deterministic SHA-256 of the canonical typed event';

COMMENT ON COLUMN evidence.human_verification_decisions.target_id IS 'SHA-256 of the exact typed target including scope, version and purpose';

COMMENT ON COLUMN evidence.human_verification_decisions.request_key IS 'SHA-256 of authenticated reviewer and client request ID';

COMMENT ON COLUMN evidence.human_verification_decisions.reviewer IS 'Authenticated authorized human principal reference';

COMMENT ON COLUMN evidence.human_verification_decisions.performed_at IS 'Actual UTC instant of the human decision';

COMMENT ON COLUMN evidence.human_verification_decisions.recorded_at IS 'Separate trusted UTC journal recording time';

COMMENT ON COLUMN evidence.human_verification_decisions.outcome IS 'Append-only acceptance, rejection, revocation or supersession';

COMMENT ON COLUMN evidence.human_verification_decisions.event_json IS 'Canonical human-verification v1 event; authoritative replay payload';
