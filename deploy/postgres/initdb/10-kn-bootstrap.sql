-- KN database bootstrap: PostGIS, the KN schemas, and owner, loader, and reader roles per schema.
--
-- The image entrypoint runs this file once when it initializes an empty data directory, and
-- `make db-up` applies it again on every start. It is idempotent and runs in one transaction, so
-- a failure leaves no partial bootstrap. Run it as a superuser connected to database `kn`.
--
-- Roles are NOLOGIN groups. Login roles become members of them:
--   kn_<schema>_owner   owns the schema and runs its DDL (SET ROLE before CREATE)
--   kn_<schema>_loader  reads and writes rows and sequences; no DDL
--   kn_<schema>_reader  reads rows
-- Default privileges cover objects that the owner role creates. Re-running this file also grants
-- objects that already exist.

\set ON_ERROR_STOP on

BEGIN;

-- Re-runs would otherwise print a "skipping" notice for every existing object.
SET LOCAL client_min_messages = warning;

-- Concurrent runs wait for each other; otherwise one fails with "tuple concurrently updated".
-- The two-key lock ("KNBS" in ASCII) never collides with the single bigint keys of product code.
DO $lock$ BEGIN PERFORM pg_advisory_xact_lock(x'4B4E4253'::int, 0); END $lock$;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;
-- A new image digest can bring a newer PostGIS. The library loads at once, but the installed
-- extension keeps its old SQL objects until it is updated. A no-op when it is current.
ALTER EXTENSION postgis UPDATE;

DO $bootstrap$
DECLARE
    kn_schemas CONSTANT text[] := ARRAY[
        'system', 'semantic', 'identity', 'evidence', 'supply', 'interchange',
        'space', 'gdelt', 'microelectronics', 'analytics'
    ];
    role_suffixes CONSTANT text[] := ARRAY['owner', 'loader', 'reader'];
    loader_table_privileges CONSTANT text := 'SELECT, INSERT, UPDATE, DELETE';
    schema_name text;
    role_suffix text;
    role_name text;
    owner_role text;
    loader_role text;
    reader_role text;
BEGIN
    EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;

    FOREACH schema_name IN ARRAY kn_schemas LOOP
        FOREACH role_suffix IN ARRAY role_suffixes LOOP
            role_name := format('kn_%s_%s', schema_name, role_suffix);
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = role_name) THEN
                EXECUTE format('CREATE ROLE %I', role_name);
            END IF;
            EXECUTE format(
                'ALTER ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION '
                'NOBYPASSRLS INHERIT',
                role_name
            );
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), role_name);
        END LOOP;

        owner_role := format('kn_%s_owner', schema_name);
        loader_role := format('kn_%s_loader', schema_name);
        reader_role := format('kn_%s_reader', schema_name);

        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION %I', schema_name, owner_role);
        EXECUTE format('ALTER SCHEMA %I OWNER TO %I', schema_name, owner_role);
        EXECUTE format(
            'REVOKE ALL ON SCHEMA %I FROM PUBLIC, %I, %I', schema_name, loader_role, reader_role
        );
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I, %I', schema_name, loader_role, reader_role);

        EXECUTE format(
            'GRANT %s ON ALL TABLES IN SCHEMA %I TO %I',
            loader_table_privileges, schema_name, loader_role
        );
        EXECUTE format(
            'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', schema_name, loader_role
        );
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', schema_name, reader_role);

        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT %s ON TABLES TO %I',
            owner_role, schema_name, loader_table_privileges, loader_role
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I '
            'GRANT USAGE, SELECT ON SEQUENCES TO %I',
            owner_role, schema_name, loader_role
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO %I',
            owner_role, schema_name, reader_role
        );
    END LOOP;
END
$bootstrap$;

COMMIT;
