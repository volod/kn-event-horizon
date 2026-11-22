CREATE TABLE space.aliases_crosswalk (
	import_id TEXT NOT NULL,
	alias_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	alias TEXT NOT NULL,
	alias_type TEXT NOT NULL,
	valid_from TEXT,
	valid_to TEXT,
	source_id TEXT,
	notes TEXT,
	CONSTRAINT pk_aliases_crosswalk PRIMARY KEY (import_id, alias_id),
	CONSTRAINT ck_aliases_crosswalk_valid_from_precision CHECK (valid_from ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_aliases_crosswalk_valid_to_precision CHECK (valid_to ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.classifications (
	import_id TEXT NOT NULL,
	class_id TEXT NOT NULL,
	scheme TEXT NOT NULL,
	code TEXT NOT NULL,
	label_uk TEXT,
	label_en TEXT,
	parent_class_id TEXT,
	definition_uk TEXT,
	origin TEXT,
	CONSTRAINT pk_classifications PRIMARY KEY (import_id, class_id)
);

CREATE TABLE space.compatibility (
	import_id TEXT NOT NULL,
	compatibility_id TEXT NOT NULL,
	subject_id TEXT NOT NULL,
	program_id TEXT NOT NULL,
	compatibility_type TEXT NOT NULL,
	status TEXT,
	claim_id TEXT,
	CONSTRAINT pk_compatibility PRIMARY KEY (import_id, compatibility_id)
);

CREATE TABLE space.constellations_programs (
	import_id TEXT NOT NULL,
	program_id TEXT NOT NULL,
	name TEXT NOT NULL,
	entity_kind TEXT NOT NULL,
	orbit_class TEXT NOT NULL,
	primary_segment TEXT NOT NULL,
	lifecycle_status TEXT NOT NULL,
	status_as_of TEXT,
	operator_org_id TEXT,
	owner_org_id TEXT,
	country_iso2 TEXT,
	user_class TEXT,
	coverage_scope TEXT,
	planned_spacecraft_total BIGINT,
	first_launch_date TEXT,
	service_start_date TEXT,
	altitude_km_nominal NUMERIC(38, 18),
	inclination_deg_nominal NUMERIC(38, 18),
	isl_type TEXT,
	ukraine_service_status TEXT,
	website_url TEXT,
	notes TEXT,
	CONSTRAINT pk_constellations_programs PRIMARY KEY (import_id, program_id),
	CONSTRAINT ck_constellations_programs_entity_kind_enum CHECK (entity_kind IN ('constellation', 'fleet', 'program', 'service_brand', 'demonstrator', 'relay_system')),
	CONSTRAINT ck_constellations_programs_orbit_class_enum CHECK (orbit_class IN ('LEO', 'MEO', 'GEO', 'HEO', 'LEO+MEO', 'LEO+GEO', 'MEO+GEO', 'LEO+MEO+GEO', 'GEO+HEO', 'multi', 'suborbital', 'n/a')),
	CONSTRAINT ck_constellations_programs_primary_segment_enum CHECK (primary_segment IN ('broadband', 'telecom_fss', 'broadcast', 'mss', 'iot_m2m', 'd2d', 'govmil', 'data_relay', 'multi', 'adjacent_eo_isr')),
	CONSTRAINT ck_constellations_programs_lifecycle_status_enum CHECK (lifecycle_status IN ('operational', 'partial_service', 'deploying', 'trial', 'experimental', 'planned', 'announced', 'suspended', 'retired', 'cancelled', 'unknown')),
	CONSTRAINT ck_constellations_programs_status_as_of_precision CHECK (status_as_of ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_constellations_programs_user_class_enum CHECK (user_class IN ('commercial', 'state_owned_commercial', 'government', 'military', 'mixed', 'unknown')),
	CONSTRAINT ck_constellations_programs_first_launch_date_precision CHECK (first_launch_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_constellations_programs_service_start_date_precision CHECK (service_start_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_constellations_programs_ukraine_service_status_enum CHECK (ukraine_service_status IN ('available_documented', 'trial_or_limited', 'announced', 'not_available', 'unknown'))
);

CREATE TABLE space.countries (
	import_id TEXT NOT NULL,
	country_iso2 TEXT NOT NULL,
	name_uk TEXT NOT NULL,
	name_en TEXT NOT NULL,
	region TEXT NOT NULL,
	is_ukraine_neighbor BOOLEAN,
	CONSTRAINT pk_countries PRIMARY KEY (import_id, country_iso2),
	CONSTRAINT ck_countries_region_enum CHECK (region IN (U&'\0404\0432\0440\043e\043f\0430', U&'\041f\0456\0432\043d\0456\0447\043d\0430 \0410\043c\0435\0440\0438\043a\0430', U&'\041b\0430\0442\0438\043d\0441\044c\043a\0430 \0410\043c\0435\0440\0438\043a\0430', U&'\0411\043b\0438\0437\044c\043a\0438\0439 \0421\0445\0456\0434', U&'\0410\0444\0440\0438\043a\0430', U&'\0410\0437\0456\044f-\041f\0430\0446\0438\0444\0456\043a', U&'\0404\0432\0440\0430\0437\0456\044f / \0421\041d\0414', U&'\041c\0456\0436\043d\0430\0440\043e\0434\043d\0456'))
);

CREATE TABLE space.deployment_observations (
	import_id TEXT NOT NULL,
	observation_id TEXT NOT NULL,
	program_id TEXT NOT NULL,
	spacecraft_model_id TEXT,
	status_metric TEXT NOT NULL,
	count BIGINT NOT NULL,
	observation_date TEXT NOT NULL,
	definition_uk TEXT,
	information_character TEXT,
	claim_id TEXT NOT NULL,
	CONSTRAINT pk_deployment_observations PRIMARY KEY (import_id, observation_id),
	CONSTRAINT ck_deployment_observations_status_metric_enum CHECK (status_metric IN ('planned', 'authorized', 'ordered', 'launched', 'on_orbit', 'working', 'operational_orbit', 'operational', 'spare', 'retired', 'deorbited', 'failed', 'ascent_or_relocating')),
	CONSTRAINT ck_deployment_observations_observation_date_precision CHECK (observation_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_deployment_observations_information_character_enum CHECK (information_character IN ('independent_measurement', 'orbital_catalog', 'regulatory_filing', 'financial_report', 'manufacturer_operator_statement', 'dealer_reseller', 'secondary_source', 'plan_forecast', 'calculation', 'user_document', 'standard_specification'))
);

CREATE TABLE space.enabling_devices_technologies (
	import_id TEXT NOT NULL,
	tech_id TEXT NOT NULL,
	name TEXT NOT NULL,
	category TEXT NOT NULL,
	vendor_org_id TEXT,
	example_products TEXT,
	function_uk TEXT,
	expected_effect_uk TEXT,
	effect_evidence_type TEXT,
	application_conditions_uk TEXT,
	maturity TEXT,
	compatibility_uk TEXT,
	dependencies_uk TEXT,
	customer_relevance_uk TEXT,
	claim_id TEXT,
	CONSTRAINT pk_enabling_devices_technologies PRIMARY KEY (import_id, tech_id),
	CONSTRAINT ck_enabling_devices_technologies_category_enum CHECK (category IN ('antenna', 'rf_component', 'modem_sdr', 'waveform_standard', 'optical_link', 'payload_processing', 'network_software', 'power_thermal_pointing', 'spectrum_security', 'test_emulation', 'ground_segment', 'launch_inspace')),
	CONSTRAINT ck_enabling_devices_technologies_maturity_enum CHECK (maturity IN ('concept', 'lab_demo', 'flight_or_field_demo', 'early_commercial', 'serial_commercial', 'standardized'))
);

CREATE TABLE space.entity_classifications (
	import_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	class_id TEXT NOT NULL,
	basis TEXT,
	CONSTRAINT pk_entity_classifications PRIMARY KEY (import_id, entity_id, class_id)
);

CREATE TABLE space.entity_registry (
	import_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	entity_table TEXT NOT NULL,
	display_name TEXT NOT NULL,
	CONSTRAINT pk_entity_registry PRIMARY KEY (import_id, entity_id)
);

CREATE TABLE space.evidence_claims (
	import_id TEXT NOT NULL,
	claim_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	field_key TEXT NOT NULL,
	raw_value TEXT NOT NULL,
	value_num NUMERIC(38, 18),
	value_text TEXT,
	unit TEXT,
	qualifier TEXT NOT NULL,
	value_min NUMERIC(38, 18),
	value_max NUMERIC(38, 18),
	fact_date TEXT,
	valid_from TEXT,
	valid_to TEXT,
	access_date DATE NOT NULL,
	source_id TEXT NOT NULL,
	locator TEXT,
	quote TEXT,
	information_character TEXT NOT NULL,
	comment TEXT,
	contradiction_group TEXT,
	is_canonical BOOLEAN NOT NULL,
	selection_rule TEXT,
	formula TEXT,
	input_claim_ids TEXT,
	verification_status TEXT NOT NULL,
	origin TEXT,
	CONSTRAINT pk_evidence_claims PRIMARY KEY (import_id, claim_id),
	CONSTRAINT ck_evidence_claims_qualifier_enum CHECK (qualifier IN ('exact', 'approx', 'min', 'max', 'range', 'upper_bound', 'lower_bound', 'nominal', 'typical')),
	CONSTRAINT ck_evidence_claims_fact_date_precision CHECK (fact_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_evidence_claims_valid_from_precision CHECK (valid_from ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_evidence_claims_valid_to_precision CHECK (valid_to ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_evidence_claims_information_character_enum CHECK (information_character IN ('independent_measurement', 'orbital_catalog', 'regulatory_filing', 'financial_report', 'manufacturer_operator_statement', 'dealer_reseller', 'secondary_source', 'plan_forecast', 'calculation', 'user_document', 'standard_specification'))
);

CREATE TABLE space.field_dictionary (
	import_id TEXT NOT NULL,
	field_key TEXT NOT NULL,
	entity_table TEXT,
	field_group TEXT,
	unit TEXT,
	description_uk TEXT,
	applies_to TEXT,
	CONSTRAINT pk_field_dictionary PRIMARY KEY (import_id, field_key)
);

CREATE TABLE space.financial_observations (
	import_id TEXT NOT NULL,
	fin_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	basis TEXT NOT NULL,
	comparison_group TEXT,
	amount NUMERIC(38, 18) NOT NULL,
	currency TEXT NOT NULL,
	amount_usd_nominal NUMERIC(38, 18),
	fx_id TEXT,
	fact_date TEXT,
	period_start TEXT,
	period_end TEXT,
	counterparty_org_id TEXT,
	price_region TEXT,
	package_scope TEXT,
	claim_id TEXT NOT NULL,
	notes TEXT,
	CONSTRAINT pk_financial_observations PRIMARY KEY (import_id, fin_id),
	CONSTRAINT ck_financial_observations_basis_enum CHECK (basis IN ('capital_raised', 'committed_funding', 'program_budget', 'enterprise_spend', 'credit_facility', 'grant_subsidy', 'contract_value', 'equipment_price', 'service_price_recurring', 'service_price_one_time', 'launch_price', 'revenue', 'valuation', 'backlog', 'capex', 'opex')),
	CONSTRAINT ck_financial_observations_fact_date_precision CHECK (fact_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_financial_observations_period_start_precision CHECK (period_start ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_financial_observations_period_end_precision CHECK (period_end ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.fx_rates (
	import_id TEXT NOT NULL,
	fx_id TEXT NOT NULL,
	currency TEXT NOT NULL,
	usd_per_unit NUMERIC(38, 18) NOT NULL,
	rate_date DATE NOT NULL,
	source_id TEXT NOT NULL,
	notes TEXT,
	CONSTRAINT pk_fx_rates PRIMARY KEY (import_id, fx_id)
);

CREATE TABLE space.ground_infrastructure (
	import_id TEXT NOT NULL,
	ground_id TEXT NOT NULL,
	name TEXT NOT NULL,
	infra_type TEXT NOT NULL,
	operator_org_id TEXT,
	program_id TEXT,
	country_iso2 TEXT,
	location_text TEXT,
	sites_count BIGINT,
	bands_text TEXT,
	status TEXT,
	claim_id TEXT,
	notes TEXT,
	CONSTRAINT pk_ground_infrastructure PRIMARY KEY (import_id, ground_id),
	CONSTRAINT ck_ground_infrastructure_infra_type_enum CHECK (infra_type IN ('gateway', 'teleport', 'ttc_station', 'noc_soc', 'gsaas_network', 'satellite_network_portal', 'optical_ground_station', 'point_of_presence', 'manufacturing_site', 'control_center'))
);

CREATE TABLE space.launch_configurations (
	import_id TEXT NOT NULL,
	config_id TEXT NOT NULL,
	lv_id TEXT NOT NULL,
	config_name TEXT NOT NULL,
	recovery_mode TEXT,
	orbit_type TEXT NOT NULL,
	altitude_km NUMERIC(38, 18),
	apogee_km NUMERIC(38, 18),
	inclination_deg NUMERIC(38, 18),
	payload_kg NUMERIC(38, 18) NOT NULL,
	qualifier TEXT,
	claim_id TEXT NOT NULL,
	notes TEXT,
	CONSTRAINT pk_launch_configurations PRIMARY KEY (import_id, config_id),
	CONSTRAINT ck_launch_configurations_qualifier_enum CHECK (qualifier IN ('exact', 'approx', 'min', 'max', 'range', 'upper_bound', 'lower_bound', 'nominal', 'typical'))
);

CREATE TABLE space.launch_events_contracts (
	import_id TEXT NOT NULL,
	event_id TEXT NOT NULL,
	event_type TEXT NOT NULL,
	program_id TEXT,
	lv_id TEXT,
	customer_org_id TEXT,
	provider_org_id TEXT,
	announced_date TEXT,
	event_date TEXT,
	window_start TEXT,
	window_end TEXT,
	launches_count BIGINT,
	spacecraft_count BIGINT,
	status TEXT,
	claim_id TEXT,
	notes TEXT,
	CONSTRAINT pk_launch_events_contracts PRIMARY KEY (import_id, event_id),
	CONSTRAINT ck_launch_events_contracts_event_type_enum CHECK (event_type IN ('contract', 'launch', 'option', 'rideshare_booking', 'milestone')),
	CONSTRAINT ck_launch_events_contracts_announced_date_precision CHECK (announced_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_launch_events_contracts_event_date_precision CHECK (event_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_launch_events_contracts_window_start_precision CHECK (window_start ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_launch_events_contracts_window_end_precision CHECK (window_end ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.launch_vehicles (
	import_id TEXT NOT NULL,
	lv_id TEXT NOT NULL,
	name TEXT NOT NULL,
	family TEXT,
	provider_org_id TEXT,
	country_iso2 TEXT,
	status TEXT NOT NULL,
	first_flight_date TEXT,
	stages BIGINT,
	reusability TEXT,
	height_m NUMERIC(38, 18),
	diameter_m NUMERIC(38, 18),
	liftoff_mass_t NUMERIC(38, 18),
	fairing_diameter_m NUMERIC(38, 18),
	fairing_height_m NUMERIC(38, 18),
	flights_total BIGINT,
	flights_successful BIGINT,
	flights_as_of DATE,
	export_access_note TEXT,
	notes TEXT,
	CONSTRAINT pk_launch_vehicles PRIMARY KEY (import_id, lv_id),
	CONSTRAINT ck_launch_vehicles_status_enum CHECK (status IN ('operational', 'development', 'retired', 'grounded', 'unknown')),
	CONSTRAINT ck_launch_vehicles_first_flight_date_precision CHECK (first_flight_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.opportunity_evidence (
	import_id TEXT NOT NULL,
	opportunity_id TEXT NOT NULL,
	claim_id TEXT NOT NULL,
	CONSTRAINT pk_opportunity_evidence PRIMARY KEY (import_id, opportunity_id, claim_id)
);

CREATE TABLE space.organization_relationships (
	import_id TEXT NOT NULL,
	relationship_id TEXT NOT NULL,
	from_org_id TEXT NOT NULL,
	to_org_id TEXT NOT NULL,
	relationship_type TEXT NOT NULL,
	share_pct NUMERIC(38, 18),
	start_date TEXT,
	end_date TEXT,
	program_id TEXT,
	claim_id TEXT,
	notes TEXT,
	CONSTRAINT pk_organization_relationships PRIMARY KEY (import_id, relationship_id),
	CONSTRAINT ck_organization_relationships_relationship_type_enum CHECK (relationship_type IN ('subsidiary_of', 'acquired_by', 'merged_into', 'shareholder_of', 'joint_venture_with', 'manufacturer_for', 'launch_provider_for', 'distributor_reseller_of', 'gateway_partner_of', 'investor_in', 'customer_of', 'technology_partner_of', 'renamed_to', 'consortium_member_of')),
	CONSTRAINT ck_organization_relationships_start_date_precision CHECK (start_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_organization_relationships_end_date_precision CHECK (end_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.organizations (
	import_id TEXT NOT NULL,
	org_id TEXT NOT NULL,
	name TEXT NOT NULL,
	legal_name TEXT,
	country_iso2 TEXT,
	org_type TEXT NOT NULL,
	ownership_type TEXT,
	parent_org_id TEXT,
	status TEXT,
	website_url TEXT,
	public_contact_channel TEXT,
	competencies TEXT,
	notes TEXT,
	CONSTRAINT pk_organizations PRIMARY KEY (import_id, org_id),
	CONSTRAINT ck_organizations_org_type_enum CHECK (org_type IN ('satellite_operator', 'service_provider', 'manufacturer_spacecraft', 'manufacturer_terminal', 'manufacturer_component', 'launch_provider', 'ground_segment_provider', 'integrator_reseller', 'government_agency', 'military', 'intergovernmental', 'research_institution', 'investor', 'regulator', 'consortium', 'software_network')),
	CONSTRAINT ck_organizations_ownership_type_enum CHECK (ownership_type IN ('public_listed', 'private', 'state_owned', 'government', 'intergovernmental', 'consortium', 'subsidiary', 'unknown'))
);

CREATE TABLE space.parameter_gaps (
	import_id TEXT NOT NULL,
	gap_id TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	field_key TEXT NOT NULL,
	field_group TEXT,
	null_reason TEXT NOT NULL,
	decision_impact TEXT,
	next_step_uk TEXT,
	CONSTRAINT pk_parameter_gaps PRIMARY KEY (import_id, gap_id)
);

CREATE TABLE space.partnerships_opportunities (
	import_id TEXT NOT NULL,
	opportunity_id TEXT NOT NULL,
	opportunity_type TEXT NOT NULL,
	title_uk TEXT NOT NULL,
	counterparty_org_id TEXT,
	program_id TEXT,
	factual_basis_uk TEXT NOT NULL,
	required_competencies_uk TEXT,
	dependencies_uk TEXT,
	open_questions_uk TEXT,
	analyst_assumption_uk TEXT,
	readiness TEXT,
	ukraine_access_note TEXT,
	basis_claim_id TEXT,
	CONSTRAINT pk_partnerships_opportunities PRIMARY KEY (import_id, opportunity_id),
	CONSTRAINT ck_partnerships_opportunities_opportunity_type_enum CHECK (opportunity_type IN ('service_procurement', 'equipment_procurement_integration', 'reseller_wholesale', 'gateway_teleport', 'joint_development', 'production_localization', 'hosted_payload', 'own_satellite_constellation', 'research_partnership'))
);

CREATE TABLE space.program_organizations (
	import_id TEXT NOT NULL,
	program_id TEXT NOT NULL,
	org_id TEXT NOT NULL,
	role TEXT NOT NULL,
	claim_id TEXT,
	CONSTRAINT pk_program_organizations PRIMARY KEY (import_id, program_id, org_id, role),
	CONSTRAINT ck_program_organizations_role_enum CHECK (role IN ('operator', 'owner', 'prime_manufacturer', 'payload_supplier', 'bus_supplier', 'launch_provider', 'service_distributor', 'ground_segment', 'funding_agency', 'consortium_member', 'customer', 'terminal_supplier', 'investor'))
);

CREATE TABLE space.satcom_contract (
	contract_id TEXT NOT NULL,
	version TEXT NOT NULL,
	digest TEXT NOT NULL,
	managed_tables_json TEXT NOT NULL,
	CONSTRAINT pk_satcom_contract PRIMARY KEY (contract_id)
);

CREATE TABLE space.satcom_files (
	import_id TEXT NOT NULL,
	path TEXT NOT NULL,
	sha256 TEXT NOT NULL,
	size_bytes BIGINT NOT NULL,
	CONSTRAINT pk_satcom_files PRIMARY KEY (import_id, path)
);

CREATE TABLE space.satcom_imports (
	import_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	contract_digest TEXT NOT NULL,
	adapter_version TEXT NOT NULL,
	CONSTRAINT pk_satcom_imports PRIMARY KEY (import_id)
);

CREATE TABLE space.satcom_rows (
	import_id TEXT NOT NULL,
	table_name TEXT NOT NULL,
	row_number BIGINT NOT NULL,
	cells_json TEXT NOT NULL,
	CONSTRAINT pk_satcom_rows PRIMARY KEY (import_id, table_name, row_number)
);

CREATE TABLE space.search_coverage (
	import_id TEXT NOT NULL,
	coverage_id TEXT NOT NULL,
	category TEXT NOT NULL,
	region TEXT NOT NULL,
	sources_checked TEXT,
	entities_found BIGINT,
	open_gaps_uk TEXT,
	saturation TEXT,
	check_date DATE,
	CONSTRAINT pk_search_coverage PRIMARY KEY (import_id, coverage_id)
);

CREATE TABLE space.services_offerings (
	import_id TEXT NOT NULL,
	service_id TEXT NOT NULL,
	name TEXT NOT NULL,
	provider_org_id TEXT,
	program_id TEXT,
	service_type TEXT NOT NULL,
	channel TEXT,
	region_scope TEXT,
	ukraine_availability TEXT,
	dl_mbps_claimed NUMERIC(38, 18),
	ul_mbps_claimed NUMERIC(38, 18),
	latency_ms_claimed NUMERIC(38, 18),
	sla_note TEXT,
	terms_note TEXT,
	claim_id TEXT,
	notes TEXT,
	CONSTRAINT pk_services_offerings PRIMARY KEY (import_id, service_id),
	CONSTRAINT ck_services_offerings_service_type_enum CHECK (service_type IN ('retail_broadband', 'enterprise_broadband', 'managed_service', 'backup_resilience', 'wholesale_capacity', 'mobility_maritime', 'mobility_aviation', 'mobility_land', 'cellular_backhaul', 'iot_m2m', 'd2d_messaging', 'd2d_voice_data', 'mss_voice_data', 'ground_segment_as_a_service', 'gateway_hosting', 'teleport_services', 'spectrum_lease', 'hosted_payload', 'rideshare_launch', 'dedicated_launch', 'orbital_transfer', 'data_relay', 'government_satcom')),
	CONSTRAINT ck_services_offerings_ukraine_availability_enum CHECK (ukraine_availability IN ('available_documented', 'trial_or_limited', 'announced', 'not_available', 'unknown'))
);

CREATE TABLE space.sources (
	import_id TEXT NOT NULL,
	source_id TEXT NOT NULL,
	url TEXT NOT NULL,
	title TEXT,
	publisher TEXT,
	document_date TEXT,
	document_revision TEXT,
	document_type TEXT,
	language TEXT,
	access_date DATE,
	http_status BIGINT,
	content_kind TEXT,
	content_sha256 TEXT,
	verification_status TEXT NOT NULL,
	archive_url TEXT,
	notes TEXT,
	CONSTRAINT pk_sources PRIMARY KEY (import_id, source_id),
	CONSTRAINT ck_sources_document_date_precision CHECK (document_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'),
	CONSTRAINT ck_sources_document_type_enum CHECK (document_type IN ('orbital_catalog', 'datasheet', 'user_guide', 'regulatory_filing', 'financial_report', 'press_release', 'official_web_page', 'news_media', 'standard', 'research_paper', 'dealer_page', 'secondary_reference', 'user_document', 'government_document', 'contract_award')),
	CONSTRAINT ck_sources_verification_status_enum CHECK (verification_status IN ('quote_verified', 'value_found', 'partially_verified', 'fetch_blocked', 'unreachable', 'local_document', 'not_rechecked'))
);

CREATE TABLE space.spacecraft_models (
	import_id TEXT NOT NULL,
	spacecraft_model_id TEXT NOT NULL,
	program_id TEXT,
	name TEXT NOT NULL,
	generation TEXT,
	manufacturer_org_id TEXT,
	bus_platform TEXT,
	launch_mass_kg NUMERIC(38, 18),
	dry_mass_kg NUMERIC(38, 18),
	power_kw NUMERIC(38, 18),
	design_life_years NUMERIC(38, 18),
	payload_architecture TEXT,
	design_capacity_gbps NUMERIC(38, 18),
	isl_type TEXT,
	first_launch_date TEXT,
	norad_id BIGINT,
	cospar_id TEXT,
	orbital_position TEXT,
	notes TEXT,
	CONSTRAINT pk_spacecraft_models PRIMARY KEY (import_id, spacecraft_model_id),
	CONSTRAINT ck_spacecraft_models_first_launch_date_precision CHECK (first_launch_date ~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')
);

CREATE TABLE space.terminal_models (
	import_id TEXT NOT NULL,
	terminal_id TEXT NOT NULL,
	name TEXT NOT NULL,
	family TEXT,
	revision TEXT,
	manufacturer_org_id TEXT,
	primary_program_id TEXT,
	form_factor TEXT NOT NULL,
	service_class TEXT NOT NULL,
	antenna_type TEXT,
	multi_orbit BOOLEAN,
	aperture_w_mm NUMERIC(38, 18),
	aperture_h_mm NUMERIC(38, 18),
	depth_mm NUMERIC(38, 18),
	mass_antenna_kg NUMERIC(38, 18),
	mass_with_mount_kg NUMERIC(38, 18),
	mass_device_with_battery_kg NUMERIC(38, 18),
	mass_idu_kg NUMERIC(38, 18),
	mass_psu_kg NUMERIC(38, 18),
	mass_with_mount_cable_kg NUMERIC(38, 18),
	mass_installed_kg NUMERIC(38, 18),
	mass_packaged_kg NUMERIC(38, 18),
	mass_unspecified_kg NUMERIC(38, 18),
	mass_basis_note TEXT,
	power_idle_w NUMERIC(38, 18),
	power_typical_w NUMERIC(38, 18),
	power_avg_min_w NUMERIC(38, 18),
	power_avg_max_w NUMERIC(38, 18),
	power_peak_w NUMERIC(38, 18),
	dc_input_min_v NUMERIC(38, 18),
	dc_input_max_v NUMERIC(38, 18),
	dl_peak_mbps NUMERIC(38, 18),
	ul_peak_mbps NUMERIC(38, 18),
	speed_basis TEXT,
	eirp_dbw NUMERIC(38, 18),
	gt_dbk NUMERIC(38, 18),
	fov_deg NUMERIC(38, 18),
	min_elevation_deg NUMERIC(38, 18),
	ip_rating TEXT,
	temp_min_c NUMERIC(38, 18),
	temp_max_c NUMERIC(38, 18),
	interfaces TEXT,
	availability_status TEXT NOT NULL,
	availability_as_of DATE,
	notes TEXT,
	CONSTRAINT pk_terminal_models PRIMARY KEY (import_id, terminal_id),
	CONSTRAINT ck_terminal_models_form_factor_enum CHECK (form_factor IN ('fixed', 'portable', 'vehicle', 'maritime', 'aero', 'handheld', 'iot_module', 'manpack', 'flyaway', 'multi_use', 'smartphone')),
	CONSTRAINT ck_terminal_models_service_class_enum CHECK (service_class IN ('broadband_consumer', 'broadband_enterprise', 'broadband_mobility', 'mss_data', 'mss_voice', 'iot_m2m', 'd2d_smartphone', 'military_tactical')),
	CONSTRAINT ck_terminal_models_availability_status_enum CHECK (availability_status IN ('serial_commercial', 'limited_market', 'announced', 'experimental_prototype', 'legacy_supported', 'discontinued', 'unknown'))
);

ALTER TABLE space.aliases_crosswalk ADD CONSTRAINT fk_aliases_crosswalk_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.aliases_crosswalk ADD CONSTRAINT fk_aliases_crosswalk_import_id_entity_id FOREIGN KEY(import_id, entity_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.aliases_crosswalk ADD CONSTRAINT fk_aliases_crosswalk_import_id_source_id FOREIGN KEY(import_id, source_id) REFERENCES space.sources (import_id, source_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.aliases_crosswalk.alias_type IS 'former_name / brand / abbreviation / local_name / catalog_name / legacy_catalog_id / merger_predecessor';

ALTER TABLE space.classifications ADD CONSTRAINT fk_classifications_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.classifications ADD CONSTRAINT fk_classifications_import_id_parent_class_id FOREIGN KEY(import_id, parent_class_id) REFERENCES space.classifications (import_id, class_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.classifications.class_id IS U&'\0421\0442\0430\0431\0456\043b\044c\043d\0438\0439 \043a\043e\0434 \043a\043b\0430\0441\0443 (scheme:code)';

COMMENT ON COLUMN space.classifications.scheme IS U&'\0421\0445\0435\043c\0430 \043a\043b\0430\0441\0438\0444\0456\043a\0430\0446\0456\0457 (orbit_class, segment, band, ontology_entity, esa_gpt, nasa_tx, esa_tech, euspa, service_tag, opportunity_type, tech_category \0442\043e\0449\043e)';

COMMENT ON COLUMN space.classifications.code IS U&'\041a\043e\0434 \0443 \043c\0435\0436\0430\0445 \0441\0445\0435\043c\0438';

COMMENT ON COLUMN space.classifications.label_uk IS U&'\041d\0430\0437\0432\0430 \0443\043a\0440\0430\0457\043d\0441\044c\043a\043e\044e';

COMMENT ON COLUMN space.classifications.label_en IS U&'\041d\0430\0437\0432\0430 \0430\043d\0433\043b\0456\0439\0441\044c\043a\043e\044e';

COMMENT ON COLUMN space.classifications.parent_class_id IS U&'\0411\0430\0442\044c\043a\0456\0432\0441\044c\043a\0438\0439 \043a\043b\0430\0441';

COMMENT ON COLUMN space.classifications.definition_uk IS U&'\0412\0438\0437\043d\0430\0447\0435\043d\043d\044f';

COMMENT ON COLUMN space.classifications.origin IS U&'\041f\043e\0445\043e\0434\0436\0435\043d\043d\044f \043a\043e\0434\0443: input-\043e\043d\0442\043e\043b\043e\0433\0456\044f (\0444\0430\0439\043b/\0430\0440\043a\0443\0448/\0440\044f\0434\043e\043a) \0430\0431\043e \043a\0430\0442\0430\043b\043e\0433';

ALTER TABLE space.compatibility ADD CONSTRAINT fk_compatibility_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.compatibility ADD CONSTRAINT fk_compatibility_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.compatibility ADD CONSTRAINT fk_compatibility_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.compatibility ADD CONSTRAINT fk_compatibility_import_id_subject_id FOREIGN KEY(import_id, subject_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.compatibility.compatibility_id IS U&'ID (CMP-\2026)';

COMMENT ON COLUMN space.compatibility.subject_id IS U&'\0422\0435\0440\043c\0456\043d\0430\043b / \0442\0435\0445\043d\043e\043b\043e\0433\0456\044f / \0441\0435\0440\0432\0456\0441';

COMMENT ON COLUMN space.compatibility.program_id IS U&'\041c\0435\0440\0435\0436\0430';

COMMENT ON COLUMN space.compatibility.compatibility_type IS 'native / certified / announced / multi_network / via_partner';

COMMENT ON COLUMN space.compatibility.status IS 'active / announced / legacy';

ALTER TABLE space.constellations_programs ADD CONSTRAINT fk_constellations_programs_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.constellations_programs ADD CONSTRAINT fk_constellations_programs_import_id_country_iso2 FOREIGN KEY(import_id, country_iso2) REFERENCES space.countries (import_id, country_iso2) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.constellations_programs ADD CONSTRAINT fk_constellations_programs_import_id_operator_org_id FOREIGN KEY(import_id, operator_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.constellations_programs ADD CONSTRAINT fk_constellations_programs_import_id_owner_org_id FOREIGN KEY(import_id, owner_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.constellations_programs.program_id IS U&'ID \043f\0440\043e\0433\0440\0430\043c\0438 / \0444\043b\043e\0442\0443 / \0441\0435\0440\0432\0456\0441\043d\043e\0433\043e \0431\0440\0435\043d\0434\0443 (PRG-\2026)';

COMMENT ON COLUMN space.constellations_programs.name IS U&'\041d\0430\0437\0432\0430';

COMMENT ON COLUMN space.constellations_programs.entity_kind IS U&'\0422\0438\043f \0441\0443\0442\043d\043e\0441\0442\0456';

COMMENT ON COLUMN space.constellations_programs.orbit_class IS U&'\041e\0440\0431\0456\0442\0430\043b\044c\043d\0438\0439 \043a\043b\0430\0441';

COMMENT ON COLUMN space.constellations_programs.primary_segment IS U&'\041e\0441\043d\043e\0432\043d\0438\0439 \0441\0435\0433\043c\0435\043d\0442';

COMMENT ON COLUMN space.constellations_programs.lifecycle_status IS U&'\0421\0442\0430\043d \043d\0430 \0434\0430\0442\0443 status_as_of';

COMMENT ON COLUMN space.constellations_programs.status_as_of IS U&'\0414\0430\0442\0430, \043d\0430 \044f\043a\0443 \0432\0441\0442\0430\043d\043e\0432\043b\0435\043d\043e \0441\0442\0430\043d';

COMMENT ON COLUMN space.constellations_programs.operator_org_id IS U&'\041e\043f\0435\0440\0430\0442\043e\0440';

COMMENT ON COLUMN space.constellations_programs.owner_org_id IS U&'\0412\043b\0430\0441\043d\0438\043a (\044f\043a\0449\043e \0432\0456\0434\0440\0456\0437\043d\044f\0454\0442\044c\0441\044f)';

COMMENT ON COLUMN space.constellations_programs.country_iso2 IS U&'\041a\0440\0430\0457\043d\0430 \044e\0440\0438\0441\0434\0438\043a\0446\0456\0457 / \043b\0456\0446\0435\043d\0437\0443\0432\0430\043d\043d\044f';

COMMENT ON COLUMN space.constellations_programs.user_class IS 'commercial / government / military / mixed';

COMMENT ON COLUMN space.constellations_programs.coverage_scope IS U&'\0413\043b\043e\0431\0430\043b\044c\043d\0438\0439 / \0440\0435\0433\0456\043e\043d\0430\043b\044c\043d\0438\0439 / \043d\0430\0446\0456\043e\043d\0430\043b\044c\043d\0438\0439 / \043f\043e\043b\044f\0440\043d\0438\0439';

COMMENT ON COLUMN space.constellations_programs.planned_spacecraft_total IS U&'\0417\0430\044f\0432\043b\0435\043d\0430 / \043b\0456\0446\0435\043d\0437\043e\0432\0430\043d\0430 \0446\0456\043b\044c\043e\0432\0430 \043a\0456\043b\044c\043a\0456\0441\0442\044c \041a\0410 (\043a\0430\043d\043e\043d\0456\0447\043d\0435 \0442\0432\0435\0440\0434\0436\0435\043d\043d\044f) [\041a\0410]';

COMMENT ON COLUMN space.constellations_programs.first_launch_date IS U&'\041f\0435\0440\0448\0438\0439 \0437\0430\043f\0443\0441\043a \041a\0410 \043f\0440\043e\0433\0440\0430\043c\0438';

COMMENT ON COLUMN space.constellations_programs.service_start_date IS U&'\041f\043e\0447\0430\0442\043e\043a \043a\043e\043c\0435\0440\0446\0456\0439\043d\043e\0433\043e / \0448\0442\0430\0442\043d\043e\0433\043e \0441\0435\0440\0432\0456\0441\0443';

COMMENT ON COLUMN space.constellations_programs.altitude_km_nominal IS U&'\041d\043e\043c\0456\043d\0430\043b\044c\043d\0430 \0432\0438\0441\043e\0442\0430 \043e\0441\043d\043e\0432\043d\043e\0457 \043e\0431\043e\043b\043e\043d\043a\0438 [\043a\043c]';

COMMENT ON COLUMN space.constellations_programs.inclination_deg_nominal IS U&'\041d\043e\043c\0456\043d\0430\043b\044c\043d\0438\0439 \043d\0430\0445\0438\043b \043e\0441\043d\043e\0432\043d\043e\0457 \043e\0431\043e\043b\043e\043d\043a\0438 [\00b0]';

COMMENT ON COLUMN space.constellations_programs.isl_type IS U&'\041c\0456\0436\0441\0443\043f\0443\0442\043d\0438\043a\043e\0432\0456 \043b\0456\043d\0456\0457: none / RF / optical / unknown';

COMMENT ON COLUMN space.constellations_programs.ukraine_service_status IS U&'\0421\0442\0430\0442\0443\0441 \0441\0435\0440\0432\0456\0441\0443 \0432 \0423\043a\0440\0430\0457\043d\0456 \0437\0430 \0434\0436\0435\0440\0435\043b\0430\043c\0438';

COMMENT ON COLUMN space.constellations_programs.website_url IS U&'\041e\0444\0456\0446\0456\0439\043d\0430 \0441\0442\043e\0440\0456\043d\043a\0430';

COMMENT ON COLUMN space.constellations_programs.notes IS U&'\041f\043e\044f\0441\043d\0435\043d\043d\044f \043c\0435\0436 \0441\0443\0442\043d\043e\0441\0442\0456';

ALTER TABLE space.countries ADD CONSTRAINT fk_countries_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.countries.country_iso2 IS U&'\041a\043e\0434 ISO 3166-1 alpha-2; XX \2014 \043c\0456\0436\043d\0430\0440\043e\0434\043d\0430 / \0431\0430\0433\0430\0442\043e\043d\0430\0446\0456\043e\043d\0430\043b\044c\043d\0430 \043e\0440\0433\0430\043d\0456\0437\0430\0446\0456\044f, EU \2014 \0404\0421';

COMMENT ON COLUMN space.countries.name_uk IS U&'\041d\0430\0437\0432\0430 \0443\043a\0440\0430\0457\043d\0441\044c\043a\043e\044e';

COMMENT ON COLUMN space.countries.name_en IS U&'\041d\0430\0437\0432\0430 \0430\043d\0433\043b\0456\0439\0441\044c\043a\043e\044e';

COMMENT ON COLUMN space.countries.region IS U&'\041c\0430\043a\0440\043e\0440\0435\0433\0456\043e\043d \0434\043b\044f \0430\0433\0440\0435\0433\0430\0442\0456\0432';

COMMENT ON COLUMN space.countries.is_ukraine_neighbor IS U&'\0421\0443\0441\0456\0434\043d\044f \0437 \0423\043a\0440\0430\0457\043d\043e\044e \0434\0435\0440\0436\0430\0432\0430 (\0434\043b\044f \043e\0446\0456\043d\043a\0438 \0440\0438\043d\043a\043e\0432\043e\0433\043e \0434\043e\0441\0442\0443\043f\0443)';

ALTER TABLE space.deployment_observations ADD CONSTRAINT fk_deployment_observations_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.deployment_observations ADD CONSTRAINT fk_deployment_observations_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.deployment_observations ADD CONSTRAINT fk_deployment_observations_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.deployment_observations ADD CONSTRAINT fk_deployment_observations_import_id_spacecraft_model_id FOREIGN KEY(import_id, spacecraft_model_id) REFERENCES space.spacecraft_models (import_id, spacecraft_model_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.deployment_observations.observation_id IS U&'ID \0441\043f\043e\0441\0442\0435\0440\0435\0436\0435\043d\043d\044f (DEP-\2026)';

COMMENT ON COLUMN space.deployment_observations.status_metric IS U&'\0421\0442\0430\0442\0443\0441\043d\0430 \0432\0435\043b\0438\0447\0438\043d\0430 (\043d\0435 \043f\0456\0434\0441\0443\043c\043e\0432\0443\044e\0442\044c\0441\044f \043c\0456\0436 \0441\043e\0431\043e\044e)';

COMMENT ON COLUMN space.deployment_observations.count IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \041a\0410 [\041a\0410]';

COMMENT ON COLUMN space.deployment_observations.observation_date IS U&'\0414\0430\0442\0430 \0437\0440\0456\0437\0443';

COMMENT ON COLUMN space.deployment_observations.definition_uk IS U&'\0412\0438\0437\043d\0430\0447\0435\043d\043d\044f \043f\043e\043a\0430\0437\043d\0438\043a\0430 \0432 \0434\0436\0435\0440\0435\043b\0456';

COMMENT ON COLUMN space.deployment_observations.information_character IS U&'\0425\0430\0440\0430\043a\0442\0435\0440 \0456\043d\0444\043e\0440\043c\0430\0446\0456\0457';

ALTER TABLE space.enabling_devices_technologies ADD CONSTRAINT fk_enabling_devices_technologies_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.enabling_devices_technologies ADD CONSTRAINT fk_enabling_devices_technologies_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.enabling_devices_technologies ADD CONSTRAINT fk_enabling_devices_technologies_import_id_vendor_org_id FOREIGN KEY(import_id, vendor_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.enabling_devices_technologies.tech_id IS U&'ID (TEC-\2026)';

COMMENT ON COLUMN space.enabling_devices_technologies.category IS U&'\041a\0430\0442\0435\0433\043e\0440\0456\044f';

COMMENT ON COLUMN space.enabling_devices_technologies.vendor_org_id IS U&'\041f\043e\0441\0442\0430\0447\0430\043b\044c\043d\0438\043a (NULL \2014 \043a\043b\0430\0441 \0442\0435\0445\043d\043e\043b\043e\0433\0456\0457)';

COMMENT ON COLUMN space.enabling_devices_technologies.example_products IS U&'\041f\0440\0438\043a\043b\0430\0434\0438 \043f\0440\043e\0434\0443\043a\0442\0456\0432 / \0441\0442\0430\043d\0434\0430\0440\0442\0456\0432';

COMMENT ON COLUMN space.enabling_devices_technologies.function_uk IS U&'\0424\0443\043d\043a\0446\0456\044f';

COMMENT ON COLUMN space.enabling_devices_technologies.expected_effect_uk IS U&'\041e\0447\0456\043a\0443\0432\0430\043d\0438\0439 \0435\0444\0435\043a\0442';

COMMENT ON COLUMN space.enabling_devices_technologies.effect_evidence_type IS 'measured / vendor_claim / standard_spec / research_hypothesis';

COMMENT ON COLUMN space.enabling_devices_technologies.application_conditions_uk IS U&'\0423\043c\043e\0432\0438 \0437\0430\0441\0442\043e\0441\0443\0432\0430\043d\043d\044f';

COMMENT ON COLUMN space.enabling_devices_technologies.maturity IS U&'\0417\0440\0456\043b\0456\0441\0442\044c';

COMMENT ON COLUMN space.enabling_devices_technologies.compatibility_uk IS U&'\0421\0443\043c\0456\0441\043d\0456\0441\0442\044c';

COMMENT ON COLUMN space.enabling_devices_technologies.dependencies_uk IS U&'\0417\0430\043b\0435\0436\043d\043e\0441\0442\0456';

COMMENT ON COLUMN space.enabling_devices_technologies.customer_relevance_uk IS U&'\0417\043d\0430\0447\0435\043d\043d\044f \0434\043b\044f \0437\0430\043c\043e\0432\043d\0438\043a\0430';

ALTER TABLE space.entity_classifications ADD CONSTRAINT fk_entity_classifications_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.entity_classifications ADD CONSTRAINT fk_entity_classifications_import_id_class_id FOREIGN KEY(import_id, class_id) REFERENCES space.classifications (import_id, class_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.entity_classifications ADD CONSTRAINT fk_entity_classifications_import_id_entity_id FOREIGN KEY(import_id, entity_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.entity_classifications.basis IS U&'claim_id \0430\0431\043e analyst_mapping';

ALTER TABLE space.entity_registry ADD CONSTRAINT fk_entity_registry_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.entity_registry.entity_id IS U&'\0413\043b\043e\0431\0430\043b\044c\043d\043e \0443\043d\0456\043a\0430\043b\044c\043d\0438\0439 ID \0441\0443\0442\043d\043e\0441\0442\0456 \0431\0443\0434\044c-\044f\043a\043e\0457 \043f\0440\0435\0434\043c\0435\0442\043d\043e\0457 \0442\0430\0431\043b\0438\0446\0456';

COMMENT ON COLUMN space.entity_registry.entity_table IS U&'\0422\0430\0431\043b\0438\0446\044f, \0434\0435 \0432\0438\0437\043d\0430\0447\0435\043d\043e \0441\0443\0442\043d\0456\0441\0442\044c';

COMMENT ON COLUMN space.entity_registry.display_name IS U&'\041d\0430\0437\0432\0430 \0434\043b\044f \0432\0456\0434\043e\0431\0440\0430\0436\0435\043d\043d\044f';

ALTER TABLE space.evidence_claims ADD CONSTRAINT fk_evidence_claims_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.evidence_claims ADD CONSTRAINT fk_evidence_claims_import_id_entity_id FOREIGN KEY(import_id, entity_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.evidence_claims ADD CONSTRAINT fk_evidence_claims_import_id_source_id FOREIGN KEY(import_id, source_id) REFERENCES space.sources (import_id, source_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.evidence_claims.claim_id IS U&'\0421\0442\0430\0431\0456\043b\044c\043d\0438\0439 ID (CLM-\2026; \0445\0435\0448 entity/field/source/value)';

COMMENT ON COLUMN space.evidence_claims.field_key IS U&'\041a\043b\044e\0447 \043f\043e\043b\044f (\0434\0438\0432. field_dictionary)';

COMMENT ON COLUMN space.evidence_claims.raw_value IS U&'\0417\043d\0430\0447\0435\043d\043d\044f \044f\043a \0443 \0434\0436\0435\0440\0435\043b\0456';

COMMENT ON COLUMN space.evidence_claims.value_num IS U&'\041d\043e\0440\043c\0430\043b\0456\0437\043e\0432\0430\043d\0435 \0447\0438\0441\043b\043e';

COMMENT ON COLUMN space.evidence_claims.value_text IS U&'\041d\043e\0440\043c\0430\043b\0456\0437\043e\0432\0430\043d\0435 \0442\0435\043a\0441\0442\043e\0432\0435 / \043a\043b\0430\0441\043e\0432\0435 \0437\043d\0430\0447\0435\043d\043d\044f';

COMMENT ON COLUMN space.evidence_claims.unit IS U&'\041e\0434\0438\043d\0438\0446\044f \043d\043e\0440\043c\0430\043b\0456\0437\043e\0432\0430\043d\043e\0433\043e \0437\043d\0430\0447\0435\043d\043d\044f';

COMMENT ON COLUMN space.evidence_claims.qualifier IS U&'\041a\0432\0430\043b\0456\0444\0456\043a\0430\0442\043e\0440';

COMMENT ON COLUMN space.evidence_claims.fact_date IS U&'\0414\0430\0442\0430 \0444\0430\043a\0442\0443';

COMMENT ON COLUMN space.evidence_claims.locator IS U&'\0421\0442\043e\0440\0456\043d\043a\0430 / \0442\0430\0431\043b\0438\0446\044f / \0440\043e\0437\0434\0456\043b';

COMMENT ON COLUMN space.evidence_claims.quote IS U&'\0414\043e\0441\043b\0456\0432\043d\0438\0439 \0444\0440\0430\0433\043c\0435\043d\0442 \0434\0436\0435\0440\0435\043b\0430';

COMMENT ON COLUMN space.evidence_claims.information_character IS U&'\0425\0430\0440\0430\043a\0442\0435\0440 \0456\043d\0444\043e\0440\043c\0430\0446\0456\0457';

COMMENT ON COLUMN space.evidence_claims.comment IS U&'\041e\0431\043c\0435\0436\0435\043d\043d\044f';

COMMENT ON COLUMN space.evidence_claims.contradiction_group IS U&'\0413\0440\0443\043f\0430 \0430\043b\044c\0442\0435\0440\043d\0430\0442\0438\0432\043d\0438\0445 \0442\0432\0435\0440\0434\0436\0435\043d\044c \0442\043e\0433\043e \0436 \043f\043e\043b\044f';

COMMENT ON COLUMN space.evidence_claims.is_canonical IS U&'\041a\0430\043d\043e\043d\0456\0447\043d\0435 \0437\043d\0430\0447\0435\043d\043d\044f \043f\043e\043b\044f';

COMMENT ON COLUMN space.evidence_claims.selection_rule IS U&'\041f\0440\0430\0432\0438\043b\043e \0432\0438\0431\043e\0440\0443 \043a\0430\043d\043e\043d\0456\0447\043d\043e\0433\043e \0437\043d\0430\0447\0435\043d\043d\044f';

COMMENT ON COLUMN space.evidence_claims.formula IS U&'\0424\043e\0440\043c\0443\043b\0430 \0434\043b\044f \0440\043e\0437\0440\0430\0445\0443\043d\043a\0443';

COMMENT ON COLUMN space.evidence_claims.input_claim_ids IS U&'\0412\0445\0456\0434\043d\0456 claim_id \0440\043e\0437\0440\0430\0445\0443\043d\043a\0443 (\0447\0435\0440\0435\0437 '';'')';

COMMENT ON COLUMN space.evidence_claims.verification_status IS 'quote_verified / value_found / token_found / fetch_blocked / unreachable / not_rechecked / calculated';

COMMENT ON COLUMN space.evidence_claims.origin IS U&'\041f\043e\0445\043e\0434\0436\0435\043d\043d\044f \0437\0430\043f\0438\0441\0443: catalog_research / prior_catalog_import / orbital_catalog_parser';

ALTER TABLE space.field_dictionary ADD CONSTRAINT fk_field_dictionary_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.field_dictionary.entity_table IS U&'\0422\0430\0431\043b\0438\0446\044f, \0434\043e \044f\043a\043e\0457 \043d\0430\043b\0435\0436\0438\0442\044c \043f\043e\043b\0435';

COMMENT ON COLUMN space.field_dictionary.field_group IS U&'\0413\0440\0443\043f\0430 \0434\043b\044f \0437\0430\043f\043e\0432\043d\0435\043d\043e\0441\0442\0456';

COMMENT ON COLUMN space.field_dictionary.applies_to IS U&'\041f\0440\0430\0432\0438\043b\043e \0437\0430\0441\0442\043e\0441\043e\0432\043d\043e\0441\0442\0456';

ALTER TABLE space.financial_observations ADD CONSTRAINT fk_financial_observations_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.financial_observations ADD CONSTRAINT fk_financial_observations_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.financial_observations ADD CONSTRAINT fk_financial_observations_import_id_counterparty_org_id FOREIGN KEY(import_id, counterparty_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.financial_observations ADD CONSTRAINT fk_financial_observations_import_id_entity_id FOREIGN KEY(import_id, entity_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.financial_observations ADD CONSTRAINT fk_financial_observations_import_id_fx_id FOREIGN KEY(import_id, fx_id) REFERENCES space.fx_rates (import_id, fx_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.financial_observations.fin_id IS U&'ID (FIN-\2026)';

COMMENT ON COLUMN space.financial_observations.entity_id IS U&'\0421\0443\0442\043d\0456\0441\0442\044c (\043e\0440\0433\0430\043d\0456\0437\0430\0446\0456\044f, \043f\0440\043e\0433\0440\0430\043c\0430, \0441\0435\0440\0432\0456\0441, \0442\0435\0440\043c\0456\043d\0430\043b, \043d\043e\0441\0456\0439)';

COMMENT ON COLUMN space.financial_observations.basis IS U&'\0424\0456\043d\0430\043d\0441\043e\0432\0430 \0431\0430\0437\0430 (\043d\0435 \0437\043c\0456\0448\0443\044e\0442\044c\0441\044f \0432 \0440\0435\0439\0442\0438\043d\0433\0430\0445)';

COMMENT ON COLUMN space.financial_observations.comparison_group IS U&'A \2014 \0437\0430\043b\0443\0447\0435\043d\0438\0439 \043a\0430\043f\0456\0442\0430\043b; B \2014 \043a\043e\043d\0442\0440\0430\043a\0442\043d\043e \0437\043e\0431\043e\0432''\044f\0437\0430\043d\0435 \0444\0456\043d\0430\043d\0441\0443\0432\0430\043d\043d\044f (\043a\0440\0435\0434\0438\0442\043d\0456 \043b\0456\043d\0456\0457, \0433\0440\0430\043d\0442\0438, \0437\043e\0431\043e\0432''\044f\0437\0430\043d\043d\044f \0430\043a\0446\0456\043e\043d\0435\0440\0456\0432); C \2014 \0431\044e\0434\0436\0435\0442 / \0432\0430\0440\0442\0456\0441\0442\044c \043f\0440\043e\0433\0440\0430\043c\0438; D \2014 \0432\0438\0442\0440\0430\0442\0438 \0433\0440\0443\043f\0438 (CAPEX); K \2014 \0432\0430\0440\0442\0456\0441\0442\044c \043a\043e\043d\0442\0440\0430\043a\0442\0443 \0437\0430\043c\043e\0432\043b\0435\043d\043d\044f (\0437\0430\043a\0443\043f\0456\0432\043b\044f \041a\0410/\043f\043e\0441\043b\0443\0433); M \2014 \043e\0446\0456\043d\043a\0430 \0443\0433\043e\0434\0438 M&A; P \2014 \0446\0456\043d\0438';

COMMENT ON COLUMN space.financial_observations.amount IS U&'\0421\0443\043c\0430 \0443 \0432\0430\043b\044e\0442\0456 \0434\0436\0435\0440\0435\043b\0430';

COMMENT ON COLUMN space.financial_observations.currency IS 'ISO 4217';

COMMENT ON COLUMN space.financial_observations.amount_usd_nominal IS U&'\041d\043e\043c\0456\043d\0430\043b\044c\043d\0430 \043a\043e\043d\0432\0435\0440\0442\0430\0446\0456\044f (\0444\043e\0440\043c\0443\043b\0430: amount \00d7 fx_rates.usd_per_unit) [USD]';

COMMENT ON COLUMN space.financial_observations.fact_date IS U&'\0414\0430\0442\0430 \0444\0430\043a\0442\0443 / \043e\0433\043e\043b\043e\0448\0435\043d\043d\044f';

COMMENT ON COLUMN space.financial_observations.counterparty_org_id IS U&'\041a\0440\0435\0434\0438\0442\043e\0440 / \0456\043d\0432\0435\0441\0442\043e\0440 / \0437\0430\043c\043e\0432\043d\0438\043a';

COMMENT ON COLUMN space.financial_observations.price_region IS U&'\0420\0435\0433\0456\043e\043d \0446\0456\043d\0438';

COMMENT ON COLUMN space.financial_observations.package_scope IS U&'\041a\043e\043c\043f\043b\0435\043a\0442\0430\0446\0456\044f / \043f\043e\0434\0430\0442\043a\0438 / \043f\0435\0440\0456\043e\0434';

ALTER TABLE space.fx_rates ADD CONSTRAINT fk_fx_rates_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.fx_rates ADD CONSTRAINT fk_fx_rates_import_id_source_id FOREIGN KEY(import_id, source_id) REFERENCES space.sources (import_id, source_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.fx_rates.currency IS 'ISO 4217';

COMMENT ON COLUMN space.fx_rates.usd_per_unit IS U&'USD \0437\0430 1 \043e\0434\0438\043d\0438\0446\044e \0432\0430\043b\044e\0442\0438';

ALTER TABLE space.ground_infrastructure ADD CONSTRAINT fk_ground_infrastructure_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.ground_infrastructure ADD CONSTRAINT fk_ground_infrastructure_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.ground_infrastructure ADD CONSTRAINT fk_ground_infrastructure_import_id_country_iso2 FOREIGN KEY(import_id, country_iso2) REFERENCES space.countries (import_id, country_iso2) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.ground_infrastructure ADD CONSTRAINT fk_ground_infrastructure_import_id_operator_org_id FOREIGN KEY(import_id, operator_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.ground_infrastructure ADD CONSTRAINT fk_ground_infrastructure_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.ground_infrastructure.ground_id IS U&'ID (GND-\2026)';

COMMENT ON COLUMN space.ground_infrastructure.infra_type IS U&'\0422\0438\043f';

COMMENT ON COLUMN space.ground_infrastructure.location_text IS U&'\0420\043e\0437\0442\0430\0448\0443\0432\0430\043d\043d\044f \044f\043a \0443 \0434\0436\0435\0440\0435\043b\0456';

COMMENT ON COLUMN space.ground_infrastructure.sites_count IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \043c\0430\0439\0434\0430\043d\0447\0438\043a\0456\0432 / \0430\043d\0442\0435\043d (\0434\043b\044f \043c\0435\0440\0435\0436)';

COMMENT ON COLUMN space.ground_infrastructure.bands_text IS U&'\0414\0456\0430\043f\0430\0437\043e\043d\0438';

COMMENT ON COLUMN space.ground_infrastructure.status IS 'operational / planned / construction / retired';

ALTER TABLE space.launch_configurations ADD CONSTRAINT fk_launch_configurations_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_configurations ADD CONSTRAINT fk_launch_configurations_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_configurations ADD CONSTRAINT fk_launch_configurations_import_id_lv_id FOREIGN KEY(import_id, lv_id) REFERENCES space.launch_vehicles (import_id, lv_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.launch_configurations.config_id IS U&'ID \043a\043e\043d\0444\0456\0433\0443\0440\0430\0446\0456\0457 (LVC-\2026)';

COMMENT ON COLUMN space.launch_configurations.config_name IS U&'\041d\0430\0437\0432\0430 \043a\043e\043d\0444\0456\0433\0443\0440\0430\0446\0456\0457 (\043a\0456\043b\044c\043a\0456\0441\0442\044c \043f\0440\0438\0441\043a\043e\0440\044e\0432\0430\0447\0456\0432, \0440\0435\0436\0438\043c \043f\043e\0432\0435\0440\043d\0435\043d\043d\044f)';

COMMENT ON COLUMN space.launch_configurations.recovery_mode IS 'expendable / droneship / rtls / partial / n/a';

COMMENT ON COLUMN space.launch_configurations.orbit_type IS 'LEO / SSO / GTO / GEO / MEO / TLI / TMI';

COMMENT ON COLUMN space.launch_configurations.altitude_km IS U&'\0412\0438\0441\043e\0442\0430 \043e\043f\043e\0440\043d\043e\0457 \043e\0440\0431\0456\0442\0438 (\0430\0431\043e \043f\0435\0440\0438\0433\0435\0439) [\043a\043c]';

COMMENT ON COLUMN space.launch_configurations.payload_kg IS U&'\0412\0430\043d\0442\0430\0436\043d\0456\0441\0442\044c \043d\0430 \0432\043a\0430\0437\0430\043d\0443 \043e\0440\0431\0456\0442\0443 [\043a\0433]';

COMMENT ON COLUMN space.launch_configurations.qualifier IS 'exact / approx / max / min';

COMMENT ON COLUMN space.launch_configurations.notes IS U&'\0423\043c\043e\0432\0438';

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id_customer_org_id FOREIGN KEY(import_id, customer_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id_lv_id FOREIGN KEY(import_id, lv_id) REFERENCES space.launch_vehicles (import_id, lv_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_events_contracts ADD CONSTRAINT fk_launch_events_contracts_import_id_provider_org_id FOREIGN KEY(import_id, provider_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.launch_events_contracts.event_id IS U&'ID (LEC-\2026)';

COMMENT ON COLUMN space.launch_events_contracts.event_type IS 'contract / launch / option / rideshare_booking / milestone';

COMMENT ON COLUMN space.launch_events_contracts.announced_date IS U&'\0414\0430\0442\0430 \043e\0433\043e\043b\043e\0448\0435\043d\043d\044f / \043f\0456\0434\043f\0438\0441\0430\043d\043d\044f';

COMMENT ON COLUMN space.launch_events_contracts.event_date IS U&'\0414\0430\0442\0430 \043f\043e\0434\0456\0457 (\0434\043b\044f \043f\0443\0441\043a\0443)';

COMMENT ON COLUMN space.launch_events_contracts.window_start IS U&'\041f\043e\0447\0430\0442\043e\043a \043a\043e\043d\0442\0440\0430\043a\0442\043d\043e\0433\043e \0432\0456\043a\043d\0430';

COMMENT ON COLUMN space.launch_events_contracts.window_end IS U&'\041a\0456\043d\0435\0446\044c \043a\043e\043d\0442\0440\0430\043a\0442\043d\043e\0433\043e \0432\0456\043a\043d\0430';

COMMENT ON COLUMN space.launch_events_contracts.launches_count IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \043f\0443\0441\043a\0456\0432 \0443 \043a\043e\043d\0442\0440\0430\043a\0442\0456 / \043f\043e\0434\0456\0457';

COMMENT ON COLUMN space.launch_events_contracts.spacecraft_count IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \041a\0410';

COMMENT ON COLUMN space.launch_events_contracts.status IS 'contracted / completed / in_progress / cancelled / option_unexercised';

COMMENT ON COLUMN space.launch_events_contracts.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.launch_vehicles ADD CONSTRAINT fk_launch_vehicles_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_vehicles ADD CONSTRAINT fk_launch_vehicles_import_id_country_iso2 FOREIGN KEY(import_id, country_iso2) REFERENCES space.countries (import_id, country_iso2) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.launch_vehicles ADD CONSTRAINT fk_launch_vehicles_import_id_provider_org_id FOREIGN KEY(import_id, provider_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.launch_vehicles.lv_id IS U&'ID \043d\043e\0441\0456\044f (LV-\2026)';

COMMENT ON COLUMN space.launch_vehicles.name IS U&'\041d\0430\0437\0432\0430';

COMMENT ON COLUMN space.launch_vehicles.family IS U&'\0421\0456\043c\0435\0439\0441\0442\0432\043e';

COMMENT ON COLUMN space.launch_vehicles.provider_org_id IS U&'\041f\0440\043e\0432\0430\0439\0434\0435\0440 \043f\0443\0441\043a\0443';

COMMENT ON COLUMN space.launch_vehicles.status IS U&'\0421\0442\0430\043d';

COMMENT ON COLUMN space.launch_vehicles.first_flight_date IS U&'\041f\0435\0440\0448\0438\0439 \043f\043e\043b\0456\0442';

COMMENT ON COLUMN space.launch_vehicles.stages IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \0441\0442\0443\043f\0435\043d\0456\0432';

COMMENT ON COLUMN space.launch_vehicles.reusability IS 'none / first_stage_recovery / full_reuse_planned / booster_recovery / unknown';

COMMENT ON COLUMN space.launch_vehicles.fairing_diameter_m IS U&'\0417\043e\0432\043d\0456\0448\043d\0456\0439 \0434\0456\0430\043c\0435\0442\0440 \0441\0442\0430\043d\0434\0430\0440\0442\043d\043e\0433\043e \043e\0431\0442\0456\0447\043d\0438\043a\0430 [\043c]';

COMMENT ON COLUMN space.launch_vehicles.fairing_height_m IS U&'\0412\0438\0441\043e\0442\0430 \0441\0442\0430\043d\0434\0430\0440\0442\043d\043e\0433\043e \043e\0431\0442\0456\0447\043d\0438\043a\0430 [\043c]';

COMMENT ON COLUMN space.launch_vehicles.flights_total IS U&'\041a\0456\043b\044c\043a\0456\0441\0442\044c \0437\0430\043f\0443\0441\043a\0456\0432 \043d\0430 \0434\0430\0442\0443 flights_as_of';

COMMENT ON COLUMN space.launch_vehicles.flights_successful IS U&'\0423\0441\043f\0456\0448\043d\0456 \0437\0430\043f\0443\0441\043a\0438';

COMMENT ON COLUMN space.launch_vehicles.flights_as_of IS U&'\0414\0430\0442\0430 \043b\0456\0447\0438\043b\044c\043d\0438\043a\0430';

COMMENT ON COLUMN space.launch_vehicles.export_access_note IS U&'\041e\0431\043c\0435\0436\0435\043d\043d\044f \0434\043e\0441\0442\0443\043f\0443 (\0441\0430\043d\043a\0446\0456\0457, \043b\0438\0448\0435 \0443\0440\044f\0434\043e\0432\0456 \0437\0430\043c\043e\0432\043d\0438\043a\0438 \0442\043e\0449\043e)';

COMMENT ON COLUMN space.launch_vehicles.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.opportunity_evidence ADD CONSTRAINT fk_opportunity_evidence_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.opportunity_evidence ADD CONSTRAINT fk_opportunity_evidence_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.opportunity_evidence ADD CONSTRAINT fk_opportunity_evidence_import_id_opportunity_id FOREIGN KEY(import_id, opportunity_id) REFERENCES space.partnerships_opportunities (import_id, opportunity_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organization_relationships ADD CONSTRAINT fk_organization_relationships_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organization_relationships ADD CONSTRAINT fk_organization_relationships_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organization_relationships ADD CONSTRAINT fk_organization_relationships_import_id_from_org_id FOREIGN KEY(import_id, from_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organization_relationships ADD CONSTRAINT fk_organization_relationships_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organization_relationships ADD CONSTRAINT fk_organization_relationships_import_id_to_org_id FOREIGN KEY(import_id, to_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.organization_relationships.relationship_id IS U&'ID \0437\0432''\044f\0437\043a\0443 (REL-\2026)';

COMMENT ON COLUMN space.organization_relationships.from_org_id IS U&'\0421\0443\0431''\0454\043a\0442 \0437\0432''\044f\0437\043a\0443';

COMMENT ON COLUMN space.organization_relationships.to_org_id IS U&'\041e\0431''\0454\043a\0442 \0437\0432''\044f\0437\043a\0443';

COMMENT ON COLUMN space.organization_relationships.relationship_type IS U&'\0422\0438\043f \0437\0432''\044f\0437\043a\0443';

COMMENT ON COLUMN space.organization_relationships.share_pct IS U&'\0427\0430\0441\0442\043a\0430 \0443\0447\0430\0441\0442\0456, \044f\043a\0449\043e \0440\043e\0437\043a\0440\0438\0442\0430 [%%]';

COMMENT ON COLUMN space.organization_relationships.start_date IS U&'\041f\043e\0447\0430\0442\043e\043a \0434\0456\0457';

COMMENT ON COLUMN space.organization_relationships.end_date IS U&'\0417\0430\0432\0435\0440\0448\0435\043d\043d\044f \0434\0456\0457';

COMMENT ON COLUMN space.organization_relationships.program_id IS U&'\041f\0440\043e\0433\0440\0430\043c\0430, \044f\043a\043e\0457 \0441\0442\043e\0441\0443\0454\0442\044c\0441\044f \0437\0432''\044f\0437\043e\043a';

COMMENT ON COLUMN space.organization_relationships.claim_id IS U&'\0414\043e\043a\0430\0437';

COMMENT ON COLUMN space.organization_relationships.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.organizations ADD CONSTRAINT fk_organizations_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organizations ADD CONSTRAINT fk_organizations_import_id_country_iso2 FOREIGN KEY(import_id, country_iso2) REFERENCES space.countries (import_id, country_iso2) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.organizations ADD CONSTRAINT fk_organizations_import_id_parent_org_id FOREIGN KEY(import_id, parent_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.organizations.org_id IS U&'ID \043e\0440\0433\0430\043d\0456\0437\0430\0446\0456\0457 (ORG-\2026)';

COMMENT ON COLUMN space.organizations.name IS U&'\041f\043e\0448\0438\0440\0435\043d\0430 \043d\0430\0437\0432\0430';

COMMENT ON COLUMN space.organizations.legal_name IS U&'\042e\0440\0438\0434\0438\0447\043d\0430 \043d\0430\0437\0432\0430 (\044f\043a\0449\043e \0432\0441\0442\0430\043d\043e\0432\043b\0435\043d\0430)';

COMMENT ON COLUMN space.organizations.country_iso2 IS U&'\041a\0440\0430\0457\043d\0430 \0456\043d\043a\043e\0440\043f\043e\0440\0430\0446\0456\0457 / \0448\0442\0430\0431-\043a\0432\0430\0440\0442\0438\0440\0438';

COMMENT ON COLUMN space.organizations.org_type IS U&'\041e\0441\043d\043e\0432\043d\0430 \0440\043e\043b\044c';

COMMENT ON COLUMN space.organizations.ownership_type IS U&'\0422\0438\043f \0432\043b\0430\0441\043d\043e\0441\0442\0456';

COMMENT ON COLUMN space.organizations.parent_org_id IS U&'\041c\0430\0442\0435\0440\0438\043d\0441\044c\043a\0430 \043e\0440\0433\0430\043d\0456\0437\0430\0446\0456\044f (\044f\043a\0449\043e \0432\0441\0442\0430\043d\043e\0432\043b\0435\043d\0430 \0434\0436\0435\0440\0435\043b\043e\043c)';

COMMENT ON COLUMN space.organizations.status IS 'active / merged / acquired / defunct / renamed';

COMMENT ON COLUMN space.organizations.website_url IS U&'\041e\0444\0456\0446\0456\0439\043d\0438\0439 \0441\0430\0439\0442 (\0456\0434\0435\043d\0442\0438\0444\0456\043a\0430\0446\0456\044f, \043d\0435 \0434\043e\043a\0430\0437 \0447\0438\0441\043b\043e\0432\0438\0445 \043f\0430\0440\0430\043c\0435\0442\0440\0456\0432)';

COMMENT ON COLUMN space.organizations.public_contact_channel IS U&'\041f\0443\0431\043b\0456\0447\043d\0438\0439 \043a\0430\043d\0430\043b \043a\043e\043d\0442\0430\043a\0442\0443 \0434\043b\044f \043f\0430\0440\0442\043d\0435\0440\0441\0442\0432\0430 / \0437\0430\043a\0443\043f\0456\0432\043b\0456 (URL \0441\0442\043e\0440\0456\043d\043a\0438)';

COMMENT ON COLUMN space.organizations.competencies IS U&'\041a\043b\044e\0447\043e\0432\0456 \0442\0435\0445\043d\043e\043b\043e\0433\0456\0447\043d\0456 \043a\043e\043c\043f\0435\0442\0435\043d\0446\0456\0457 (\043a\043e\0440\043e\0442\043a\043e)';

COMMENT ON COLUMN space.organizations.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.parameter_gaps ADD CONSTRAINT fk_parameter_gaps_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.parameter_gaps ADD CONSTRAINT fk_parameter_gaps_import_id_entity_id FOREIGN KEY(import_id, entity_id) REFERENCES space.entity_registry (import_id, entity_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.parameter_gaps.null_reason IS 'not_found / not_disclosed / requires_vendor_quote / cannot_verify / not_applicable';

COMMENT ON COLUMN space.parameter_gaps.decision_impact IS 'high / medium / low';

COMMENT ON COLUMN space.parameter_gaps.next_step_uk IS U&'\0429\043e \0437\0430\043f\0438\0442\0430\0442\0438 / \0434\0435 \0448\0443\043a\0430\0442\0438';

ALTER TABLE space.partnerships_opportunities ADD CONSTRAINT fk_partnerships_opportunities_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.partnerships_opportunities ADD CONSTRAINT fk_partnerships_opportunities_import_id_basis_claim_id FOREIGN KEY(import_id, basis_claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.partnerships_opportunities ADD CONSTRAINT fk_partnerships_opportunities_import_id_counterparty_org_id FOREIGN KEY(import_id, counterparty_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.partnerships_opportunities ADD CONSTRAINT fk_partnerships_opportunities_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.partnerships_opportunities.opportunity_id IS U&'ID (OPP-\2026)';

COMMENT ON COLUMN space.partnerships_opportunities.opportunity_type IS U&'\0422\0438\043f \043c\043e\0436\043b\0438\0432\043e\0441\0442\0456';

COMMENT ON COLUMN space.partnerships_opportunities.title_uk IS U&'\041a\043e\0440\043e\0442\043a\0430 \043d\0430\0437\0432\0430';

COMMENT ON COLUMN space.partnerships_opportunities.factual_basis_uk IS U&'\0424\0430\043a\0442\0438\0447\043d\0430 \043f\0456\0434\0441\0442\0430\0432\0430 (\0437 \0434\0436\0435\0440\0435\043b\043e\043c)';

COMMENT ON COLUMN space.partnerships_opportunities.required_competencies_uk IS U&'\041d\0435\043e\0431\0445\0456\0434\043d\0456 \043a\043e\043c\043f\0435\0442\0435\043d\0446\0456\0457 \0437\0430\043c\043e\0432\043d\0438\043a\0430';

COMMENT ON COLUMN space.partnerships_opportunities.dependencies_uk IS U&'\0417\0430\043b\0435\0436\043d\043e\0441\0442\0456 / \0440\0438\0437\0438\043a\0438';

COMMENT ON COLUMN space.partnerships_opportunities.open_questions_uk IS U&'\0412\0456\0434\043a\0440\0438\0442\0456 \043f\0438\0442\0430\043d\043d\044f \0434\043e \043f\043e\0441\0442\0430\0447\0430\043b\044c\043d\0438\043a\0430';

COMMENT ON COLUMN space.partnerships_opportunities.analyst_assumption_uk IS U&'\041f\0440\0438\043f\0443\0449\0435\043d\043d\044f \0430\043d\0430\043b\0456\0442\0438\043a\0430 (\043e\043a\0440\0435\043c\043e \0432\0456\0434 \0444\0430\043a\0442\0456\0432)';

COMMENT ON COLUMN space.partnerships_opportunities.readiness IS 'available_now / requires_negotiation / emerging / watchlist';

COMMENT ON COLUMN space.partnerships_opportunities.ukraine_access_note IS U&'\0420\0435\0433\0443\043b\044f\0442\043e\0440\043d\0456 \0439 \0435\043a\0441\043f\043e\0440\0442\043d\0456 \0443\043c\043e\0432\0438 \0434\043b\044f \0423\043a\0440\0430\0457\043d\0438';

COMMENT ON COLUMN space.partnerships_opportunities.basis_claim_id IS U&'\041e\0441\043d\043e\0432\043d\0435 \0442\0432\0435\0440\0434\0436\0435\043d\043d\044f-\043f\0456\0434\0441\0442\0430\0432\0430';

ALTER TABLE space.program_organizations ADD CONSTRAINT fk_program_organizations_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.program_organizations ADD CONSTRAINT fk_program_organizations_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.program_organizations ADD CONSTRAINT fk_program_organizations_import_id_org_id FOREIGN KEY(import_id, org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.program_organizations ADD CONSTRAINT fk_program_organizations_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.program_organizations.role IS U&'\0420\043e\043b\044c';

COMMENT ON COLUMN space.program_organizations.claim_id IS U&'\0414\043e\043a\0430\0437';

ALTER TABLE space.satcom_files ADD CONSTRAINT fk_satcom_files_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.satcom_rows ADD CONSTRAINT fk_satcom_rows_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.search_coverage ADD CONSTRAINT fk_search_coverage_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.search_coverage.sources_checked IS U&'\041f\0435\0440\0435\0432\0456\0440\0435\043d\0456 \043f\0440\043e\0444\0456\043b\044c\043d\0456 \0434\0436\0435\0440\0435\043b\0430';

COMMENT ON COLUMN space.search_coverage.saturation IS 'saturated / continuing_yield / not_started';

ALTER TABLE space.services_offerings ADD CONSTRAINT fk_services_offerings_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.services_offerings ADD CONSTRAINT fk_services_offerings_import_id_claim_id FOREIGN KEY(import_id, claim_id) REFERENCES space.evidence_claims (import_id, claim_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.services_offerings ADD CONSTRAINT fk_services_offerings_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.services_offerings ADD CONSTRAINT fk_services_offerings_import_id_provider_org_id FOREIGN KEY(import_id, provider_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.services_offerings.service_id IS U&'ID (SVC-\2026)';

COMMENT ON COLUMN space.services_offerings.name IS U&'\041d\0430\0437\0432\0430 \0441\0435\0440\0432\0456\0441\0443 / \0442\0430\0440\0438\0444\043d\043e\0457 \043b\0456\043d\0456\0439\043a\0438';

COMMENT ON COLUMN space.services_offerings.provider_org_id IS U&'\041f\043e\0441\0442\0430\0447\0430\043b\044c\043d\0438\043a';

COMMENT ON COLUMN space.services_offerings.program_id IS U&'\041c\0435\0440\0435\0436\0430';

COMMENT ON COLUMN space.services_offerings.service_type IS U&'\0422\0438\043f \0441\0435\0440\0432\0456\0441\0443';

COMMENT ON COLUMN space.services_offerings.channel IS 'direct / reseller / wholesale / partner / government';

COMMENT ON COLUMN space.services_offerings.region_scope IS U&'\0413\0435\043e\0433\0440\0430\0444\0456\044f \043f\0440\043e\043f\043e\0437\0438\0446\0456\0457';

COMMENT ON COLUMN space.services_offerings.ukraine_availability IS U&'\0414\043e\0441\0442\0443\043f\043d\0456\0441\0442\044c \0432 \0423\043a\0440\0430\0457\043d\0456 \0437\0430 \0434\0436\0435\0440\0435\043b\0430\043c\0438';

COMMENT ON COLUMN space.services_offerings.dl_mbps_claimed IS U&'\0417\0430\044f\0432\043b\0435\043d\0430 \0448\0432\0438\0434\043a\0456\0441\0442\044c DL (\043d\0435 \0433\0430\0440\0430\043d\0442\0456\044f) [\041c\0431\0456\0442/\0441]';

COMMENT ON COLUMN space.services_offerings.sla_note IS U&'CIR / SLA / \043f\0440\0456\043e\0440\0438\0442\0435\0442 \2014 \044f\043a \0441\0444\043e\0440\043c\0443\043b\044c\043e\0432\0430\043d\043e \0434\0436\0435\0440\0435\043b\043e\043c';

COMMENT ON COLUMN space.services_offerings.terms_note IS U&'\041e\0431\043c\0435\0436\0435\043d\043d\044f \0442\0440\0430\0444\0456\043a\0443, \043c\043e\0431\0456\043b\044c\043d\0456\0441\0442\044c, \0443\043c\043e\0432\0438';

COMMENT ON COLUMN space.services_offerings.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.sources ADD CONSTRAINT fk_sources_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.sources.source_id IS U&'\0421\0442\0430\0431\0456\043b\044c\043d\0438\0439 ID \0434\0436\0435\0440\0435\043b\0430 (SRC-\2026; \0445\0435\0448 URL)';

COMMENT ON COLUMN space.sources.url IS U&'\041f\0440\044f\043c\0438\0439 URL \0434\043e\043a\0443\043c\0435\043d\0442\0430';

COMMENT ON COLUMN space.sources.title IS U&'\041d\0430\0437\0432\0430 \0434\043e\043a\0443\043c\0435\043d\0442\0430 / \0441\0442\043e\0440\0456\043d\043a\0438';

COMMENT ON COLUMN space.sources.publisher IS U&'\0412\0438\0434\0430\0432\0435\0446\044c / \0430\0432\0442\043e\0440';

COMMENT ON COLUMN space.sources.document_date IS U&'\0414\0430\0442\0430 \0434\043e\043a\0443\043c\0435\043d\0442\0430 \0430\0431\043e \043e\043d\043e\0432\043b\0435\043d\043d\044f (\044f\043a\0449\043e \0432\043a\0430\0437\0430\043d\0430)';

COMMENT ON COLUMN space.sources.document_revision IS U&'\0420\0435\0432\0456\0437\0456\044f / \0432\0435\0440\0441\0456\044f \0434\043e\043a\0443\043c\0435\043d\0442\0430';

COMMENT ON COLUMN space.sources.document_type IS U&'\0422\0438\043f \0434\043e\043a\0443\043c\0435\043d\0442\0430';

COMMENT ON COLUMN space.sources.language IS U&'\041c\043e\0432\0430 (ISO 639-1)';

COMMENT ON COLUMN space.sources.access_date IS U&'\0414\0430\0442\0430 \043e\0441\0442\0430\043d\043d\044c\043e\0433\043e \0434\043e\0441\0442\0443\043f\0443';

COMMENT ON COLUMN space.sources.http_status IS U&'HTTP-\043a\043e\0434 \043f\0440\0438 \043e\0441\0442\0430\043d\043d\0456\0439 \043f\0435\0440\0435\0432\0456\0440\0446\0456';

COMMENT ON COLUMN space.sources.content_kind IS 'html / pdf / csv / local';

COMMENT ON COLUMN space.sources.content_sha256 IS U&'SHA-256 \0437\0430\0432\0430\043d\0442\0430\0436\0435\043d\043e\0433\043e \0432\043c\0456\0441\0442\0443 (\043a\0435\0448 output/cache/sources)';

COMMENT ON COLUMN space.sources.verification_status IS U&'\0420\0435\0437\0443\043b\044c\0442\0430\0442 \043f\0435\0440\0435\0432\0456\0440\043a\0438 \0432\043c\0456\0441\0442\0443';

COMMENT ON COLUMN space.sources.archive_url IS U&'\0410\0440\0445\0456\0432\043d\0430 \043a\043e\043f\0456\044f, \0432\0438\043a\043e\0440\0438\0441\0442\0430\043d\0430 \0434\043b\044f \043f\0435\0440\0435\0432\0456\0440\043a\0438, \044f\043a\0449\043e \043e\0440\0438\0433\0456\043d\0430\043b \0431\043b\043e\043a\0443\0454 \0430\0432\0442\043e\043c\0430\0442\0438\0447\043d\0438\0439 \0434\043e\0441\0442\0443\043f';

COMMENT ON COLUMN space.sources.notes IS U&'\041e\0431\043c\0435\0436\0435\043d\043d\044f \0434\0436\0435\0440\0435\043b\0430';

ALTER TABLE space.spacecraft_models ADD CONSTRAINT fk_spacecraft_models_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.spacecraft_models ADD CONSTRAINT fk_spacecraft_models_import_id_manufacturer_org_id FOREIGN KEY(import_id, manufacturer_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.spacecraft_models ADD CONSTRAINT fk_spacecraft_models_import_id_program_id FOREIGN KEY(import_id, program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.spacecraft_models.spacecraft_model_id IS U&'ID \043c\043e\0434\0435\043b\0456 / \043f\043e\043a\043e\043b\0456\043d\043d\044f \041a\0410 (SCM-\2026)';

COMMENT ON COLUMN space.spacecraft_models.program_id IS U&'\041f\0440\043e\0433\0440\0430\043c\0430';

COMMENT ON COLUMN space.spacecraft_models.name IS U&'\041d\0430\0437\0432\0430 \043c\043e\0434\0435\043b\0456 / \041a\0410';

COMMENT ON COLUMN space.spacecraft_models.generation IS U&'\041f\043e\043a\043e\043b\0456\043d\043d\044f / \0441\0435\0440\0456\044f';

COMMENT ON COLUMN space.spacecraft_models.manufacturer_org_id IS U&'\0413\043e\043b\043e\0432\043d\0438\0439 \0432\0438\0440\043e\0431\043d\0438\043a';

COMMENT ON COLUMN space.spacecraft_models.bus_platform IS U&'\041f\043b\0430\0442\0444\043e\0440\043c\0430';

COMMENT ON COLUMN space.spacecraft_models.launch_mass_kg IS U&'\0421\0442\0430\0440\0442\043e\0432\0430 \043c\0430\0441\0430 [\043a\0433]';

COMMENT ON COLUMN space.spacecraft_models.dry_mass_kg IS U&'\0421\0443\0445\0430 \043c\0430\0441\0430 [\043a\0433]';

COMMENT ON COLUMN space.spacecraft_models.power_kw IS U&'\041f\043e\0442\0443\0436\043d\0456\0441\0442\044c (\0431\0430\0437\0430 \0432 \043f\0440\0438\043c\0456\0442\0446\0456) [\043a\0412\0442]';

COMMENT ON COLUMN space.spacecraft_models.design_life_years IS U&'\041f\0440\043e\0454\043a\0442\043d\0438\0439 \0440\0435\0441\0443\0440\0441 [\0440\043e\043a\0456\0432]';

COMMENT ON COLUMN space.spacecraft_models.payload_architecture IS 'bent_pipe / regenerative / digital_processor / unknown';

COMMENT ON COLUMN space.spacecraft_models.design_capacity_gbps IS U&'\041f\0440\043e\0454\043a\0442\043d\0430 / \0437\0430\044f\0432\043b\0435\043d\0430 \043c\0456\0441\0442\043a\0456\0441\0442\044c \043e\0434\043d\043e\0433\043e \041a\0410 [\0413\0431\0456\0442/\0441]';

COMMENT ON COLUMN space.spacecraft_models.isl_type IS 'none / RF / optical / unknown';

COMMENT ON COLUMN space.spacecraft_models.first_launch_date IS U&'\041f\0435\0440\0448\0438\0439 \0437\0430\043f\0443\0441\043a \043c\043e\0434\0435\043b\0456';

COMMENT ON COLUMN space.spacecraft_models.norad_id IS U&'NORAD (\0434\043b\044f \043e\0434\0438\043d\0438\0447\043d\043e\0433\043e \041a\0410)';

COMMENT ON COLUMN space.spacecraft_models.cospar_id IS U&'COSPAR (\0434\043b\044f \043e\0434\0438\043d\0438\0447\043d\043e\0433\043e \041a\0410)';

COMMENT ON COLUMN space.spacecraft_models.orbital_position IS U&'\041e\0440\0431\0456\0442\0430\043b\044c\043d\0430 \043f\043e\0437\0438\0446\0456\044f GEO \0430\0431\043e \043e\0431\043e\043b\043e\043d\043a\0430';

COMMENT ON COLUMN space.spacecraft_models.notes IS U&'\041f\0440\0438\043c\0456\0442\043a\0438';

ALTER TABLE space.terminal_models ADD CONSTRAINT fk_terminal_models_import_id FOREIGN KEY(import_id) REFERENCES space.satcom_imports (import_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.terminal_models ADD CONSTRAINT fk_terminal_models_import_id_manufacturer_org_id FOREIGN KEY(import_id, manufacturer_org_id) REFERENCES space.organizations (import_id, org_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE space.terminal_models ADD CONSTRAINT fk_terminal_models_import_id_primary_program_id FOREIGN KEY(import_id, primary_program_id) REFERENCES space.constellations_programs (import_id, program_id) DEFERRABLE INITIALLY DEFERRED;

COMMENT ON COLUMN space.terminal_models.terminal_id IS U&'ID \043c\043e\0434\0435\043b\0456 (TRM-\2026)';

COMMENT ON COLUMN space.terminal_models.name IS U&'\041d\0430\0437\0432\0430 \043c\043e\0434\0435\043b\0456';

COMMENT ON COLUMN space.terminal_models.family IS U&'\0421\0456\043c\0435\0439\0441\0442\0432\043e / \043b\0456\043d\0456\0439\043a\0430';

COMMENT ON COLUMN space.terminal_models.revision IS U&'\0420\0435\0432\0456\0437\0456\044f / \043f\043e\043a\043e\043b\0456\043d\043d\044f';

COMMENT ON COLUMN space.terminal_models.primary_program_id IS U&'\041e\0441\043d\043e\0432\043d\0430 \043c\0435\0440\0435\0436\0430 (NULL \2014 \043c\0443\043b\044c\0442\0438\043c\0435\0440\0435\0436\0435\0432\0438\0439)';

COMMENT ON COLUMN space.terminal_models.form_factor IS U&'\0424\043e\0440\043c-\0444\0430\043a\0442\043e\0440';

COMMENT ON COLUMN space.terminal_models.service_class IS U&'\041a\043b\0430\0441 \0441\0435\0440\0432\0456\0441\0443';

COMMENT ON COLUMN space.terminal_models.antenna_type IS 'ESA / phased_array / parabolic_mech / flat_panel_mech / omni / patch / hybrid / metasurface';

COMMENT ON COLUMN space.terminal_models.multi_orbit IS U&'\041f\0456\0434\0442\0440\0438\043c\043a\0430 \043a\0456\043b\044c\043a\043e\0445 \043e\0440\0431\0456\0442 / \043c\0435\0440\0435\0436';

COMMENT ON COLUMN space.terminal_models.mass_antenna_kg IS U&'\041c\0430\0441\0430 \0430\043d\0442\0435\043d\0438 / ODU \0431\0435\0437 \043a\0440\0456\043f\043b\0435\043d\043d\044f, \043a\0430\0431\0435\043b\044e, \0411\0416 [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_with_mount_kg IS U&'\0410\043d\0442\0435\043d\0430 \0437 \043f\0456\0434\0441\0442\0430\0432\043a\043e\044e / \043a\0440\0456\043f\043b\0435\043d\043d\044f\043c [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_device_with_battery_kg IS U&'\041f\043e\0440\0442\0430\0442\0438\0432\043d\0438\0439 \043f\0440\0438\0441\0442\0440\0456\0439 \0437\0456 \0448\0442\0430\0442\043d\043e\044e \0431\0430\0442\0430\0440\0435\0454\044e [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_idu_kg IS U&'\0412\043d\0443\0442\0440\0456\0448\043d\0456\0439 \0431\043b\043e\043a / \0440\043e\0443\0442\0435\0440 / \043c\043e\0434\0435\043c [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_psu_kg IS U&'\0411\043b\043e\043a \0436\0438\0432\043b\0435\043d\043d\044f [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_with_mount_cable_kg IS U&'\0410\043d\0442\0435\043d\0430 \0437 \043a\0440\0456\043f\043b\0435\043d\043d\044f\043c / \043a\0430\0431\0435\043b\0435\043c (\044f\043a \0443 \043f\0430\0441\043f\043e\0440\0442\0456) [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_installed_kg IS U&'\0412\0441\0442\0430\043d\043e\0432\043b\0435\043d\0430 \0441\0438\0441\0442\0435\043c\0430 (\0443\0441\0456 \0430\043d\0442\0435\043d\0438/\0440\0430\0434\043e\043c\0438 \0430\0431\043e \043a\043e\043c\043f\043b\0435\043a\0442 \0456\0437 \0411\0416, \043a\0430\0431\0435\043b\044f\043c\0438, \0442\0440\0438\043d\043e\0433\043e\044e \2014 \0434\0438\0432. mass_basis_note) [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_packaged_kg IS U&'\041c\0430\0441\0430 \0432 \0443\043f\0430\043a\043e\0432\0446\0456 [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_unspecified_kg IS U&'\041c\0430\0441\0430 \0431\0435\0437 \0440\043e\0437\043a\0440\0438\0442\043e\0457 \0431\0430\0437\0438 [\043a\0433]';

COMMENT ON COLUMN space.terminal_models.mass_basis_note IS U&'\0429\043e \0432\043a\043b\044e\0447\0435\043d\043e \0432 \043c\0430\0441\0443';

COMMENT ON COLUMN space.terminal_models.dl_peak_mbps IS U&'\041f\0430\0441\043f\043e\0440\0442\043d\0430 / \0437\0430\044f\0432\043b\0435\043d\0430 \043f\0456\043a\043e\0432\0430 DL [\041c\0431\0456\0442/\0441]';

COMMENT ON COLUMN space.terminal_models.speed_basis IS 'datasheet_peak / marketing_up_to / measured / guaranteed';

COMMENT ON COLUMN space.terminal_models.ip_rating IS U&'IP-\043a\043b\0430\0441';

COMMENT ON COLUMN space.terminal_models.interfaces IS U&'\0406\043d\0442\0435\0440\0444\0435\0439\0441\0438';

COMMENT ON COLUMN space.terminal_models.availability_status IS U&'\0421\0442\0430\043d \0434\043e\0441\0442\0443\043f\043d\043e\0441\0442\0456 \0432\0438\0440\043e\0431\0443';

COMMENT ON COLUMN space.terminal_models.notes IS U&'\041e\0431\043c\0435\0436\0435\043d\043d\044f \0442\0430 \043a\043e\043c\043f\043b\0435\043a\0442\0430\0446\0456\044f';
