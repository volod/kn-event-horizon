"""Deterministic current and as-of views over claims, facts and relations.

`knowledge_time` asks what KN had recorded at that instant; None asks for the current view.
`valid_time` asks what held at that instant; None applies no validity filter. Intervals are
half-open. A null validity bound is unknown or open, so it never excludes a row.
"""

from datetime import datetime

import sqlalchemy as sa

from kn.review.model import utc


def claims_as_of(
    claims: sa.Table, knowledge_time: datetime | None = None, valid_time: datetime | None = None
) -> sa.Select[tuple[object, ...]]:
    """Recorded claims that no recorded successor of the same record had superseded."""
    successor = claims.alias("successor")
    replaced = sa.select(successor.c.claim_key).where(successor.c.supersedes == claims.c.claim_key)
    clauses: list[sa.ColumnElement[bool]] = [_valid(claims, valid_time)]
    if knowledge_time is not None:
        known = utc(knowledge_time)
        clauses.append(claims.c.recorded_at <= known)
        replaced = replaced.where(successor.c.recorded_at <= known)
    clauses.append(~replaced.exists())
    return (
        sa.select(claims)
        .where(*clauses)
        .order_by(claims.c.kn_id, claims.c.field_id, claims.c.claim_key)
    )


def facts_as_of(
    facts: sa.Table, knowledge_time: datetime | None = None, valid_time: datetime | None = None
) -> sa.Select[tuple[object, ...]]:
    """The one fact version per fact key whose knowledge interval holds the instant."""
    known = _interval(facts.c.knowledge_from, facts.c.knowledge_to, knowledge_time)
    return (
        sa.select(facts)
        .where(known, _valid(facts, valid_time))
        .order_by(facts.c.kn_id, facts.c.field_id, facts.c.fact_key)
    )


def relations_as_of(
    relations: sa.Table,
    knowledge_time: datetime | None = None,
    valid_time: datetime | None = None,
) -> sa.Select[tuple[object, ...]]:
    known = _interval(relations.c.opened_at, relations.c.closed_at, knowledge_time)
    return (
        sa.select(relations)
        .where(known, _valid(relations, valid_time))
        .order_by(relations.c.relation_key, relations.c.assertion_id)
    )


def _interval(
    start: sa.ColumnElement[datetime], end: sa.ColumnElement[datetime], at: datetime | None
) -> sa.ColumnElement[bool]:
    if at is None:
        return end.is_(None)
    instant = utc(at)
    return sa.and_(start <= instant, sa.or_(end.is_(None), end > instant))


def _valid(table: sa.Table, at: datetime | None) -> sa.ColumnElement[bool]:
    if at is None:
        return sa.true()
    instant = utc(at)
    return sa.and_(
        sa.or_(table.c.valid_from.is_(None), table.c.valid_from <= instant),
        sa.or_(table.c.valid_to.is_(None), table.c.valid_to > instant),
    )
