"""Track the validated SQL identity prefix and invalidate it on out-of-band changes."""

from alembic import context, op

from kn.contracts.sqlalchemy import metadata
from kn.db.governance import CONTRACTS_ATTRIBUTE, deployment
from kn.db.platform import MIGRATION_SCHEMA, role_name
from kn.db.statements import SetRole
from kn.identity.checkpoint import CHECKPOINT, CreateCheckpointInvalidator, CreateCheckpointTrigger

revision = "0002_identity_checkpoint"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    contracts = context.config.attributes.get(CONTRACTS_ATTRIBUTE) or deployment()
    identity = next(
        (contract for contract in contracts if contract.contract_id == "kn.core.identity"), None
    )
    if identity is None:
        return
    op.execute(SetRole(role_name("identity", "owner")))
    CHECKPOINT.create(op.get_bind())
    op.execute(CreateCheckpointInvalidator())
    op.execute(CreateCheckpointTrigger(metadata(identity).tables["identity.lifecycle_events"]))
    op.execute(SetRole(role_name(MIGRATION_SCHEMA, "owner")))


def downgrade() -> None:
    raise ValueError("destructive downgrade refused; restore or author a reviewed migration")
