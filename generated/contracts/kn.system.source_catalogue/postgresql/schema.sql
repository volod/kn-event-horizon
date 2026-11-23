CREATE TABLE system.source_catalogue (
	source_id TEXT NOT NULL,
	domain TEXT NOT NULL,
	original_id TEXT,
	label TEXT NOT NULL,
	priority TEXT NOT NULL,
	cadence TEXT NOT NULL,
	access_notes_json TEXT NOT NULL,
	access_verification TEXT NOT NULL,
	lifecycle_state TEXT NOT NULL,
	proposal_workbook TEXT NOT NULL,
	proposal_sheet TEXT NOT NULL,
	proposal_sha256 TEXT NOT NULL,
	proposal_row BIGINT NOT NULL,
	proposal_values_json TEXT NOT NULL,
	CONSTRAINT pk_source_catalogue PRIMARY KEY (source_id),
	CONSTRAINT ck_source_catalogue_domain_enum CHECK (domain IN ('space', 'microelectronics', 'gdelt')),
	CONSTRAINT ck_source_catalogue_priority_enum CHECK (priority IN ('P0', 'P1', 'P2')),
	CONSTRAINT ck_source_catalogue_access_verification_enum CHECK (access_verification IN ('unverified')),
	CONSTRAINT ck_source_catalogue_lifecycle_state_enum CHECK (lifecycle_state IN ('candidate', 'investigating', 'sampling_authorized', 'approved', 'enabled', 'paused', 'retired', 'rejected'))
);

COMMENT ON TABLE system.source_catalogue IS 'Source discovery and lifecycle catalogue. Catalogue rows confer no execution authority.';

COMMENT ON COLUMN system.source_catalogue.source_id IS 'The stable domain-qualified catalogue identifier';

COMMENT ON COLUMN system.source_catalogue.domain IS 'The owning knowledge domain';

COMMENT ON COLUMN system.source_catalogue.original_id IS 'Native proposal identifier when the sheet supplies one';

COMMENT ON COLUMN system.source_catalogue.label IS 'Original proposal resource name in the source language';

COMMENT ON COLUMN system.source_catalogue.priority IS 'Original proposal priority for investigation';

COMMENT ON COLUMN system.source_catalogue.cadence IS 'Original cadence as stated in the proposal';

COMMENT ON COLUMN system.source_catalogue.access_notes_json IS 'Canonical JSON of provisional access and limitation cells';

COMMENT ON COLUMN system.source_catalogue.access_verification IS 'Verification status of the proposal access notes';

COMMENT ON COLUMN system.source_catalogue.lifecycle_state IS 'Lifecycle designation, independent of execution approval';

COMMENT ON COLUMN system.source_catalogue.proposal_workbook IS 'Original workbook file name';

COMMENT ON COLUMN system.source_catalogue.proposal_sheet IS 'Original workbook sheet name';

COMMENT ON COLUMN system.source_catalogue.proposal_sha256 IS 'SHA-256 of the original proposal workbook';

COMMENT ON COLUMN system.source_catalogue.proposal_row IS 'One-based row number in the original workbook';

COMMENT ON COLUMN system.source_catalogue.proposal_values_json IS 'All proposal cells as canonical JSON including source text and nulls';
