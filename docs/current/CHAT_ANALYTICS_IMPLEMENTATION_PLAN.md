# Chat membership and Analytics/ML implementation plan

Status: approved for implementation (2026-07-13). This document records the
product and data-model decisions that must not be changed implicitly during
implementation.

## Group chat membership

### Data model

- `ChatParticipant.role`: `owner`, `admin`, or `member`; new memberships default
  to `member`.
- `ChatParticipant.joined_at`, nullable `invited_by` (`SET_NULL`), and
  `role_updated_at`.
- Keep the unique `(chat_room, user)` membership constraint; add `(chat_room,
  role)` index and a conditional unique constraint allowing at most one owner.
- Add `ChatMembershipEvent` with room, actor, subject, action, old/new role, and
  timestamp for an immutable membership audit trail.
- Change `ChatRoom.created_by` to `SET_NULL`. It remains audit metadata; the
  participant role is the authorization source.
- Feature migrations are generated and applied only through the isolated dev
  migration namespace. Production requires a manual schema/data reconcile.

### Capacity

The platform hard cap defaults to **100 participants** and is configurable with
`CHAT_GROUP_MAX_PARTICIPANTS=100`, because WebSocket fan-out and database load
depend on deployment capacity and should be adjustable without a schema
migration. A room may select a limit from 2 through that server-controlled cap.
The client cannot raise the platform cap. Capacity checks run in an atomic,
row-locked operation; overflow returns `409 participant_limit_reached`.

### API and permissions

- `POST /api/v1/chat/rooms/`: authenticated users may create invite-only group
  rooms and become owner. Private/support/market membership remains
  system-managed.
- `GET /api/v1/chat/rooms/{room_id}/participants/`: any member may list safe
  display data and roles. Mobile/email are never returned.
- `POST /api/v1/chat/rooms/{room_id}/participants/`: owner/admin adds a user by
  exact mobile number. Owner may add admin/member; admin may add member only.
  Duplicate membership is `409 participant_already_member`; full room is
  `409 participant_limit_reached`.
- `PATCH /api/v1/chat/rooms/{room_id}/participants/{user_id}/`: owner changes an
  admin/member role. Ownership uses only the transfer endpoint.
- `DELETE /api/v1/chat/rooms/{room_id}/participants/{user_id}/`: owner may
  remove admin/member; admin may remove member. An owner is never removed by
  this endpoint.
- `POST /api/v1/chat/rooms/{room_id}/leave/`: admin/member may leave. A sole
  owner leaving archives the room and removes their membership. An owner with
  other members receives `409 ownership_transfer_required`.
- `POST /api/v1/chat/rooms/{room_id}/transfer-ownership/`: owner-only and atomic;
  target must already be a member, target becomes owner, previous owner becomes
  admin.
- Owner alone may archive or change sensitive settings; owner/admin may update
  ordinary group metadata. Hard delete is not exposed.
- Private rooms have no manual role/membership mutation. Support and market
  rooms remain system-managed. All group rooms are invite-only in v1.
- Legacy add/remove actions delegate to the same service and rules.

Tests cover creation/backfill, uniqueness, every permission combination,
duplicate add, exact-mobile privacy, cap and concurrent adds, owner transfer and
leave lifecycle, last owner/member cases, each room type, update/archive rules,
audit events, immediate role enforcement, and WebSocket revocation after
removal.

## Analytics/ML v2

### Legacy failures and disposition

The 18-test legacy baseline was 11 pass / 7 fail with ML dependencies present.

1. `test_user_session_creation`: duration is not derived from end minus start —
   fix the session model/lifecycle.
2. `test_analytics_service_dashboard_data`: sums a JSON event value — replace
   with authoritative paid orders.
3. `test_analytics_service_time_series_data`: same obsolete JSON revenue source
   — replace with paid-order aggregation.
4. `test_real_time_service_metrics`: same obsolete JSON revenue source — replace
   with authoritative read-only metrics.
5. `test_end_to_end_analytics_flow`: depends on the broken dashboard source —
   rewrite as a real server-event-to-dashboard integration test.
6. `test_ml_service_product_recommendations`: references nonexistent
   `content_object_id`, while old integer object IDs cannot represent UUID
   products — migrate to explicit UUID foreign keys and authoritative purchase
   signals.
7. `test_ml_recommendations_integration`: same obsolete relation and signal —
   migrate/rewrite the integration path.

### Truth sources and data model

- Financial metrics come only from paid `Order` and `OrderItem`: gross paid
  revenue uses `Order.payable_amount`; product units/revenue use immutable
  `OrderItem.unit_price * quantity`. No client amount or analytics metadata may
  affect financial results.
- Conversion is authenticated unique buyers divided by authenticated unique
  product viewers in the requested period.
- Affiliate sales are attributed to the affiliate selling market.
- `AnalyticsEvent`: UUID, user/session, allowlisted event type, explicit nullable
  product/market/order foreign keys, nullable unique dedupe key, occurrence
  timestamp, and limited non-financial metadata. Events are server-generated.
- `UserSession`: UUID/session identifier, start/last-seen/end, derived duration,
  active flag, and optional coarse device data. No precise coordinates.
- `AnalyticsDailyMetric`: date and platform/market/product scope with views,
  unique viewers, cart additions, paid orders, units, gross revenue, unique
  buyers, and calculation timestamp.
- `MLModelArtifact`: model type/version, training window/sample count, validation
  metrics, artifact path/checksum, and active status.
- Retire obsolete denormalized analytics truth tables and fake/random generators.
  Production data migration/reconcile remains a separate manual operation.

### API and visible revenue disclaimer

Platform/raw endpoints are staff-only; owner endpoints are read-only and scoped
to markets owned by the current user; recommendation endpoints are self-only.
There is no client event-write API and no training API.

Both platform and owner dashboard responses include a machine-readable
`refunds_deducted: false` plus the explicit disclaimer:

> Gross paid revenue; refunds are not deducted.

Every platform and owner dashboard UI renders the equivalent visible Persian
text next to gross revenue: «درآمد ناخالص پرداخت‌شده است؛ مبالغ بازپرداخت‌شده
از آن کسر نشده است.» It is not hidden in source documentation or a tooltip.

### ML dependencies and training schedule

ML dependencies live in `requirements-ml.txt`, separate from core runtime:
`numpy==1.26.4`, `pandas==2.2.0`, and `scikit-learn==1.5.0` (with their normal
transitive dependencies). The local ML image/test target installs this file;
the core image remains small. Production compose/settings are unchanged.

Training is management-command only. The command uses a database/cache lock to
prevent overlap, validates the candidate, writes a checksummed versioned
artifact, and atomically activates it only after success; a failure leaves the
previous artifact active.

Recommended server-time schedule (Asia/Tehran for the current deployment):

```cron
# Recommender and RFM after daily metrics are rebuilt
30 2 * * *  <compose-exec> python manage.py train_analytics_models --models recommender rfm --activate-if-better
# Demand changes more slowly and trains weekly
30 3 * * 0  <compose-exec> python manage.py train_analytics_models --models demand --activate-if-better
```

The deployment-specific `<compose-exec>` is intentionally documented as a
placeholder because production compose is out of scope and must not be edited.
The metrics rebuild is scheduled before these jobs. Local/dev commands may be
run manually for verification.

Analytics is enabled only after the new 18-test suite and integration tests are
green. The final enablement applies to the requested local/dev path; production
settings remain untouched.
