"""Development SATCOM baseline: edit contract 1.0.0 in place until release."""

from alembic import op

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import MIGRATION_SCHEMA, install_contract
from kn.db.platform import role_name
from kn.db.statements import SetRole

revision = "0001_satcom"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    contract = load_contract()
    connection = op.get_bind()
    op.execute(SetRole(role_name(contract.schema, "owner")))
    model = metadata(contract)
    model.create_all(connection, checkfirst=False)
    install_contract(connection, contract)
    op.execute(SetRole(role_name(MIGRATION_SCHEMA, "owner")))


def downgrade() -> None:
    raise ValueError("destructive downgrade refused; restore or author a reviewed migration")
