"""Claims that cite retired concepts, reported through the semantic lifecycle report."""

from collections.abc import Iterable, Mapping
from typing import Any

from kn.evidence.records import CLAIM_REFERENCE
from kn.semantic.lifecycle import lifecycle_report
from kn.semantic.structure import Snapshot


def concept_uses(claims: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Claim rows by the concept they state as their value, in key order.

    Rows are SQL mappings or `Record.row()` values. Units and conditions keep their own
    identifiers and are not concept citations.
    """
    uses: dict[str, set[str]] = {}
    for row in claims:
        if row["value_concept"] is not None:
            uses.setdefault(row["value_concept"], set()).add(CLAIM_REFERENCE + row["claim_key"])
    return {concept: sorted(keys) for concept, keys in sorted(uses.items())}


def retired_concept_claims(
    snapshot: Snapshot, claims: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """The lifecycle report with every citing claim as an external use and its successor."""
    return lifecycle_report(snapshot, concept_uses(claims))
