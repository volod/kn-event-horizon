"""Deterministic subprocesses and ASCII evidence for bilingual acceptance."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("fixtures")
LOCALES = ("en", "uk")
TIMEOUT_SECONDS = 30


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", "ascii")


def run_cli(arguments: list[str], **environment: str) -> dict[str, object]:
    # Never inherit a connection, password file, user locale, or external Python module path.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("KN_") and key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    env.update(COLUMNS="80", LC_ALL="C.UTF-8", PYTHONIOENCODING="utf-8", **environment)
    result = subprocess.run(
        [sys.executable, "-m", "kn.cli", *arguments],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def normalize_usage(output: str, prefix: str = "usage: ") -> str:
    """Ignore argparse synopsis wrapping while retaining the help body."""
    if not output.startswith(prefix):
        return output
    usage, separator, body = output.partition("\n\n")
    return re.sub(r"\n +", " ", usage) + separator + body
