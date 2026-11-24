"""Synthetic semantic snapshots; no proposal content is imported."""

import json
from pathlib import Path

import pytest

from kn.semantic import ExternalReferences, Snapshot

REFERENCES = ExternalReferences(frozenset({"fixture.entity"}), frozenset({"fixture.evidence"}))


@pytest.fixture(autouse=True)
def default_vocabulary_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KN_VOCABULARY_DOMAIN", raising=False)


@pytest.fixture
def model() -> Snapshot:
    return json.loads((Path(__file__).parent / "fixtures" / "model.json").read_text())
