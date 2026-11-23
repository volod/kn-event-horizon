"""Structural v1 match profiles for later domain contracts and matching engines."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from kn.review.model import Frozen, Text, digest

type Chance = Annotated[float, Field(gt=0, lt=1, strict=True, allow_inf_nan=False)]


class Agreement(Frozen):
    outcome: Text
    m: Chance
    u: Chance


class Attribute(Frozen):
    field_id: Text
    normalizer: Text
    comparator: Literal[
        "exact",
        "normalized_exact",
        "graded_string",
        "numeric_tolerance",
        "date_window",
        "set_overlap",
    ]
    authority: Literal["authoritative", "source_qualified", "weak"]
    discriminating: bool = Field(strict=True)
    tolerance: Annotated[float, Field(ge=0, strict=True, allow_inf_nan=False)] | None = None
    agreements: tuple[Agreement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def outcomes(self) -> Self:
        if len({part.outcome for part in self.agreements}) != len(self.agreements):
            raise ValueError("agreement outcomes must be unique")
        if self.comparator in {"numeric_tolerance", "date_window"} and self.tolerance is None:
            raise ValueError("tolerance comparator requires an explicit tolerance")
        return self


class Profile(Frozen):
    schema_version: Literal[1] = 1
    profile_id: Text
    version: Text
    entity_class: Text
    blocking_keys: tuple[tuple[Text, ...], ...] = Field(min_length=1)
    attributes: tuple[Attribute, ...] = Field(min_length=1)
    prior: Chance
    review_threshold: Chance
    link_threshold: Chance
    minimum_margin: Annotated[float, Field(ge=0, strict=True, allow_inf_nan=False)]
    calibrated: bool = Field(default=False, strict=True)
    calibration_ref: Text | None = None

    @model_validator(mode="after")
    def structure(self) -> Self:
        fields = {item.field_id for item in self.attributes}
        if len(fields) != len(self.attributes):
            raise ValueError("profile attributes must be unique")
        if self.review_threshold >= self.link_threshold:
            raise ValueError("review threshold must be below link threshold")
        if self.calibrated and not self.calibration_ref:
            raise ValueError("calibrated profiles require an evaluation reference")
        for key in self.blocking_keys:
            if not key or len(set(key)) != len(key) or not set(key) <= fields:
                raise ValueError("blocking keys must name distinct declared attributes")
        return self

    @property
    def digest(self) -> str:
        return digest(self.model_dump(mode="json"))
