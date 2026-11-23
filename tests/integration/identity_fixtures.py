"""Replay fixtures shared by the identity and combined model acceptance suites."""

from pathlib import Path

from kn.identity.journal import Journal
from tests.identity.fixtures import history


def seed_identity_fixture(data_dir: Path) -> Journal:
    journal = Journal(data_dir)
    for item in history():
        journal.append(item)
    return journal
