# Chat membership and Analytics/ML local runbook

This runbook applies only to the disposable local/dev stack. Production compose
and production settings are intentionally unchanged.

## Start the complete stack

From `asoud-project-full`:

```shell
docker compose up --build
```

The frontend is served on `http://localhost:8080` and proxies `/api/`, `/ws/`,
and `/media/` to the local backend. PostgreSQL and Redis are not published to
the host. OTP uses Redis and has no LocMem fallback.

The compose stack supplies local non-secret defaults. Optional environment
names, without values, are:

- `DJANGO_SECRET_KEY` (optional for local; required outside local)
- `DATABASE_NAME`
- `DATABASE_USERNAME`
- `DATABASE_PASSWORD`
- `DATABASE_HOST`
- `DATABASE_PORT`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `CHAT_GROUP_MAX_PARTICIPANTS`

Do not reuse any historical tracked env file or TLS key. Those credentials need
rotation/reissue before any history cleanup or untracking operation.

## Dev-only migrations

Local compose loads `config.settings.migration_dev`, whose migration graph is
under `dev_migrations/`. It is a complete baseline for a fresh disposable
database because the repository has no reconciled production graph. Never use
this settings module against production. Before production deployment, the chat
and analytics schema changes must be manually reconciled with real production
schema and data.

Validate the dev graph:

```shell
docker compose exec backend python manage.py migrate --plan
docker compose exec backend python manage.py makemigrations --check --dry-run
```

## Analytics maintenance and ML training

Rebuild authoritative daily metrics before model training:

```shell
docker compose exec backend python manage.py rebuild_analytics_daily_metrics
docker compose exec backend python manage.py train_analytics_models --models recommender rfm --activate-if-better
docker compose exec backend python manage.py train_analytics_models --models demand --activate-if-better
```

Recommended server-time schedule (Asia/Tehran), following the stale-payment
reconciliation command pattern:

```cron
30 2 * * * cd /path/to/asoud-project-full && docker compose exec -T backend python manage.py train_analytics_models --models recommender rfm --activate-if-better
30 3 * * 0 cd /path/to/asoud-project-full && docker compose exec -T backend python manage.py train_analytics_models --models demand --activate-if-better
```

Schedule the daily-metric rebuild before 02:30. Training has no public API; it
uses a lock, writes versioned checksummed artifacts, and activates a candidate
only after validation succeeds.
