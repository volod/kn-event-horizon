"""Shared row conventions: deterministic keys, exact decimals and canonical JSON columns."""

from datetime import datetime
from decimal import Decimal, localcontext
from typing import Annotated, Any, ClassVar

from pydantic import AfterValidator, JsonValue, StrictStr

from kn.contracts.model import canonical
from kn.evidence.vocabulary import TimePrecision
from kn.review.model import Frozen, Instant
from kn.review.targets import content_version

NUMBER_SCALE = 18
NUMBER_INTEGER_DIGITS = 20
CONFIDENCE_SCALE = 4
NUL = "\x00"
# How other engines and translations cite a claim.
CLAIM_REFERENCE = "claim:"


def _storable(value: str) -> str:
    if NUL in value:
        raise ValueError("text must not contain NUL characters")
    return value


# Source text may be empty or whitespace: an original value is preserved exactly.
SourceString = Annotated[StrictStr, AfterValidator(_storable)]


def exact(value: Decimal, scale: int, integer_digits: int) -> Decimal:
    """Quantize to the column scale; refuse values PostgreSQL would round or overflow."""
    if not value.is_finite():
        raise ValueError("use a finite decimal")
    with localcontext(prec=scale + integer_digits + 2):
        result = value.quantize(Decimal(1).scaleb(-scale))
    if result != value:
        raise ValueError(f"use at most {scale} fractional digits; values are never rounded")
    if not result.is_zero() and result.adjusted() >= integer_digits:
        raise ValueError(f"use at most {integer_digits} integer digits")
    return result


def json_object(value: dict[str, JsonValue]) -> str:
    """Conditions and qualifiers keep one canonical serialization; {} means none."""
    return canonical(value)


class Time(Frozen):
    """A UTC instant with its precision; a year-precise date keeps its stated precision."""

    at: Instant
    precision: TimePrecision


def time_columns(prefix: str, value: Time | None) -> dict[str, datetime | str | None]:
    column = prefix if prefix.startswith("valid") else f"{prefix}_at"
    return {
        column: value.at if value else None,
        f"{prefix}_precision": value.precision if value else None,
    }


def validity(valid_from: Time | None, valid_to: Time | None) -> None:
    """Validity intervals are half-open and nonempty."""
    if valid_from and valid_to and valid_to.at <= valid_from.at:
        raise ValueError("valid_to must be after valid_from in a half-open interval")


class Record(Frozen):
    """A row of one evidence table with a deterministic primary key.

    `FIRST_SEEN` columns record when KN first wrote the row; they are not part of the key, so a
    rerun at a later time adds nothing. `MUTABLE` columns belong to projection writers.
    """

    TABLE: ClassVar[str]
    KEY: ClassVar[str]
    FIRST_SEEN: ClassVar[frozenset[str]] = frozenset({"recorded_at"})
    MUTABLE: ClassVar[frozenset[str]] = frozenset()

    def columns(self) -> dict[str, Any]:
        """Column values other than the key, in native SQL types."""
        raise NotImplementedError

    def row(self) -> dict[str, Any]:
        return {self.KEY: self.key, **self.columns()}

    @property
    def key(self) -> str:
        """The same content digest as human verification uses, over the identifying columns."""
        excluded = self.FIRST_SEEN | self.MUTABLE
        return content_version(
            {name: value for name, value in self.columns().items() if name not in excluded}
        )
