\set ON_ERROR_STOP on
\pset pager off
\pset null '(null)'

-- Run only against an isolated, anonymized PostgreSQL snapshot. Output is
-- catalog/migration metadata plus aggregate counts; no business/user record
-- identifier or raw payload is selected.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10min';
SET LOCAL lock_timeout = '5s';
SET LOCAL idle_in_transaction_session_timeout = '20min';

\echo '=== environment ==='
SELECT current_setting('server_version_num') AS server_version_num,
       current_setting('server_encoding') AS server_encoding,
       current_setting('TimeZone') AS timezone,
       current_setting('default_transaction_isolation') AS default_isolation,
       current_setting('transaction_read_only') AS transaction_read_only;

\echo '=== installed extensions ==='
SELECT extname, extversion
FROM pg_extension
ORDER BY extname;

\echo '=== application tables and estimated sizes ==='
SELECT n.nspname AS table_schema,
       c.relname AS table_name,
       CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned table' END AS kind,
       COALESCE(s.n_live_tup, 0)::bigint AS estimated_rows,
       pg_total_relation_size(c.oid)::bigint AS total_bytes,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE c.relkind IN ('r', 'p')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname !~ '^pg_toast'
ORDER BY n.nspname, c.relname;

\echo '=== exact row counts (one result row per table) ==='
SELECT format(
           'SELECT %L AS table_name, count(*)::bigint AS exact_row_count FROM %I.%I;',
           n.nspname || '.' || c.relname,
           n.nspname,
           c.relname
       )
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname !~ '^pg_toast'
ORDER BY n.nspname, c.relname
\gexec

\echo '=== columns ==='
SELECT table_schema,
       table_name,
       ordinal_position,
       column_name,
       data_type,
       udt_schema,
       udt_name,
       character_maximum_length,
       numeric_precision,
       numeric_scale,
       is_nullable,
       column_default,
       is_identity,
       identity_generation,
       is_generated
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position;

\echo '=== constraints ==='
SELECT n.nspname AS table_schema,
       c.relname AS table_name,
       con.conname AS constraint_name,
       CASE con.contype
           WHEN 'p' THEN 'primary_key'
           WHEN 'u' THEN 'unique'
           WHEN 'f' THEN 'foreign_key'
           WHEN 'c' THEN 'check'
           WHEN 'x' THEN 'exclusion'
           ELSE con.contype::text
       END AS constraint_type,
       con.convalidated AS is_validated,
       con.condeferrable AS is_deferrable,
       con.condeferred AS initially_deferred,
       pg_get_constraintdef(con.oid, true) AS definition
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname, con.conname;

\echo '=== indexes ==='
SELECT n.nspname AS table_schema,
       c.relname AS table_name,
       i.relname AS index_name,
       ix.indisprimary AS is_primary,
       ix.indisunique AS is_unique,
       ix.indisvalid AS is_valid,
       ix.indisready AS is_ready,
       pg_get_indexdef(i.oid) AS definition
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname, i.relname;

\echo '=== user triggers ==='
SELECT n.nspname AS table_schema,
       c.relname AS table_name,
       t.tgname AS trigger_name,
       t.tgenabled AS enabled_mode,
       pg_get_triggerdef(t.oid, true) AS definition
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT t.tgisinternal
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname, t.tgname;

\echo '=== row-level security policies ==='
SELECT schemaname,
       tablename,
       policyname,
       permissive,
       roles,
       cmd,
       qual,
       with_check
FROM pg_policies
ORDER BY schemaname, tablename, policyname;

\echo '=== sequences ==='
SELECT sequence_schema,
       sequence_name,
       data_type,
       start_value,
       minimum_value,
       maximum_value,
       increment
FROM information_schema.sequences
WHERE sequence_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY sequence_schema, sequence_name;

\echo '=== invalid/unready indexes and unvalidated constraints ==='
SELECT 'index' AS object_type,
       n.nspname AS table_schema,
       c.relname AS table_name,
       i.relname AS object_name,
       concat('valid=', ix.indisvalid, ', ready=', ix.indisready) AS state
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (NOT ix.indisvalid OR NOT ix.indisready)
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 'constraint',
       n.nspname,
       c.relname,
       con.conname,
       'validated=false'
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT con.convalidated
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, object_name;

\echo '=== Django migration history ==='
SELECT to_regclass('public.django_migrations') IS NOT NULL AS has_django_migrations
\gset
\if :has_django_migrations
SELECT app, name, applied
FROM public.django_migrations
ORDER BY app, applied, name;

SELECT app,
       count(*)::bigint AS applied_count,
       min(applied) AS first_applied,
       max(applied) AS last_applied
FROM public.django_migrations
GROUP BY app
ORDER BY app;

SELECT count(*)::bigint AS duplicate_migration_entries
FROM (
    SELECT app, name
    FROM public.django_migrations
    GROUP BY app, name
    HAVING count(*) > 1
) duplicate_history;
\else
\echo 'django_migrations is absent'
\endif

\echo '=== foreign-key orphan counts (aggregate only) ==='
WITH fk_columns AS (
    SELECT con.oid AS constraint_oid,
           con.conname,
           child_ns.nspname AS child_schema,
           child.relname AS child_table,
           parent_ns.nspname AS parent_schema,
           parent.relname AS parent_table,
           child_att.attname AS child_column,
           parent_att.attname AS parent_column,
           child_key.ordinality AS position
    FROM pg_constraint con
    JOIN pg_class child ON child.oid = con.conrelid
    JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
    JOIN pg_class parent ON parent.oid = con.confrelid
    JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
    CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS child_key(attnum, ordinality)
    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS parent_key(attnum, ordinality)
      ON parent_key.ordinality = child_key.ordinality
    JOIN pg_attribute child_att
      ON child_att.attrelid = child.oid AND child_att.attnum = child_key.attnum
    JOIN pg_attribute parent_att
      ON parent_att.attrelid = parent.oid AND parent_att.attnum = parent_key.attnum
    WHERE con.contype = 'f'
      AND child_ns.nspname NOT IN ('pg_catalog', 'information_schema')
), statements AS (
    SELECT constraint_oid,
           format(
               'SELECT %L AS constraint_name, count(*)::bigint AS orphan_rows FROM %I.%I AS child WHERE %s AND NOT EXISTS (SELECT 1 FROM %I.%I AS parent WHERE %s);',
               child_schema || '.' || child_table || '.' || conname,
               child_schema,
               child_table,
               string_agg(format('child.%I IS NOT NULL', child_column), ' AND ' ORDER BY position),
               parent_schema,
               parent_table,
               string_agg(format('parent.%I = child.%I', parent_column, child_column), ' AND ' ORDER BY position)
           ) AS statement
    FROM fk_columns
    GROUP BY constraint_oid, conname, child_schema, child_table, parent_schema, parent_table
)
SELECT statement
FROM statements
ORDER BY constraint_oid
\gexec

\echo '=== duplicate counts for declared primary/unique constraints (aggregate only) ==='
WITH unique_columns AS (
    SELECT con.oid AS constraint_oid,
           con.conname,
           n.nspname AS table_schema,
           c.relname AS table_name,
           a.attname AS column_name,
           key.ordinality AS position
    FROM pg_constraint con
    JOIN pg_class c ON c.oid = con.conrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS key(attnum, ordinality)
    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = key.attnum
    WHERE con.contype IN ('p', 'u')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
), statements AS (
    SELECT constraint_oid,
           format(
               'SELECT %L AS constraint_name, count(*)::bigint AS duplicate_key_groups, COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_extra_rows, COALESCE(max(group_size), 0)::bigint AS max_group_size FROM (SELECT count(*)::bigint AS group_size FROM %I.%I WHERE %s GROUP BY %s HAVING count(*) > 1) duplicates;',
               table_schema || '.' || table_name || '.' || conname,
               table_schema,
               table_name,
               string_agg(format('%I IS NOT NULL', column_name), ' AND ' ORDER BY position),
               string_agg(format('%I', column_name), ', ' ORDER BY position)
           ) AS statement
    FROM unique_columns
    GROUP BY constraint_oid, conname, table_schema, table_name
)
SELECT statement
FROM statements
ORDER BY constraint_oid
\gexec

ROLLBACK;
