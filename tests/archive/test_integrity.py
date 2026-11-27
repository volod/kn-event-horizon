import gzip
import json
import zlib
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

from kn.archive import Archive
from kn.archive.model import ArchiveError, HttpExchange, Limits, Redaction
from tests.archive.fixtures import (
    LIMITS,
    SAMPLE,
    batch,
    capture,
    committed_path,
    rewrite_descriptor,
)


@pytest.mark.parametrize("encoding", ["gzip", "deflate"])
def test_content_decoding_limits_and_invalid_streams(tmp_path: Path, encoding: str) -> None:
    compress = gzip.compress if encoding == "gzip" else zlib.compress
    data = compress(b"a" * 120_000)
    archive = Archive(tmp_path)
    http = HttpExchange("GET", 200, response_headers=(("content-encoding", encoding),))
    with pytest.raises(ArchiveError, match="decoded_size"):
        archive.commit(batch(), [capture(data, http=http)], limits=Limits(500, 50_000))
    with pytest.raises(ArchiveError, match="invalid_content_encoding"):
        archive.commit(batch(), [capture(data[:-3], http=http)], limits=LIMITS)
    with pytest.raises(ArchiveError, match="payload_size"):
        archive.commit(batch(), [capture(data, backend="blob")], limits=Limits(1, 1))
    assert archive.verify()["batches"] == 0
    archive.commit(batch(), [capture(data, http=http)], limits=LIMITS)
    assert next(archive.iter_metadata()).decoded_size == 120_000


def test_bodyless_response_can_describe_a_content_encoding(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    http = HttpExchange("GET", 304, response_headers=(("content-encoding", "deflate"),))
    manifest = archive.commit(batch(), [capture(b"", http=http)], limits=Limits(0, 0))
    output = BytesIO()
    metadata = archive.replay(manifest.captures[0].fetch_id, output)
    assert metadata.decoded_size == 0
    assert output.getvalue() == b""


def test_redaction_precedes_persistence_and_errors(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    marker = "fixture-sensitive-" + "sentinel"
    origin = f"https://masked-user:{marker}@example.test/items?x=1&X-Signed={marker}&x=2#private"
    exchange = HttpExchange(
        "GET",
        200,
        request_headers=(("Authorization", f"Bearer {marker}"), ("accept", "text/json")),
        response_headers=(("Set-Cookie", marker), ("location", origin), ("etag", marker)),
    )
    rules = Redaction(query_parameters=frozenset({"x-signed"}), secret_values=(marker,))
    manifest = archive.commit(
        batch(), [capture(origin_uri=origin, http=exchange)], limits=LIMITS, redaction=rules
    )
    entry = manifest.captures[0]
    metadata = archive.metadata(entry.fetch_id)
    assert metadata.origin_uri == "https://example.test/items?x=1&x=2"
    assert metadata.http is not None and metadata.http.request_headers == (("accept", "text/json"),)
    assert metadata.http.response_headers == ()
    stored = gzip.decompress(committed_path(tmp_path, batch(), entry.payload_path).read_bytes())
    assert marker.encode() not in stored and b"masked-user" not in stored
    with pytest.raises(ArchiveError, match=r"^origin_uri_secret$"):
        archive.commit(
            batch("bad"),
            [capture(origin_uri=f"https://example.test/{marker}")],
            limits=LIMITS,
            redaction=rules,
        )
    inferred = archive.commit(batch("inferred"), [capture(http=exchange)], limits=LIMITS)
    inferred_entry = inferred.captures[0]
    inferred_path = committed_path(tmp_path, batch("inferred"), inferred_entry.payload_path)
    assert marker.encode() not in gzip.decompress(inferred_path.read_bytes())


def test_legacy_and_current_descriptors_and_unknown_versions(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    legacy = archive.commit(batch("legacy"), [capture(backend="blob")], limits=LIMITS)
    current = archive.commit(batch("current"), [capture(backend="blob")], limits=LIMITS)
    rewrite_descriptor(tmp_path, "legacy", {"schema_version": 1})
    first = BytesIO()
    second = BytesIO()
    assert archive.replay(legacy.captures[0].record_id, first).decoded_size is None
    assert archive.replay(current.captures[0].record_id, second).decoded_size == len(SAMPLE)
    assert first.getvalue() == second.getvalue() == SAMPLE
    assert archive.verify()["captures"] == 2
    rewrite_descriptor(tmp_path, "legacy", {"schema_version": 99})
    with pytest.raises(ArchiveError, match="capture_schema_version"):
        archive.verify()


@pytest.mark.parametrize("corruption", ["missing", "digest", "manifest", "type", "locator"])
def test_verification_rejects_corrupt_archive(tmp_path: Path, corruption: str) -> None:
    archive = Archive(tmp_path)
    manifest = archive.commit(batch(), [capture(backend="blob")], limits=LIMITS)
    entry = manifest.captures[0]
    body = committed_path(tmp_path, batch(), entry.payload_path)
    manifest_path = body.parent.parent / "manifest.json"
    data = json.loads(manifest_path.read_bytes())
    if corruption == "missing":
        body.unlink()
    elif corruption == "digest":
        body.write_bytes(b"Z" * len(SAMPLE))
    elif corruption == "manifest":
        manifest_path.write_text(json.dumps(data | {"version": 8}), encoding="ascii")
    elif corruption == "type":
        manifest_path.write_text(json.dumps(data | {"version": True}), encoding="ascii")
    else:
        data["captures"][0]["payload_path"] = "../missing"
        manifest_path.write_text(json.dumps(data), encoding="ascii")
    with pytest.raises(ArchiveError):
        archive.verify()


def test_warc_member_integrity_even_when_container_hash_matches(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    key = batch()
    entry = archive.commit(key, [capture()], limits=LIMITS).captures[0]
    assert entry.payload_member is not None
    path = committed_path(tmp_path, key, entry.payload_path)
    segment = bytearray(path.read_bytes())
    segment[entry.payload_member.length - 8] ^= 1  # First member's gzip CRC.
    path.write_bytes(segment)
    manifest_path = committed_path(tmp_path, key, "manifest.json")
    manifest = json.loads(manifest_path.read_bytes())
    for key_name in ("payload", "metadata"):
        manifest["captures"][0][key_name]["sha256"] = sha256(segment).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="ascii")
    with pytest.raises(ArchiveError, match="warc_gzip"):
        archive.verify()


def test_legacy_warc_metadata_is_read_without_rewriting(tmp_path: Path) -> None:
    from unittest.mock import patch

    from kn.archive.model import Document, Metadata, encode

    def legacy(document: Document) -> bytes:
        if isinstance(document, Metadata):
            data = document.model_dump(mode="json", exclude={"decoded_size"})
            data["schema_version"] = 1
            return json.dumps(data, ensure_ascii=True).encode("ascii")
        return encode(document)

    archive = Archive(tmp_path)
    with patch("kn.archive.writer.encode", side_effect=legacy):
        older = archive.commit(batch("legacy"), [capture()], limits=LIMITS).captures[0]
    newer = archive.commit(batch("newer"), [capture()], limits=LIMITS).captures[0]
    older_path = committed_path(tmp_path, batch("legacy"), older.payload_path)
    proof = older_path.read_bytes()
    assert archive.metadata(older.record_id).decoded_size is None
    assert archive.metadata(newer.record_id).decoded_size == len(SAMPLE)
    assert archive.verify()["captures"] == 2
    assert older_path.read_bytes() == proof
