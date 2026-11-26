"""Journal-backed matching, ownership and retry semantics."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kn.contracts.model import canonical
from kn.identity.events import Event
from kn.identity.journal import Journal, LockedJournal
from kn.identity.matching.ingest import Receipt, record
from kn.identity.matching.observe import Observation
from kn.identity.matching.scoring import verify_match
from kn.identity.model import Link, Match, Mint, Retire, SourceKey, Unlink
from kn.identity.profiles import Profile
from kn.identity.queries import inspect
from tests.identity.fixtures import NOW, A
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


def test_pending_match_refuses_other_journal_writes_until_its_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = apply(journal, config, observation({}, source="fixture:first"))
    incoming = observation({}, source="fixture:pending")
    original_append = LockedJournal.append_batch

    def interrupted(locked: LockedJournal, values: tuple[Event, ...]) -> None:
        original_append(locked, values[:1])
        raise OSError("injected interruption")

    with monkeypatch.context() as patch:
        patch.setattr(LockedJournal, "append_batch", interrupted)
        with pytest.raises(OSError, match="injected interruption"):
            apply(journal, config, incoming)
    before = journal.read()
    retire = append(before, Retire(kn_id=first.kn_id))[-1]
    with pytest.raises(ValueError, match="retry the pending identity match"):
        journal.append(retire)
    with journal.locked() as locked, pytest.raises(ValueError, match="retry the pending"):
        locked.mint(
            SourceKey(source="fixture:operator", key="00042"),
            config.entity_class,
            occurred_at=NOW,
            actor="engine:fixture",
            reason="Fixture",
            evidence="archive:fixture",
        )
    assert journal.read() == before
    assert apply(journal, config, incoming).kn_id is not None
    assert journal.append(append(journal.read(), Retire(kn_id=first.kn_id))[-1])


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
    parallel = append(
        journal.read(),
        Mint(
            kn_id=A,
            entity_class=config.entity_class,
            anchor=SourceKey(source="fixture:parallel", key="00042"),
        ),
    )[-1]
    # A journal written before appends checked for a pending match can hold this suffix.
    with journal.path.open("ab") as stream:
        stream.write((canonical(parallel.model_dump(mode="json")) + "\n").encode("ascii"))
    before = journal.read()
    with pytest.raises(ValueError, match="diverged from the pending match"):
        apply(journal, config, incoming)
    assert journal.read() == before


def test_observations_refuse_duplicates_and_retry_across_utc_offsets(tmp_path: Path) -> None:
    from datetime import timedelta, timezone

    from kn.identity.matching.observe import Key, Reading

    record_key = SourceKey(source="fixture:offset", key="00042")
    for extra in (
        {"attributes": (Reading(field_id="x", value="1"), Reading(field_id="x", value="2"))},
        {
            "authoritative": (
                Key(namespace="lei", issuer="fixture:a", value="1"),
                Key(namespace="lei", issuer="fixture:b", value="1"),
            )
        },
    ):
        with pytest.raises(ValueError, match="duplicate"):
            Observation(record=record_key, version="1", observed_at=NOW, **extra)
    journal = Journal(tmp_path)
    config = profile()
    utc = Observation(record=record_key, version="1", observed_at=NOW)
    shifted = utc.model_copy(update={"observed_at": NOW.astimezone(timezone(timedelta(hours=2)))})
    assert apply(journal, config, utc) == apply(
        journal, config, Observation.model_validate(shifted.model_dump())
    )
    assert len(journal.read()) == 3


def test_match_retry_uses_the_link_and_identifiers_before_its_decision(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = observation({}, lei="00000000000000000042")
    minted = apply(journal, config, first)
    later = observation({"organization.name": "Fixture"}, version="2")
    linked = apply(journal, config, later)
    assert linked.match.trace.route == "existing_link"
    assert journal.append(
        append(journal.read(), Unlink(kn_id=minted.kn_id, record=first.record))[-1]
    )
    before = journal.path.read_bytes()
    assert apply(journal, config, first) == minted
    assert apply(journal, config, later) == linked
    assert journal.path.read_bytes() == before
