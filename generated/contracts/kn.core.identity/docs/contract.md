# kn.core.identity

Version: 1.0.0

Digest: `30574ce33df4be587e272e68d4644daa102e5df21ccc80bfc399980f2b2144d8`

Storage schema: `identity`

## attributes

Disposable projection of identity events: attributes.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| attribute_id | identity.attributes.attribute_id | string | True | True | attributes: attribute id. |
| kn_id | identity.attributes.kn_id | string | True | False | attributes: kn id. |
| field_id | identity.attributes.field_id | string | True | False | attributes: field id. |
| original | identity.attributes.original | string | True | False | attributes: original. |
| normalized | identity.attributes.normalized | string | True | False | attributes: normalized. |
| normalizer | identity.attributes.normalizer | string | True | False | attributes: normalizer. |
| profile_digest | identity.attributes.profile_digest | string | True | False | attributes: profile digest. |
| evidence | identity.attributes.evidence | string | True | False | attributes: evidence. |

## change_sets

Disposable projection of identity events: change sets.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| change_set_id | identity.change_sets.change_set_id | string | True | True | change_sets: change set id. |
| version_id | identity.change_sets.version_id | string | True | False | change_sets: version id. |
| changes_json | identity.change_sets.changes_json | string | True | False | change_sets: changes json. |

## identifiers

Disposable projection of identity events: identifiers.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| identifier_id | identity.identifiers.identifier_id | string | True | True | identifiers: identifier id. |
| kn_id | identity.identifiers.kn_id | string | True | False | identifiers: kn id. |
| namespace | identity.identifiers.namespace | string | True | False | identifiers: namespace. |
| value | identity.identifiers.value | string | True | False | identifiers: value. |
| issuer | identity.identifiers.issuer | string | True | False | identifiers: issuer. |
| authority | identity.identifiers.authority | string | True | False | identifiers: authority. |
| valid_from | identity.identifiers.valid_from | timestamp | True | False | identifiers: valid from. |
| valid_to | identity.identifiers.valid_to | timestamp | False | False | identifiers: valid to. |
| evidence | identity.identifiers.evidence | string | True | False | identifiers: evidence. |

## lifecycle_events

Disposable projection of identity events: lifecycle events.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| event_id | identity.lifecycle_events.event_id | string | True | True | lifecycle_events: event id. |
| sequence | identity.lifecycle_events.sequence | integer | True | False | lifecycle_events: sequence. |
| previous | identity.lifecycle_events.previous | string | False | False | lifecycle_events: previous. |
| kind | identity.lifecycle_events.kind | string | True | False | lifecycle_events: kind. |
| occurred_at | identity.lifecycle_events.occurred_at | timestamp | True | False | lifecycle_events: occurred at. |
| actor | identity.lifecycle_events.actor | string | True | False | lifecycle_events: actor. |
| reason | identity.lifecycle_events.reason | string | True | False | lifecycle_events: reason. |
| evidence | identity.lifecycle_events.evidence | string | True | False | lifecycle_events: evidence. |
| decision_ref | identity.lifecycle_events.decision_ref | string | False | False | lifecycle_events: decision ref. |
| event_json | identity.lifecycle_events.event_json | string | True | False | lifecycle_events: event json. |

## links

Disposable projection of identity events: links.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| link_id | identity.links.link_id | string | True | True | links: link id. |
| record_id | identity.links.record_id | string | True | False | links: record id. |
| kn_id | identity.links.kn_id | string | True | False | links: kn id. |
| method | identity.links.method | string | True | False | links: method. |
| score | identity.links.score | number | False | False | links: score. |
| probability | identity.links.probability | number | False | False | links: probability. |
| profile_digest | identity.links.profile_digest | string | False | False | links: profile digest. |
| profile_version | identity.links.profile_version | string | False | False | links: profile version. |
| match_id | identity.links.match_id | string | False | False | links: match id. |
| decision_ref | identity.links.decision_ref | string | False | False | links: decision ref. |
| ended_event | identity.links.ended_event | string | False | False | links: ended event. |

## matches

Disposable projection of identity events: matches.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| match_id | identity.matches.match_id | string | True | True | matches: match id. |
| record_id | identity.matches.record_id | string | True | False | matches: record id. |
| profile_digest | identity.matches.profile_digest | string | True | False | matches: profile digest. |
| profile_version | identity.matches.profile_version | string | True | False | matches: profile version. |
| candidates_json | identity.matches.candidates_json | string | True | False | matches: candidates json. |
| decision | identity.matches.decision | string | True | False | matches: decision. |
| selected | identity.matches.selected | string | False | False | matches: selected. |
| decision_ref | identity.matches.decision_ref | string | False | False | matches: decision ref. |

## objects

Disposable projection of identity events: objects.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| kn_id | identity.objects.kn_id | string | True | True | objects: kn id. |
| entity_class | identity.objects.entity_class | string | True | False | objects: entity class. |
| state | identity.objects.state | string | True | False | objects: state. |
| anchor_record_id | identity.objects.anchor_record_id | string | True | False | objects: anchor record id. |
| mint_event | identity.objects.mint_event | string | True | False | objects: mint event. |
| current_redirect | identity.objects.current_redirect | string | False | False | objects: current redirect. |
| revision_event | identity.objects.revision_event | string | True | False | Lifecycle event defining the current object revision. |

## redirects

Disposable projection of identity events: redirects.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| kn_id | identity.redirects.kn_id | string | True | True | redirects: kn id. |
| successor | identity.redirects.successor | string | True | True | redirects: successor. |

## source_records

Disposable projection of identity events: source records.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| record_id | identity.source_records.record_id | string | True | True | source_records: record id. |
| source | identity.source_records.source | string | True | False | source_records: source. |
| native_key | identity.source_records.native_key | string | True | False | source_records: native key. |
| last_seen | identity.source_records.last_seen | timestamp | False | False | source_records: last seen. |

## source_versions

Disposable projection of identity events: source versions.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| version_id | identity.source_versions.version_id | string | True | True | source_versions: version id. |
| record_id | identity.source_versions.record_id | string | True | False | source_versions: record id. |
| version | identity.source_versions.version | string | True | False | source_versions: version. |
| content_digest | identity.source_versions.content_digest | string | True | False | source_versions: content digest. |
| field_hashes_json | identity.source_versions.field_hashes_json | string | True | False | source_versions: field hashes json. |
| observed_at | identity.source_versions.observed_at | timestamp | True | False | source_versions: observed at. |
| source_updated_at | identity.source_versions.source_updated_at | timestamp | False | False | source_versions: source updated at. |
| fetch_id | identity.source_versions.fetch_id | string | True | False | source_versions: fetch id. |
| archive_record_id | identity.source_versions.archive_record_id | string | True | False | source_versions: archive record id. |
| code_digest | identity.source_versions.code_digest | string | True | False | source_versions: code digest. |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
