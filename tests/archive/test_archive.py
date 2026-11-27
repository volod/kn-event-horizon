import gzip
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from multiprocessing import get_context
from pathlib import Path
from unittest.mock import patch

import pytest
from warcio.archiveiterator import ArchiveIterator

from kn.archive import Archive
from kn.archive.model import ArchiveError, HttpExchange
from tests.archive.fixtures import LIMITS, SAMPLE, batch, capture, committed_path


def test_backends_replay_and_relocate(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive")
    key = batch()
    encoded = gzip.compress(SAMPLE, mtime=0)
    package = b"\x00\xff\r\n" * 200_000
    manifest = archive.commit(
        key,
        [
            capture(
                encoded,
                http=HttpExchange(
                    "GET",
                    200,
                    response_headers=(
                        ("Content-Encoding", "gzip"),
                        ("Content-Type", "application/json"),
                    ),
                ),
            ),
            capture(package, key="package", backend="blob", origin_uri="urn:fixture:package"),
            capture(key="document", origin_uri="file:///fixture.json"),
        ],
        limits=LIMITS,
    )
    restored = Archive(tmp_path / "restored")
    shutil.copytree(archive.root, restored.root, ignore=shutil.ignore_patterns("locks", "staging"))

    for entry, expected in zip(manifest.captures, (encoded, package, SAMPLE), strict=True):
        by_record = BytesIO()
        by_fetch = BytesIO()
        metadata = restored.replay(entry.record_id, by_record)
        assert restored.replay(entry.fetch_id, by_fetch) == metadata
        assert by_record.getvalue() == by_fetch.getvalue() == expected
        assert metadata.payload_sha256 == sha256(expected).hexdigest()
        assert metadata.payload_size == len(expected)
    assert restored.verify() == {"status": "verified", "batches": 1, "captures": 3, "tombstones": 0}
    assert [row.fetch_id for row in restored.iter_metadata()] == sorted(
        row.fetch_id for row in manifest.captures
    )


def test_warc_standard_reader_and_metadata_locator(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    key = batch()
    manifest = archive.commit(key, [capture(http=HttpExchange("GET", 200))], limits=LIMITS)
    entry = manifest.captures[0]
    path = committed_path(tmp_path, key, entry.payload_path)
    with path.open("rb") as stream:
        records = [
            (record.rec_type, record.rec_headers.protocol, record.raw_stream.read())
            for record in ArchiveIterator(stream, check_digests="raise")
        ]
    assert [kind for kind, _, _ in records] == ["response", "request", "metadata"]
    assert {version for _, version, _ in records} == {"WARC/1.1"}
    assert records[0][2] == SAMPLE
    assert json.loads(records[-1][2])["record_id"] == entry.record_id

    with path.open("r+b") as stream:
        stream.write(b"\x00")
    assert archive.metadata(entry.fetch_id).status == 200
    output = BytesIO()
    with pytest.raises(ArchiveError, match="warc_object_digest"):
        archive.replay(entry.fetch_id, output)
    assert output.getvalue() == b""


def test_two_sources_and_same_batch_retry(tmp_path: Path) -> None:
    archive = Archive(tmp_path)

    def write(source: str) -> str:
        key = batch(source=source)
        stored = archive.commit(key, [capture()], limits=LIMITS)
        stream = BytesIO(SAMPLE)
        assert archive.commit(key, [capture(body=stream)], limits=LIMITS) == stored
        assert stream.tell() == 0
        return stored.captures[0].fetch_id

    with ThreadPoolExecutor(4) as pool:
        first, second, first_again, second_again = pool.map(write, ["first", "second"] * 2)
    assert first == first_again and second == second_again and first != second
    assert archive.verify()["batches"] == 2


def _exit_before_publish(root: Path) -> None:
    with patch("kn.archive.writer.publish", side_effect=lambda *args: os._exit(73)):
        Archive(root).commit(batch("interrupted"), [capture()], limits=LIMITS)


def test_process_exit_leaves_only_previous_commits(tmp_path: Path) -> None:
    archive = Archive(tmp_path)
    archive.commit(batch(), [capture()], limits=LIMITS)
    process = get_context("fork").Process(target=_exit_before_publish, args=(tmp_path,))
    process.start()
    process.join(timeout=15)
    if process.is_alive():
        process.kill()
        process.join()
    assert process.exitcode == 73
    assert list((tmp_path / "staging").glob("*/manifest.json"))
    assert archive.verify()["batches"] == 1
    retried = archive.commit(batch("interrupted"), [capture()], limits=LIMITS)
    assert archive.commit(batch("interrupted"), [], limits=LIMITS) == retried
    assert archive.verify()["captures"] == 2


def test_blob_stream_reads_are_bounded(tmp_path: Path) -> None:
    class Stream(BytesIO):
        def read(self, count: int = -1) -> bytes:
            assert 0 < count <= 64 * 1024
            return super().read(count)

        def seek(self, *args: object) -> int:
            pytest.fail("caller input streams may be non-seekable")

    payload = b"\x00\x02" * 90_000
    archive = Archive(tmp_path)
    archive.commit(batch(), [replace(capture(backend="blob"), body=Stream(payload))], limits=LIMITS)
    assert next(archive.iter_metadata()).payload_sha256 == sha256(payload).hexdigest()
