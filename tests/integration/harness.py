"""Integration database harness: connection settings, connections, and scratch schemas.

Tests reach the database through the fixtures in tests/conftest.py. KN_TEST_DATABASE_URL names the
server as a libpq connection string or URI, and KN_TEST_DATABASE_PASSWORD_FILE optionally names a
file that holds the password. `make test-integration` sets both for the local database.
"""

import re
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL_VARIABLE = "KN_TEST_DATABASE_URL"
PASSWORD_FILE_VARIABLE = "KN_TEST_DATABASE_PASSWORD_FILE"
NOT_CONFIGURED = (
    f"no integration database configured: {DATABASE_URL_VARIABLE} is not set. "
    "Start the local database with make db-up, then run make test-integration."
)
START_HINT = (
    f"Start the local database with make db-up, or check {DATABASE_URL_VARIABLE} "
    f"and {PASSWORD_FILE_VARIABLE}."
)
CONNECT_TIMEOUT_SECONDS = 10
APPLICATION_NAME = "kn-integration-tests"

SCRATCH_PREFIX = "kn_test_"
# A token is a positive int4, so it also keys an advisory lock. Eight hex digits name it.
TOKEN_LIMIT = 2**31
TOKEN_DIGITS = 8
TOKEN_ATTEMPTS = 5
SCRATCH_SCHEMA = re.compile(rf"^{SCRATCH_PREFIX}([0-7][0-9a-f]{{{TOKEN_DIGITS - 1}}})_[a-z0-9_]+$")
# First key of the two-key advisory lock that marks a live session ("KNTS" in ASCII). Two-key locks
# never collide with the single bigint keys that product code may take.
SCRATCH_LOCK_CLASS = 0x4B4E5453
SCHEMA_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_IDENTIFIER_LENGTH = 63
# A drop that waits longer on a lock fails instead of hanging. The next session drops the rest.
LOCK_TIMEOUT = "10s"

Connection = psycopg.Connection[tuple[Any, ...]]


class HarnessError(RuntimeError):
    """The integration database is configured but cannot be used."""


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _read_password(path: Path) -> str:
    try:
        # Trailing newlines are dropped, as the image entrypoint drops them from its secret file.
        password = path.read_text(encoding="utf-8").rstrip("\n")
    except (OSError, UnicodeDecodeError):
        password = ""
    if not password:
        raise HarnessError(f"password file {path} is missing or empty. {START_HINT}")
    return password


@dataclass(frozen=True)
class IntegrationDatabase:
    """A configured integration database. Its password is never part of a message."""

    conninfo: str
    # Kept out of the representation, which pytest prints for the arguments of a failing test.
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "IntegrationDatabase | None":
        """Read the configuration, or return None when no database is configured."""
        conninfo = environ.get(DATABASE_URL_VARIABLE, "").strip()
        if not conninfo:
            return None
        try:
            conninfo_to_dict(conninfo)
        except psycopg.ProgrammingError:
            # The parser's message can quote part of the string, which may hold a password.
            raise HarnessError(
                f"{DATABASE_URL_VARIABLE} is not a libpq connection string or URI"
            ) from None
        password_file = environ.get(PASSWORD_FILE_VARIABLE, "").strip()
        password = _read_password(_resolve(password_file)) if password_file else None
        return cls(conninfo, password)

    def describe(self) -> str:
        """Name the server as user@host:port/database, without the password."""
        params = conninfo_to_dict(self.conninfo)
        host = params.get("host") or params.get("hostaddr") or "default"
        return (
            f"{params.get('user', 'default')}@{host}:{params.get('port', 'default')}"
            f"/{params.get('dbname', 'default')}"
        )

    def connect(self, **overrides: Any) -> Connection:
        """Open a connection. Keyword arguments override the configured libpq parameters."""
        options: dict[str, Any] = {
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
            "application_name": APPLICATION_NAME,
        }
        if self.password is not None:
            options["password"] = self.password
        options.update(overrides)
        return psycopg.connect(self.conninfo, **options)

    def check(self) -> None:
        """Fail with a hint when the database does not answer a query."""
        try:
            with self.connect() as connection:
                connection.execute("SELECT 1")
        except psycopg.Error as error:
            detail = " ".join(str(error).split())
            raise HarnessError(
                f"cannot connect to the integration database {self.describe()} ({detail}). "
                f"{START_HINT}"
            ) from None


class ScratchSchemas:
    """Schemas private to one test session, named kn_test_<token>_<name> and dropped at its end.

    A session draws a random token and holds a session-level advisory lock on it while it lives.
    Creating a session first drops the schemas of every token whose lock is free, which a run that
    was killed before its teardown left behind.
    """

    def __init__(self, connection: Connection, token: int) -> None:
        self._connection = connection
        self.prefix = f"{SCRATCH_PREFIX}{token:0{TOKEN_DIGITS}x}_"
        self._token = token

    @classmethod
    def create(cls, database: IntegrationDatabase) -> "ScratchSchemas":
        connection = database.connect(autocommit=True)
        try:
            connection.execute("SELECT set_config('lock_timeout', %s, false)", [LOCK_TIMEOUT])
            scratch = cls(connection, _lock_new_token(connection))
            scratch._drop_orphans()
        except BaseException:
            connection.close()
            raise
        return scratch

    def schema(self, name: str) -> str:
        """Create the scratch schema for a logical name unless it exists, and return its name."""
        physical = f"{self.prefix}{name}"
        if not SCHEMA_NAME.fullmatch(name) or len(physical) > MAX_IDENTIFIER_LENGTH:
            raise ValueError(
                f"a scratch schema name must match {SCHEMA_NAME.pattern} and have at most "
                f"{MAX_IDENTIFIER_LENGTH - len(self.prefix)} characters, got {name!r}"
            )
        statement = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(physical))
        self._connection.execute(statement)
        return physical

    def close(self) -> None:
        """Drop every schema of this session and release its lock."""
        try:
            self._drop(name for name in self._scratch_names() if name.startswith(self.prefix))
        finally:
            self._connection.close()

    def _scratch_names(self) -> list[str]:
        rows = self._connection.execute(
            "SELECT nspname FROM pg_catalog.pg_namespace WHERE nspname ~ %s ORDER BY nspname",
            [SCRATCH_SCHEMA.pattern],
        ).fetchall()
        return [row[0] for row in rows]

    def _drop_orphans(self) -> None:
        by_token: dict[int, list[str]] = {}
        for name in self._scratch_names():
            match = SCRATCH_SCHEMA.match(name)
            if match:
                by_token.setdefault(int(match[1], 16), []).append(name)
        for token, names in sorted(by_token.items()):
            if token == self._token:
                # This session holds the lock, so these are leftovers of an earlier, killed run.
                self._drop(names)
            elif _try_lock(self._connection, token):
                try:
                    self._drop(names)
                finally:
                    self._connection.execute(
                        "SELECT pg_advisory_unlock(%s::int4, %s::int4)", [SCRATCH_LOCK_CLASS, token]
                    )

    def _drop(self, names: Iterable[str]) -> None:
        for name in names:
            statement = sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(name))
            self._connection.execute(statement)


def _try_lock(connection: Connection, token: int) -> bool:
    row = connection.execute(
        "SELECT pg_try_advisory_lock(%s::int4, %s::int4)", [SCRATCH_LOCK_CLASS, token]
    ).fetchone()
    return bool(row and row[0])


def _lock_new_token(connection: Connection) -> int:
    for _ in range(TOKEN_ATTEMPTS):
        token = secrets.randbelow(TOKEN_LIMIT)
        if _try_lock(connection, token):
            return token
    raise HarnessError(f"no free scratch token after {TOKEN_ATTEMPTS} attempts")
