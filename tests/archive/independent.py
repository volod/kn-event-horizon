"""Read committed WARC segments with FastWARC, a parser independent of warcio."""

import json
from pathlib import Path

from fastwarc.warc import ArchiveIterator  # type: ignore[import-untyped]

_HTTP = "application/http"


def read_segment(path: Path) -> list[dict[str, object]]:
    """Return what FastWARC reads from each record, with its own digest results."""
    records: list[dict[str, object]] = []
    with path.open("rb") as stream:
        for record in ArchiveIterator(stream, parse_http=False, verify_digests=False):
            headers = dict(record.headers)
            row: dict[str, object] = {
                "version": record.headers.status_line,
                "type": headers["WARC-Type"],
                "record_id": headers["WARC-Record-ID"].strip("<>"),
                "offset": record.stream_pos,
                "block_ok": record.verify_block_digest(consume=False),
                "block_digest": headers.get("WARC-Block-Digest"),
                "payload_digest": headers.get("WARC-Payload-Digest"),
                "refers_to": headers.get("WARC-Refers-To", "").strip("<>") or None,
                "http": headers.get("Content-Type", "").startswith(_HTTP),
            }
            if row["http"]:
                record.parse_http()
                row["status_line"] = record.http_headers.status_line
                if row["type"] in ("response", "request"):
                    row["payload_ok"] = record.verify_payload_digest(consume=False)
            row["payload"] = record.reader.read()
            records.append(row)
    return records


def manifests(root: Path) -> list[tuple[Path, dict[str, object]]]:
    return [
        (path.parent, json.loads(path.read_bytes()))
        for path in sorted(root.glob("captures/*/*/*/*/manifest.json"))
    ]
