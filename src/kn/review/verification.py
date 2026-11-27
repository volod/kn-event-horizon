"""Prepare an exact record or field target from registered typed row keys."""

from sqlalchemy.engine import Connection

from kn.evidence.lineage import jsonable
from kn.review import store
from kn.review.model import Frozen, KeyPart, Purpose, Text
from kn.review.targets import ContractResolver, TargetUnavailable


class Query(Frozen):
    contract_id: Text
    dataset: Text
    key: tuple[KeyPart, ...]
    purpose: Purpose
    field_id: Text | None = None


def inspect(connection: Connection, resolver: ContractResolver, document: str) -> dict[str, object]:
    query = Query.model_validate_json(document)
    dataset = resolver.dataset(query.contract_id, query.dataset)
    row = dataset.fetch(connection, query.key)
    if row is None:
        raise TargetUnavailable("missing", "unknown review target")
    target = dataset.target(row, query.purpose, query.field_id)
    state = store.projection(connection, target)
    return {
        "action": "target",
        "values": jsonable(dict(row)),
        "target": target.model_dump(mode="json"),
        "state": state.state,
        "heads": list(state.heads),
        **state.stamp.model_dump(mode="json"),
    }
