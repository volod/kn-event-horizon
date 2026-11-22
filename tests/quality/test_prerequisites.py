"""Host prerequisite checks and pinned tool installs, without network or system changes."""

import hashlib
import io
import tarfile
from pathlib import Path
from typing import Any

import pytest

from kn.quality import prerequisites
from kn.quality.prerequisites import ensure_tool, host_problems, installed, load_manifest

ROOT = Path(__file__).resolve().parents[2]
JAVA = {
    "command": "java",
    "hint": "a Java 21 runtime",
    "version_command": ["java", "-version"],
    "minimum": "21",
}


def archive(members: dict[str, bytes], *, link: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            tar.addfile(info, io.BytesIO(data))
        if link:
            info = tarfile.TarInfo("tool-1.0/escape")
            info.type, info.linkname = tarfile.SYMTYPE, link
            tar.addfile(info)
    return buffer.getvalue()


def tool(data: bytes) -> dict[str, Any]:
    return {
        "version": "1.0",
        "archive": "https://example.org/tool-1.0.tar.gz",
        "sha512": hashlib.sha512(data).hexdigest(),
        "install_dir": "tools/tool-1.0",
        "executable": "bin/run",
    }


def test_the_manifest_declares_the_prerequisites_and_a_pinned_https_jena() -> None:
    manifest = load_manifest(ROOT)
    assert [item["command"] for item in manifest["host_prerequisites"]] == [
        "git",
        "make",
        "uv",
        "docker",
        "java",
    ]
    jena = manifest["downloaded_tools"]["apache_jena"]
    assert jena["archive"].startswith("https://archive.apache.org/")
    assert len(jena["sha512"]) == 128 and jena["install_dir"].endswith(jena["version"])


@pytest.mark.parametrize(
    ("found", "output", "expected"),
    [
        (True, 'openjdk version "21.0.13.1" 2026-11-17', []),
        (True, 'openjdk version "17.0.9" 2023-10-17', ["java 17.0.9 is older than 21"]),
        (True, "no version here", ["java an unknown version is older than 21"]),
        (False, "", ["java is missing"]),
    ],
)
def test_host_problems_name_the_command_and_the_install_hint(
    found: bool, output: str, expected: list[str]
) -> None:
    problems = host_problems(
        [JAVA, {"command": "git", "hint": "git"}],
        which=lambda command: f"/usr/bin/{command}" if found or command == "git" else None,
        probe=lambda command: output,
    )
    assert [problem.split(";")[0] for problem in problems] == expected
    assert all(problem.endswith("install a Java 21 runtime") for problem in problems)


def test_a_pinned_archive_installs_once_through_a_marker(tmp_path: Path) -> None:
    data = archive({"tool-1.0/bin/run": b"#!/bin/sh\n"})
    calls: list[str] = []
    fetch = lambda url: calls.append(url) or data  # noqa: E731
    target = ensure_tool(tool(data), tmp_path, fetch)
    assert (target / "bin/run").is_file() and installed(tool(data), tmp_path)
    assert ensure_tool(tool(data), tmp_path, fetch) == target
    assert calls == ["https://example.org/tool-1.0.tar.gz"]
    assert sorted(path.name for path in (tmp_path / "tools").iterdir()) == ["tool-1.0"]


@pytest.mark.parametrize("damage", ["checksum", "parent_path", "link", "executable", "http"])
def test_an_unverified_or_hostile_archive_installs_nothing(tmp_path: Path, damage: str) -> None:
    members = {"tool-1.0/bin/run": b"run"}
    if damage == "parent_path":
        members["tool-1.0/../../outside"] = b"escape"
    if damage == "executable":
        members = {"tool-1.0/README": b"no executable"}
    data = archive(members, link="/etc/passwd" if damage == "link" else None)
    pinned = tool(data)
    if damage == "checksum":
        pinned["sha512"] = "0" * 128
    if damage == "http":
        pinned["archive"] = "http://example.org/tool-1.0.tar.gz"
    with pytest.raises((ValueError, tarfile.TarError)):
        ensure_tool(pinned, tmp_path, lambda url: data)
    assert not (tmp_path / "tools" / "tool-1.0").exists()
    assert not (tmp_path / "outside").exists() and not list(tmp_path.rglob(".staging-*"))


def test_an_existing_directory_without_the_marker_is_never_reused(tmp_path: Path) -> None:
    data = archive({"tool-1.0/bin/run": b"run"})
    (tmp_path / "tools/tool-1.0/bin").mkdir(parents=True)
    (tmp_path / "tools/tool-1.0/bin/run").write_bytes(b"unverified")
    with pytest.raises(ValueError, match="verified marker"):
        ensure_tool(tool(data), tmp_path, lambda url: data)


def test_main_reports_host_problems_and_missing_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        prerequisites, "host_problems", lambda items: ["java is missing; install x"]
    )
    assert prerequisites.main(["--root", str(ROOT), "--data-dir", str(tmp_path), "--install"]) == 1
    messages = [record.getMessage() for record in caplog.records]
    assert "ERROR: java is missing; install x" in messages
    assert any("apache_jena 6.3.0 is not installed" in message for message in messages)
    assert not (tmp_path / "tools").exists()
