"""Review CLI operations; parser and presentation stay outside domain behavior."""

from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.contracts.registry import registered_contracts
from kn.db.connection import engine_from_env
from kn.evidence.lineage import jsonable
from kn.evidence.store import evidence_tables
from kn.i18n import Translator
from kn.identity.journal import Journal as IdentityJournal
from kn.review.authorization import TTY, authorize
from kn.review.facts import applied, refresh
from kn.review.journal import Journal
from kn.review.model import Request, Target
from kn.review.queue import Item, items
from kn.review.queue_replay import reattach
from kn.review.queue_store import history, submit
from kn.review.selection import dispute_rates
from kn.review.targets import ContractResolver


def listing(
    connection: Connection, data_dir: Path, resolver: ContractResolver, overrides: bool = False
) -> dict[str, object]:
    available = items(connection, resolver, IdentityJournal(data_dir))
    events = applied(connection)
    visible = [
        item.document(events)
        for item in available.values()
        if not overrides or item.kind == "owner_override"
    ]
    table = evidence_tables()["claims"]
    sources: dict[str, str] = dict(
        connection.execute(sa.select(table.c.claim_key, table.c.source_id)).all()
    )
    result: dict[str, object] = {
        "action": "list",
        "items": visible,
        "dispute_rates": dispute_rates(events, sources),
        "orphans": orphan_report(connection, data_dir, resolver, available),
    }
    if overrides:
        facts = evidence_tables()["canonical_facts"]
        result["overrides"] = [
            jsonable(dict(row))
            for row in connection.execute(
                sa.select(facts)
                .where(facts.c.owner_override, facts.c.knowledge_to.is_(None))
                .order_by(facts.c.fact_key)
            ).mappings()
        ]
    return result


def orphan_report(
    connection: Connection, data_dir: Path, resolver: ContractResolver, available: dict[str, Item]
) -> list[dict[str, str]]:
    from kn.review.queue_replay import attachment_state

    return sorted(
        [
            {"decision_id": event.decision_id, "state": state}
            for event in history(data_dir)
            if (state := attachment_state(connection, resolver, available, event)) != "applied"
        ],
        key=lambda row: row["decision_id"],
    )


def operation(
    translator: Translator,
    data_dir: Path,
    domain: str,
    action: str,
    *,
    item_id: str | None = None,
    selected: str | None = None,
    details: dict[str, object] | None = None,
    target: Target | None = None,
    overrides: bool = False,
    query: str | None = None,
) -> dict[str, object]:
    contracts = registered_contracts()
    resolver = ContractResolver.registered(contracts)
    engine = engine_from_env()
    try:
        if action == "decide":
            with engine.connect() as connection:
                choice = None
                reviewed = None
                if item_id:
                    item = items(connection, resolver, IdentityJournal(data_dir)).get(item_id)
                    if item is None:
                        raise ValueError("unknown review item")
                    target, choice = item.target, item.choice(selected)
                    reviewed = item.document(applied(connection))
                if target is None or details is None:
                    raise ValueError("review requires a target and decision details")
                request = Request.model_validate({**details, "target": target, "queue": choice})
                if choice is None:
                    resolver.resolve(connection, target)
                    dataset = resolver.dataset(target.contract_id, target.dataset)
                    row = dataset.fetch(connection, target.key)
                    assert row is not None
                    reviewed = jsonable(dict(row))
            identity = IdentityJournal(data_dir)
            reviewer = authorize(
                translator,
                data_dir,
                (identity.path, Journal(data_dir, domain).path),
                {"request": request.model_dump(mode="json"), "reviewed_item": reviewed},
                target.purpose,
                TTY,
            )
            with engine.begin() as connection:
                event = submit(
                    connection,
                    data_dir,
                    domain,
                    resolver,
                    request,
                    lambda: reviewer,
                    lambda: datetime.now(UTC),
                )
                refresh(connection, identity, contracts)
            return {"action": "decided", "decision": event.model_dump(mode="json")}
        with engine.begin() as connection:
            if action == "replay":
                report = reattach(connection, data_dir, resolver)
                refresh(connection, IdentityJournal(data_dir), contracts)
                return {"action": "replayed", "report": report}
            if query is not None:
                from kn.review.verification import inspect

                return inspect(connection, resolver, query)
            return listing(connection, data_dir, resolver, overrides)
    finally:
        engine.dispose()
