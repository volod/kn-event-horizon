"""Lineage fixtures: a merge into a price conflict, a partial update, a split and restricted rights.

Two offers of one part come from sources of equal rank. The first changes only its price, then is
seen again unchanged; the second, merged into the first, conflicts with that price. A third object
is split after both of its records were tracked; the second record has restricted rights.
"""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from kn.evidence.lineage import TABLE_KEYS, Row
from kn.evidence.projection import history, subjects, successors
from kn.evidence.ranking import Audience, Context
from kn.evidence.records import Record
from kn.identity.events import event
from kn.identity.journal import Journal
from kn.identity.model import (
    Assignment,
    Attribute,
    Candidate,
    Feature,
    Identifier,
    Link,
    Match,
    Merge,
    Mint,
    Payload,
    SourceKey,
    Split,
)
from kn.review.model import digest
from tests.evidence.selection_fixtures import policy
from tests.identity.tracking_fixtures import (
    ACTOR,
    PRICE,
    RECORD,
    SOURCE,
    T0,
    MemoryClaims,
    delivery,
    package,
    price,
    track,
)

X1, X2, S, S1, S2 = (f"kn:019b76da-a800-7000-8000-{number:012x}" for number in range(0xA1, 0xA6))
OFFER_CLASS = "core.supplier_offer"
BROKER = "microelectronics:fixture-broker"
BROKER_RECORD = SourceKey(source=BROKER, key="SKU-42")
SPLIT_FIRST = SourceKey(source=SOURCE, key="OFFER-00044")
SPLIT_SECOND = SourceKey(source=SOURCE, key="OFFER-00045")
OPEN = "license:fixture-open"
RESTRICTED = "license:fixture-restricted"
PARTNER = Audience(name="partner", rights=frozenset({OPEN}))
NAMESPACE, NATIVE = "inventree:vl-itree:part", "42"
QUALIFIED = f"{NAMESPACE}:{NATIVE}"
PROFILE = digest("lineage-fixture-profile")
MERGED_AT, SPLIT_AT = T0 + timedelta(hours=5), T0 + timedelta(hours=8)


class MemoryRows:
    """Evidence rows as PostgreSQL would return them, filtered like `SqlEvidenceRows`."""

    def __init__(self, records: Iterable[Record]) -> None:
        self.tables: dict[str, dict[str, Row]] = {}
        for item in records:
            for row in (item.evidence, item) if hasattr(item, "evidence") else (item,):
                self.tables.setdefault(row.TABLE, {})[row.key] = row.row()

    def rows(self, table: str, column: str, values: Collection[str], **equal: object) -> list[Row]:
        found = [
            row
            for row in self.tables.get(table, {}).values()
            if row[column] in values and all(row[name] == value for name, value in equal.items())
        ]
        return sorted(found, key=lambda row: row[TABLE_KEYS[table]])


@dataclass(frozen=True)
class Fixture:
    journal: Journal
    claims: MemoryClaims
    records: tuple[Record, ...]

    @property
    def rows(self) -> MemoryRows:
        return MemoryRows(self.records)


def append(journal: Journal, payload: Payload, at: Any, decision_ref: str | None = None) -> str:
    with journal.locked() as locked:
        value = event(
            payload,
            previous=locked.events[-1] if locked.events else None,
            occurred_at=at,
            actor="local:fixture-reviewer" if decision_ref else ACTOR,
            reason="Lineage fixture",
            evidence="archive:lineage-fixture",
            decision_ref=decision_ref,
        )
        locked.append(value)
    return value.event_id


def mint_object(journal: Journal, kn_id: str, anchor: SourceKey, *records: SourceKey) -> list[str]:
    append(journal, Mint(kn_id=kn_id, entity_class=OFFER_CLASS, anchor=anchor), T0)
    return [
        append(journal, Link(record=item, kn_id=kn_id, method="minted"), T0) for item in records
    ]


def _offers(journal: Journal, claims: MemoryClaims) -> list[Record]:
    mint_object(journal, X1, RECORD, RECORD)
    append(
        journal,
        Identifier(
            kn_id=X1,
            namespace=NAMESPACE,
            value=NATIVE,
            issuer="inventree:vl-itree",
            authority="source_qualified",
            valid_from=T0,
        ),
        T0,
    )
    append(
        journal,
        Attribute(
            kn_id=X1,
            field_id="offer.sku",
            original="SKU-42",
            normalized="sku-42",
            normalizer="casefold-v1",
            profile_digest=PROFILE,
            record=RECORD,
        ),
        T0,
    )
    feature = Feature(
        field_id="offer.sku",
        left="sku-42",
        right="sku-42",
        comparator="exact",
        outcome="agree",
        weight=2.0,
    )
    append(
        journal,
        Match(
            record=BROKER_RECORD,
            profile_digest=PROFILE,
            profile_version="1.0.0",
            candidates=(Candidate(kn_id=X1, features=(feature,), score=2.0, probability=0.7),),
            decision="review",
        ),
        T0,
    )
    mint_object(journal, X2, BROKER_RECORD, BROKER_RECORD)
    rows: list[Record] = []
    for item in (
        delivery(price("1.20"), package("SOT-23"), fetch=1),
        delivery(price("1.25"), fetch=2),
        delivery(price("1.25"), fetch=3),
        delivery(price("1.30"), fetch=4, record=BROKER_RECORD),
    ):
        rows.extend(track(journal, claims, item)[1])
    append(journal, Merge(kn_id=X2, survivor=X1), MERGED_AT, "decision:fixture-merge")
    return rows


def _split(journal: Journal, claims: MemoryClaims) -> list[Record]:
    first, second = mint_object(journal, S, SPLIT_FIRST, SPLIT_FIRST, SPLIT_SECOND)
    rows: list[Record] = []
    for item in (
        delivery(price("2.00"), fetch=6, record=SPLIT_FIRST),
        delivery(price("2.10"), fetch=7, record=SPLIT_SECOND, rights=RESTRICTED),
    ):
        rows.extend(track(journal, claims, item)[1])
    mint_object(journal, S1, SourceKey(source="fixture:split", key="S1"))
    mint_object(journal, S2, SourceKey(source="fixture:split", key="S2"))
    assignments = (
        Assignment(item_id=first, successor=S1),
        Assignment(item_id=second, successor=S2),
    )
    split = Split(kn_id=S, successors=(S1, S2), assignments=assignments)
    append(journal, split, SPLIT_AT, "decision:fixture-split")
    for item in (
        delivery(price("2.05"), fetch=9, record=SPLIT_FIRST),
        delivery(price("2.20"), fetch=10, record=SPLIT_SECOND, rights=RESTRICTED),
    ):
        rows.extend(track(journal, claims, item)[1])
    return rows


def facts(journal: Journal, claims: MemoryClaims) -> list[Record]:
    """Fact histories of every survivor subject for the internal and partner audiences."""
    state = journal.state()
    grouped, _ = subjects(claims.claims.values(), state.resolve)
    superseded = successors(claims.claims.values())
    rows: list[Record] = []
    for audience in (Audience(), PARTNER):
        context = Context(audience=audience, resolve=state.resolve)
        for subject, members in sorted(grouped.items(), key=lambda item: repr(item[0])):
            for version in history(subject, members, policy(), context, superseded):
                rows.extend(version.records)
    return rows


def build(data_dir: Path) -> Fixture:
    journal = Journal(data_dir)
    claims = MemoryClaims()
    tracked = [*_offers(journal, claims), *_split(journal, claims)]
    return Fixture(journal, claims, (*tracked, *facts(journal, claims)))


@dataclass(frozen=True)
class Case:
    """One golden lookup; `arguments` are the same lookup on the `kn lineage` command line."""

    reference: str
    field_id: str | None = None
    permit: frozenset[str] | None = None

    @property
    def audience(self) -> Audience:
        return Audience(rights=self.permit)

    @property
    def arguments(self) -> list[str]:
        field = [] if self.field_id is None else ["--field", self.field_id]
        rights = [item for right in sorted(self.permit or ()) for item in ("--permit", right)]
        return ["lineage", self.reference, *field, *rights]


CASES = {
    "merged": Case(X2),
    "split": Case(S1),
    "identifier-field": Case(QUALIFIED, field_id=PRICE),
    "restricted": Case(S2, permit=frozenset({OPEN})),
}
