"""Development SATCOM baseline: edit contract 1.0.0 in place until release."""

from alembic import op

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import install_contract
from kn.db.platform import ddl

revision = "0001_satcom"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    contract = load_contract()
    connection = op.get_bind()
    ddl(connection, "SET LOCAL ROLE kn_space_owner")
    model = metadata(contract)
    model.create_all(connection, checkfirst=False)
    install_contract(connection, contract)
    ddl(connection, "SET LOCAL ROLE kn_system_owner")


def downgrade() -> None:
    raise ValueError("destructive downgrade refused; restore or author a reviewed migration")
