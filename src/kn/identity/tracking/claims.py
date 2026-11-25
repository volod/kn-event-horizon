"""Claims and confirmations that a planned change set implies."""

from typing import Protocol

from kn.evidence.model import Claim, Confirmation
from kn.evidence.records import Record
from kn.evidence.values import Missing
from kn.evidence.vocabulary import ChangeKind
from kn.identity.model import Change, FieldChange
from kn.identity.tracking.changes import Baseline, Tracked
from kn.identity.tracking.delivery import Delivery, Statement
from kn.review.model import Instant

# Change classes that create a claim, and the claim's change kind.
CLAIM_KINDS: dict[Change, ChangeKind] = {
    "added": "added",
    "changed": "changed",
    "emptied": "emptied",
}


class ClaimIndex(Protocol):
    def claim(self, record_id: str, field_id: str, version_id: str) -> str | None:
        """The stored claim a record version made for a field, if any."""
        ...


def evidence_rows(
    tracked: Tracked, delivery: Delivery, claims: ClaimIndex, recorded_at: Instant
) -> tuple[Record, ...]:
    """Added, changed and emptied fields claim; unchanged fields confirm; others do nothing.

    A claim the version already made, for example before a later merge moved the record, is
    kept and not written again.
    """
    stated = {item.field_id: item for item in delivery.statements}
    record_id = delivery.record.record_id
    result: list[Record] = []
    for change in tracked.changes:
        if change.change in CLAIM_KINDS:
            if claims.claim(record_id, change.field_id, tracked.version_id) is None:
                item = stated[change.field_id]
                result.append(_claim(tracked, delivery, claims, change, item, recorded_at))
        elif change.change == "unchanged":
            item = stated[change.field_id]
            result.append(
                Confirmation(
                    claim_key=_previous(claims, record_id, change, tracked.baseline),
                    source_version_id=tracked.version_id,
                    evidence=delivery.evidence(item.locator, recorded_at),
                    observed_at=delivery.fetched_at,
                    recorded_at=recorded_at,
                )
            )
    return tuple(result)


def _claim(
    tracked: Tracked,
    delivery: Delivery,
    claims: ClaimIndex,
    change: FieldChange,
    item: Statement,
    recorded_at: Instant,
) -> Claim:
    record_id = delivery.record.record_id
    supersedes = None
    if change.change != "added":
        supersedes = _previous(claims, record_id, change, tracked.baseline)
    return Claim(
        kn_id=tracked.kn_id,
        field_id=change.field_id,
        conditions=item.conditions,
        source_id=delivery.record.source,
        record_id=record_id,
        source_version_id=tracked.version_id,
        change_set_id=tracked.change_set_id,
        change_kind=CLAIM_KINDS[change.change],
        supersedes=supersedes,
        evidence=delivery.evidence(item.locator, recorded_at),
        original_value=item.original_value,
        original_unit=item.original_unit,
        value=item.value if item.value is not None else Missing(reason="source_empty"),
        assertion_type=delivery.assertion_type,
        evidence_class=delivery.evidence_class,
        observed_at=delivery.fetched_at,
        recorded_at=recorded_at,
    )


def _previous(
    claims: ClaimIndex, record_id: str, change: FieldChange, baseline: dict[str, Baseline]
) -> str:
    known = baseline[change.field_id]
    key = claims.claim(record_id, change.field_id, known.version_id)
    if key is None:
        raise ValueError(
            f"the record's previous claim for {change.field_id} is missing; "
            "track its earlier versions first"
        )
    return key
