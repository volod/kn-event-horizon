"""Update-policy and ranking formats that canonical selection reads and records.

The `kn.updatePolicy` field extension declares a policy; its canonical digest is stored on each
fact version. `Criteria` is the recorded form of a candidate's ranking inputs, for the winner,
the runner-up and every evaluated claim. `kn.evidence.selection` applies them.
"""

from decimal import Decimal
from typing import Annotated, Literal, get_args

from pydantic import ConfigDict, Field

from kn.contracts.model import Contract
from kn.contracts.physical import extensions
from kn.evidence.vocabulary import EvidenceClass, Mode
from kn.review.model import Frozen, Instant, Text, digest
from kn.sources.ranks import Rank

# Highest first, in the order the vocabularies declare. Repetition never adds rank.
RANK_ORDER: tuple[Rank, ...] = get_args(Rank.__value__)
EVIDENCE_ORDER: tuple[EvidenceClass, ...] = get_args(EvidenceClass.__value__)
type PriorityCriterion = Literal["source_rank", "evidence_class", "data_time"]


class UpdatePolicy(Frozen):
    """The `kn.updatePolicy` declaration of one field, read with its contract names."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    mode: Mode
    priority_criteria: tuple[PriorityCriterion, ...] = Field(alias="priorityCriteria")
    minimum_source_rank: Rank = Field(alias="minimumSourceRank")
    minimum_evidence_class: EvidenceClass = Field(alias="minimumEvidenceClass")
    time_basis: Literal["valid_from", "published", "observed"] = Field(alias="timeBasis")
    value_tolerance: Annotated[Decimal, Field(ge=0)] = Field(alias="valueTolerance")
    freshness_seconds: Annotated[int, Field(ge=0)] = Field(alias="freshnessSeconds")
    empty_value_handling: Literal["review", "allow_clear"] = Field(alias="emptyValueHandling")
    # Rule 6: ownership, contracts, availability and performance need primary evidence or review.
    high_impact: bool = Field(default=False, alias="highImpact")

    @property
    def digest(self) -> str:
        """The `policy_digest` of facts selected under this declaration."""
        return digest(self.model_dump(mode="json", by_alias=True))


def field_policy(contract: Contract, field_id: str) -> UpdatePolicy | None:
    """The declared policy of a stable field ID; None when the field declares none."""
    for table in contract.tables:
        for field in table.fields:
            if field.field_id == field_id:
                value = extensions(field).get("updatePolicy")
                return None if value is None else UpdatePolicy.model_validate(value)
    raise ValueError(f"unknown stable field ID: {field_id}")


class Criteria(Frozen):
    """Recorded ranking inputs of one candidate; data time uses the policy's time basis."""

    source_id: Text
    source_rank: Rank
    evidence_class: EvidenceClass
    data_time: Instant | None = None
