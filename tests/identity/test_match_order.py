"""Resolution decisions that must not depend on submission order or a disagreeing discriminator."""

import itertools
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pytest

from kn.identity.journal import Journal
from kn.identity.matching.observe import Observation, Reading
from kn.identity.matching.resolve import resolve
from kn.identity.model import Identifier, Mint, SourceKey
from kn.identity.state import replay
from tests.identity.fixtures import NOW, A, B
from tests.identity.test_match_registry import LEI, _ingest, _org
from tests.identity.test_matching import calibrated, observation, profile, registry
from tests.identity.test_state import append

OTHER_LEI = "00000000000000000043"
MAKER, OTHER_MAKER, PART = (f"kn:019b76da-a800-7000-8000-{n:012x}" for n in (0xB1, 0xB2, 0xB3))
GTIN, OTHER_GTIN = "4006381333931", "5901234123457"


def _observe(source: str, minutes: int, prefix: str, **fields: str) -> Observation:
    return Observation(
        record=SourceKey(source=source, key="00042"),
        version="1",
        observed_at=NOW + timedelta(minutes=minutes),
        attributes=tuple(
            Reading(field_id=f"{prefix}.{key}", value=value) for key, value in fields.items()
        ),
    )


# Each class's records, with the groups that every submission order must produce.
CORPORA = {
    "core.organization": (
        {
            "lei": _org("src:alpha", 0, LEI, name="Alpha Ltd", domain="fixture-alpha.com"),
            "lei-renamed": _org("src:renamed", 1, LEI, name="Alpha Holdings Ltd"),
            "other-lei": _org("src:beta", 2, OTHER_LEI, name="Beta GmbH"),
            "domain-early": _org("src:gamma", 3, name="Gamma Ltd", domain="fixture-gamma.com"),
            "domain-late": _org("src:delta", 5, name="Gamma Ltd", domain="fixture-gamma.com"),
        },
        {("domain-early", "domain-late"), ("lei", "lei-renamed"), ("other-lei",)},
    ),
    "core.manufacturer_part": (
        {
            "maker": _observe("src:a", 0, "part", manufacturer=MAKER, mpn="BC547B"),
            "other-maker": _observe("src:b", 1, "part", manufacturer=OTHER_MAKER, mpn="BC547B"),
        },
        {("maker",), ("other-maker",)},
    ),
    "core.orderable_variant": (
        {
            "tape": _observe(
                "src:a", 0, "variant", part=PART, packaging="Tape", ordering_suffix="T", gtin=GTIN
            ),
            "reel": _observe(
                "src:b",
                1,
                "variant",
                part=PART,
                packaging="Reel",
                ordering_suffix="T",
                gtin=OTHER_GTIN,
            ),
        },
        {("reel",), ("tape",)},
    ),
}


@pytest.mark.parametrize("entity_class", sorted(CORPORA))
def test_every_submission_order_yields_the_same_objects_and_decisions(
    tmp_path: Path, entity_class: str
) -> None:
    """Authoritative keys and scored evidence agree however late an earlier observation arrives."""
    config = calibrated(profile(entity_class))
    corpus, expected = CORPORA[entity_class]
    decisions: set[tuple[tuple[str, int], ...]] = set()
    for number, order in enumerate(itertools.permutations(corpus)):
        journal = Journal(tmp_path / str(number))
        receipts = {name: _ingest(journal, config, corpus[name]) for name in order}
        state = journal.state()
        groups: dict[tuple[str, ...], set[str]] = {}
        for name, receipt in receipts.items():
            assert receipt.kn_id is not None, (order, name, receipt.match.trace)
            groups.setdefault(state.resolve(receipt.kn_id), set()).add(name)
        assert {tuple(sorted(group)) for group in groups.values()} == expected, order
        decisions.add(
            tuple(sorted(Counter(item.match.decision for item in receipts.values()).items()))
        )
    assert len(decisions) == 1


def test_an_observation_older_than_every_reading_of_a_candidate_still_blocks(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    known = _ingest(journal, config, _org("src:known", 10, domain="fixture-alpha.com"))
    late = _ingest(journal, config, _org("src:late", 0, domain="fixture-alpha.com"))
    assert late.match.decision == "review"
    assert [item.kn_id for item in late.match.candidates] == [known.kn_id]
    domain = next(
        item for item in late.match.candidates[0].features if item.field_id.endswith("domain")
    )
    assert domain.outcome == "agree"


def test_an_authoritative_key_seen_before_its_first_interval_links_to_its_holder(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    renamed = _ingest(journal, config, _org("src:renamed", 10, LEI, name="Alpha Holdings"))
    original = _ingest(journal, config, _org("src:original", 0, LEI, name="Alpha Ltd"))
    assert original.match.trace is not None
    assert original.match.trace.route == "authoritative_key"
    assert original.kn_id == renamed.kn_id
    state = journal.state()
    intervals = state.identifiers("lei", LEI)
    assert len(intervals) == 1
    assert intervals[0].kn_id == renamed.kn_id


def test_an_authoritative_key_seen_between_two_holders_still_needs_review() -> None:
    config = profile()
    events: tuple = ()
    for kn_id, start, end in ((A, 0, 10), (B, 20, None)):
        events = append(
            events,
            Mint(
                kn_id=kn_id,
                entity_class=config.entity_class,
                anchor=SourceKey(source="fixture:known", key=kn_id),
            ),
        )
        events = append(
            events,
            Identifier(
                kn_id=kn_id,
                namespace="lei",
                issuer="fixture:lei",
                value=LEI,
                authority="authoritative",
                valid_from=NOW + timedelta(minutes=start),
                valid_to=None if end is None else NOW + timedelta(minutes=end),
            ),
        )
    incoming = _org("src:between", 15, LEI)
    match = resolve(replay(events), config, incoming)
    assert (match.decision, match.trace and match.trace.route) == ("review", "conflict")
    early = resolve(replay(events), config, _org("src:early", -5, LEI))
    assert (early.decision, early.selected) == ("link", A)


def test_a_disagreeing_discriminator_never_links_automatically() -> None:
    """A GTIN that differs vetoes an auto-link that manufacturer and MPN would reach alone."""
    config = calibrated(profile("core.manufacturer_part"))
    known = {
        "part.manufacturer": MAKER,
        "part.mpn": "BC547B",
        "part.gtin": GTIN,
        "part.package_code": "TO-92",
        "part.packaging_suffix": "BULK",
    }
    state = registry(config, [{"attributes": known}])
    match = resolve(state, config, observation({**known, "part.gtin": OTHER_GTIN}))
    best = match.candidates[0]
    assert best.probability >= config.link_threshold
    assert [item.field_id for item in best.features if item.outcome == "disagree"] == ["part.gtin"]
    assert (match.decision, match.selected) == ("review", None)
