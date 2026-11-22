CREATE TABLE system.installed_contracts (
	contract_id TEXT NOT NULL,
	version TEXT NOT NULL,
	digest TEXT NOT NULL,
	storage_schema TEXT NOT NULL,
	managed_tables_json TEXT NOT NULL,
	CONSTRAINT pk_installed_contracts PRIMARY KEY (contract_id)
);

COMMENT ON TABLE system.installed_contracts IS 'One row per deployed storage contract: the installed-contract marker.';

COMMENT ON COLUMN system.installed_contracts.contract_id IS 'ODCS id of the deployed storage contract';

COMMENT ON COLUMN system.installed_contracts.version IS 'Semantic version of the deployed contract';

COMMENT ON COLUMN system.installed_contracts.digest IS 'Canonical SHA-256 digest of the contract and its reference catalog';

COMMENT ON COLUMN system.installed_contracts.storage_schema IS 'KN schema that holds the contract''s tables';

COMMENT ON COLUMN system.installed_contracts.managed_tables_json IS 'Canonical JSON array of the contract''s table names';
