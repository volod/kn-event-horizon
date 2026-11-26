# kn.core.evidence

Version: 1.0.0

Digest: `59cc497a134eca6ae6d877c7d6cbbcb2ad93d93f6de1ff44e6a112a2fdac4a80`

Storage schema: `evidence`

## aliases

Weak, non-unique alias identifiers of objects.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| alias_id | evidence.aliases.alias_id | string | True | True | SHA-256 of the object, text, language and claim |
| kn_id | evidence.aliases.kn_id | string | True | False | Object the alias weakly identifies |
| alias | evidence.aliases.alias | string | True | False | Alias text exactly as stated |
| language | evidence.aliases.language | string | True | False | BCP-47 tag of the alias; und when unknown |
| normalized_key | evidence.aliases.normalized_key | string | True | False | Normalized lookup key; not unique |
| normalizer | evidence.aliases.normalizer | string | True | False | Normalizer that produced the key |
| claim_key | evidence.aliases.claim_key | string | True | False | Claim that states the alias |
| recorded_at | evidence.aliases.recorded_at | timestamp | True | False | UTC time KN recorded the alias |

## canonical_facts

Bitemporal projection of selected claims and unresolved fields.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| fact_version_id | evidence.canonical_facts.fact_version_id | string | True | True | SHA-256 of the fact key, selection content and knowledge start |
| fact_key | evidence.canonical_facts.fact_key | string | True | False | SHA-256 of object, field, conditions and audience |
| kn_id | evidence.canonical_facts.kn_id | string | True | False | Object of the fact; a survivor after merges |
| field_id | evidence.canonical_facts.field_id | string | True | False | Stable contract field ID |
| conditions_json | evidence.canonical_facts.conditions_json | string | True | False | Canonical JSON condition set; {} when unconditioned |
| audience | evidence.canonical_facts.audience | string | True | False | Audience whose eligible evidence was selected |
| claim_key | evidence.canonical_facts.claim_key | string | False | False | Selected claim; null when unresolved |
| unresolved_reason | evidence.canonical_facts.unresolved_reason | string | False | False | Why no claim is selected |
| mode | evidence.canonical_facts.mode | string | True | False | Update policy mode |
| policy_digest | evidence.canonical_facts.policy_digest | string | True | False | SHA-256 of the canonical update policy |
| outcome | evidence.canonical_facts.outcome | string | True | False | Outcome of the change that produced this version; ignored claims leave no version |
| deciding_criterion | evidence.canonical_facts.deciding_criterion | string | True | False | Criterion that decided the outcome |
| winner_criteria_json | evidence.canonical_facts.winner_criteria_json | string | True | False | Canonical criteria values of the winner |
| runner_up_criteria_json | evidence.canonical_facts.runner_up_criteria_json | string | False | False | Canonical criteria values of the runner-up |
| verification_state | evidence.canonical_facts.verification_state | string | True | False | Derived verification label |
| owner_override | evidence.canonical_facts.owner_override | boolean | True | False | An owner-entered value outranks a differing first-party value |
| review_item_id | evidence.canonical_facts.review_item_id | string | False | False | Open review item for this version |
| valid_from | evidence.canonical_facts.valid_from | timestamp | False | False | Inclusive start of validity (UTC); null when unknown |
| valid_from_precision | evidence.canonical_facts.valid_from_precision | string | False | False | Precision of valid_from; present exactly when it is |
| valid_to | evidence.canonical_facts.valid_to | timestamp | False | False | Exclusive end of validity (UTC); null when unknown |
| valid_to_precision | evidence.canonical_facts.valid_to_precision | string | False | False | Precision of valid_to; present exactly when it is |
| knowledge_from | evidence.canonical_facts.knowledge_from | timestamp | True | False | Inclusive UTC knowledge time of this version |
| knowledge_to | evidence.canonical_facts.knowledge_to | timestamp | False | False | Exclusive UTC knowledge end; null while current |

## claim_confirmations

Re-observations of unchanged claim values.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| confirmation_id | evidence.claim_confirmations.confirmation_id | string | True | True | SHA-256 of the claim key, source version and fetch |
| claim_key | evidence.claim_confirmations.claim_key | string | True | False | Unchanged claim that was observed again |
| source_version_id | evidence.claim_confirmations.source_version_id | string | True | False | Source record version that repeated the value |
| evidence_id | evidence.claim_confirmations.evidence_id | string | True | False | Evidence of the re-observation |
| fetch_id | evidence.claim_confirmations.fetch_id | string | True | False | Fetch ID of the re-observation |
| observed_at | evidence.claim_confirmations.observed_at | timestamp | True | False | UTC time of the re-observation |
| recorded_at | evidence.claim_confirmations.recorded_at | timestamp | True | False | UTC time KN recorded the confirmation |

## claims

Immutable claims about KN objects with claim-level provenance.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| claim_key | evidence.claims.claim_key | string | True | True | Deterministic SHA-256 of the claim content and its evidence |
| kn_id | evidence.claims.kn_id | string | True | False | KN ID of the object the claim is about |
| field_id | evidence.claims.field_id | string | True | False | Stable contract field ID the claim states |
| conditions_json | evidence.claims.conditions_json | string | True | False | Canonical JSON object of conditions; {} when unconditioned |
| source_id | evidence.claims.source_id | string | True | False | Qualified source catalogue ID |
| record_id | evidence.claims.record_id | string | True | False | Identity source record that stated the value |
| source_version_id | evidence.claims.source_version_id | string | True | False | Identity source record version that stated the value |
| change_set_id | evidence.claims.change_set_id | string | False | False | Identity change set that produced the claim, when tracked |
| change_kind | evidence.claims.change_kind | string | True | False | Change that produced the claim |
| supersedes | evidence.claims.supersedes | string | False | False | Earlier claim of the same record and field |
| decision_ref | evidence.claims.decision_ref | string | False | False | Review decision that produced an owner-entered claim |
| evidence_id | evidence.claims.evidence_id | string | True | False | Evidence that carries the full provenance |
| fetch_id | evidence.claims.fetch_id | string | True | False | Fetch ID of the evidence |
| origin_uri | evidence.claims.origin_uri | string | True | False | Redacted origin URI of the evidence |
| fetched_at | evidence.claims.fetched_at | timestamp | True | False | UTC fetch time of the evidence |
| original_value | evidence.claims.original_value | string | False | False | Value exactly as the source states it |
| original_unit | evidence.claims.original_unit | string | False | False | Unit exactly as the source states it |
| value_text | evidence.claims.value_text | string | False | False | Normalized text value in its original language |
| value_language | evidence.claims.value_language | string | False | False | BCP-47 tag of value_text; und when unknown |
| value_number | evidence.claims.value_number | number | False | False | Exact normalized decimal value |
| value_boolean | evidence.claims.value_boolean | boolean | False | False | Normalized boolean value |
| value_date | evidence.claims.value_date | string | False | False | Partial ISO date value |
| value_concept | evidence.claims.value_concept | string | False | False | Qualified semantic concept ID value |
| value_kn_id | evidence.claims.value_kn_id | string | False | False | KN ID of a referenced object |
| missing_reason | evidence.claims.missing_reason | string | False | False | Why no value is stated; exclusive with every value |
| normalized_unit | evidence.claims.normalized_unit | string | False | False | Unit of value_number after conversion |
| conversion_rule | evidence.claims.conversion_rule | string | False | False | Rule that converted the original unit |
| assertion_type | evidence.claims.assertion_type | string | True | False | How the source asserts the value |
| evidence_class | evidence.claims.evidence_class | string | True | False | Evidence class used by selection |
| extraction_confidence | evidence.claims.extraction_confidence | number | False | False | Extraction confidence from 0 to 1, never a truth probability |
| source_verification_label | evidence.claims.source_verification_label | string | False | False | Imported source verification label; never human verification |
| event_at | evidence.claims.event_at | timestamp | False | False | Time the described event happened (UTC); null when unknown |
| event_precision | evidence.claims.event_precision | string | False | False | Precision of event_at; present exactly when it is |
| published_at | evidence.claims.published_at | timestamp | False | False | Time the source published the value (UTC); null when unknown |
| published_precision | evidence.claims.published_precision | string | False | False | Precision of published_at; present exactly when it is |
| valid_from | evidence.claims.valid_from | timestamp | False | False | Inclusive start of validity (UTC); null when unknown |
| valid_from_precision | evidence.claims.valid_from_precision | string | False | False | Precision of valid_from; present exactly when it is |
| valid_to | evidence.claims.valid_to | timestamp | False | False | Exclusive end of validity (UTC); null when unknown |
| valid_to_precision | evidence.claims.valid_to_precision | string | False | False | Precision of valid_to; present exactly when it is |
| observed_at | evidence.claims.observed_at | timestamp | True | False | UTC time the value was observed |
| recorded_at | evidence.claims.recorded_at | timestamp | True | False | UTC knowledge time KN recorded the claim |

## evidence_records

Fetch-level provenance of claims: origin, locator, rights and digests.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| evidence_id | evidence.evidence_records.evidence_id | string | True | True | SHA-256 of the canonical provenance content |
| source_id | evidence.evidence_records.source_id | string | True | False | Qualified source catalogue ID |
| fetch_id | evidence.evidence_records.fetch_id | string | True | False | Fetch run that retrieved the bytes |
| archive_record_id | evidence.evidence_records.archive_record_id | string | False | False | Raw archive record; null only for review decisions and curated entries |
| origin_uri | evidence.evidence_records.origin_uri | string | True | False | Origin URI after credential redaction |
| fetched_at | evidence.evidence_records.fetched_at | timestamp | True | False | UTC fetch or capture time |
| locator_kind | evidence.evidence_records.locator_kind | string | True | False | Kind of native record locator |
| locator | evidence.evidence_records.locator | string | True | False | Native locator inside the archived record |
| excerpt | evidence.evidence_records.excerpt | string | False | False | Original excerpt, stored only when its rights permit |
| excerpt_rights | evidence.evidence_records.excerpt_rights | string | False | False | Rights reference that permits the stored excerpt |
| rights | evidence.evidence_records.rights | string | True | False | Rights or license policy reference of the evidence |
| code_digest | evidence.evidence_records.code_digest | string | True | False | SHA-256 of the parser or mapping code |
| contract_digest | evidence.evidence_records.contract_digest | string | True | False | Digest of the contract the parser applied |
| curator | evidence.evidence_records.curator | string | False | False | Curator of a curated observation |
| recorded_at | evidence.evidence_records.recorded_at | timestamp | True | False | UTC time KN recorded the evidence |

## relation_assertions

Typed relations between objects with no active duplicates.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| assertion_id | evidence.relation_assertions.assertion_id | string | True | True | SHA-256 of the relation key and the claim that opened it |
| relation_key | evidence.relation_assertions.relation_key | string | True | False | SHA-256 of subject, type, object, qualifiers and validity |
| subject_kn_id | evidence.relation_assertions.subject_kn_id | string | True | False | Subject object |
| relation_type | evidence.relation_assertions.relation_type | string | True | False | Ontology relation type ID |
| object_kn_id | evidence.relation_assertions.object_kn_id | string | True | False | Object at the other endpoint |
| qualifiers_json | evidence.relation_assertions.qualifiers_json | string | True | False | Canonical JSON object of qualifiers; {} when none |
| valid_from | evidence.relation_assertions.valid_from | timestamp | False | False | Inclusive start of validity (UTC); null when unknown |
| valid_from_precision | evidence.relation_assertions.valid_from_precision | string | False | False | Precision of valid_from; present exactly when it is |
| valid_to | evidence.relation_assertions.valid_to | timestamp | False | False | Exclusive end of validity (UTC); null when unknown |
| valid_to_precision | evidence.relation_assertions.valid_to_precision | string | False | False | Precision of valid_to; present exactly when it is |
| review_state | evidence.relation_assertions.review_state | string | True | False | Review state of the assertion |
| decision_ref | evidence.relation_assertions.decision_ref | string | False | False | Review decision behind the review state |
| opened_by | evidence.relation_assertions.opened_by | string | True | False | Claim that first asserted the relation |
| opened_at | evidence.relation_assertions.opened_at | timestamp | True | False | UTC knowledge time the assertion became active |
| closed_at | evidence.relation_assertions.closed_at | timestamp | False | False | UTC knowledge time the assertion stopped being active |
| close_reason | evidence.relation_assertions.close_reason | string | False | False | Why the assertion closed |

## relation_supports

Claims that support a relation assertion.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| assertion_id | evidence.relation_supports.assertion_id | string | True | True | Supported relation assertion |
| claim_key | evidence.relation_supports.claim_key | string | True | True | Claim that supports the assertion |
| recorded_at | evidence.relation_supports.recorded_at | timestamp | True | False | UTC time KN recorded the support |

## review_decisions

Append-only review decisions with reviewer, reason and times.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| decision_id | evidence.review_decisions.decision_id | string | True | True | SHA-256 of the canonical decision event |
| item_id | evidence.review_decisions.item_id | string | True | False | Decided review item |
| outcome | evidence.review_decisions.outcome | string | True | False | Append-only decision outcome |
| selected_claim_key | evidence.review_decisions.selected_claim_key | string | False | False | Claim selected by a select decision |
| predecessor | evidence.review_decisions.predecessor | string | False | False | Earlier decision this one supersedes |
| reviewer | evidence.review_decisions.reviewer | string | True | False | Authenticated reviewer principal |
| reason | evidence.review_decisions.reason | string | True | False | Reviewer's reason |
| performed_at | evidence.review_decisions.performed_at | timestamp | True | False | UTC time of the human decision |
| recorded_at | evidence.review_decisions.recorded_at | timestamp | True | False | Separate UTC journal recording time |
| human_verification_decision_id | evidence.review_decisions.human_verification_decision_id | string | False | False | Shared human verification decision, when the decision also verifies |
| event_json | evidence.review_decisions.event_json | string | True | False | Canonical decision event; authoritative replay payload |

## review_items

Candidates, conflicts and quarantine awaiting human review.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| item_id | evidence.review_items.item_id | string | True | True | SHA-256 of the kind, subject and sorted candidates |
| kind | evidence.review_items.kind | string | True | False | Registered review item kind |
| kn_id | evidence.review_items.kn_id | string | False | False | Object under review, when the item has one |
| field_id | evidence.review_items.field_id | string | False | False | Field under review, when the item has one |
| fact_key | evidence.review_items.fact_key | string | False | False | Fact under review, when the item has one |
| candidates_json | evidence.review_items.candidates_json | string | True | False | Canonical sorted array of candidate claim keys or references |
| reason_code | evidence.review_items.reason_code | string | True | False | Stable reason code |
| opened_by | evidence.review_items.opened_by | string | True | False | Selection, run or match record that opened the item |
| opened_at | evidence.review_items.opened_at | timestamp | True | False | UTC time the item opened |

## selection_outcomes

Explained outcome of each claim evaluated by selection.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| outcome_id | evidence.selection_outcomes.outcome_id | string | True | True | SHA-256 of the fact version and evaluated claim |
| fact_key | evidence.selection_outcomes.fact_key | string | True | False | Fact whose selection evaluated the claim |
| claim_key | evidence.selection_outcomes.claim_key | string | True | False | Evaluated claim |
| fact_version_id | evidence.selection_outcomes.fact_version_id | string | True | False | Fact version current after the evaluation |
| outcome | evidence.selection_outcomes.outcome | string | True | False | Explained outcome for the claim |
| criterion | evidence.selection_outcomes.criterion | string | True | False | Deciding criterion |
| criteria_json | evidence.selection_outcomes.criteria_json | string | True | False | Canonical criteria values of the evaluated claim |
| recorded_at | evidence.selection_outcomes.recorded_at | timestamp | True | False | UTC time of the evaluation |

## text_translations

Derived translations of text claims; originals stay unchanged.

| Field | Stable ID | Type | Required | Primary key | Description |
| --- | --- | --- | --- | --- | --- |
| translation_id | evidence.text_translations.translation_id | string | True | True | SHA-256 of the claim, language, text and provenance |
| claim_key | evidence.text_translations.claim_key | string | True | False | Text claim whose original stays unchanged |
| language | evidence.text_translations.language | string | True | False | BCP-47 tag of the translation |
| text | evidence.text_translations.text | string | True | False | Derived translated text |
| method | evidence.text_translations.method | string | True | False | Who produced the translation |
| provenance | evidence.text_translations.provenance | string | True | False | Source record, review or model and prompt reference |
| recorded_at | evidence.text_translations.recorded_at | timestamp | True | False | UTC time KN recorded the translation |

## Contract metadata

All ODCS and KN metadata is retained in `contract.json`.
Reference definitions used for compilation are in `references.json`.
