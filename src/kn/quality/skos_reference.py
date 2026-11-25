"""Validate every reviewed SKOS export with the pinned Apache Jena RIOT, an independent parser.

RIOT runs in strict mode (`--validate`) on the pinned Java runtime: a non-zero exit or any warning
fails the check. The exports and a summary are kept under `DATA_DIR/skos-reference/<run-id>/`.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from uuid import uuid4

from kn.quality.prerequisites import installed, load_manifest, tool_path
from kn.semantic.seeds import reviewed_snapshot
from kn.semantic.skos import export_scheme

TOOL = "apache_jena"
RUNTIME = "temurin_jre"
TIMEOUT_SECONDS = 300
_LOG = logging.getLogger("kn.skos_reference")

type Run = Callable[[list[str], Mapping[str, str]], subprocess.CompletedProcess[str]]


def _riot(command: list[str], env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False, env=env
    )


def check(root: Path, data_dir: Path, run: Run = _riot) -> tuple[Path, list[dict[str, object]]]:
    """Export each scheme, validate it, and return the summary path and the failed schemes."""
    tools = load_manifest(root)["downloaded_tools"]
    tool, runtime = tools[TOOL], tools[RUNTIME]
    if not (installed(tool, data_dir) and installed(runtime, data_dir)):
        raise ValueError(
            "Apache Jena or its Java runtime is missing; run make skos-reference-tools"
        )
    riot = tool_path(tool, data_dir) / tool["executable"]
    # The riot launcher prefers JAVA over JAVA_HOME and PATH, so a host Java never takes over.
    env = {**os.environ, "JAVA": str(tool_path(runtime, data_dir) / runtime["executable"])}
    destination = data_dir / "skos-reference" / uuid4().hex
    destination.mkdir(parents=True)
    results: list[dict[str, object]] = []
    for scheme_id in sorted(row["id"] for row in reviewed_snapshot()["concept_schemes"]):
        path = Path(str(export_scheme(scheme_id, destination)["path"]))
        completed = run([str(riot), "--validate", str(path)], env)
        messages = (completed.stdout + completed.stderr).strip()
        results.append(
            {
                "scheme_id": scheme_id,
                "path": str(path.relative_to(destination)),
                "exit_code": completed.returncode,
                "messages": messages,
            }
        )
    summary = destination / "summary.json"
    document = {
        "tool": f"Apache Jena RIOT {tool['version']}",
        "runtime": f"Eclipse Temurin JRE {runtime['version']}",
        "schemes": results,
    }
    summary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed = [item for item in results if item["exit_code"] != 0 or item["messages"]]
    return summary, failed


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary, failed = check(args.root, args.data_dir)
    except ValueError as error:
        _LOG.error("ERROR: %s", error)
        return 1
    for item in failed:
        _LOG.error("ERROR: %s failed RIOT validation: %s", item["scheme_id"], item["messages"])
    if not failed:
        _LOG.info("All SKOS exports passed Apache Jena RIOT validation. Summary: %s", summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
