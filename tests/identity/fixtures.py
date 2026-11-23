"""Synthetic v1 history covers every event kind and every registered identity table."""

from datetime import UTC, datetime

from kn.identity.events import Event, event
from kn.identity.model import (
    Assignment,
    Attribute,
    Candidate,
    ChangeSet,
    Feature,
    FieldChange,
    FieldHash,
    Identifier,
    Link,
    Match,
    Merge,
    Mint,
    Reclassify,
    Restore,
    Retire,
    SourceKey,
    Split,
    Unlink,
    Version,
)
from kn.identity.state import replay

NOW = datetime(2026, 1, 1, tzinfo=UTC)
A, B, C, D, E, F = (f"kn:019b76da-a800-7000-8000-{number:012d}" for number in range(1, 7))
KEY = SourceKey(source="fixture:manufacturer", key="00042")
OTHER = SourceKey(source="fixture:distributor", key="00042")
DIGEST = "a" * 64


def history() -> tuple[Event, ...]:
    result: list[Event] = []

    def add(payload):
        value = event(
            payload,
            previous=result[-1] if result else None,
            occurred_at=NOW,
            actor="engine:fixture",
            reason="Fixture history",
            evidence="archive:fixture",
            decision_ref="decision:fixture",
        )
        result.append(value)
        return value.event_id

    for key, kn_id in enumerate((A, B, C, D, E)):
        add(
            Mint(
                kn_id=kn_id,
                entity_class="core.organization",
                anchor=KEY if kn_id == A else SourceKey(source="fixture:anchor", key=str(key)),
            )
        )
    link = add(Link(record=KEY, kn_id=A, method="minted"))
    identifier = add(
        Identifier(
            kn_id=A,
            namespace="lei",
            value="fixture-lei",
            issuer="lei:fixture",
            authority="authoritative",
            valid_from=NOW,
        )
    )
    attribute = add(
        Attribute(
            kn_id=A,
            field_id="organization.name",
            original="Fixture Ltd",
            normalized="fixture ltd",
            normalizer="casefold-v1",
            profile_digest=DIGEST,
        )
    )
    version = add(
        Version(
            record=KEY,
            version="0001",
            content_digest=DIGEST,
            field_hashes=(FieldHash(field_id="organization.name", digest=DIGEST),),
            observed_at=NOW,
            fetch_id="fetch:fixture",
            archive_record_id="archive:fixture",
            code_digest=DIGEST,
        )
    )
    add(
        ChangeSet(
            version_id=version,
            changes=(
                FieldChange(field_id="organization.name", change="added", current_hash=DIGEST),
            ),
        )
    )
    match = add(
        Match(
            record=OTHER,
            profile_digest=DIGEST,
            profile_version="1.0.0",
            decision="link",
            selected=B,
            candidates=(
                Candidate(
                    kn_id=B,
                    score=2,
                    probability=0.9,
                    features=(
                        Feature(
                            field_id="organization.name",
                            left="fixture",
                            right="fixture",
                            comparator="exact",
                            outcome="agree",
                            weight=2,
                        ),
                    ),
                ),
            ),
        )
    )
    add(
        Link(
            record=OTHER,
            kn_id=B,
            method="scored_match",
            score=2,
            probability=0.9,
            profile_digest=DIGEST,
            profile_version="1.0.0",
            match_id=match,
        )
    )
    add(Unlink(record=OTHER, kn_id=B))
    other_link = add(Link(record=OTHER, kn_id=B, method="existing_link"))
    add(Merge(kn_id=A, survivor=B))
    add(Merge(kn_id=B, survivor=C))
    add(
        Split(
            kn_id=C,
            successors=(D, E),
            assignments=tuple(
                Assignment(item_id=key, successor=D if key != other_link else E)
                for key in (link, identifier, attribute, other_link)
            ),
        )
    )
    add(Retire(kn_id=D))
    add(Restore(kn_id=D))
    add(
        Reclassify(
            kn_id=E,
            successor=Mint(
                kn_id=F,
                entity_class="core.manufacturer",
                anchor=SourceKey(source="fixture:anchor", key="new-class"),
            ),
        )
    )
    replay(tuple(result))
    return tuple(result)
