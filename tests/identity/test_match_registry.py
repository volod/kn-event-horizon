"""Matching evidence after merges, splits, aliases and links from several source records."""

import json
from datetime import timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

from kn.identity.events import Event
from kn.identity.journal import Journal
from kn.identity.matching.ingest import Receipt, record
from kn.identity.matching.observe import Key, Observation, Reading
from kn.identity.matching.resolve import resolve
from kn.identity.matching.scoring import verify_match
from kn.identity.model import Assignment, Attribute, Link, Merge, SourceKey, Split
from kn.identity.profiles import Profile
from kn.identity.state import replay
from tests.identity.fixtures import NOW, A, B
from tests.identity.test_matching import ROOT, calibrated, observation, profile, registry
from tests.identity.test_state import append

LEI = "00000000000000000042"


def _org(
    source: str, minutes: int, lei: str | None = None, version: str = "1", **fields: str
) -> Observation:
    return Observation(
        record=SourceKey(source=source, key="00042"),
        version=version,
        observed_at=NOW + timedelta(minutes=minutes),
        attributes=tuple(
            Reading(field_id=f"organization.{key}", value=value) for key, value in fields.items()
        ),
        authoritative=(Key(namespace="lei", issuer="fixture:lei", value=lei),) if lei else (),
    )


def _ingest(journal: Journal, config: Profile, incoming: Observation) -> Receipt:
    with journal.locked() as locked:
        return record(locked, config, incoming, actor="engine:fixture", evidence="archive:fixture")


def _reviewed(journal: Journal, payload: Merge | Split) -> None:
    journal.append(append(journal.read(), payload)[-1])


def _candidates(receipt: Receipt) -> list[str]:
    return [item.kn_id for item in receipt.match.candidates]


def test_survivor_blocks_on_the_evidence_of_each_absorbed_record(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    alpha = _ingest(
        journal, config, _org("src:alpha", 0, name="Alpha Ltd", domain="fixture-alpha.com")
    )
    beta = _ingest(journal, config, _org("src:beta", 1, name="Beta Ltd", domain="fixture-beta.com"))
    assert alpha.kn_id and beta.kn_id
    _reviewed(journal, Merge(kn_id=alpha.kn_id, survivor=beta.kn_id))
    later = _ingest(journal, config, _org("src:new", 2, domain="fixture-alpha.com"))
    assert later.match.decision == "review"
    assert _candidates(later) == [beta.kn_id]
    verify_match(config, later.match)
    schema = json.loads((ROOT / "contracts/core/identity/event.schema.json").read_text())
    attributes = [item for item in journal.read() if isinstance(item.payload, Attribute)]
    assert {item.payload.record.source for item in attributes} == {"src:alpha", "src:beta"}
    for item in attributes:
        Draft202012Validator(schema).validate(item.model_dump(mode="json"))
        assert Event.model_validate_json(item.model_dump_json()) == item


def test_records_linked_through_one_identifier_keep_their_own_readings(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = _ingest(journal, config, _org("src:x", 0, LEI, domain="fixture-alpha.com"))
    second = _ingest(journal, config, _org("src:y", 1, LEI, domain="fixture-alpha-group.com"))
    assert second.kn_id == first.kn_id
    later = _ingest(journal, config, _org("src:z", 2, domain="fixture-alpha.com"))
    assert (later.match.decision, _candidates(later)) == ("review", [first.kn_id])

    same_time = Journal(tmp_path / "same-time")
    one = _ingest(same_time, config, _org("src:x", 0, LEI, name="Omega Fixture Ltd"))
    _ingest(same_time, config, _org("src:y", 0, LEI, name="Omega Holdings"))
    named = _ingest(same_time, config, _org("src:z", 1, name="Omega Fixture Ltd"))
    assert (named.match.decision, _candidates(named)) == ("review", [one.kn_id])


def test_split_successors_keep_the_readings_assigned_to_them(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    receipts = [
        _ingest(journal, config, _org(f"src:{name}", index, domain=f"fixture-{name}.com"))
        for index, name in enumerate(("alpha", "beta", "gamma", "delta"))
    ]
    alpha, beta, gamma, delta = (item.kn_id for item in receipts)
    assert alpha and beta and gamma and delta
    _reviewed(journal, Merge(kn_id=alpha, survivor=beta))
    alpha_record = receipts[0].match.record
    assignments = tuple(
        Assignment(
            item_id=key,
            successor=gamma
            if isinstance(payload := holding.event.payload, Link | Attribute)
            and payload.record == alpha_record
            else delta,
        )
        for key, holding in journal.state().owned(beta).items()
    )
    _reviewed(journal, Split(kn_id=beta, successors=(gamma, delta), assignments=assignments))
    assert journal.state().resolve(alpha) == tuple(sorted((gamma, delta)))
    later = _ingest(journal, config, _org("src:new", 9, domain="fixture-alpha.com"))
    assert (later.match.decision, _candidates(later)) == ("review", [gamma])
    again = _ingest(journal, config, _org("src:alpha", 10, version="2"))
    assert (again.match.trace.route, again.kn_id) == ("existing_link", gamma)


def test_aliases_follow_merge_and_split_redirects() -> None:
    config = calibrated(profile())
    state = registry(
        config,
        [
            {"attributes": {"organization.name": "Fixture Alpha"}},
            {"attributes": {"organization.name": "Fixture Beta"}},
        ],
    )
    merged = replay(append(tuple(state.events), Merge(kn_id=A, survivor=B)))
    result = resolve(merged, config, observation({}, aliases=(A,)))
    assert (result.trace.route, result.decision) == ("alias", "review")
    assert [item.kn_id for item in result.candidates] == [B]
    unknown = "kn:019b76da-a800-7000-8000-000000009999"
    assert resolve(merged, config, observation({}, aliases=(unknown,))).decision == "mint"


def test_blocking_checks_the_latest_reading_at_the_observation_instant(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = _ingest(journal, config, _org("src:known", 0, domain="fixture-alpha.com"))
    _ingest(journal, config, _org("src:known", 2, version="2", domain="fixture-beta.com"))
    with journal.locked() as locked:
        before = resolve(locked.state, config, _org("src:new", 1, domain="fixture-alpha.com"))
        after = resolve(locked.state, config, _org("src:new", 3, domain="fixture-alpha.com"))
        assert [candidate.kn_id for candidate in before.candidates] == [first.kn_id]
        assert after.candidates == ()


def test_blocking_requires_a_composite_key_within_one_origin(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    config = profile()
    first = _ingest(journal, config, _org("src:alpha", 0, LEI, tax_id="ORG-42"))
    _ingest(journal, config, _org("src:beta", 1, LEI, country="UA"))
    incoming = _org("src:new", 3, tax_id="ORG-42", country="UA")
    with journal.locked() as locked:
        assert resolve(locked.state, config, incoming).candidates == ()
    _ingest(journal, config, _org("src:gamma", 2, LEI, tax_id="ORG-42", country="UA"))
    with journal.locked() as locked:
        assert [item.kn_id for item in resolve(locked.state, config, incoming).candidates] == [
            first.kn_id
        ]
