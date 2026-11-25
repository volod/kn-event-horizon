"""Claim values: exactly one typed value or a missing reason, never a zero default."""

from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import Field, StrictBool, model_validator

from kn.contracts.sqlalchemy import PARTIAL_DATE
from kn.evidence.records import NUMBER_INTEGER_DIGITS, NUMBER_SCALE, SourceString, exact
from kn.evidence.vocabulary import MissingReason
from kn.i18n.data import TextVariant
from kn.identity.model import KnId
from kn.review.model import Frozen, Text

VALUE_COLUMNS = (
    "value_text",
    "value_language",
    "value_number",
    "value_boolean",
    "value_date",
    "value_concept",
    "value_kn_id",
    "missing_reason",
    "normalized_unit",
    "conversion_rule",
)


class TextValue(Frozen):
    kind: Literal["text"] = "text"
    text: SourceString
    language: Text

    @model_validator(mode="after")
    def _language(self) -> Self:
        TextVariant(self.text, self.language, "claim")
        return self

    def columns(self) -> dict[str, Any]:
        return {"value_text": self.text, "value_language": self.language}


class NumberValue(Frozen):
    kind: Literal["number"] = "number"
    number: Decimal
    normalized_unit: Text | None = None
    conversion_rule: Text | None = None

    @model_validator(mode="after")
    def _exact(self) -> Self:
        object.__setattr__(self, "number", exact(self.number, NUMBER_SCALE, NUMBER_INTEGER_DIGITS))
        if (self.normalized_unit is None) != (self.conversion_rule is None):
            raise ValueError("a normalized unit needs the conversion rule that produced it")
        return self

    def columns(self) -> dict[str, Any]:
        return {
            "value_number": self.number,
            "normalized_unit": self.normalized_unit,
            "conversion_rule": self.conversion_rule,
        }


class BooleanValue(Frozen):
    kind: Literal["boolean"] = "boolean"
    boolean: StrictBool

    def columns(self) -> dict[str, Any]:
        return {"value_boolean": self.boolean}


class DateValue(Frozen):
    kind: Literal["date"] = "date"
    date: Annotated[Text, Field(pattern=PARTIAL_DATE)]

    def columns(self) -> dict[str, Any]:
        return {"value_date": self.date}


class ConceptValue(Frozen):
    kind: Literal["concept"] = "concept"
    concept: Text

    def columns(self) -> dict[str, Any]:
        return {"value_concept": self.concept}


class ObjectValue(Frozen):
    kind: Literal["object"] = "object"
    kn_id: KnId

    def columns(self) -> dict[str, Any]:
        return {"value_kn_id": self.kn_id}


class Missing(Frozen):
    """Unknown is not zero: a stated absence with its reason."""

    kind: Literal["missing"] = "missing"
    reason: MissingReason

    def columns(self) -> dict[str, Any]:
        return {"missing_reason": self.reason}


type Value = Annotated[
    TextValue | NumberValue | BooleanValue | DateValue | ConceptValue | ObjectValue | Missing,
    Field(discriminator="kind"),
]


def value_columns(value: Value) -> dict[str, Any]:
    """Exactly one value column or the missing reason is non-null, as the contract checks."""
    return {**dict.fromkeys(VALUE_COLUMNS), **value.columns()}
