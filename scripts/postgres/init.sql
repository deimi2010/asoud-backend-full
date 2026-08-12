-- =============================================================================
-- PostgreSQL Initialization Script
-- Sets up extensions, users, and security
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_buffercache;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Create monitoring user for metrics collection
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'monitor') THEN

      CREATE ROLE monitor LOGIN PASSWORD 'monitor_password_change_me';
   END IF;
END
$do$;

-- Grant monitoring permissions
GRANT CONNECT ON DATABASE postgres TO monitor;
GRANT pg_monitor TO monitor;

-- Create read-only user for reporting
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'readonly') THEN

      CREATE ROLE readonly LOGIN PASSWORD 'readonly_password_change_me';
   END IF;
END
$do$;

-- Grant read-only permissions
GRANT CONNECT ON DATABASE postgres TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO readonly;

-- Performance tuning: Create btree index for commonly queried fields
-- (These will be created by Django migrations, but listed here for reference)

-- Security: Revoke public schema creation
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Performance monitoring setup
SELECT pg_stat_statements_reset();

-- Log the initialization
DO
$do$
BEGIN
   RAISE NOTICE 'PostgreSQL initialization completed successfully';
   RAISE NOTICE 'Extensions created: pg_stat_statements, pg_buffercache, pgcrypto, uuid-ossp';
   RAISE NOTICE 'Users created: monitor, readonly';
   RAISE NOTICE 'Security: Public schema creation revoked';
END
$do$;