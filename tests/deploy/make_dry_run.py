"""The pytest commands that make would run for a target, read with make -n."""

import os
import shlex
import subprocess
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Variables of a calling make that would change a nested make -n, and the shell helpers' root.
INHERITED_VARIABLES = ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEOVERRIDES", "PROJECT_ROOT")


def pytest_commands(
    target: str | tuple[str, ...], directory: Path = ROOT, unset: Iterable[str] = (), **env: str
) -> list[list[str]]:
    """The arguments after `pytest` of every pytest command that make would run for the target."""
    dropped = {*INHERITED_VARIABLES, *unset}
    environment = {key: value for key, value in os.environ.items() if key not in dropped}
    environment.update(env)
    targets = (target,) if isinstance(target, str) else target
    result = subprocess.run(
        ["make", "--no-print-directory", "-n", "-C", str(directory), *targets],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    commands = []
    for line in result.stdout.replace("\\\n", "").splitlines():
        if " pytest " not in line:
            continue
        words = shlex.split(line.rsplit(";", 1)[-1])
        commands.append(words[words.index("pytest") + 1 :])
    return commands
