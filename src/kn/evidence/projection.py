"""Canonical fact projection: subjects under survivors, knowledge-time versions and writes.

Claims about a merged object are selected under its survivor. A claim whose object was split
into several successors names no single subject; it stays unattributed until it is re-stated.
An emptied claim states no value under any condition set, so it joins its predecessor's subject.
A claim superseded by a claim of another subject, such as a correction of its conditions, leaves
selection when its successor is recorded (`successors`).
`history` replays selection at every recorded claim time and every time a decision about its
claims changes, so its versions depend only on stored data. `write` stores them idempotently and
closes replaced versions.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from itertools import chain
from typing import Self

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.facts import CanonicalFact, SelectionOutcome
from kn.evidence.model import Claim
from kn.evidence.policy import UpdatePolicy
from kn.evidence.ranking import Context, Resolve, Reviews, ReviewSnapshot
from kn.evidence.records import Record
from kn.evidence.selection import Selection, Subject, select
from kn.evidence.store import evidence_tables, record


def subjects(
    claims: Iterable[Claim], resolve: Resolve
) -> tuple[dict[Subject, list[Claim]], list[Claim]]:
    """Claims by survivor subject, and the claims of split objects that name no single one."""
    known = list(claims)
    by_key = {claim.key: claim for claim in known}
    grouped: dict[Subject, list[Claim]] = {}
    unattributed: list[Claim] = []
    for claim in known:
        home = _home(claim, by_key)
        targets = resolve(home.kn_id)
        if len(targets) != 1:
            unattributed.append(claim)
            continue
        grouped.setdefault(Subject.of(home, targets[0]), []).append(claim)
    return grouped, unattributed


def _home(claim: Claim, by_key: Mapping[str, Claim]) -> Claim:
    """The claim whose subject this claim belongs to: an emptied claim follows its predecessor."""
    seen = {claim.key}
    while claim.change_kind == "emptied" and claim.supersedes is not None:
        predecessor = by_key.get(claim.supersedes)
        if predecessor is None or predecessor.key in seen:
            break
        claim = predecessor
        seen.add(claim.key)
    return claim


def successors(claims: Iterable[Claim]) -> dict[str, datetime]:
    """When each superseded claim's first successor was recorded, whatever its subject."""
    first: dict[str, datetime] = {}
    for claim in claims:
        if claim.supersedes is None:
            continue
        known = first.get(claim.supersedes)
        if known is None or claim.recorded_at < known:
            first[claim.supersedes] = claim.recorded_at
    return first


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
    subject: Subject,
    claims: Iterable[Claim],
    policy: UpdatePolicy,
    context: Context,
    superseded: Mapping[str, datetime] | None = None,
) -> list[Version]:
    """Fact versions in knowledge order; a version ends when the next starts or nothing applies.

    Selection is replayed at every claim recording time, every time a decision about these claims
    changes and every time a claim of another subject supersedes one of them (`successors`). A
    claim that changes nothing a version states (an ignored claim, a new runner-up) adds its
    outcome to that version.
    """
    known = list(claims)
    keys = {claim.key for claim in known}
    retiring = {key: at for key, at in (superseded or {}).items() if key in keys}
    recorded = {claim.recorded_at for claim in known} | set(retiring.values())
    times = sorted(recorded | _review_times(context.reviews, known))
    versions: list[Version] = []
    current: Selection | None = None
    for instant in times:
        visible = [claim for claim in known if claim.recorded_at <= instant]
        at = replace(context, reviews=context.reviews.at(instant))
        retired = frozenset(key for key, time in retiring.items() if time <= instant)
        result = select(subject, visible, policy, at, instant, current, retired)
        arrived = {claim.key for claim in visible if claim.recorded_at == instant}
        current = _record(versions, current, result, instant, arrived)
    return versions


def _record(
    versions: list[Version],
    current: Selection | None,
    result: Selection | None,
    instant: datetime,
    arrived: Collection[str],
) -> Selection | None:
    """Add the selection at the instant to the open version, or start a new one; the current."""
    if current is not None and result is not None and result.state == current.state:
        last = versions[-1]
        rows = result.outcomes(last.fact, arrived)
        versions[-1] = replace(last, arrivals=(*last.arrivals, *rows))
        return current
    if current is not None:
        versions[-1] = versions[-1].closed(instant)
    if result is not None:
        versions.append(Version(result, result.fact))
    return result


type _View = tuple[tuple[datetime | None, ...], ...]


def _view(state: Reviews | ReviewSnapshot, keys: list[str], refs: list[str]) -> _View:
    """The decision times that selection of these claims reads from one review state."""
    return (
        tuple(state.selected.get(key) for key in keys),
        tuple(state.rejected.get(key) for key in keys),
        tuple(state.decisions.get(ref) for ref in refs),
    )


def _review_times(reviews: Reviews, claims: Collection[Claim]) -> set[datetime]:
    """When the decisions about these claims change; other decisions cannot change their fact."""
    keys = sorted({claim.key for claim in claims})
    refs = sorted({claim.decision_ref for claim in claims if claim.decision_ref is not None})
    if not reviews.snapshots:
        stated = chain.from_iterable(_view(reviews, keys, refs))
        return {time for time in stated if time is not None}
    changed: set[datetime] = set()
    last = _view(Reviews(), keys, refs)
    for state in reviews.snapshots:
        seen = _view(state, keys, refs)
        if seen != last:
            changed.add(state.at)
            last = seen
    return changed


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
