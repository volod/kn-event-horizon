"""Synthetic semantic snapshots; no proposal content is imported."""

import json
from pathlib import Path

import pytest

from kn.semantic import ExternalReferences, Snapshot

REFERENCES = ExternalReferences(frozenset({"fixture.entity"}), frozenset({"fixture.evidence"}))


@pytest.fixture
def model() -> Snapshot:
    return json.loads((Path(__file__).parent / "fixtures" / "model.json").read_text())
