"""Local operator authorization and database application for the identity CLI."""

from datetime import UTC, datetime
from pathlib import Path

from kn.db.connection import engine_from_env
from kn.i18n import Translator
from kn.identity.journal import Journal
from kn.identity.lifecycle import submit
from kn.identity.lifecycle_reviews import PURPOSE, REVIEW_REF, Change, ReviewDetails
from kn.identity.state import PENDING_MATCH
from kn.review.authorization import AuthorizationError, authorize
from kn.review.journal import Journal as ReviewJournal
from kn.review.protocol import Reviewer

TTY = Path("/dev/tty")
APPROVAL = "yes"


IdentityAuthorizationError = AuthorizationError


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
    return authorize(
        translator,
        journal.data_dir,
        (journal.path, ReviewJournal(journal.data_dir).path),
        {
            "change": change.model_dump(mode="json"),
            "review": details.model_dump(mode="json"),
            "identity_head": head,
        },
        PURPOSE,
        TTY,
    )
