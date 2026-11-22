"""Development baseline: every registered contract at 1.0.0, edited in place until release."""

from alembic import context, op

from kn.contracts.sqlalchemy import metadata
from kn.db.governance import CONTRACTS_ATTRIBUTE, deployment, record_installed
from kn.db.platform import MIGRATION_SCHEMA, role_name
from kn.db.statements import SetRole

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create each contract as its schema owner, in registry order, then record the markers."""
    contracts = context.config.attributes.get(CONTRACTS_ATTRIBUTE) or deployment()
    connection = op.get_bind()
    for contract in contracts:
        op.execute(SetRole(role_name(contract.schema, "owner")))
        metadata(contract).create_all(connection, checkfirst=False)
    op.execute(SetRole(role_name(MIGRATION_SCHEMA, "owner")))
    record_installed(connection, contracts)


def downgrade() -> None:
    raise ValueError("destructive downgrade refused; restore or author a reviewed migration")
