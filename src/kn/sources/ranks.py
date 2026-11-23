"""Validate the source key references in a reviewed rank policy."""

from collections.abc import Set
from pathlib import Path
from typing import Annotated, Literal

from pydantic import StringConstraints

from kn.contracts.diagnostics import ContractError
from kn.sources.validation import ReviewDocument, read_model

type Rank = Literal["owner_entered", "first_party", "authorized_channel", "third_party", "unranked"]
type FieldGroup = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_.:-]+$")]


class Override(ReviewDocument):
    source_id: str
    rank: Rank
    field_group: FieldGroup | None = None


class Policy(ReviewDocument):
    overrides: list[Override]


def validate_rank_overrides(path: Path, source_ids: Set[str]) -> None:
    """Require each override to target a known source and have a unique scope."""
    policy = read_model(path, Policy)
    seen: set[tuple[str, str | None]] = set()
    for index, override in enumerate(policy.overrides):
        scope = (override.source_id, override.field_group)
        if override.source_id not in source_ids:
            raise ContractError(
                ("overrides", index, "source_id"), "sourceId", "use a qualified catalogue ID"
            )
        if scope in seen:
            raise ContractError(("overrides", index), "duplicate", "use one override per scope")
        seen.add(scope)
