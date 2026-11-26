"""Claims from ranked fixture sources for canonical selection tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from kn.evidence.model import Claim
from kn.evidence.policy import UpdatePolicy
from kn.evidence.ranking import Context, RankTable, Reviews
from kn.evidence.records import Time
from kn.evidence.selection import Selection, Subject, select
from kn.evidence.values import Missing, NumberValue, ObjectValue, TextValue, Value
from kn.review.model import digest
from kn.sources.ranks import Override
from tests.evidence.fixtures import claim, evidence

T0 = datetime(2026, 3, 1, 12, tzinfo=UTC)
PART = "kn:0190a5f0-0000-7000-8000-0000000000a1"
MASS = "microelectronics.part.mass"
PRICE = "microelectronics.offer.unit_price"
OWNER = "micro:owner"
MAKER = "micro:maker"
MAKER_TWO = "micro:maker-two"
MAKER_THREE = "micro:maker-three"
DISTRIBUTOR = "micro:distributor"
AGGREGATOR = "micro:aggregator"
AGGREGATOR_TWO = "micro:aggregator-two"
UNLISTED = "micro:unlisted"
SIGNAL = "gdelt:row-5"
RANKS = RankTable(
    (
        Override(source_id=OWNER, rank="owner_entered"),
        Override(source_id=MAKER, rank="first_party"),
        Override(source_id=MAKER_TWO, rank="first_party"),
        Override(source_id=MAKER_THREE, rank="first_party"),
        Override(source_id=DISTRIBUTOR, rank="authorized_channel"),
        Override(source_id=DISTRIBUTOR, rank="first_party", field_group="microelectronics.offer"),
        Override(source_id=AGGREGATOR, rank="third_party"),
        Override(source_id=AGGREGATOR_TWO, rank="third_party"),
        Override(source_id=SIGNAL, rank="first_party"),
    )
)
CONTEXT = Context(ranks=RANKS)
POLICY: dict[str, Any] = {
    "mode": "priority",
    "priorityCriteria": ["source_rank", "evidence_class", "data_time"],
    "minimumSourceRank": "unranked",
    "minimumEvidenceClass": "derived",
    "timeBasis": "valid_from",
    "valueTolerance": 0,
    "freshnessSeconds": 0,
    "emptyValueHandling": "review",
}


def policy(**changes: Any) -> UpdatePolicy:
    return UpdatePolicy.model_validate({**POLICY, **changes})


def kg(number: str) -> NumberValue:
    return NumberValue(number=Decimal(number), normalized_unit="kg", conversion_rule="identity")


def tonnes(number: str) -> NumberValue:
    """A mass the mapping left in another normalized unit, which never agrees with kilograms."""
    return NumberValue(number=Decimal(number), normalized_unit="t", conversion_rule="identity")


def stated(
    source: str,
    value: Value | str,
    *,
    record: str = "1",
    at: datetime = T0,
    valid: datetime | None = None,
    **changes: Any,
) -> Claim:
    """A claim of one source's record; `at` is when KN recorded it."""
    fetched = changes.pop("fetched_at", T0 - timedelta(days=1))
    rights = changes.pop("rights", "license:fixture-open")
    item = kg(value) if isinstance(value, str) else value
    original = "" if isinstance(item, Missing) else str(value)
    data: dict[str, Any] = {
        "field_id": MASS,
        "kn_id": PART,
        "source_id": source,
        "record_id": digest([source, record]),
        "source_version_id": digest([source, record, "v1"]),
        "evidence": evidence(
            source_id=source,
            fetch_id=f"{source}/{record}",
            fetched_at=fetched,
            recorded_at=at,
            rights=rights,
        ),
        "original_value": original,
        "value": item,
        "valid_from": None if valid is None else Time(at=valid, precision="day"),
        "observed_at": fetched,
        "recorded_at": at,
    }
    return claim(**{**data, **changes})


def emptied(previous: Claim, at: datetime) -> Claim:
    """The next version of the same record states the field empty."""
    data = previous.model_dump()
    data.update(
        source_version_id=digest([previous.source_version_id, "next"]),
        change_kind="emptied",
        supersedes=previous.key,
        value={"kind": "missing", "reason": "source_empty"},
        original_value="",
        valid_from=None,
        recorded_at=at,
    )
    fetch = f"{previous.evidence.fetch_id}/next"
    data["evidence"] = {**data["evidence"], "fetch_id": fetch, "recorded_at": at}
    return Claim.model_validate(data)


def operator(kn_id: str) -> ObjectValue:
    return ObjectValue(kn_id=kn_id)


def name(text: str) -> TextValue:
    return TextValue(text=text, language="en")


def choose(
    claims: list[Claim],
    rule: UpdatePolicy | None = None,
    context: Context = CONTEXT,
    at: datetime | None = None,
) -> Selection | None:
    subject = Subject.of(claims[0])
    known = at or max(item.recorded_at for item in claims)
    return select(subject, claims, rule or policy(), context, known)


def reviewed(context: Context = CONTEXT, **reviews: dict[str, datetime]) -> Context:
    return Context(ranks=context.ranks, audience=context.audience, reviews=Reviews(**reviews))


def outcome_of(selection: Selection, item: Claim) -> tuple[str, str]:
    found = next(each for each in selection.explained if each.claim_key == item.key)
    return found.outcome, found.criterion
