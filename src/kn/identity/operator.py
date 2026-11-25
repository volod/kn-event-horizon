"""Local operator authorization and database application for the identity CLI."""

import os
import pwd
import stat
from datetime import UTC, datetime
from pathlib import Path

from kn.contracts.model import canonical
from kn.db.connection import engine_from_env
from kn.i18n import Translator
from kn.identity.journal import Journal
from kn.identity.lifecycle import submit
from kn.identity.lifecycle_reviews import PURPOSE, REVIEW_REF, Change, ReviewDetails
from kn.identity.state import PENDING_MATCH
from kn.review.journal import Journal as ReviewJournal
from kn.review.protocol import Reviewer

TTY = Path("/dev/tty")
APPROVAL = "yes"


class IdentityAuthorizationError(ValueError):
    """Local identity changes require confirmation by the authorized journal owner."""


def apply_change(
    translator: Translator, journal: Journal, change: Change, details: ReviewDetails
) -> dict[str, object]:
    snapshot = journal.state()
    snapshot.resolve(change.kn_id)
    if snapshot.pending_match() is not None:
        raise ValueError(PENDING_MATCH)
    head = snapshot.events[-1].event_id
    reviewer = local_reviewer(translator, journal, change, details, head)
    engine = engine_from_env()
    try:
        with engine.begin() as connection:
            value = submit(
                connection,
                journal,
                change,
                details,
                lambda: reviewer,
                lambda: datetime.now(UTC),
                expected_head=head,
            )
    finally:
        engine.dispose()
    assert value.decision_ref is not None
    return {
        "action": "applied",
        "event": value.model_dump(mode="json"),
        "decision_id": value.decision_ref.removeprefix(REVIEW_REF),
    }


def local_reviewer(
    translator: Translator, journal: Journal, change: Change, details: ReviewDetails, head: str
) -> Reviewer:
    """Use the local account and require explicit approval on its controlling terminal."""
    uid = os.getuid()
    if uid != os.geteuid() or not _authorized_storage(journal, uid):
        raise IdentityAuthorizationError("identity journal owner is required")
    try:
        principal = f"local:{pwd.getpwuid(uid).pw_name}"
        proposal = canonical(
            {
                "change": change.model_dump(mode="json"),
                "review": details.model_dump(mode="json"),
                "identity_head": head,
            }
        )
        with TTY.open("r", encoding="utf-8") as terminal, TTY.open("w", encoding="utf-8") as output:
            if not terminal.isatty() or not output.isatty():
                raise IdentityAuthorizationError("controlling terminal required")
            output.write(
                translator.text(
                    "cli.identity_confirm",
                    reviewer=canonical(principal),
                    proposal=proposal,
                    approval=APPROVAL,
                )
                + "\n"
            )
            output.flush()
            approved = terminal.readline().strip() == APPROVAL
    except (KeyError, OSError, UnicodeError) as error:
        raise IdentityAuthorizationError("local operator session is unavailable") from error
    if not approved:
        raise IdentityAuthorizationError("identity change was not confirmed")
    return Reviewer(principal, "human", True, frozenset({PURPOSE}))


def _authorized_storage(journal: Journal, uid: int) -> bool:
    root = journal.data_dir
    logs = (journal.path, ReviewJournal(root).path)
    paths = (root, *(log.parent for log in logs), *logs)
    for path in paths:
        try:
            info = path.lstat()
        except FileNotFoundError:
            if path == root:
                return False
            continue
        expected_type = stat.S_ISREG if path in logs else stat.S_ISDIR
        if (
            not expected_type(info.st_mode)
            or info.st_uid != uid
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            return False
    return True
