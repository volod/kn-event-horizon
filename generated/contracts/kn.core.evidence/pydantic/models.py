"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class Aliases(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    alias_id: _kn_builtins.str = _kn_pydantic.Field(alias='alias_id', description='SHA-256 of the object, text, language and claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.alias_id'}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='Object the alias weakly identifies', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.kn_id'}})
    alias: _kn_builtins.str = _kn_pydantic.Field(alias='alias', description='Alias text exactly as stated', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.alias'}})
    language: _kn_builtins.str = _kn_pydantic.Field(alias='language', description='BCP-47 tag of the alias; und when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.language'}})
    normalized_key: _kn_builtins.str = _kn_pydantic.Field(alias='normalized_key', description='Normalized lookup key; not unique', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.normalized_key'}})
    normalizer: _kn_builtins.str = _kn_pydantic.Field(alias='normalizer', description='Normalizer that produced the key', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.normalizer'}})
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Claim that states the alias', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time KN recorded the alias', json_schema_extra={'x-kn': {'fieldId': 'evidence.aliases.recorded_at'}})

class CanonicalFacts(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    fact_version_id: _kn_builtins.str = _kn_pydantic.Field(alias='fact_version_id', description='SHA-256 of the fact key, selection content and knowledge start', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.fact_version_id'}})
    fact_key: _kn_builtins.str = _kn_pydantic.Field(alias='fact_key', description='SHA-256 of object, field, conditions and audience', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.fact_key'}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='Object of the fact; a survivor after merges', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.kn_id'}})
    field_id: _kn_builtins.str = _kn_pydantic.Field(alias='field_id', description='Stable contract field ID', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.field_id'}})
    conditions_json: _kn_builtins.str = _kn_pydantic.Field(alias='conditions_json', description='Canonical JSON condition set; {} when unconditioned', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.conditions_json'}})
    audience: _kn_builtins.str = _kn_pydantic.Field(alias='audience', description='Audience whose eligible evidence was selected', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.audience'}})
    claim_key: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='claim_key', description='Selected claim; null when unresolved', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    unresolved_reason: _kn_typing.Literal['no_eligible_claim', 'conflict', 'review_pending', 'cleared'] | None = _kn_pydantic.Field(default=None, alias='unresolved_reason', description='Why no claim is selected', json_schema_extra={'x-kn': {'enum': ['no_eligible_claim', 'conflict', 'review_pending', 'cleared'], 'fieldId': 'evidence.canonical_facts.unresolved_reason'}})
    mode: _kn_typing.Literal['priority', 'latest_observed', 'accumulate', 'fixed'] = _kn_pydantic.Field(alias='mode', description='Update policy mode', json_schema_extra={'x-kn': {'enum': ['priority', 'latest_observed', 'accumulate', 'fixed'], 'fieldId': 'evidence.canonical_facts.mode'}})
    policy_digest: _kn_builtins.str = _kn_pydantic.Field(alias='policy_digest', description='SHA-256 of the canonical update policy', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.policy_digest'}})
    outcome: _kn_typing.Literal['filled', 'replaced', 'corroborated', 'conflict'] = _kn_pydantic.Field(alias='outcome', description='Outcome of the change that produced this version; ignored claims leave no version', json_schema_extra={'x-kn': {'enum': ['filled', 'replaced', 'corroborated', 'conflict'], 'fieldId': 'evidence.canonical_facts.outcome'}})
    deciding_criterion: _kn_typing.Literal['first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision'] = _kn_pydantic.Field(alias='deciding_criterion', description='Criterion that decided the outcome', json_schema_extra={'x-kn': {'enum': ['first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision'], 'fieldId': 'evidence.canonical_facts.deciding_criterion'}})
    winner_criteria_json: _kn_builtins.str = _kn_pydantic.Field(alias='winner_criteria_json', description='Canonical criteria values of the winner', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.winner_criteria_json'}})
    runner_up_criteria_json: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='runner_up_criteria_json', description='Canonical criteria values of the runner-up', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.runner_up_criteria_json'}})
    verification_state: _kn_typing.Literal['unreviewed', 'corroborated', 'verified', 'disputed'] = _kn_pydantic.Field(alias='verification_state', description='Derived verification label', json_schema_extra={'x-kn': {'enum': ['unreviewed', 'corroborated', 'verified', 'disputed'], 'fieldId': 'evidence.canonical_facts.verification_state'}})
    owner_override: _kn_builtins.bool = _kn_pydantic.Field(alias='owner_override', description='An owner-entered value outranks a differing first-party value', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.owner_override'}})
    review_item_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='review_item_id', description='Open review item for this version', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.review_item_id', 'foreignKey': {'fields': ['review_item_id'], 'table': 'review_items', 'targetFields': ['item_id']}}})
    valid_from: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_from', description='Inclusive start of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.valid_from'}})
    valid_from_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_from_precision', description='Precision of valid_from; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.canonical_facts.valid_from_precision'}})
    valid_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_to', description='Exclusive end of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.valid_to'}})
    valid_to_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_to_precision', description='Precision of valid_to; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.canonical_facts.valid_to_precision'}})
    knowledge_from: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='knowledge_from', description='Inclusive UTC knowledge time of this version', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.knowledge_from'}})
    knowledge_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='knowledge_to', description='Exclusive UTC knowledge end; null while current', json_schema_extra={'x-kn': {'fieldId': 'evidence.canonical_facts.knowledge_to'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'CanonicalFacts':
        for _kn_exact, _kn_names in ((True, ('claim_key', 'unresolved_reason')), (False, ('valid_from', 'valid_from_precision')), (False, ('valid_to', 'valid_to_precision'))):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class ClaimConfirmations(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    confirmation_id: _kn_builtins.str = _kn_pydantic.Field(alias='confirmation_id', description='SHA-256 of the claim key, source version and fetch', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.confirmation_id'}})
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Unchanged claim that was observed again', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    source_version_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_version_id', description='Source record version that repeated the value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.source_version_id'}})
    evidence_id: _kn_builtins.str = _kn_pydantic.Field(alias='evidence_id', description='Evidence of the re-observation', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.evidence_id', 'foreignKey': {'fields': ['evidence_id'], 'table': 'evidence_records', 'targetFields': ['evidence_id']}}})
    fetch_id: _kn_builtins.str = _kn_pydantic.Field(alias='fetch_id', description='Fetch ID of the re-observation', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.fetch_id'}})
    observed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='observed_at', description='UTC time of the re-observation', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.observed_at'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time KN recorded the confirmation', json_schema_extra={'x-kn': {'fieldId': 'evidence.claim_confirmations.recorded_at'}})

class Claims(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Deterministic SHA-256 of the claim content and its evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.claim_key'}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='KN ID of the object the claim is about', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.kn_id'}})
    field_id: _kn_builtins.str = _kn_pydantic.Field(alias='field_id', description='Stable contract field ID the claim states', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.field_id'}})
    conditions_json: _kn_builtins.str = _kn_pydantic.Field(alias='conditions_json', description='Canonical JSON object of conditions; {} when unconditioned', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.conditions_json'}})
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Qualified source catalogue ID', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.source_id'}})
    record_id: _kn_builtins.str = _kn_pydantic.Field(alias='record_id', description='Identity source record that stated the value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.record_id'}})
    source_version_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_version_id', description='Identity source record version that stated the value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.source_version_id'}})
    change_set_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='change_set_id', description='Identity change set that produced the claim, when tracked', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.change_set_id'}})
    change_kind: _kn_typing.Literal['added', 'changed', 'emptied', 'decided'] = _kn_pydantic.Field(alias='change_kind', description='Change that produced the claim', json_schema_extra={'x-kn': {'enum': ['added', 'changed', 'emptied', 'decided'], 'fieldId': 'evidence.claims.change_kind'}})
    supersedes: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='supersedes', description='Earlier claim of the same record and field', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.supersedes', 'foreignKey': {'fields': ['supersedes'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    decision_ref: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='decision_ref', description='Review decision that produced an owner-entered claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.decision_ref'}})
    evidence_id: _kn_builtins.str = _kn_pydantic.Field(alias='evidence_id', description='Evidence that carries the full provenance', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.evidence_id', 'foreignKey': {'fields': ['evidence_id'], 'table': 'evidence_records', 'targetFields': ['evidence_id']}}})
    fetch_id: _kn_builtins.str = _kn_pydantic.Field(alias='fetch_id', description='Fetch ID of the evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.fetch_id'}})
    origin_uri: _kn_builtins.str = _kn_pydantic.Field(alias='origin_uri', description='Redacted origin URI of the evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.origin_uri'}})
    fetched_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='fetched_at', description='UTC fetch time of the evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.fetched_at'}})
    original_value: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='original_value', description='Value exactly as the source states it', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.original_value'}})
    original_unit: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='original_unit', description='Unit exactly as the source states it', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.original_unit'}})
    value_text: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='value_text', description='Normalized text value in its original language', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_text'}})
    value_language: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='value_language', description='BCP-47 tag of value_text; und when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_language'}})
    value_number: _kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits=38, decimal_places=18, allow_inf_nan=False)] | None = _kn_pydantic.Field(default=None, alias='value_number', description='Exact normalized decimal value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_number'}})
    value_boolean: _kn_builtins.bool | None = _kn_pydantic.Field(default=None, alias='value_boolean', description='Normalized boolean value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_boolean'}})
    value_date: _kn_typing.Annotated[_kn_builtins.str, _kn_pydantic.Field(pattern='^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$')] | None = _kn_pydantic.Field(default=None, alias='value_date', description='Partial ISO date value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_date', 'partialDate': True}})
    value_concept: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='value_concept', description='Qualified semantic concept ID value', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_concept'}})
    value_kn_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='value_kn_id', description='KN ID of a referenced object', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.value_kn_id'}})
    missing_reason: _kn_typing.Literal['source_empty', 'not_found', 'not_disclosed', 'requires_vendor_quote', 'cannot_verify', 'not_applicable'] | None = _kn_pydantic.Field(default=None, alias='missing_reason', description='Why no value is stated; exclusive with every value', json_schema_extra={'x-kn': {'enum': ['source_empty', 'not_found', 'not_disclosed', 'requires_vendor_quote', 'cannot_verify', 'not_applicable'], 'fieldId': 'evidence.claims.missing_reason'}})
    normalized_unit: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='normalized_unit', description='Unit of value_number after conversion', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.normalized_unit'}})
    conversion_rule: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='conversion_rule', description='Rule that converted the original unit', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.conversion_rule'}})
    assertion_type: _kn_typing.Literal['declared', 'observed', 'derived', 'reported'] = _kn_pydantic.Field(alias='assertion_type', description='How the source asserts the value', json_schema_extra={'x-kn': {'enum': ['declared', 'observed', 'derived', 'reported'], 'fieldId': 'evidence.claims.assertion_type'}})
    evidence_class: _kn_typing.Literal['primary', 'secondary', 'derived', 'extracted_candidate'] = _kn_pydantic.Field(alias='evidence_class', description='Evidence class used by selection', json_schema_extra={'x-kn': {'enum': ['primary', 'secondary', 'derived', 'extracted_candidate'], 'fieldId': 'evidence.claims.evidence_class'}})
    extraction_confidence: _kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits=5, decimal_places=4, allow_inf_nan=False)] | None = _kn_pydantic.Field(default=None, alias='extraction_confidence', description='Extraction confidence from 0 to 1, never a truth probability', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.extraction_confidence', 'precision': 5, 'scale': 4}})
    source_verification_label: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='source_verification_label', description='Imported source verification label; never human verification', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.source_verification_label'}})
    event_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='event_at', description='Time the described event happened (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.event_at'}})
    event_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='event_precision', description='Precision of event_at; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.claims.event_precision'}})
    published_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='published_at', description='Time the source published the value (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.published_at'}})
    published_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='published_precision', description='Precision of published_at; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.claims.published_precision'}})
    valid_from: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_from', description='Inclusive start of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.valid_from'}})
    valid_from_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_from_precision', description='Precision of valid_from; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.claims.valid_from_precision'}})
    valid_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_to', description='Exclusive end of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.valid_to'}})
    valid_to_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_to_precision', description='Precision of valid_to; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.claims.valid_to_precision'}})
    observed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='observed_at', description='UTC time the value was observed', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.observed_at'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC knowledge time KN recorded the claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.claims.recorded_at'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'Claims':
        for _kn_exact, _kn_names in ((True, ('value_text', 'value_number', 'value_boolean', 'value_date', 'value_concept', 'value_kn_id', 'missing_reason')), (False, ('value_text', 'value_language')), (False, ('normalized_unit', 'conversion_rule')), (False, ('event_at', 'event_precision')), (False, ('published_at', 'published_precision')), (False, ('valid_from', 'valid_from_precision')), (False, ('valid_to', 'valid_to_precision'))):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class EvidenceRecords(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    evidence_id: _kn_builtins.str = _kn_pydantic.Field(alias='evidence_id', description='SHA-256 of the canonical provenance content', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.evidence_id'}})
    source_id: _kn_builtins.str = _kn_pydantic.Field(alias='source_id', description='Qualified source catalogue ID', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.source_id'}})
    fetch_id: _kn_builtins.str = _kn_pydantic.Field(alias='fetch_id', description='Fetch run that retrieved the bytes', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.fetch_id'}})
    archive_record_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='archive_record_id', description='Raw archive record; null only for review decisions and curated entries', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.archive_record_id'}})
    origin_uri: _kn_builtins.str = _kn_pydantic.Field(alias='origin_uri', description='Origin URI after credential redaction', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.origin_uri'}})
    fetched_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='fetched_at', description='UTC fetch or capture time', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.fetched_at'}})
    locator_kind: _kn_typing.Literal['json_pointer', 'row', 'page', 'offset'] = _kn_pydantic.Field(alias='locator_kind', description='Kind of native record locator', json_schema_extra={'x-kn': {'enum': ['json_pointer', 'row', 'page', 'offset'], 'fieldId': 'evidence.evidence_records.locator_kind'}})
    locator: _kn_builtins.str = _kn_pydantic.Field(alias='locator', description='Native locator inside the archived record', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.locator'}})
    excerpt: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='excerpt', description='Original excerpt, stored only when its rights permit', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.excerpt'}})
    excerpt_rights: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='excerpt_rights', description='Rights reference that permits the stored excerpt', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.excerpt_rights'}})
    rights: _kn_builtins.str = _kn_pydantic.Field(alias='rights', description='Rights or license policy reference of the evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.rights'}})
    code_digest: _kn_builtins.str = _kn_pydantic.Field(alias='code_digest', description='SHA-256 of the parser or mapping code', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.code_digest'}})
    contract_digest: _kn_builtins.str = _kn_pydantic.Field(alias='contract_digest', description='Digest of the contract the parser applied', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.contract_digest'}})
    curator: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='curator', description='Curator of a curated observation', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.curator'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time KN recorded the evidence', json_schema_extra={'x-kn': {'fieldId': 'evidence.evidence_records.recorded_at'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'EvidenceRecords':
        for _kn_exact, _kn_names in ((False, ('excerpt', 'excerpt_rights')),):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class RelationAssertions(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    assertion_id: _kn_builtins.str = _kn_pydantic.Field(alias='assertion_id', description='SHA-256 of the relation key and the claim that opened it', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.assertion_id'}})
    relation_key: _kn_builtins.str = _kn_pydantic.Field(alias='relation_key', description='SHA-256 of subject, type, object, qualifiers and validity', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.relation_key'}})
    subject_kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='subject_kn_id', description='Subject object', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.subject_kn_id'}})
    relation_type: _kn_builtins.str = _kn_pydantic.Field(alias='relation_type', description='Ontology relation type ID', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.relation_type'}})
    object_kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='object_kn_id', description='Object at the other endpoint', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.object_kn_id'}})
    qualifiers_json: _kn_builtins.str = _kn_pydantic.Field(alias='qualifiers_json', description='Canonical JSON object of qualifiers; {} when none', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.qualifiers_json'}})
    valid_from: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_from', description='Inclusive start of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.valid_from'}})
    valid_from_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_from_precision', description='Precision of valid_from; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.relation_assertions.valid_from_precision'}})
    valid_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_to', description='Exclusive end of validity (UTC); null when unknown', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.valid_to'}})
    valid_to_precision: _kn_typing.Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'] | None = _kn_pydantic.Field(default=None, alias='valid_to_precision', description='Precision of valid_to; present exactly when it is', json_schema_extra={'x-kn': {'enum': ['year', 'month', 'day', 'hour', 'minute', 'second', 'subsecond'], 'fieldId': 'evidence.relation_assertions.valid_to_precision'}})
    review_state: _kn_typing.Literal['unreviewed', 'accepted', 'disputed', 'rejected'] = _kn_pydantic.Field(alias='review_state', description='Review state of the assertion', json_schema_extra={'x-kn': {'enum': ['unreviewed', 'accepted', 'disputed', 'rejected'], 'fieldId': 'evidence.relation_assertions.review_state'}})
    decision_ref: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='decision_ref', description='Review decision behind the review state', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.decision_ref'}})
    opened_by: _kn_builtins.str = _kn_pydantic.Field(alias='opened_by', description='Claim that first asserted the relation', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.opened_by', 'foreignKey': {'fields': ['opened_by'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    opened_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='opened_at', description='UTC knowledge time the assertion became active', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.opened_at'}})
    closed_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='closed_at', description='UTC knowledge time the assertion stopped being active', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_assertions.closed_at'}})
    close_reason: _kn_typing.Literal['rejected', 'retracted', 'superseded'] | None = _kn_pydantic.Field(default=None, alias='close_reason', description='Why the assertion closed', json_schema_extra={'x-kn': {'enum': ['rejected', 'retracted', 'superseded'], 'fieldId': 'evidence.relation_assertions.close_reason'}})

    @_kn_pydantic.model_validator(mode='after')
    def _kn_presence(self) -> 'RelationAssertions':
        for _kn_exact, _kn_names in ((False, ('closed_at', 'close_reason')), (False, ('valid_from', 'valid_from_precision')), (False, ('valid_to', 'valid_to_precision'))):
            _kn_count = sum(getattr(self, _kn_n) is not None for _kn_n in _kn_names)
            if _kn_count not in ((1,) if _kn_exact else (0, len(_kn_names))):
                raise ValueError('presence rule violated: ' + ', '.join(_kn_names))
        return self

class RelationSupports(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    assertion_id: _kn_builtins.str = _kn_pydantic.Field(alias='assertion_id', description='Supported relation assertion', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_supports.assertion_id', 'foreignKey': {'fields': ['assertion_id'], 'table': 'relation_assertions', 'targetFields': ['assertion_id']}}})
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Claim that supports the assertion', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_supports.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time KN recorded the support', json_schema_extra={'x-kn': {'fieldId': 'evidence.relation_supports.recorded_at'}})

class ReviewDecisions(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    decision_id: _kn_builtins.str = _kn_pydantic.Field(alias='decision_id', description='SHA-256 of the canonical decision event', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.decision_id'}})
    item_id: _kn_builtins.str = _kn_pydantic.Field(alias='item_id', description='Decided review item', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.item_id', 'foreignKey': {'fields': ['item_id'], 'table': 'review_items', 'targetFields': ['item_id']}}})
    outcome: _kn_typing.Literal['select', 'reject', 'accept', 'defer', 'dismiss'] = _kn_pydantic.Field(alias='outcome', description='Append-only decision outcome', json_schema_extra={'x-kn': {'enum': ['select', 'reject', 'accept', 'defer', 'dismiss'], 'fieldId': 'evidence.review_decisions.outcome'}})
    selected_claim_key: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='selected_claim_key', description='Claim selected by a select decision', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.selected_claim_key', 'foreignKey': {'fields': ['selected_claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    predecessor: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='predecessor', description='Earlier decision this one supersedes', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.predecessor', 'foreignKey': {'fields': ['predecessor'], 'table': 'review_decisions', 'targetFields': ['decision_id']}}})
    reviewer: _kn_builtins.str = _kn_pydantic.Field(alias='reviewer', description='Authenticated reviewer principal', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.reviewer'}})
    reason: _kn_builtins.str = _kn_pydantic.Field(alias='reason', description="Reviewer's reason", json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.reason'}})
    performed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='performed_at', description='UTC time of the human decision', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.performed_at'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='Separate UTC journal recording time', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.recorded_at'}})
    human_verification_decision_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='human_verification_decision_id', description='Shared human verification decision, when the decision also verifies', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.human_verification_decision_id'}})
    event_json: _kn_builtins.str = _kn_pydantic.Field(alias='event_json', description='Canonical decision event; authoritative replay payload', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_decisions.event_json'}})

class ReviewItems(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    item_id: _kn_builtins.str = _kn_pydantic.Field(alias='item_id', description='SHA-256 of the kind, subject and sorted candidates', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.item_id'}})
    kind: _kn_typing.Literal['fact_conflict', 'fixed_value_change', 'empty_claim', 'high_impact', 'owner_override', 'relation_candidate', 'quarantine', 'identity_match', 'identity_drift'] = _kn_pydantic.Field(alias='kind', description='Registered review item kind', json_schema_extra={'x-kn': {'enum': ['fact_conflict', 'fixed_value_change', 'empty_claim', 'high_impact', 'owner_override', 'relation_candidate', 'quarantine', 'identity_match', 'identity_drift'], 'fieldId': 'evidence.review_items.kind'}})
    kn_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='kn_id', description='Object under review, when the item has one', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.kn_id'}})
    field_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='field_id', description='Field under review, when the item has one', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.field_id'}})
    fact_key: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='fact_key', description='Fact under review, when the item has one', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.fact_key'}})
    candidates_json: _kn_builtins.str = _kn_pydantic.Field(alias='candidates_json', description='Canonical sorted array of candidate claim keys or references', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.candidates_json'}})
    reason_code: _kn_builtins.str = _kn_pydantic.Field(alias='reason_code', description='Stable reason code', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.reason_code'}})
    opened_by: _kn_builtins.str = _kn_pydantic.Field(alias='opened_by', description='Selection, run or match record that opened the item', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.opened_by'}})
    opened_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='opened_at', description='UTC time the item opened', json_schema_extra={'x-kn': {'fieldId': 'evidence.review_items.opened_at'}})

class SelectionOutcomes(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    outcome_id: _kn_builtins.str = _kn_pydantic.Field(alias='outcome_id', description='SHA-256 of the fact version and evaluated claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.outcome_id'}})
    fact_key: _kn_builtins.str = _kn_pydantic.Field(alias='fact_key', description='Fact whose selection evaluated the claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.fact_key'}})
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Evaluated claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    fact_version_id: _kn_builtins.str = _kn_pydantic.Field(alias='fact_version_id', description='Fact version current after the evaluation', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.fact_version_id', 'foreignKey': {'fields': ['fact_version_id'], 'table': 'canonical_facts', 'targetFields': ['fact_version_id']}}})
    outcome: _kn_typing.Literal['filled', 'replaced', 'ignored', 'corroborated', 'conflict'] = _kn_pydantic.Field(alias='outcome', description='Explained outcome for the claim', json_schema_extra={'x-kn': {'enum': ['filled', 'replaced', 'ignored', 'corroborated', 'conflict'], 'fieldId': 'evidence.selection_outcomes.outcome'}})
    criterion: _kn_typing.Literal['first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision'] = _kn_pydantic.Field(alias='criterion', description='Deciding criterion', json_schema_extra={'x-kn': {'enum': ['first_eligible', 'source_rank', 'evidence_class', 'data_time', 'tie', 'fixed_value', 'review_decision'], 'fieldId': 'evidence.selection_outcomes.criterion'}})
    criteria_json: _kn_builtins.str = _kn_pydantic.Field(alias='criteria_json', description='Canonical criteria values of the evaluated claim', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.criteria_json'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time of the evaluation', json_schema_extra={'x-kn': {'fieldId': 'evidence.selection_outcomes.recorded_at'}})

class TextTranslations(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    translation_id: _kn_builtins.str = _kn_pydantic.Field(alias='translation_id', description='SHA-256 of the claim, language, text and provenance', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.translation_id'}})
    claim_key: _kn_builtins.str = _kn_pydantic.Field(alias='claim_key', description='Text claim whose original stays unchanged', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.claim_key', 'foreignKey': {'fields': ['claim_key'], 'table': 'claims', 'targetFields': ['claim_key']}}})
    language: _kn_builtins.str = _kn_pydantic.Field(alias='language', description='BCP-47 tag of the translation', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.language'}})
    text: _kn_builtins.str = _kn_pydantic.Field(alias='text', description='Derived translated text', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.text'}})
    method: _kn_typing.Literal['source', 'human', 'machine'] = _kn_pydantic.Field(alias='method', description='Who produced the translation', json_schema_extra={'x-kn': {'enum': ['source', 'human', 'machine'], 'fieldId': 'evidence.text_translations.method'}})
    provenance: _kn_builtins.str = _kn_pydantic.Field(alias='provenance', description='Source record, review or model and prompt reference', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.provenance'}})
    recorded_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='recorded_at', description='UTC time KN recorded the translation', json_schema_extra={'x-kn': {'fieldId': 'evidence.text_translations.recorded_at'}})
