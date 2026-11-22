"""Alembic runs only on the connection supplied by KN governance.

Every run converges the platform policy (extension, roles, schemas, grants) before and after the
revisions, so `alembic upgrade head` is the complete deployment step.
"""

from alembic import context

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata
from kn.db.governance import MIGRATION_SCHEMA, governed_migrations

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=metadata(load_contract()),
    include_schemas=True,
    version_table_schema=MIGRATION_SCHEMA,
    transactional_ddl=True,
)
with context.begin_transaction():
    governed_migrations(connection, context.run_migrations)
