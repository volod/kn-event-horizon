"""Source-language vocabulary text, explicit translation review and shared display selection."""

import json

from kn.i18n.data import SelectedText, SourceText, TextVariant, select_text
from kn.semantic.structure import Snapshot, refuse


def validate_text(snapshot: Snapshot) -> None:
    for dataset, rows in snapshot.items():
        for index, row in enumerate(rows):
            if row.get("definition") is not None and _is_json(row["definition"]):
                refuse(
                    (dataset, index, "definition"),
                    "definition",
                    "keep prose definitions separate from proposal metadata",
                )
    for dataset in ("labels", "namespace_labels", "alternative_labels"):
        _reviews(snapshot, dataset)


def _is_json(value: str) -> bool:
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def _reviews(snapshot: Snapshot, dataset: str) -> None:
    rows = snapshot.get(dataset, [])
    comparison_rows = (
        rows
        if dataset == "namespace_labels"
        else snapshot.get("labels", []) + snapshot.get("alternative_labels", [])
    )
    key = "namespace_id" if dataset == "namespace_labels" else "term_id"
    english = {(row[key], row["label"]) for row in comparison_rows if row["locale"].lower() == "en"}
    for index, row in enumerate(rows):
        identical = row["locale"].lower() == "uk" and (row[key], row["label"]) in english
        reviewed = bool(row.get("review_reference")) and row.get("reviewed_identical") is True
        if (identical and not reviewed) or (
            row.get("reviewed_identical") and (not identical or not reviewed)
        ):
            refuse(
                (dataset, index),
                "translation",
                "identical en/uk text needs an explicit terminology review",
            )


def select_label(snapshot: Snapshot, term_id: str, requested: str) -> SelectedText:
    """Select real text without creating a translated row or changing its language tag.

    Proposal content has an English original. Other snapshots can carry an original in any
    language; a stable row reference supplies provenance when no terminology review is present.
    """
    rows = sorted(
        (row for row in snapshot.get("labels", []) if row["term_id"] == term_id),
        key=lambda row: (
            bool(row.get("review_reference")),
            row["locale"].lower() != "en",
            row["locale"].lower(),
        ),
    )
    if not rows:
        raise ValueError("term has no preferred label")
    variants = tuple(
        TextVariant(
            row["label"],
            row["locale"],
            row.get("review_reference") or f"semantic.labels:{term_id}:{row['locale']}",
        )
        for row in rows
    )
    return select_text(SourceText(variants[0], variants[1:]), requested)
