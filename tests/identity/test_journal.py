"""Durable minting, idempotent retries, locking and fail-closed damaged journals."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from kn.identity.journal import Journal
from kn.identity.model import Mint, SourceKey
from tests.identity.fixtures import KEY, NOW, A, F, history
from tests.identity.test_state import append


def mint(journal: Journal, key: SourceKey = KEY, entity_class: str = "core.organization") -> str:
    with journal.locked() as locked:
        return locked.mint(
            key,
            entity_class,
            occurred_at=NOW,
            actor="engine:test",
            reason="First sight",
            evidence="archive:test",
        )


def test_concurrent_anchor_mint_retries_keep_uuid_after_sql_loss(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: mint(journal), range(8)))
    assert len(set(ids)) == 1
    assert len(journal.read()) == 1
    assert mint(Journal(tmp_path)) == ids[0]
    assert mint(journal, SourceKey(source="other-source", key=KEY.key)) != ids[0]
    with pytest.raises(ValueError, match="different entity class"):
        mint(journal, entity_class="core.manufacturer")
    assert journal.path.stat().st_mode & 0o777 == 0o600
    assert journal.path.parent.stat().st_mode & 0o777 == 0o700
    assert journal.path.read_bytes().isascii()


def test_append_retries_invalid_transition_and_sequence_collision(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    events = history()[:5]
    for item in events:
        assert journal.append(item)
        assert not journal.append(item)
    before = journal.path.read_bytes()
    invalid = append(
        events,
        Mint(kn_id=A, entity_class="core.organization", anchor=SourceKey(source="x", key="y")),
    )[-1]
    with pytest.raises(ValueError, match="reused"):
        journal.append(invalid)
    collision = append((), Mint(kn_id=F, entity_class="core.organization", anchor=KEY))[-1]
    with pytest.raises(ValueError, match="different content"):
        journal.append(collision)
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("damage", ["torn", "malformed", "digest", "gap", "blank", "version"])
def test_damaged_history_is_preserved_and_refuses_append(tmp_path: Path, damage: str) -> None:
    journal = Journal(tmp_path)
    for item in history()[:2]:
        journal.append(item)
    content = journal.path.read_bytes()
    if damage == "torn":
        content = content[:-1]
    elif damage == "malformed":
        content += b"{\n"
    elif damage == "blank":
        content += b"\n"
    elif damage == "gap":
        content = content.splitlines(keepends=True)[1]
    else:
        data = json.loads(content.splitlines()[0])
        data["reason" if damage == "digest" else "schema_version"] = "tampered"
        content = (json.dumps(data) + "\n").encode()
    journal.path.write_bytes(content)
    with pytest.raises(ValueError):
        mint(journal)
    assert journal.path.read_bytes() == content


def test_symlinks_are_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "identity").symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        Journal(tmp_path).read()


def test_copied_event_cannot_bypass_validation_at_append(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    value = history()[0].model_copy(update={"reason": "changed without rehashing"})
    with pytest.raises(ValueError, match="digest mismatch"):
        journal.append(value)
    assert journal.read() == ()


def test_refused_batch_does_not_change_the_cached_prefix(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    first, second, *_ = history()
    assert journal.append(first)
    invalid = append(
        (first, second),
        Mint(kn_id=A, entity_class="core.organization", anchor=SourceKey(source="x", key="y")),
    )[-1]
    with journal.locked() as locked:
        with pytest.raises(ValueError, match="reused"):
            locked.append_batch((second, invalid))
        assert locked.events == (first,)
        assert locked.append(second)
    assert journal.read() == (first, second)


def test_external_writer_and_replaced_prefix_invalidate_cached_state(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    first, second, third, *_ = history()
    assert journal.append(first)
    assert Journal(tmp_path).append(second)
    assert journal.append(third)

    original = journal.path.read_bytes()
    replacement = journal.path.with_suffix(".new")
    replacement.write_bytes(original.replace(b"Fixture history", b"fixture history", 1))
    replacement.replace(journal.path)
    with pytest.raises(ValueError, match="digest mismatch"):
        journal.append(third)


def test_interrupted_append_requires_reopening_before_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = Journal(tmp_path)
    first, second, *_ = history()
    assert journal.append(first)

    def fail_write(encoded: bytes) -> None:
        raise OSError("interrupted append")

    with journal.locked() as locked:
        monkeypatch.setattr(locked, "_write", fail_write)
        with pytest.raises(OSError, match="interrupted append"):
            locked.append(second)
        with pytest.raises(ValueError, match="reopen the identity journal"):
            locked.append(second)
    assert journal.read() == (first,)
    assert journal.append(second)
