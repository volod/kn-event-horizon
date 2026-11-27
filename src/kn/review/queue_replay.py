"""Explicit queue reattachment and recovery of decisions referenced by identity effects."""

from collections.abc import Mapping
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.identity import store as identity_store
from kn.identity.events import Event
from kn.identity.journal import Journal as IdentityJournal
from kn.identity.journal import LockedJournal
from kn.review import store
from kn.review.identity import REVIEW_REF, effects, validate_reference
from kn.review.journal import Journal
from kn.review.model import Decision
from kn.review.queue import Item, items
from kn.review.queue_store import ItemResolver, apply_fact_event, journals
from kn.review.targets import ContractResolver, TargetUnavailable


def reattach(
    connection: Connection,
    data_dir: Path,
    resolver: ContractResolver,
    tables: Mapping[str, sa.Table] | None = None,
) -> list[dict[str, str]]:
    identity = IdentityJournal(data_dir)
    identity_store.lock(connection)
    store.lock(connection)
    with connection.begin_nested():
        return _reattach(connection, data_dir, resolver, tables, identity)


def _reattach(
    connection: Connection,
    data_dir: Path,
    resolver: ContractResolver,
    tables: Mapping[str, sa.Table] | None,
    identity: IdentityJournal,
) -> list[dict[str, str]]:
    available = items(connection, resolver, identity, tables)
    report = []
    for log in journals(data_dir):
        valid = []
        for event in log.read():
            state = attachment_state(connection, resolver, available, event)
            if state == "applied":
                try:
                    _restore_effects(connection, identity, event)
                except TargetUnavailable as unavailable:
                    state = unavailable.state
                else:
                    valid.append(event.decision_id)
                    apply_fact_event(connection, event, tables)
            report.append({"decision_id": event.decision_id, "state": state})
        _replay_ids(connection, log, tuple(valid))
    return sorted(report, key=lambda entry: entry["decision_id"])


def attachment_state(
    connection: Connection,
    resolver: ContractResolver,
    available: Mapping[str, Item],
    event: Decision,
) -> str:
    try:
        if event.queue is None:
            resolver.resolve(connection, event.target)
        else:
            item = available.get(event.queue.item_id)
            if item is None:
                raise TargetUnavailable("missing", "item disappeared")
            ItemResolver(resolver, item).resolve(connection, event.target)
            if event.queue != item.choice(event.queue.selected):
                return "incompatible"
    except TargetUnavailable as error:
        return "orphan" if error.state == "missing" else error.state
    except ValueError:
        return "orphan"
    return "applied"


def _restore_effects(connection: Connection, identity: IdentityJournal, event: Decision) -> None:
    if event.queue is not None and event.queue.kind.startswith("identity_"):

        def apply(locked: LockedJournal) -> None:
            locked.append_batch(effects(locked, event))

        identity_store.apply(connection, identity, apply)


def restore_identity_reviews(connection: Connection, locked: LockedJournal) -> None:
    referenced: dict[str, list[Event]] = {}
    for event in locked.state.events:
        if event.decision_ref and event.decision_ref.startswith(REVIEW_REF):
            referenced.setdefault(event.decision_ref.removeprefix(REVIEW_REF), []).append(event)
    if not referenced:
        return
    remaining = set(referenced)
    for log in journals(locked.data_dir):

        def select(events: dict[str, Decision]) -> tuple[str, ...]:
            found = remaining & events.keys()
            for key in found:
                for value in referenced[key]:
                    validate_reference(value, events[key])
            remaining.difference_update(found)
            return tuple(sorted(found))

        store.replay_selected(connection, log, select)
    if remaining:
        raise ValueError("identity effect requires its durable queue decision")


def _replay_ids(connection: Connection, log: Journal, ids: tuple[str, ...]) -> None:
    store.replay_selected(connection, log, lambda _: ids)
