"""Representative durable human decision replay for the combined model checkpoint."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import Contract
from kn.contracts.sqlalchemy import metadata
from kn.review.journal import Journal
from kn.review.model import Request, Target
from kn.review.protocol import Reviewer
from kn.review.store import replay_target, submit
from kn.review.targets import ContractResolver, Coverage, content_version


def replay_review_fixture(
    connection: Connection, contracts: Sequence[Contract], data_dir: Path
) -> None:
    semantic = next(item for item in contracts if item.contract_id == "kn.core.semantic")
    model = semantic.table("namespace_labels")
    table = metadata(semantic).tables["semantic.namespace_labels"]
    row = (
        connection.execute(sa.select(table).order_by(*table.primary_key.columns)).mappings().first()
    )
    assert row is not None
    ids = {field.name: field.field_id for field in model.fields}
    content = tuple(ids.values())
    coverage = Coverage(semantic.contract_id, model.name, content, {ids["label"]: content})
    resolver = ContractResolver(contracts, [coverage])
    target = Target.model_validate(
        {
            "contract_id": semantic.contract_id,
            "dataset": model.name,
            "key": [
                {"field_id": ids[name], "kind": "string", "value": row[name]}
                for name in model.primary_key
            ],
            "scope": "field",
            "field_id": ids["label"],
            "purpose": "factual",
            "version": content_version({ids[name]: value for name, value in row.items()}),
        }
    )
    instant = datetime(2026, 1, 2, 12, tzinfo=UTC)
    journal = Journal(data_dir)
    request = Request(
        request_id="combined-baseline-label-review",
        target=target,
        outcome="accept",
        performed_at=instant,
        reason="Fixture label checked",
        evidence="review:fixture",
    )
    reviewer = Reviewer("person:fixture-reviewer", "human", True, frozenset({"factual"}))
    decision = submit(connection, journal, resolver, request, lambda: reviewer, lambda: instant)
    result = replay_target(connection, journal, resolver, target)
    assert result.stamp.human_verified_at == instant
    assert result.stamp.human_verified_by == reviewer.principal
    assert result.stamp.human_verification_decision_id == decision.decision_id
