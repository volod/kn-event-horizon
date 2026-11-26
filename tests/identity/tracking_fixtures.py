"""Partial-update deliveries of one distributor offer record, with an in-memory claim index."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from kn.evidence.model import Claim, Confirmation
from kn.evidence.records import Record
from kn.evidence.values import NumberValue, TextValue
from kn.identity.events import event
from kn.identity.journal import Journal
from kn.identity.model import Link, Merge, SourceKey
from kn.identity.tracking.changes import Tracked, prepare
from kn.identity.tracking.claims import evidence_rows
from kn.identity.tracking.delivery import Delivery, Statement
from kn.review.model import digest

T0 = datetime(2026, 4, 1, 8, tzinfo=UTC)
ACTOR = "engine:tracking-fixture"
SOURCE = "microelectronics:fixture-distributor"
RECORD = SourceKey(source=SOURCE, key="OFFER-00042")
FRAGMENT = SourceKey(source=SOURCE, key="OFFER-00042/break-100")
PRICE, PACKAGE, VOLTAGE = "part.unit_price", "part.package", "part.voltage_max"


def price(amount: str, locator: str = "/price") -> Statement:
    return Statement(
        field_id=PRICE,
        value=NumberValue(number=Decimal(amount)),
        original_value=amount,
        original_unit="EUR",
        locator=locator,
    )


def package(text: str | None) -> Statement:
    value = TextValue(text=text, language="und") if text and text.strip() else None
    return Statement(field_id=PACKAGE, value=value, original_value=text, locator="/package")


def voltage(volts: str) -> Statement:
    return Statement(
        field_id=VOLTAGE,
        value=NumberValue(number=Decimal(volts)),
        original_value=volts,
        original_unit="V",
        locator="/vmax",
    )


def delivery(*statements: Statement, fetch: int, **changes: Any) -> Delivery:
    """Fetch `n` happens `n` hours after T0 unless the fixture says otherwise."""
    data: dict[str, Any] = {
        "record": RECORD,
        "version": None,
        "ordering": "fetch",
        "fetch_id": f"fetch-{fetch}",
        "archive_record_id": f"warc:{fetch}",
        "fetched_at": T0 + timedelta(hours=fetch),
        "origin_uri": "https://distributor.example.test/offers/42",
        "locator_kind": "json_pointer",
        "rights": "license:fixture-open",
        "code_digest": digest("tracker-fixture-code"),
        "contract_digest": digest("tracker-fixture-contract"),
        "assertion_type": "reported",
        "evidence_class": "secondary",
        "statements": statements,
    }
    return Delivery.model_validate({**data, **changes})


class MemoryClaims:
    """The claim and confirmation rows a database would hold, keyed like the writer's."""

    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}
        self.confirmations: dict[str, Confirmation] = {}

    def claim(self, record_id: str, field_id: str, version_id: str) -> str | None:
        return next(
            (
                key
                for key, item in sorted(self.claims.items())
                if (item.record_id, item.field_id, item.source_version_id)
                == (record_id, field_id, version_id)
            ),
            None,
        )

    def store(self, rows: tuple[Record, ...]) -> int:
        added = 0
        for row in rows:
            target: dict[str, Any] = self.claims if isinstance(row, Claim) else self.confirmations
            added += row.key not in target
            target.setdefault(row.key, row)
        return added

    def current(self, record: SourceKey = RECORD) -> dict[str, Claim]:
        """A record's claims that no stored claim supersedes, as `claims_as_of` selects them."""
        replaced = {item.supersedes for item in self.claims.values()}
        return {
            item.field_id: item
            for key, item in self.claims.items()
            if key not in replaced and item.record_id == record.record_id
        }


def link(journal: Journal, record: SourceKey) -> str:
    """Mint and link an object for a record, as identity resolution would before tracking."""
    with journal.locked() as locked:
        kn_id = locked.mint(
            record,
            "core.supplier_offer",
            occurred_at=T0,
            actor=ACTOR,
            reason="Fixture identity",
            evidence="archive:fixture",
        )
        locked.append(
            event(
                Link(record=record, kn_id=kn_id, method="minted"),
                previous=locked.events[-1],
                occurred_at=T0,
                actor=ACTOR,
                reason="Fixture identity",
                evidence="archive:fixture",
            )
        )
    return kn_id


def merge(journal: Journal, kn_id: str, survivor: str) -> None:
    with journal.locked() as locked:
        locked.append(
            event(
                Merge(kn_id=kn_id, survivor=survivor),
                previous=locked.events[-1],
                occurred_at=T0 + timedelta(days=1),
                actor="local:reviewer",
                reason="Fixture duplicate",
                evidence="archive:fixture",
                decision_ref="identity-review:fixture",
            )
        )


def linked_journal(data_dir: Path) -> tuple[Journal, str]:
    journal = Journal(data_dir)
    return journal, link(journal, RECORD)


def track(
    journal: Journal, claims: MemoryClaims, item: Delivery
) -> tuple[Tracked, tuple[Record, ...], int]:
    """The writer's sequence on a local journal: plan, validate rows, append, store."""
    with journal.locked() as locked:
        tracked, events = prepare(locked, item, actor=ACTOR)
        rows = evidence_rows(tracked, item, claims, item.fetched_at + timedelta(minutes=1))
        locked.append_batch(events)
    return tracked, rows, claims.store(rows)
