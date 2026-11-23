"""Check the development host and install pinned, checksum-verified tool archives.

`deploy/versions.yaml` declares both. System packages are never installed: a missing or too-old
command fails with its install hint. A downloaded tool is installed under `DATA_DIR/tools/` only
when its archive matches the pinned SHA-512, through a staging directory and one rename, and an
installation is trusted only with the marker that records that checksum.
"""

import argparse
import hashlib
import io
import logging
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

MANIFEST = Path("deploy") / "versions.yaml"
VERSION = re.compile(r"\d+(?:\.\d+)*")
MARKER = ".kn-sha512"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
TIMEOUT_SECONDS = 120
_LOG = logging.getLogger("kn.prerequisites")

type Fetch = Callable[[str], bytes]
type Probe = Callable[[Sequence[str]], str]


def load_manifest(root: Path) -> dict[str, Any]:
    return dict(yaml.safe_load((root / MANIFEST).read_text(encoding="utf-8")))


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _probe(command: Sequence[str]) -> str:
    """Version output; some tools, such as java, write it to stderr."""
    completed = subprocess.run(
        list(command), capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
    )
    return completed.stdout + completed.stderr


def host_problems(
    prerequisites: Sequence[dict[str, Any]],
    which: Callable[[str], str | None] = shutil.which,
    probe: Probe = _probe,
) -> list[str]:
    """One actionable message per missing or too-old command; empty when the host is ready."""
    problems = []
    for item in prerequisites:
        command, hint = item["command"], item["hint"]
        if which(command) is None:
            problems.append(f"{command} is missing; install {hint}")
            continue
        if "minimum" not in item:
            continue
        found = VERSION.search(probe(item["version_command"]))
        if found is None or _version(found.group()) < _version(item["minimum"]):
            version = found.group() if found else "an unknown version"
            problems.append(f"{command} {version} is older than {item['minimum']}; install {hint}")
    return problems


def tool_path(tool: dict[str, Any], data_dir: Path) -> Path:
    return data_dir / str(tool["install_dir"])


def installed(tool: dict[str, Any], data_dir: Path) -> bool:
    target = tool_path(tool, data_dir)
    marker = target / MARKER
    return (
        marker.is_file()
        and marker.read_text(encoding="ascii").strip() == tool["sha512"]
        and (target / tool["executable"]).is_file()
    )


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        if urlsplit(response.geturl()).scheme != "https":
            raise ValueError("tool downloads must stay on HTTPS")
        data = bytes(response.read(MAX_ARCHIVE_BYTES + 1))
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("tool archive exceeds the download limit")
    return data


def ensure_tool(tool: dict[str, Any], data_dir: Path, fetch: Fetch = _fetch) -> Path:
    """Install the pinned archive once; an unverified directory is never reused or replaced."""
    target = tool_path(tool, data_dir)
    if installed(tool, data_dir):
        return target
    if target.exists():
        raise ValueError(f"{target} exists without a verified marker; remove it and rerun")
    if urlsplit(tool["archive"]).scheme != "https":
        raise ValueError("tool archives must be pinned to HTTPS URLs")
    data = fetch(tool["archive"])
    if hashlib.sha512(data).hexdigest() != tool["sha512"]:
        raise ValueError("tool archive differs from the pinned SHA-512")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=target.parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            # The data filter refuses absolute paths, parent references, links outside and devices.
            archive.extractall(staging, filter="data")
        unpacked = staging / target.name
        if not (unpacked / tool["executable"]).is_file():
            raise ValueError("tool archive does not contain the declared executable")
        (unpacked / MARKER).write_text(tool["sha512"] + "\n", encoding="ascii")
        unpacked.rename(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--install", action="store_true", help="install missing pinned tools")
    args = parser.parse_args(argv)
    manifest = load_manifest(args.root)
    host = host_problems(manifest["host_prerequisites"])
    problems = list(host)
    for name, tool in manifest["downloaded_tools"].items():
        if installed(tool, args.data_dir):
            continue
        if not args.install or host:
            problems.append(f"{name} {tool['version']} is not installed; run make bootstrap")
            continue
        try:
            ensure_tool(tool, args.data_dir)
            _LOG.info(
                "Installed %s %s in %s.", name, tool["version"], tool_path(tool, args.data_dir)
            )
        except (OSError, ValueError, tarfile.TarError) as error:
            problems.append(f"{name} {tool['version']}: {error}")
    for problem in problems:
        _LOG.error("ERROR: %s", problem)
    if not problems:
        _LOG.info("Host prerequisites and pinned tools are ready.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
