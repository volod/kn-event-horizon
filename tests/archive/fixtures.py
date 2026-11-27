"""Deterministic approved-capture inputs for archive tests."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from kn.archive.model import BatchKey, Capture, Limits, Retention

AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
LIMITS = Limits(max_payload_bytes=2_000_000, max_decoded_bytes=2_000_000)
SAMPLE = (Path(__file__).parents[1] / "fixtures/archive/response.json").read_bytes()


def batch(batch_id: str = "001", *, source: str = "example", domain: str = "space") -> BatchKey:
    return BatchKey(
        domain=domain, source_id=f"{domain}:{source}", run_id="run-1", batch_id=batch_id
    )


def capture(payload: bytes = SAMPLE, **overrides: Any) -> Capture:
    return Capture(
        **{
            "key": "record-1",
            "origin_uri": "https://example.test/catalog?format=json",
            "fetched_at": AT,
            "body": BytesIO(payload),
            "config_sha256": "a" * 64,
            "code_sha256": "b" * 64,
            "retention": Retention(access="internal", deletion_scope="fixture"),
            **overrides,
        }
    )


def committed_path(root: Path, key: BatchKey, relative: str) -> Path:
    return root.joinpath("captures", *key.parts(), relative)


def rewrite_descriptor(root: Path, key: str, modifications: dict[str, object]) -> None:
    manifest_path = committed_path(root, batch(key), "manifest.json")
    manifest = json.loads(manifest_path.read_bytes())
    entry = manifest["captures"][0]
    descriptor = manifest_path.parent / entry["metadata_path"]
    data = json.loads(descriptor.read_bytes())
    data.update(modifications)
    if data["schema_version"] == 1:
        del data["decoded_size"]
    serialized = json.dumps(data, ensure_ascii=True).encode("ascii")
    descriptor.write_bytes(serialized)
    entry["metadata"] = {"size": len(serialized), "sha256": sha256(serialized).hexdigest()}
    manifest_path.write_text(json.dumps(manifest), encoding="ascii")
