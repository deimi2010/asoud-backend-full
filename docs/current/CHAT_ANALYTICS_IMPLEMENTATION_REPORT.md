# Chat membership and Analytics/ML implementation report

Date: 2026-07-13

## Outcome

Group-chat membership and Analytics/ML v2 are implemented and enabled in the
local/development/test path. Production settings and production compose were not
changed. Production Analytics therefore remains disabled until the dev-only
migration graph is manually reconciled with production schema and data.

## Bugs found and fixed

### Group chat

- Membership had no authoritative room role. `ChatParticipant.role` is now the
  permission source with one conditional-unique owner, role timestamps, inviter,
  and an immutable membership audit event.
- Add-member always failed and remove-member handled only self-leave. Atomic
  services and REST endpoints now implement add, remove, leave, role change,
  ownership transfer, and soft archive with stable 400/403/404/409 contracts.
- Concurrent additions could overfill a room. Capacity checks now lock the room
  row and enforce both the room limit and configurable platform cap (default 100).
- Group creation could accept enumerable user IDs, bypassing the exact-mobile
  invite contract. Initial group participant IDs are now rejected; the owner must
  invite through the exact-mobile endpoint.
- Ownership lifecycle was undefined. An owner with other members must transfer;
  the target becomes owner and the former owner becomes admin. A sole owner leave
  archives the group and removes the final membership.
- An already-open socket could retain access after removal. Every inbound frame
  rechecks membership; removal publishes `membership_revoked` and closes the
  removed user's socket with code 4403.
- Room analytics referenced a removed `last_read_at` field. Active participation
  now uses real distinct message senders in the requested period.
- Flutter had no membership UI or membership socket handling. It now has group
  creation, member listing, invite, removal, leave, role change, transfer, and
  immediate access-revoked handling.

### Analytics/ML

- Legacy revenue and time-series code treated client JSON metadata as financial
  truth. Platform revenue now uses paid `Order.payable_amount`; owner/product
  metrics use immutable paid `OrderItem` price/quantity snapshots.
- Legacy UUID-incompatible generic object references were replaced by explicit
  product, market, order, user, and session relations.
- Session duration was not derived. It is now calculated from start/end lifecycle
  fields.
- Client event writes and financial metadata could contaminate analytics. Events
  are server-generated; the recorder keeps only a small non-financial allowlist.
- Platform/owner scoping was inconsistent. Platform/raw endpoints are staff-only;
  owner endpoints are read-only and restricted to owned markets; recommendations
  are self-scoped.
- Gross revenue lacked a user-visible refund qualification. API responses include
  `refunds_deducted: false` and Flutter renders the Persian warning next to the
  amount.
- Old ML paths mixed large dependencies into the main runtime and included fake or
  random outputs. The ML target uses optional `requirements-ml.txt`; training uses
  real paid orders/daily metrics, checksummed versioned JSON artifacts, validation,
  a non-overlap lock, and atomic activation.
- Degenerate one-user/one-product recommender samples could produce an NMF
  convergence warning. They now use an exact observed-score artifact; non-degenerate
  matrices use deterministic NMF.
- Analytics signal import failures were silently swallowed. Enabled environments
  now fail startup visibly if signal registration is broken.

## Dev-only migrations

`config.settings.migration_dev` maps local application labels to
`dev_migrations/`. Because the repository had no reconciled production graph, this
is a complete fresh-development baseline, not a production migration sequence.

Feature migration files:

- Chat: `dev_migrations/chat/0001_initial.py`, `0002_initial.py`
- Analytics: `dev_migrations/analytics/0001_initial.py` through `0004_initial.py`

Dependency-app initial migrations also live under `dev_migrations/` so a new local
PostgreSQL database can be built with one command. The graph was applied to the
local `asoud_feature_migrations` database. `makemigrations --check --dry-run`
reports no changes and `migrate --plan` reports no pending operations.

Do not apply this graph to production. First inventory the live schema and data,
reconcile migration history, backfill room owners/roles and analytics relations,
and validate financial aggregates against real orders.

## Removed obsolete runtime files

- Legacy Analytics APIs/services: `advanced_analytics.py`, `advanced_views.py`,
  `dashboard_views.py`, `fraud_detection.py`, `fraud_views.py`, `ml_models.py`,
  `ml_optimization.py`, `optimization_views.py`, and old `serializers.py`.
- Unused Analytics WebSocket/template path: `consumers.py`, `routing.py`,
  `dashboard_urls.py`, and both dashboard templates.
- Fake/obsolete commands: `calculate_analytics.py`,
  `generate_advanced_analytics.py`, `generate_analytics_data.py`,
  `update_ml_recommendations.py`, and old `train_ml_models.py` (replaced by
  `train_analytics_models`).
- The obsolete app-local Analytics requirements list containing unrelated deep
  learning/visualization packages; replaced by the three pinned ML dependencies.

Historical audit documents that mention these paths were retained as evidence and
are not imported by runtime code.

## Verification

- Backend PostgreSQL + Redis regression suite: **204 passed, 0 failed**.
- Analytics contract suite: **18 passed, 0 failed**.
- Additional non-empty ML training integration: **1 passed, 0 failed**.
- Chat legacy + membership/API/concurrency/WebSocket suites: **48 passed, 0 failed**.
- Flutter full suite: **128 passed, 0 failed**.
- Flutter analyze: **0 errors, 0 warnings**; informational legacy lints remain.
- Critical Ruff checks: **passed**.
- Backend runtime image and Flutter release build for local compose: **passed**.
- Runtime: PostgreSQL, Redis, backend, and frontend all **healthy**.
- HTTP health: backend 200, frontend 200.
- Composed HTTP chat lifecycle (create/add/change role/transfer/remove/leave/
  archive): **9/9 expected statuses**.
- OTP issue through the frontend proxy: HTTP 200 and Redis key count increased;
  no OTP value was logged or returned.
- Dev migration drift/pending operations: **0 / 0**.

## Operations

Run the full local stack from the backend directory:

```shell
docker compose up --build
```

See `CHAT_ANALYTICS_RUNBOOK.md` for non-secret environment names, dev-migration
warnings, daily-metric rebuilding, ML commands, and the proposed cron schedule.
