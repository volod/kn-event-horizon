"""Synthetic JSON adapter loaded only by the ingestion acceptance harness."""

import json

from pydantic import BaseModel, ConfigDict, ValidationError

from kn.engine.adapter import NativeRecord, Snapshot
from kn.engine.outcomes import RunFailure
from kn.identity.profiles import Agreement, Attribute, Profile
from kn.review.model import digest


class Row(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    name: str
    language: str = "und"


class Payload(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    records: list[Row]


IDENTITY = Profile(
    profile_id="fixture.record",
    version="1",
    entity_class="fixture.record",
    blocking_keys=(("fixture.record.id",),),
    attributes=(
        Attribute(
            field_id="fixture.record.id",
            normalizer="casefold-v1",
            comparator="exact",
            authority="source_qualified",
            discriminating=True,
            agreements=(
                Agreement(outcome="agree", m=0.9, u=0.1),
                Agreement(outcome="disagree", m=0.1, u=0.9),
            ),
        ),
    ),
    prior=0.01,
    review_threshold=0.5,
    link_threshold=0.9,
    minimum_margin=0.05,
)
FINGERPRINT = digest(Payload.model_json_schema())


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    if len(dict(pairs)) != len(pairs):
        raise ValueError("duplicate JSON property")
    return dict(pairs)


def parse(body: bytes) -> Snapshot:
    try:
        parsed = json.loads(body.decode("utf-8"), object_pairs_hook=_unique)
    except (ValueError, RecursionError):
        raise RunFailure("payload_invalid") from None
    try:
        rows = Payload.model_validate(parsed).records
    except ValidationError:
        raise RunFailure("schema_drift") from None
    records = tuple(
        NativeRecord(f"/records/{index}", {"id": row.id, "name": row.name}, row.language)
        for index, row in enumerate(rows)
    )
    return Snapshot(FINGERPRINT, IDENTITY, records)
