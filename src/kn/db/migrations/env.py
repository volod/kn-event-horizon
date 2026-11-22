"""Alembic runs only on the connection supplied by KN governance.

Every run converges the platform policy (extension, roles, schemas, grants) before and after the
revisions, so `alembic upgrade head` is the complete deployment step.
"""

from alembic import context

from kn.contracts.sqlalchemy import metadata
from kn.db.governance import CONTRACTS_ATTRIBUTE, MIGRATION_SCHEMA, deployment, governed_migrations

connection = context.config.attributes["connection"]
contracts = context.config.attributes.get(CONTRACTS_ATTRIBUTE) or deployment()
context.configure(
    connection=connection,
    target_metadata=[metadata(contract) for contract in contracts],
    include_schemas=True,
    version_table_schema=MIGRATION_SCHEMA,
    transactional_ddl=True,
)
with context.begin_transaction():
    governed_migrations(connection, context.run_migrations)
