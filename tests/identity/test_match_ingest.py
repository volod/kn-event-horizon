"""Journal-backed matching, ownership and retry semantics."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kn.identity.events import Event
from kn.identity.journal import Journal, LockedJournal
from kn.identity.matching.ingest import Receipt, record
from kn.identity.matching.observe import Observation
from kn.identity.matching.scoring import verify_match
from kn.identity.model import Link, Match, Mint, SourceKey
from kn.identity.profiles import Profile
from kn.identity.queries import inspect
from tests.identity.fixtures import A
from tests.identity.test_matching import observation, profile
from tests.identity.test_state import append


def apply(journal: Journal, config: Profile, incoming: Observation) -> Receipt:
    with journal.locked() as locked:
        return record(locked, config, incoming, actor="engine:fixture", evidence="archive:fixture")


def test_mint_registers_keys_and_later_source_links_without_rewriting_history(
    tmp_path: Path,
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = observation({"organization.name": "Old Fixture Ltd"}, lei="00000000000000000042")
    minted = apply(journal, config, first)
    assert minted.match.decision == "mint"
    assert minted.kn_id is not None
    assert minted.kn_id == minted.match.trace.minted_id

    other = observation(
        {"organization.name": "Renamed Fixture Ltd"}, lei="00000000000000000042", source="other"
    )
    linked = apply(journal, config, other)
    assert linked.kn_id == minted.kn_id
    assert linked.match.trace.route == "authoritative_key"
    assert journal.state().matches[linked.match_id] == linked.match
    links = [entry.payload for entry in journal.read() if isinstance(entry.payload, Link)]
    assert [(link.method, link.match_id) for link in links] == [
        ("minted", minted.match_id),
        ("authoritative_key", linked.match_id),
    ]
    for result in (minted, linked):
        verify_match(config, result.match)
    history = journal.read()
    assert apply(journal, config, first) == minted
    assert apply(journal, config, other) == linked
    assert journal.read() == history
    result = inspect(journal, "history", minted.kn_id)
    assert minted.match_id in {entry["event_id"] for entry in result["events"]}
    assert linked.match_id in {entry["event_id"] for entry in result["events"]}


def test_journal_recovers_complete_prefix_without_reminting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    incoming = observation({"organization.name": "Fixture"})
    original_append = LockedJournal.append_batch

    def interrupted(locked: LockedJournal, values: tuple[Event, ...]) -> None:
        original_append(locked, values[:2])
        raise OSError("injected interruption")

    with monkeypatch.context() as patch:
        patch.setattr(LockedJournal, "append_batch", interrupted)
        with pytest.raises(OSError, match="injected interruption"):
            apply(journal, config, incoming)
    match_entry, mint_entry = journal.read()
    assert isinstance(match_entry.payload, Match)
    with pytest.raises(ValueError, match="retry the pending identity match"):
        apply(journal, config, observation({}, source="fixture:parallel"))
    result = apply(journal, config, incoming)
    assert result.kn_id == mint_entry.payload.kn_id
    assert result.match_id == match_entry.event_id
    assert len(journal.read()) == 4
    assert journal.state().matches[result.match_id] == result.match


def test_concurrent_retry_records_one_decision(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    incoming = observation({})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(journal, config, incoming), range(2)))
    assert results[0] == results[1]
    assert [entry.payload.kind for entry in journal.read()] == [
        "match_recorded",
        "minted",
        "linked",
    ]


def test_changed_history_refuses_repair_of_an_incomplete_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    incoming = observation({})
    original_append = LockedJournal.append_batch

    def interrupted(locked: LockedJournal, values: tuple[Event, ...]) -> None:
        original_append(locked, values[:1])
        raise OSError("injected interruption")

    with monkeypatch.context() as patch:
        patch.setattr(LockedJournal, "append_batch", interrupted)
        with pytest.raises(OSError, match="injected interruption"):
            apply(journal, config, incoming)
    journal.append(
        append(
            journal.read(),
            Mint(
                kn_id=A,
                entity_class=config.entity_class,
                anchor=SourceKey(source="fixture:parallel", key="00042"),
            ),
        )[-1]
    )
    before = journal.read()
    with pytest.raises(ValueError, match="diverged from the pending match"):
        apply(journal, config, incoming)
    assert journal.read() == before
