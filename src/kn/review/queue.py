"""Internal operator queue over deterministic evidence and identity review keys."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from kn.evidence.lineage import jsonable
from kn.evidence.store import evidence_tables
from kn.evidence.vocabulary import FACT_REVIEW_KINDS
from kn.identity.events import Event
from kn.identity.journal import Journal as IdentityJournal
from kn.identity.model import Match
from kn.identity.state import State
from kn.review.model import Decision, KeyPart, Target, digest
from kn.review.protocol import project
from kn.review.queue_model import KINDS, Choice
from kn.review.targets import ContractResolver

EVIDENCE = "kn.core.evidence"
IDENTITY = "kn.core.identity"


@dataclass(frozen=True)
class Item:
    item_id: str
    kind: str
    candidates: tuple[str, ...]
    target: Target
    details: Mapping[str, Any]

    def choice(self, selected: str | None) -> Choice:
        return Choice(
            item_id=self.item_id, kind=self.kind, candidates=self.candidates, selected=selected
        )

    def document(self, events: tuple[Decision, ...]) -> dict[str, object]:
        result = project([e for e in events if e.target == self.target], self.target)
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "candidates": list(self.candidates),
            "target": self.target.model_dump(mode="json"),
            "details": dict(self.details),
            "state": "open" if result.state == "unreviewed" else result.state,
            "heads": list(result.heads),
            **result.stamp.model_dump(mode="json"),
        }


def items(
    connection: Connection,
    resolver: ContractResolver,
    identity: IdentityJournal,
    tables: Mapping[str, sa.Table] | None = None,
    state: State | None = None,
) -> dict[str, Item]:
    tables = tables or evidence_tables()
    dataset = resolver.dataset(EVIDENCE, "review_items")
    result = {}
    for row in connection.execute(sa.select(tables["review_items"])).mappings():
        if row["kind"] not in KINDS:
            raise ValueError("unregistered review kind")
        key = row["item_id"]
        candidates = tuple(json.loads(row["candidates_json"]))
        claim_table = tables["claims"]
        reviewed_claims = (
            [
                jsonable(dict(claim))
                for claim in connection.execute(
                    sa.select(claim_table)
                    .where(claim_table.c.claim_key.in_(candidates))
                    .order_by(claim_table.c.claim_key)
                ).mappings()
            ]
            if row["kind"] in FACT_REVIEW_KINDS
            else []
        )
        result[key] = Item(
            key,
            row["kind"],
            candidates,
            dataset.target(dict(row), "workflow"),
            {
                "kn_id": row["kn_id"],
                "field_id": row["field_id"],
                "reason": row["reason_code"],
                "claims": reviewed_claims,
            },
        )
    state = state if state is not None else identity.state()
    for event in state.events:
        if isinstance(match := event.payload, Match) and match.decision == "review":
            item = identity_item(event)
            result[item.item_id] = item
    return dict(sorted(result.items()))


def identity_item(event: Event) -> Item:
    match = event.payload
    assert isinstance(match, Match)
    kind = "identity_drift" if match.trace and match.trace.route == "conflict" else "identity_match"
    candidates = tuple(sorted(candidate.kn_id for candidate in match.candidates))
    # A no-candidate quarantine is still reviewable as an accept/reject workflow item.
    choices = candidates or (event.event_id,)
    return Item(
        digest({"kind": kind, "match": event.event_id}),
        kind,
        choices,
        Target(
            contract_id=IDENTITY,
            dataset="matches",
            key=(
                KeyPart(field_id="identity.matches.match_id", kind="string", value=event.event_id),
            ),
            scope="record",
            version=digest(match.model_dump(mode="json")),
            purpose="workflow",
        ),
        {
            "match_id": event.event_id,
            "record": match.record.model_dump(mode="json"),
            "profile_digest": match.profile_digest,
            "profile_version": match.profile_version,
            "candidates": [candidate.model_dump(mode="json") for candidate in match.candidates],
        },
    )


def validate_item(connection: Connection, resolver: ContractResolver, item: Item) -> None:
    if item.kind.startswith("identity_"):
        return
    resolver.resolve(connection, item.target)
    if item.kind in FACT_REVIEW_KINDS:
        claims = resolver.dataset(EVIDENCE, "claims").table
        found: set[str] = set(
            connection.scalars(
                sa.select(claims.c.claim_key).where(claims.c.claim_key.in_(item.candidates))
            )
        )
        if found != set(item.candidates):
            raise ValueError("review item has orphaned claim candidates")
