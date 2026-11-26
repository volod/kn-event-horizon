"""Refresh canonical histories using applied queue decisions and declared field policies."""

from collections.abc import Mapping, Sequence

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.model import Contract
from kn.contracts.physical import extensions
from kn.evidence.policy import UpdatePolicy
from kn.evidence.projection import history, subjects, write
from kn.evidence.ranking import Context, RankTable
from kn.evidence.read import claims
from kn.evidence.store import evidence_tables
from kn.identity.journal import Journal
from kn.review.model import Decision
from kn.review.selection import accepted_reviews
from kn.review.store import decision_table


def applied(connection: Connection) -> tuple[Decision, ...]:
    table = decision_table()
    documents: sa.ScalarResult[str] = connection.scalars(sa.select(table.c.event_json))
    return tuple(Decision.model_validate_json(document) for document in documents)


def refresh(
    connection: Connection,
    identity: Journal,
    contracts: Sequence[Contract],
    tables: Mapping[str, sa.Table] | None = None,
) -> None:
    tables = tables or evidence_tables()
    policies = {
        field.field_id: UpdatePolicy.model_validate(value)
        for contract in contracts
        for table in contract.tables
        for field in table.fields
        if (value := extensions(field).get("updatePolicy")) is not None
    }
    if not policies:
        return
    state = identity.state()
    grouped, _ = subjects(claims(connection, tables), state.resolve)
    reviews = accepted_reviews(applied(connection))
    context = Context(ranks=RankTable.read(), reviews=reviews, resolve=state.resolve)
    for subject, values in grouped.items():
        if subject.field_id in policies:
            write(connection, history(subject, values, policies[subject.field_id], context), tables)
