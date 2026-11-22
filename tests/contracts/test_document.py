"""Unsafe, ambiguous, oversized, and malformed inputs fail before interpretation."""

import json
from pathlib import Path

import pytest

from kn import cli
from kn.contracts import document
from kn.contracts.diagnostics import ContractError


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"null",
        b"[]",
        b"name: first\nname: second",
        b'{"id":"a","id":"b"}',
        b"1: value",
        b"name: [",
        b"---\nid: first\n---\nid: second",
        b"id: &shared [*shared]",
        b"id: !!python/object/apply:os.system ['false']",
        b"id: .nan",
        b"id: .inf",
        b"id: !!timestamp 2026-11-22",
        b"id: !!set {a: null}",
        b"id: \xff",
        b"id: !!binary c2VjcmV0",
        b"id: " + b"[" * 2000 + b"]" * 2000,
    ],
)
def test_bad_documents_fail_cleanly_without_logging_the_input(
    tmp_path: Path, content: bytes, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "contract.yaml"
    path.write_bytes(content)
    with pytest.raises(ContractError):
        document.read_document(path)
    assert cli.main(["contract", "lint", str(path), "--json"]) == 1
    assert '"code": "E_CONTRACT"' in caplog.records[-1].message


def test_document_size_is_bounded_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "contract.yaml"
    path.write_bytes(b"id: a" * 20)
    monkeypatch.setattr(document, "MAX_DOCUMENT_BYTES", 10)
    with pytest.raises(ContractError, match="size"):
        document.read_document(path)


def test_document_depth_is_bounded_before_schema_validation(tmp_path: Path) -> None:
    value: object = "id"
    for _ in range(40):
        value = {"nested": value}
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ContractError, match="depth"):
        document.read_document(path)
