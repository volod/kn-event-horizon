"""Representative evidence rows for the combined model checkpoint."""

from sqlalchemy.engine import Connection

from kn.db.platform import role_name
from kn.db.statements import ResetRole, SetRole
from kn.evidence.store import record
from tests.evidence.fixtures import one_of_each


def seed_evidence_fixture(connection: Connection) -> int:
    """Write one row of every evidence table as the evidence loader; rerunning adds nothing."""
    rows = one_of_each()
    connection.execute(SetRole(role_name("evidence", "loader")))
    try:
        added = record(connection, rows)
        assert record(connection, rows) == 0
    finally:
        connection.execute(ResetRole())
    return added
