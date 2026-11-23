"""Generated from the contract. Regenerate instead of editing."""
import builtins as _kn_builtins
import datetime as _kn_datetime
import decimal as _kn_decimal
import typing as _kn_typing

import pydantic as _kn_pydantic


class Attributes(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    attribute_id: _kn_builtins.str = _kn_pydantic.Field(alias='attribute_id', description='attributes: attribute id.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.attribute_id', 'foreignKey': {'fields': ['attribute_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='attributes: kn id.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.kn_id', 'foreignKey': {'fields': ['kn_id'], 'table': 'objects', 'targetFields': ['kn_id']}}})
    field_id: _kn_builtins.str = _kn_pydantic.Field(alias='field_id', description='attributes: field id.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.field_id'}})
    original: _kn_builtins.str = _kn_pydantic.Field(alias='original', description='attributes: original.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.original'}})
    normalized: _kn_builtins.str = _kn_pydantic.Field(alias='normalized', description='attributes: normalized.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.normalized'}})
    normalizer: _kn_builtins.str = _kn_pydantic.Field(alias='normalizer', description='attributes: normalizer.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.normalizer'}})
    profile_digest: _kn_builtins.str = _kn_pydantic.Field(alias='profile_digest', description='attributes: profile digest.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.profile_digest'}})
    evidence: _kn_builtins.str = _kn_pydantic.Field(alias='evidence', description='attributes: evidence.', json_schema_extra={'x-kn': {'fieldId': 'identity.attributes.evidence'}})

class ChangeSets(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    change_set_id: _kn_builtins.str = _kn_pydantic.Field(alias='change_set_id', description='change_sets: change set id.', json_schema_extra={'x-kn': {'fieldId': 'identity.change_sets.change_set_id', 'foreignKey': {'fields': ['change_set_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    version_id: _kn_builtins.str = _kn_pydantic.Field(alias='version_id', description='change_sets: version id.', json_schema_extra={'x-kn': {'fieldId': 'identity.change_sets.version_id', 'foreignKey': {'fields': ['version_id'], 'table': 'source_versions', 'targetFields': ['version_id']}}})
    changes_json: _kn_builtins.str = _kn_pydantic.Field(alias='changes_json', description='change_sets: changes json.', json_schema_extra={'x-kn': {'fieldId': 'identity.change_sets.changes_json'}})

class Identifiers(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    identifier_id: _kn_builtins.str = _kn_pydantic.Field(alias='identifier_id', description='identifiers: identifier id.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.identifier_id', 'foreignKey': {'fields': ['identifier_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='identifiers: kn id.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.kn_id', 'foreignKey': {'fields': ['kn_id'], 'table': 'objects', 'targetFields': ['kn_id']}}})
    namespace: _kn_builtins.str = _kn_pydantic.Field(alias='namespace', description='identifiers: namespace.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.namespace'}})
    value: _kn_builtins.str = _kn_pydantic.Field(alias='value', description='identifiers: value.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.value'}})
    issuer: _kn_builtins.str = _kn_pydantic.Field(alias='issuer', description='identifiers: issuer.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.issuer'}})
    authority: _kn_typing.Literal['authoritative', 'source_qualified', 'weak'] = _kn_pydantic.Field(alias='authority', description='identifiers: authority.', json_schema_extra={'x-kn': {'enum': ['authoritative', 'source_qualified', 'weak'], 'fieldId': 'identity.identifiers.authority'}})
    valid_from: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='valid_from', description='identifiers: valid from.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.valid_from'}})
    valid_to: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='valid_to', description='identifiers: valid to.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.valid_to'}})
    evidence: _kn_builtins.str = _kn_pydantic.Field(alias='evidence', description='identifiers: evidence.', json_schema_extra={'x-kn': {'fieldId': 'identity.identifiers.evidence'}})

class LifecycleEvents(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    event_id: _kn_builtins.str = _kn_pydantic.Field(alias='event_id', description='lifecycle_events: event id.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.event_id'}})
    sequence: _kn_typing.Annotated[_kn_builtins.int, _kn_pydantic.Field(ge=-9223372036854775808, le=9223372036854775807)] = _kn_pydantic.Field(alias='sequence', description='lifecycle_events: sequence.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.sequence'}})
    previous: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='previous', description='lifecycle_events: previous.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.previous', 'foreignKey': {'fields': ['previous'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    kind: _kn_typing.Literal['minted', 'linked', 'unlinked', 'merged', 'split', 'reclassified', 'retired', 'restored', 'identifier_recorded', 'attribute_recorded', 'version_recorded', 'match_recorded', 'changes_recorded'] = _kn_pydantic.Field(alias='kind', description='lifecycle_events: kind.', json_schema_extra={'x-kn': {'enum': ['minted', 'linked', 'unlinked', 'merged', 'split', 'reclassified', 'retired', 'restored', 'identifier_recorded', 'attribute_recorded', 'version_recorded', 'match_recorded', 'changes_recorded'], 'fieldId': 'identity.lifecycle_events.kind'}})
    occurred_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='occurred_at', description='lifecycle_events: occurred at.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.occurred_at'}})
    actor: _kn_builtins.str = _kn_pydantic.Field(alias='actor', description='lifecycle_events: actor.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.actor'}})
    reason: _kn_builtins.str = _kn_pydantic.Field(alias='reason', description='lifecycle_events: reason.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.reason'}})
    evidence: _kn_builtins.str = _kn_pydantic.Field(alias='evidence', description='lifecycle_events: evidence.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.evidence'}})
    decision_ref: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='decision_ref', description='lifecycle_events: decision ref.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.decision_ref'}})
    event_json: _kn_builtins.str = _kn_pydantic.Field(alias='event_json', description='lifecycle_events: event json.', json_schema_extra={'x-kn': {'fieldId': 'identity.lifecycle_events.event_json'}})

class Links(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    link_id: _kn_builtins.str = _kn_pydantic.Field(alias='link_id', description='links: link id.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.link_id', 'foreignKey': {'fields': ['link_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    record_id: _kn_builtins.str = _kn_pydantic.Field(alias='record_id', description='links: record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.record_id', 'foreignKey': {'fields': ['record_id'], 'table': 'source_records', 'targetFields': ['record_id']}}})
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='links: kn id.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.kn_id', 'foreignKey': {'fields': ['kn_id'], 'table': 'objects', 'targetFields': ['kn_id']}}})
    method: _kn_typing.Literal['authoritative_key', 'existing_link', 'scored_match', 'review_decision', 'minted'] = _kn_pydantic.Field(alias='method', description='links: method.', json_schema_extra={'x-kn': {'enum': ['authoritative_key', 'existing_link', 'scored_match', 'review_decision', 'minted'], 'fieldId': 'identity.links.method'}})
    score: _kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits=38, decimal_places=18, allow_inf_nan=False)] | None = _kn_pydantic.Field(default=None, alias='score', description='links: score.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.score'}})
    probability: _kn_typing.Annotated[_kn_decimal.Decimal, _kn_pydantic.Field(max_digits=38, decimal_places=18, allow_inf_nan=False)] | None = _kn_pydantic.Field(default=None, alias='probability', description='links: probability.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.probability'}})
    profile_digest: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='profile_digest', description='links: profile digest.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.profile_digest'}})
    profile_version: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='profile_version', description='links: profile version.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.profile_version'}})
    match_id: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='match_id', description='links: match id.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.match_id', 'foreignKey': {'fields': ['match_id'], 'table': 'matches', 'targetFields': ['match_id']}}})
    decision_ref: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='decision_ref', description='links: decision ref.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.decision_ref'}})
    ended_event: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='ended_event', description='links: ended event.', json_schema_extra={'x-kn': {'fieldId': 'identity.links.ended_event', 'foreignKey': {'fields': ['ended_event'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})

class Matches(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    match_id: _kn_builtins.str = _kn_pydantic.Field(alias='match_id', description='matches: match id.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.match_id', 'foreignKey': {'fields': ['match_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    record_id: _kn_builtins.str = _kn_pydantic.Field(alias='record_id', description='matches: record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.record_id', 'foreignKey': {'fields': ['record_id'], 'table': 'source_records', 'targetFields': ['record_id']}}})
    profile_digest: _kn_builtins.str = _kn_pydantic.Field(alias='profile_digest', description='matches: profile digest.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.profile_digest'}})
    profile_version: _kn_builtins.str = _kn_pydantic.Field(alias='profile_version', description='matches: profile version.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.profile_version'}})
    candidates_json: _kn_builtins.str = _kn_pydantic.Field(alias='candidates_json', description='matches: candidates json.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.candidates_json'}})
    decision: _kn_typing.Literal['link', 'review', 'mint'] = _kn_pydantic.Field(alias='decision', description='matches: decision.', json_schema_extra={'x-kn': {'enum': ['link', 'review', 'mint'], 'fieldId': 'identity.matches.decision'}})
    selected: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='selected', description='matches: selected.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.selected', 'foreignKey': {'fields': ['selected'], 'table': 'objects', 'targetFields': ['kn_id']}}})
    decision_ref: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='decision_ref', description='matches: decision ref.', json_schema_extra={'x-kn': {'fieldId': 'identity.matches.decision_ref'}})

class Objects(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='objects: kn id.', json_schema_extra={'x-kn': {'fieldId': 'identity.objects.kn_id'}})
    entity_class: _kn_builtins.str = _kn_pydantic.Field(alias='entity_class', description='objects: entity class.', json_schema_extra={'x-kn': {'fieldId': 'identity.objects.entity_class'}})
    state: _kn_typing.Literal['active', 'merged', 'split', 'retired'] = _kn_pydantic.Field(alias='state', description='objects: state.', json_schema_extra={'x-kn': {'enum': ['active', 'merged', 'split', 'retired'], 'fieldId': 'identity.objects.state'}})
    anchor_record_id: _kn_builtins.str = _kn_pydantic.Field(alias='anchor_record_id', description='objects: anchor record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.objects.anchor_record_id', 'foreignKey': {'fields': ['anchor_record_id'], 'table': 'source_records', 'targetFields': ['record_id']}}})
    mint_event: _kn_builtins.str = _kn_pydantic.Field(alias='mint_event', description='objects: mint event.', json_schema_extra={'x-kn': {'fieldId': 'identity.objects.mint_event', 'foreignKey': {'fields': ['mint_event'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    current_redirect: _kn_builtins.str | None = _kn_pydantic.Field(default=None, alias='current_redirect', description='objects: current redirect.', json_schema_extra={'x-kn': {'fieldId': 'identity.objects.current_redirect', 'foreignKey': {'fields': ['current_redirect'], 'table': 'objects', 'targetFields': ['kn_id']}}})

class Redirects(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    kn_id: _kn_builtins.str = _kn_pydantic.Field(alias='kn_id', description='redirects: kn id.', json_schema_extra={'x-kn': {'fieldId': 'identity.redirects.kn_id', 'foreignKey': {'fields': ['kn_id'], 'table': 'objects', 'targetFields': ['kn_id']}}})
    successor: _kn_builtins.str = _kn_pydantic.Field(alias='successor', description='redirects: successor.', json_schema_extra={'x-kn': {'fieldId': 'identity.redirects.successor', 'foreignKey': {'fields': ['successor'], 'table': 'objects', 'targetFields': ['kn_id']}}})

class SourceRecords(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    record_id: _kn_builtins.str = _kn_pydantic.Field(alias='record_id', description='source_records: record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_records.record_id'}})
    source: _kn_builtins.str = _kn_pydantic.Field(alias='source', description='source_records: source.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_records.source'}})
    native_key: _kn_builtins.str = _kn_pydantic.Field(alias='native_key', description='source_records: native key.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_records.native_key'}})
    last_seen: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='last_seen', description='source_records: last seen.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_records.last_seen'}})

class SourceVersions(_kn_pydantic.BaseModel):
    model_config = _kn_pydantic.ConfigDict(extra='forbid', strict=True)
    version_id: _kn_builtins.str = _kn_pydantic.Field(alias='version_id', description='source_versions: version id.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.version_id', 'foreignKey': {'fields': ['version_id'], 'table': 'lifecycle_events', 'targetFields': ['event_id']}}})
    record_id: _kn_builtins.str = _kn_pydantic.Field(alias='record_id', description='source_versions: record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.record_id', 'foreignKey': {'fields': ['record_id'], 'table': 'source_records', 'targetFields': ['record_id']}}})
    version: _kn_builtins.str = _kn_pydantic.Field(alias='version', description='source_versions: version.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.version'}})
    content_digest: _kn_builtins.str = _kn_pydantic.Field(alias='content_digest', description='source_versions: content digest.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.content_digest'}})
    field_hashes_json: _kn_builtins.str = _kn_pydantic.Field(alias='field_hashes_json', description='source_versions: field hashes json.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.field_hashes_json'}})
    observed_at: _kn_pydantic.AwareDatetime = _kn_pydantic.Field(alias='observed_at', description='source_versions: observed at.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.observed_at'}})
    source_updated_at: _kn_pydantic.AwareDatetime | None = _kn_pydantic.Field(default=None, alias='source_updated_at', description='source_versions: source updated at.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.source_updated_at'}})
    fetch_id: _kn_builtins.str = _kn_pydantic.Field(alias='fetch_id', description='source_versions: fetch id.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.fetch_id'}})
    archive_record_id: _kn_builtins.str = _kn_pydantic.Field(alias='archive_record_id', description='source_versions: archive record id.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.archive_record_id'}})
    code_digest: _kn_builtins.str = _kn_pydantic.Field(alias='code_digest', description='source_versions: code digest.', json_schema_extra={'x-kn': {'fieldId': 'identity.source_versions.code_digest'}})
