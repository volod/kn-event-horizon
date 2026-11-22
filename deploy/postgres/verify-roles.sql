-- Probe the KN bootstrap: PostGIS, schema ownership, role attributes, and one granted and one
-- refused operation per role, including writes and reads across schemas.
--
-- `make db-verify` runs this as a superuser in database `kn`. Every probe object is created inside
-- one transaction that is rolled back, so the database is unchanged. The expected schema list is
-- stated here independently of the bootstrap, so a schema missing from the bootstrap fails.

\set ON_ERROR_STOP on

BEGIN;

-- Runs one statement as a role. Returns NULL when allowed, or the refusal message.
CREATE FUNCTION pg_temp.kn_try_as(role_name text, statement text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('SET LOCAL ROLE %I', role_name);
    EXECUTE statement;
    RESET ROLE;
    RETURN NULL;
EXCEPTION WHEN insufficient_privilege THEN
    RETURN SQLERRM;
END;
$$;

CREATE FUNCTION pg_temp.kn_expect(role_name text, statement text, allowed boolean) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    refusal text := pg_temp.kn_try_as(role_name, statement);
BEGIN
    IF allowed AND refusal IS NOT NULL THEN
        RAISE EXCEPTION 'expected % to be allowed: % (%)', role_name, statement, refusal;
    ELSIF NOT allowed AND refusal IS NULL THEN
        RAISE EXCEPTION 'expected % to be refused: %', role_name, statement;
    END IF;
END;
$$;

DO $verify$
DECLARE
    expected_schemas CONSTANT text[] := ARRAY[
        'system', 'semantic', 'identity', 'evidence', 'supply', 'interchange',
        'space', 'gdelt', 'microelectronics', 'analytics'
    ];
    probe CONSTANT text := 'kn_verify_probe';
    outsider CONSTANT text := 'kn_verify_outsider';
    schema_name text;
    other_schema text;
    role_name text;
    owner_role text;
    loader_role text;
    reader_role text;
    insert_row text;
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_extension e
        JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname = 'postgis' AND n.nspname = 'public'
    ) THEN
        RAISE EXCEPTION 'extension postgis is missing from schema public';
    END IF;

    EXECUTE format('CREATE ROLE %I NOLOGIN', outsider);
    IF has_database_privilege(outsider, current_database(), 'CONNECT')
        OR has_database_privilege(outsider, current_database(), 'TEMPORARY')
        OR has_schema_privilege(outsider, 'public', 'CREATE') THEN
        RAISE EXCEPTION 'PUBLIC keeps CONNECT, TEMPORARY, or public CREATE on database %',
            current_database();
    END IF;

    FOREACH schema_name IN ARRAY expected_schemas LOOP
        owner_role := format('kn_%s_owner', schema_name);
        loader_role := format('kn_%s_loader', schema_name);
        reader_role := format('kn_%s_reader', schema_name);

        FOREACH role_name IN ARRAY ARRAY[owner_role, loader_role, reader_role] LOOP
            IF NOT EXISTS (
                SELECT FROM pg_catalog.pg_roles
                WHERE rolname = role_name AND NOT rolcanlogin AND NOT rolsuper
                    AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication
                    AND NOT rolbypassrls
            ) THEN
                RAISE EXCEPTION 'role % is missing or has login or elevated attributes', role_name;
            END IF;
            IF NOT has_database_privilege(role_name, current_database(), 'CONNECT') THEN
                RAISE EXCEPTION 'role % lacks CONNECT on %', role_name, current_database();
            END IF;
        END LOOP;

        IF NOT EXISTS (
            SELECT FROM pg_catalog.pg_namespace n
            JOIN pg_catalog.pg_roles r ON r.oid = n.nspowner
            WHERE n.nspname = schema_name AND r.rolname = owner_role
        ) THEN
            RAISE EXCEPTION 'schema % is missing or not owned by %', schema_name, owner_role;
        END IF;
        IF has_schema_privilege(outsider, schema_name, 'USAGE') THEN
            RAISE EXCEPTION 'PUBLIC has USAGE on schema %', schema_name;
        END IF;

        insert_row := format(
            'INSERT INTO %I.%I (label, geom) VALUES '
            '(''probe'', public.ST_SetSRID(public.ST_MakePoint(30.52, 50.45), 4326))',
            schema_name, probe
        );

        PERFORM pg_temp.kn_expect(owner_role, format(
            'CREATE TABLE %I.%I (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, '
            'label text NOT NULL, geom public.geometry(Point, 4326))',
            schema_name, probe
        ), true);

        PERFORM pg_temp.kn_expect(loader_role, insert_row, true);
        PERFORM pg_temp.kn_expect(loader_role,
            format('UPDATE %I.%I SET label = ''updated''', schema_name, probe), true);
        PERFORM pg_temp.kn_expect(loader_role,
            format('SELECT count(*) FROM %I.%I', schema_name, probe), true);
        PERFORM pg_temp.kn_expect(loader_role,
            format('DELETE FROM %I.%I', schema_name, probe), true);
        PERFORM pg_temp.kn_expect(loader_role,
            format('CREATE TABLE %I.kn_verify_refused (id integer)', schema_name), false);
        PERFORM pg_temp.kn_expect(loader_role,
            format('ALTER TABLE %I.%I ADD COLUMN extra integer', schema_name, probe), false);
        PERFORM pg_temp.kn_expect(loader_role,
            format('TRUNCATE %I.%I', schema_name, probe), false);
        PERFORM pg_temp.kn_expect(loader_role,
            format('DROP TABLE %I.%I', schema_name, probe), false);

        PERFORM pg_temp.kn_expect(reader_role,
            format('SELECT count(*) FROM %I.%I', schema_name, probe), true);
        PERFORM pg_temp.kn_expect(reader_role, insert_row, false);
        PERFORM pg_temp.kn_expect(reader_role,
            format('CREATE TABLE %I.kn_verify_refused (id integer)', schema_name), false);
    END LOOP;

    FOREACH schema_name IN ARRAY expected_schemas LOOP
        FOREACH other_schema IN ARRAY expected_schemas LOOP
            CONTINUE WHEN other_schema = schema_name;
            PERFORM pg_temp.kn_expect(format('kn_%s_owner', schema_name),
                format('CREATE TABLE %I.kn_verify_refused (id integer)', other_schema), false);
            PERFORM pg_temp.kn_expect(format('kn_%s_loader', schema_name),
                format('INSERT INTO %I.%I (label) VALUES (''x'')', other_schema, probe), false);
            PERFORM pg_temp.kn_expect(format('kn_%s_reader', schema_name),
                format('SELECT count(*) FROM %I.%I', other_schema, probe), false);
        END LOOP;
    END LOOP;

    RAISE NOTICE 'kn roles verified: % schemas, % roles, postgis %',
        cardinality(expected_schemas), 3 * cardinality(expected_schemas), public.postgis_lib_version();
END
$verify$;

ROLLBACK;
