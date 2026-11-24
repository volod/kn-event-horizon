"""Versioned match profiles and semantic validation."""

import math
import re
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from kn.identity.matching.comparators import (
    AGREEING_OUTCOMES,
    COMPARISON_OUTCOMES,
    GRADED_OUTCOMES,
    Comparator,
)
from kn.identity.matching.likelihood import posterior, weight
from kn.identity.matching.normalizers import NORMALIZERS
from kn.identity.model import Authority
from kn.review.model import Frozen, Text, digest

type Chance = Annotated[float, Field(gt=0, lt=1, strict=True, allow_inf_nan=False)]


class Agreement(Frozen):
    outcome: Text
    m: Chance
    u: Chance


class Attribute(Frozen):
    field_id: Text
    normalizer: Text
    comparator: Comparator
    authority: Authority
    discriminating: bool = Field(strict=True)
    tolerance: Annotated[float, Field(ge=0, strict=True, allow_inf_nan=False)] | None = None
    agreements: tuple[Agreement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def outcomes(self) -> Self:
        expected = GRADED_OUTCOMES if self.comparator == "graded_string" else COMPARISON_OUTCOMES
        if (
            len(self.agreements) != len(expected)
            or {a.outcome for a in self.agreements} != expected
        ):
            raise ValueError("declare each comparator outcome exactly once")
        if not all(
            math.isclose(math.fsum(values), 1)
            for values in (
                [item.m for item in self.agreements],
                [item.u for item in self.agreements],
            )
        ):
            raise ValueError("m and u distributions must each sum to one")
        if self.normalizer not in NORMALIZERS:
            raise ValueError("unknown identity normalizer")
        if self.comparator in {"numeric_tolerance", "date_window"} and self.tolerance is None:
            raise ValueError("tolerance comparator requires an explicit tolerance")
        if self.tolerance is not None:
            limits = {"numeric_tolerance": math.inf, "date_window": math.inf, "set_overlap": 1}
            if self.tolerance > limits.get(self.comparator, -1):
                raise ValueError("tolerance is outside the comparator's supported range")
        if self.discriminating and (self.authority == "weak" or self.is_label):
            raise ValueError("weak attributes and name or description fields cannot discriminate")
        return self

    @property
    def is_label(self) -> bool:
        field = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", self.field_id)
        tokens = set(re.split(r"[^a-z0-9]+", field.lower()))
        return self.normalizer == "legal-name-v1" or bool(tokens & {"name", "description", "label"})

    @property
    def nondiscriminating_max(self) -> float:
        """Missing values are neutral and any nonqualifying outcome can coexist with a label."""
        return max(
            0.0,
            *(
                weight(a.m, a.u)
                for a in self.agreements
                if not self.discriminating or a.outcome not in AGREEING_OUTCOMES
            ),
        )


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
    minimum_margin: Annotated[float, Field(ge=0, le=1, strict=True, allow_inf_nan=False)]
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
        self._validate_blocking(fields)
        max_score = math.fsum(a.nondiscriminating_max for a in self.attributes)
        if posterior(self.prior, max_score) >= self.link_threshold:
            raise ValueError(
                "name or description and other nondiscriminating evidence can reach link threshold"
            )
        return self

    def _validate_blocking(self, fields: set[str]) -> None:
        for key in self.blocking_keys:
            if not key or len(set(key)) != len(key) or not set(key) <= fields:
                raise ValueError("blocking keys must name distinct declared attributes")
        weak_keys = {
            item.field_id
            for item in self.attributes
            if item.authority == "weak" and not item.is_label
        }
        if any(set(key) <= weak_keys for key in self.blocking_keys):
            raise ValueError("weak keys cannot block a match alone")

    @property
    def digest(self) -> str:
        return digest(self.model_dump(mode="json"))
