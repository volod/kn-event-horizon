import gzip
import zlib
from datetime import timedelta
from pathlib import Path
from typing import Any

from kn.archive import Archive
from kn.archive.model import HttpExchange
from tests.archive.fixtures import AT, LIMITS, SAMPLE, batch, capture
from tests.archive.independent import manifests, read_segment

_EXPECTED_TYPES = {
    "response": ["response", "request", "metadata"],
    "resource": ["resource", "metadata"],
    "revisit": ["revisit", "request", "metadata"],
}


def _commit_every_record_kind(archive: Archive) -> None:
    get = HttpExchange("GET", 200, response_headers=(("Content-Type", "application/json"),))
    encoded = HttpExchange("GET", 200, response_headers=(("Content-Encoding", "gzip"),))
    deflated = HttpExchange("GET", 200, response_headers=(("Content-Encoding", "deflate"),))
    first = archive.commit(
        batch(),
        [
            capture(http=get),
            capture(gzip.compress(SAMPLE, mtime=0), key="gzip", http=encoded),
            capture(zlib.compress(SAMPLE), key="deflate", http=deflated),
            capture(b"", key="empty", http=HttpExchange("HEAD", 304)),
            capture(b"x", key="unnamed-status", http=HttpExchange("GET", 299)),
            capture(key="file", origin_uri="file:///curated/sample.json"),
            capture(bytes(range(256)) * 300, key="bytes", origin_uri="urn:kn:fixture:bytes"),
            capture(
                b"\r\n\r\nWARC/1.1\r\n\r\n",
                key="framing",
                origin_uri="urn:kn:fixture:framing",
                fetched_at=AT + timedelta(microseconds=250_000),
            ),
            capture(key="blob", backend="blob", origin_uri="urn:kn:fixture:blob"),
        ],
        limits=LIMITS,
    ).captures[0]
    archive.commit(
        batch("revisit"),
        [capture(http=get, revisit_of=first.record_id, fetched_at=AT + timedelta(days=1))],
        limits=LIMITS,
    )


Records = list[dict[str, Any]]


def test_an_independent_reader_accepts_every_record_kind(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    _commit_every_record_kind(archive)
    segments: dict[str, tuple[str, Records]] = {}
    for directory, manifest in manifests(tmp_path):
        for entry in manifest["captures"]:  # type: ignore[attr-defined]
            if entry["backend"] == "warc":
                records = read_segment(directory / entry["payload_path"])
                kind = archive.metadata(entry["record_id"]).kind
                _check_locators(entry, kind, records)
                segments[entry["record_id"]] = kind, records
    kinds = [kind for kind, _ in segments.values()]
    assert (len(kinds), kinds.count("response"), kinds.count("revisit")) == (9, 5, 1)
    for kind, records in segments.values():
        for row in records:
            _check_digests(row)
        if kind == "revisit":
            _, target = segments[str(records[0]["refers_to"])]
            assert records[0]["payload"] == b""
            assert records[0]["payload_digest"] == target[0]["payload_digest"]
            assert target[0]["payload"] == SAMPLE


def _check_locators(entry: dict[str, Any], kind: str, records: Records) -> None:
    assert [row["type"] for row in records] == _EXPECTED_TYPES[kind]
    assert records[0]["record_id"] == entry["record_id"]
    members = (entry["payload_member"], entry["request_member"], entry["metadata_member"])
    assert [row["offset"] for row in records] == [m["offset"] for m in members if m is not None]


def _check_digests(row: dict[str, Any]) -> None:
    assert row["version"] == "WARC/1.1"
    assert row["block_ok"] is True, row["type"]
    if row["type"] in ("response", "request"):
        assert row["payload_ok"] is True, row["type"]
    elif not row["http"]:
        # FastWARC defines a payload only for HTTP messages; KN's equals the block.
        assert row["payload_digest"] == row["block_digest"]
