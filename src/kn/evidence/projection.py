"""Canonical fact projection: subjects under survivors, knowledge-time versions and writes.

Claims about a merged object are selected under its survivor. A claim whose object was split
into several successors names no single subject; it stays unattributed until it is re-stated.
`history` replays selection at every recorded claim and decision time, so its versions depend only
on stored data. `write` stores them idempotently and closes replaced versions.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.facts import CanonicalFact, SelectionOutcome
from kn.evidence.model import Claim
from kn.evidence.policy import UpdatePolicy
from kn.evidence.ranking import Context, Resolve
from kn.evidence.records import Record
from kn.evidence.selection import Selection, Subject, select
from kn.evidence.store import evidence_tables, record


def subjects(
    claims: Iterable[Claim], resolve: Resolve
) -> tuple[dict[Subject, list[Claim]], list[Claim]]:
    """Claims by survivor subject, and the claims of split objects that name no single one."""
    grouped: dict[Subject, list[Claim]] = {}
    unattributed: list[Claim] = []
    for claim in claims:
        targets = resolve(claim.kn_id)
        if len(targets) != 1:
            unattributed.append(claim)
            continue
        grouped.setdefault(Subject.of(claim, targets[0]), []).append(claim)
    return grouped, unattributed


@dataclass(frozen=True)
class Version:
    """One fact version, its knowledge end, and claims evaluated while it stayed current."""

    selection: Selection
    fact: CanonicalFact
    arrivals: tuple[SelectionOutcome, ...] = ()

    @property
    def records(self) -> tuple[Record, ...]:
        opened = self.selection.items
        return (*opened, self.fact, *self.selection.outcomes(self.fact), *self.arrivals)

    def closed(self, instant: datetime) -> Self:
        return replace(self, fact=self.fact.model_copy(update={"knowledge_to": instant}))


def history(
    subject: Subject, claims: Iterable[Claim], policy: UpdatePolicy, context: Context
) -> list[Version]:
    """Fact versions in knowledge order; a version ends when the next starts or nothing applies.

    Selection is replayed at every claim and decision recording time. A claim that changes
    nothing a version states (an ignored claim, a new runner-up) adds its outcome to that version.
    """
    known = list(claims)
    times = sorted({claim.recorded_at for claim in known} | context.reviews.times())
    versions: list[Version] = []
    current: Selection | None = None
    for instant in times:
        visible = [claim for claim in known if claim.recorded_at <= instant]
        at = replace(context, reviews=context.reviews.at(instant))
        result = select(subject, visible, policy, at, instant, current)
        if current is not None and result is not None and result.state == current.state:
            arrived = {claim.key for claim in visible if claim.recorded_at == instant}
            last = versions[-1]
            rows = result.outcomes(last.fact, arrived)
            versions[-1] = replace(last, arrivals=(*last.arrivals, *rows))
            continue
        if current is not None:
            versions[-1] = versions[-1].closed(instant)
        if result is not None:
            versions.append(Version(result, result.fact))
        current = result
    return versions


def stale(fact: CanonicalFact, policy: UpdatePolicy, at: datetime) -> timedelta | None:
    """The winner's age when a `latest_observed` value is older than its freshness threshold.

    A threshold of zero declares no freshness limit. A stale value is never shown as current.
    """
    observed = fact.winner_criteria.data_time
    limit = timedelta(seconds=policy.freshness_seconds)
    if policy.mode != "latest_observed" or fact.claim_key is None or observed is None:
        return None
    age = at - observed
    return age if policy.freshness_seconds and age > limit else None


def write(
    connection: Connection,
    versions: Iterable[Version],
    tables: Mapping[str, sa.Table] | None = None,
) -> int:
    """Store versions, items and outcomes; set each stored version's knowledge end.

    A stored version of the same fact that this history does not contain refuses the write:
    the projection is rebuilt from claims and decisions, never patched by hand.
    """
    tables = tables or evidence_tables()
    facts = tables["canonical_facts"]
    ordered = list(versions)
    added = 0
    with connection.begin_nested():
        expected = {version.fact.key: version.fact.knowledge_to for version in ordered}
        keys = {version.fact.fact_key for version in ordered}
        query = sa.select(facts.c.fact_version_id).where(facts.c.fact_key.in_(keys))
        stored: set[str] = set(connection.execute(query).scalars())
        unknown = sorted(stored - set(expected))
        if unknown:
            raise ValueError(f"stored fact versions differ from the projection: {unknown[0]}")
        for key, end in expected.items():
            connection.execute(
                sa.update(facts).where(facts.c.fact_version_id == key).values(knowledge_to=end)
            )
        for version in ordered:
            added += record(connection, version.records, tables)
    return added
