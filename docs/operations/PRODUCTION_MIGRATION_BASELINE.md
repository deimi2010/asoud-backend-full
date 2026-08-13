# Production migration baseline

The historical database must not be marked migrated from assumptions or from
`dev_migrations`. Establish the baseline only from a recent restored production
backup.

1. Take and verify a production backup.
2. Restore it into an isolated PostgreSQL instance.
3. Configure production-equivalent database environment variables for the clone.
4. Run `python scripts/audit_database_schema.py`.
5. Resolve every missing table and column difference explicitly.
6. Generate the real application migrations from the reconciled model state.
7. Use `migrate --fake-initial` only when the audit proves the initial schema is
   equivalent; never use a blanket `--fake`.
8. Apply migrations normally on a second fresh clone.
9. Run the full regression suite and smoke-test reads and writes.
10. Test restore and rollback procedures before scheduling production migration.

The audit is read-only. A non-zero exit code blocks baseline preparation. Indexes,
constraints, defaults and database functions must additionally be compared using a
schema-only PostgreSQL dump before the baseline is approved.
