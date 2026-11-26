"""Shared local human operator boundary, independent of request/source identity."""

import os
import pwd
import stat
from pathlib import Path
from typing import Any

from kn.contracts.model import canonical
from kn.i18n import Translator
from kn.review.protocol import Reviewer

TTY = Path("/dev/tty")
APPROVAL = "yes"


class AuthorizationError(ValueError):
    """Explicit controlling-terminal approval by the private journal owner is required."""


def authorize(
    translator: Translator,
    root: Path,
    logs: tuple[Path, ...],
    proposal: object,
    purpose: str,
    terminal_path: Any = TTY,
) -> Reviewer:
    uid = os.getuid()
    if uid != os.geteuid() or not authorized_storage(root, logs, uid):
        raise AuthorizationError("decision journal owner is required")
    try:
        principal = f"local:{pwd.getpwuid(uid).pw_name}"
        with (
            terminal_path.open("r", encoding="utf-8") as terminal,
            terminal_path.open("w", encoding="utf-8") as output,
        ):
            if not terminal.isatty() or not output.isatty():
                raise AuthorizationError("controlling terminal required")
            output.write(
                translator.text(
                    "cli.review_confirm",
                    reviewer=canonical(principal),
                    proposal=canonical(proposal),
                    approval=APPROVAL,
                )
                + "\n"
            )
            output.flush()
            approved = terminal.readline().strip() == APPROVAL
    except (KeyError, OSError, UnicodeError) as error:
        raise AuthorizationError("local operator session is unavailable") from error
    if not approved:
        raise AuthorizationError("review was not confirmed")
    return Reviewer(principal, "human", True, frozenset({purpose}))


def authorized_storage(root: Path, logs: tuple[Path, ...], uid: int) -> bool:
    paths = {root, *logs}
    for log in logs:
        if not log.is_relative_to(root):
            return False
        paths.update(
            parent for parent in log.parents if parent == root or parent.is_relative_to(root)
        )
    return all(_owned(path, root, logs, uid) for path in paths)


def _owned(path: Path, root: Path, logs: tuple[Path, ...], uid: int) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return path != root
    expected = stat.S_ISREG if path in logs else stat.S_ISDIR
    return bool(
        expected(info.st_mode)
        and info.st_uid == uid
        and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )
