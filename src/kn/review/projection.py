"""Current, rights-filtered read projections for registered rows and fields."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy.engine import Connection

from kn.review import store
from kn.review.model import Decision, KeyPart, Purpose, Stamp, Target
from kn.review.protocol import project
from kn.review.targets import Dataset, Row


@dataclass(frozen=True)
class ReadRights:
    """A trusted audience policy for data and the reviewer/evidence of a decision."""

    data: Callable[[Dataset, Row, str | None], bool]
    decision: Callable[[Decision], bool]


@dataclass(frozen=True)
class VerifiedRow:
    values: Row
    record: Stamp
    fields: dict[str, Stamp]


def read(
    connection: Connection,
    dataset: Dataset,
    key: tuple[KeyPart, ...],
    purpose: Purpose,
    *,
    rights: ReadRights,
) -> VerifiedRow | None:
    """Read the current row by typed key; only visible content can carry a stamp."""
    row = dataset.fetch(connection, key)
    if row is None or not rights.data(dataset, row, None):
        return None
    is_decision = (dataset.coverage.contract_id, dataset.coverage.dataset) == (
        store.DECISION_CONTRACT,
        store.DECISION_DATASET,
    )
    if is_decision and not rights.decision(Decision.model_validate_json(str(row["event_json"]))):
        return None
    visible = {field for field in dataset.fields if rights.data(dataset, row, field)}
    if not visible.issuperset(dataset.primary_key):
        return None
    targets = dataset.targets(row, key, purpose, visible)
    history = store.history(connection, [target.target_id for target in targets.values()])
    stamps = {
        field: _stamp(history.get(target.target_id, ()), target, rights)
        for field, target in targets.items()
    }
    return VerifiedRow(
        {
            model.name: row[model.name]
            for field, model in dataset.fields.items()
            if field in visible
        },
        stamps.get(None, Stamp()),
        {
            field: stamps.get(field, Stamp())
            for field in dataset.coverage.field_context
            if field in visible
        },
    )


def _stamp(events: Sequence[Decision], target: Target, rights: ReadRights) -> Stamp:
    # Hidden causal branches must never resurrect an earlier visible acceptance.
    if not all(rights.decision(event) for event in events):
        return Stamp()
    return project(events, target).stamp
