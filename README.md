# ASOUD v1

The repository contains the Django API for ASOUD. The sibling
`../fluter-sina` repository contains the Flutter web client. The root
`docker-compose.yml` is the canonical local v1 stack and starts both projects
with PostgreSQL and Redis.

## Run locally

Requirements: Docker Desktop (or Docker Engine with Compose v2) and both
repositories in their current sibling directories.

```bash
docker compose up --build
```

Open:

- Flutter web: <http://localhost:8080>
- Django API: <http://localhost:8000/api/v1/>
- Health check: <http://localhost:8000/health/>

The local stack needs no `.env` file and does not publish PostgreSQL or Redis
ports to the host. It creates a disposable schema from the current models in a
local-only database. Reset all local data with:

```bash
docker compose down --volumes
```

The compose file accepts these environment names inside the backend service:
`DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DATABASE_NAME`,
`DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`,
`REDIS_HOST`, `REDIS_PORT`, and `REDIS_DB`. Do not put real credentials in a
tracked file. The checked-in local compose intentionally supplies only
non-production development settings.

## Test targets

The production runtime image excludes tests. An isolated test target retains
them without copying them into the release image:

```bash
docker build --target test --tag asoud-v1-backend-test .
```

Flutter tests are run from `../fluter-sina` with Flutter 3.44.0.

## Release boundaries

- Analytics remains disabled with `ANALYTICS_ENABLED = False`.
- Commercial SMS, customer-paid shipping writes, and legacy product discounts
  remain fail-closed.
- Prices, payment state, reservation payment state, and inventory are owned by
  the server.
- Local schema bootstrap is not a production migration baseline. Production
  migration history must be reconciled manually before deployment.
- The production deployment path is not yet selected. See
  [current infrastructure notes](docs/current/INFRA_NOTES.md) before using any
  legacy production compose or deployment script.

Additional audits and historical documentation are indexed in
[docs/README.md](docs/README.md).
