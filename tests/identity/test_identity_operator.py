"""The CLI uses local authorization independently of its review payload."""

import io
import os
import pwd
from pathlib import Path

import pytest

from kn.i18n import Translator
from kn.identity import operator
from kn.identity.journal import Journal
from kn.identity.lifecycle_reviews import ReviewDetails
from kn.identity.model import Retire
from tests.identity.fixtures import NOW, A


class Terminal(io.StringIO):
    message = ""

    def isatty(self) -> bool:
        return True

    def close(self) -> None:
        self.message = self.getvalue()
        super().close()


class Session:
    def __init__(self, reply: str) -> None:
        self.input = Terminal(reply + "\n")
        self.output = Terminal()

    def open(self, mode: str, encoding: str) -> Terminal:
        return self.input if mode == "r" else self.output


@pytest.mark.parametrize("reply", ["yes", "no"])
def test_local_confirmation_uses_os_account_and_escapes_source_text(
    reply: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = Session(reply)
    monkeypatch.setattr(operator, "TTY", session)

    def confirm():
        return operator.local_reviewer(
            Translator("uk"),
            Journal(tmp_path),
            Retire(kn_id=A),
            ReviewDetails(request_id="1", performed_at=NOW, reason="Fixture\x1b", evidence="e:1"),
            "fixture-head",
        )

    if reply == "yes":
        actor = confirm()
        assert actor.principal == f"local:{pwd.getpwuid(os.getuid()).pw_name}"
        assert actor.kind == "human" and actor.authenticated and actor.purposes == {"workflow"}
    else:
        with pytest.raises(operator.IdentityAuthorizationError):
            confirm()
    assert "\\u001b" in session.output.message
    assert "\x1b" not in session.output.message


@pytest.mark.parametrize("mode", [0o700, 0o777])
def test_cli_does_not_authorize_a_missing_terminal_or_shared_storage(
    mode: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(mode)
    monkeypatch.setattr(operator, "TTY", tmp_path / "no-terminal")
    with pytest.raises(operator.IdentityAuthorizationError, match=r"unavailable|owner"):
        operator.local_reviewer(
            Translator(),
            Journal(tmp_path),
            Retire(kn_id=A),
            ReviewDetails(request_id="1", performed_at=NOW, reason="Fixture", evidence="e:1"),
            "fixture-head",
        )
    assert list(tmp_path.iterdir()) == []
