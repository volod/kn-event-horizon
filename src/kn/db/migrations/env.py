"""Alembic runs only on the connection supplied by KN governance."""

from alembic import context

from kn.contracts import load_contract
from kn.contracts.sqlalchemy import metadata

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=metadata(load_contract()),
    include_schemas=True,
    version_table_schema="system",
    transactional_ddl=True,
)
with context.begin_transaction():
    context.run_migrations()
