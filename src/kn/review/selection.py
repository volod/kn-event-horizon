"""Canonical selection reviews and source dispute rates from applied shared decisions."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime

from kn.evidence.ranking import Reviews, ReviewSnapshot
from kn.evidence.vocabulary import FACT_REVIEW_KINDS
from kn.review.model import Decision, Target
from kn.review.protocol import project


def active(events: Iterable[Decision]) -> tuple[Decision, ...]:
    groups: dict[Target, list[Decision]] = defaultdict(list)
    for event in events:
        groups[event.target].append(event)
    heads: list[Decision] = []
    for target, values in groups.items():
        state = project(values, target)
        if len(state.heads) == 1:
            heads.extend(value for value in values if value.decision_id == state.heads[0])
    return tuple({event.decision_id: event for event in heads}.values())


def _snapshot(events: Iterable[Decision], instant: datetime) -> ReviewSnapshot:
    """Accepted outcomes at the instant; a claim keeps the time of the latest decision about it.

    Events apply in recording order, so the order in which storage returns them never matters.
    """
    selected: dict[str, datetime] = {}
    rejected: dict[str, datetime] = {}
    decisions: dict[str, datetime] = {}
    heads = active(event for event in events if event.recorded_at <= instant)
    for event in sorted(heads, key=lambda each: (each.recorded_at, each.decision_id)):
        choice = event.queue
        if choice is None or choice.kind not in FACT_REVIEW_KINDS or choice.selected is None:
            continue
        if event.outcome in {"accept", "supersede"}:
            selected[choice.selected] = event.recorded_at
            decisions[event.decision_id] = event.recorded_at
        elif event.outcome == "reject":
            rejected[choice.selected] = event.recorded_at
    selected = {key: value for key, value in selected.items() if key not in rejected}
    return ReviewSnapshot(at=instant, selected=selected, rejected=rejected, decisions=decisions)


def accepted_reviews(events: Iterable[Decision]) -> Reviews:
    events = tuple(events)
    snapshots = tuple(
        _snapshot(events, at) for at in sorted({event.recorded_at for event in events})
    )
    if not snapshots:
        return Reviews()
    last = snapshots[-1]
    return Reviews(
        selected=last.selected,
        rejected=last.rejected,
        decisions=last.decisions,
        snapshots=snapshots,
    )


def dispute_rates(
    events: Iterable[Decision], sources: Mapping[str, str]
) -> list[dict[str, object]]:
    """One reviewed claim per source; explicit rejection or a losing candidate is disputed."""
    reviewed: set[str] = set()
    disputed: set[str] = set()
    for event in active(events):
        choice = event.queue
        if choice is None or choice.kind not in FACT_REVIEW_KINDS or choice.selected is None:
            continue
        if event.outcome in {"accept", "supersede"}:
            reviewed.update(choice.candidates)
            disputed.update(set(choice.candidates) - {choice.selected})
        elif event.outcome == "reject":
            reviewed.add(choice.selected)
            disputed.add(choice.selected)
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for key in sorted(reviewed & sources.keys()):
        totals[sources[key]][0] += 1
        totals[sources[key]][1] += int(key in disputed)
    return [
        {"source_id": source, "reviewed": count, "disputed": lost, "dispute_rate": lost / count}
        for source, (count, lost) in sorted(totals.items())
    ]
