"""The PostgreSQL system catalogs that governance reads, as SQLAlchemy Core tables."""

import sqlalchemy as sa

CATALOG_SCHEMA = "pg_catalog"
PG_ROLES = sa.table(
    "pg_roles",
    sa.column("rolname"),
    sa.column("rolcanlogin"),
    sa.column("rolsuper"),
    sa.column("rolcreatedb"),
    sa.column("rolcreaterole"),
    sa.column("rolreplication"),
    sa.column("rolbypassrls"),
    schema=CATALOG_SCHEMA,
)
PG_NAMESPACE = sa.table(
    "pg_namespace", sa.column("nspname"), sa.column("nspowner"), schema=CATALOG_SCHEMA
)
PG_EXTENSION = sa.table(
    "pg_extension", sa.column("extname"), sa.column("extversion"), schema=CATALOG_SCHEMA
)
PG_ATTRIBUTE = sa.table(
    "pg_attribute",
    sa.column("attrelid"),
    sa.column("attname"),
    sa.column("atttypid"),
    sa.column("atttypmod"),
    sa.column("attisdropped"),
    schema=CATALOG_SCHEMA,
)
# Role attributes that every KN role must have switched off.
UNSAFE_ROLE_ATTRIBUTES = (
    PG_ROLES.c.rolcanlogin,
    PG_ROLES.c.rolsuper,
    PG_ROLES.c.rolcreatedb,
    PG_ROLES.c.rolcreaterole,
    PG_ROLES.c.rolreplication,
    PG_ROLES.c.rolbypassrls,
)
