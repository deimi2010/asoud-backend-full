# Backend production-readiness audit

> Superseded for Group 1 infrastructure/auth/rate-limit/money findings by
> `GROUP_1_OPERATIONS_RUNBOOK.md`. This file remains the pre-implementation
> audit snapshot; do not use its old deployment commands.

Date: 2026-07-12

Scope: `asoud-project-full` Django/DRF backend, compared with the Flutter
contract map in `../../../fluter-sina/ARCHITECTURE_MAP.md`.

Contract rule: code-generated OpenAPI must become the source of truth;
`docs/api/legacy-artifacts/ALL_ENDPOINTS.txt` and other hand-written endpoint
lists are indexes only.

## 1. Executive verdict

The backend is **not production-ready**. Its endpoint surface is broad, but
critical money, permission, delivery, analytics, migration, schema, test, and
deployment paths are either unsafe, fake, internally inconsistent, or not
actually exercised by CI.

Immediate stop conditions:

- **SECURITY — leaked secrets and private keys:** production/development env
  files and multiple TLS private keys are tracked and have existed in git
  history. Active Docker builds use `COPY .`, while `.dockerignore` does not
  exclude these paths, so the exposure extends to image layers, GHCR versions,
  and Actions cache. Values were never printed during this audit.
- **SECURITY — vulnerable dependencies:** `pip-audit -r requirements.txt`
  reports **67 known vulnerabilities across 17 packages**. Affected direct or
  pinned packages include Django 5.1.5, cryptography 44.0.0, Daphne 4.1.2,
  Pillow 11.1.0, Twisted 24.11.0, PyJWT 2.8.0, requests 2.32.3,
  urllib3 2.3.0, python-dotenv 1.0.0, scikit-learn 1.3.0, msgpack 1.1.0,
  PyOpenSSL 25.0.0, idna 3.10, pyasn1 0.6.1, setuptools 75.8.0,
  sqlparse 0.5.3, and wheel 0.45.1. Upgrades require a compatibility batch,
  not blind pin changes.
- **SECURITY — direct financial/IDOR exposure:** wallet transfer can select and
  debit the wrong user's wallet; payment amount and target are client-controlled;
  wallet checkout can mark a target paid even when debit fails.
- **SECURITY — unrestricted messaging/data exposure:** any authenticated user
  can target notifications at an arbitrary user; SMS sending is unbilled and
  broadly authorized; analytics exposes global and personal data, with some
  global endpoints public and CSRF-exempt.

### Remediation register

**Batch 1 - financial integrity (implemented 2026-07-12):** the four direct
wallet/payment exploits recorded below are fixed in the working tree. Wallet
source IDs are normalized, source ownership is enforced, all financial paths use
a consistent `User -> Order -> Wallet` locking order, debit and order transition
are atomic, and API amounts are bounded to the narrowest transaction column.
Online order payments now derive the price under a row lock, freeze the order in
`processing`, reuse the one pending gateway session, commit the freeze before the
provider call, and process callbacks under locks exactly once. Ambiguous gateway
results remain locked for reconciliation; definitive failures make the order
`failed`. Legacy pre-hardening sessions lack the integrity marker and are denied
by redirect/callback instead of being trusted.

Verification: **24/24 focused payment/wallet/order tests pass**, Ruff passes on
all changed files, Python compilation passes, and `manage.py check` reports no
issues. Independent review was run repeatedly and its blocking lock/session/
amount/lifecycle findings were incorporated. PostgreSQL concurrency coverage,
gateway-ID database uniqueness, legacy-session reconciliation, Decimal model
migrations, and the missing migration baseline remain production gates.

**Batch 2 - auth/messaging/analytics containment (implemented 2026-07-13):**
OTP values now use `secrets`, are stored only as salted cache hashes with TTL,
have per-code attempt and per-mobile issuance locks, are consumed atomically, and
rotate the DRF token. Tokens expire after 30 days in REST and both WebSocket auth
paths; inactive users are rejected everywhere. Production OTP fails closed unless
the shared Redis cache is healthy. Notification creation is admin-only, fake
push/email/SMS providers report unavailable, immediate delivery is not duplicated
in the queue, failed delivery is accepted for retry with HTTP 202, and workers use
short claim/finalization locks with stale-claim recovery. Commercial SMS sending
is hard-disabled at owner and admin view layers; missing provider config is never
mock success and billing/provider fields are read-only. Analytics REST/dashboard
routes are disabled by default; viewsets and dormant WebSockets are staff-only,
and client event/session writes are removed.

Verification: **26/26 Batch 2 containment tests plus 24/24 Batch 1 tests pass**;
Ruff and Django system checks pass. The old full analytics suite still has seven
failures proving broken/fabricated calculations, so `ANALYTICS_ENABLED` must stay
false until that subsystem is repaired and independently revalidated.

**Batch 4 - cart/discount/inventory integrity (implemented 2026-07-12):** cart
rows are now explicit `draft` orders; checkout creates an immutable placed-order
price snapshot. Product/affiliate IDs are validated, quantities and published
state are enforced, and mixed-market carts are rejected. Payment initiation
atomically reserves actual product/affiliate stock and discount capacity; wallet
failure, gateway failure/cancellation and rejection release them idempotently;
successful gateway/wallet/cash completion confirms stock and consumes the discount
once. One code can be used once per buyer, percentages are 1-100, capacity is
locked, generated codes use `secrets` plus DB uniqueness, and referenced discounts
cannot be deleted. Legacy mixed-market orders are hidden from every vendor.
Database and service-level XOR checks reject targetless/dual-target order items;
product and affiliate deletion now preserves referenced order history. Cart update,
delete and inventory transitions share row locks, including calls made with stale
model instances. Pending gateway sessions have a bounded TTL and an idempotent
reconciliation worker: paid sessions complete, definitive failures release
reservations, and ambiguous provider states remain locked for manual reconciliation.

The uninstalled fake inventory subsystem referenced nonexistent product fields and
swallowed failures; it was removed. The real inventory authority is the locked
`Product.stock`/`AffiliateProduct.stock` transition in `apps.cart.services`.
Verification currently passes **77 tests** (the earlier 56 critical tests plus
16 cart/inventory and 5 discount tests), schema validation, Ruff and system checks.

**Batch 5a - bank-share and price-inquiry authorization (implemented
2026-07-13):** the public bank-card share contract now exposes only the record ID,
bank name, card number and account-holder name; user/account/IBAN/branch/notes and
timestamps are never serialized. Price-inquiry draft detail/update/delete/image
and answer reads are owner-scoped. Flutter's create/image/`send: true`/HTTP DELETE
flow now matches the backend; finalization is idempotent and freezes inquiry
content. Only authenticated market owners can browse active finalized inquiries,
and the inquiry row lock limits each owner to one answer. WebSocket publication
runs after commit. Eight focused privacy/authorization tests bring the critical
suite to **85 tests**.

**Batch 5b - advertisement and affiliate integrity (implemented 2026-07-13):**
manual advertisement purchase and its placeholder payment endpoint now fail closed
with 503 until an authoritative price is defined. Clients cannot write `is_paid`,
unpaid advertisements are private, and product-backed advertisements are an
idempotent unpaid projection that cannot use client-controlled `is_requirement`
to bypass the absent paid-ad flow. It cannot be detached, edited or deleted through
advertisement routes. Public
detail no longer exposes a mobile number or internal Product prices; the legacy
Flutter share route uses the same public filter. Affiliate creation locks an owned,
published Market, accepts only published marketer-enabled Products from published
source Markets, derives source type/category, forces draft status, and rejects
duplicates. Source withdrawal blocks cart add/checkout. Affiliate list/detail/theme
routes are owner-scoped. Ten focused tests bring the critical suite to **95 tests**.

**Batch 5c - comment thread integrity (implemented 2026-07-13):** comment targets
are restricted to published Products in published Markets or published Markets;
reply parents must belong to the same object, private/removed comments and withdrawn
targets are hidden, and updates lock an owned visible comment while accepting only
text. The bare Flutter create/list contract and one-level child shape are preserved.
The apparent `parent_id=F('id')` anomaly is actually django-comments-xtd's root-node
convention: its model sets a root's parent/thread ID to its own ID after insert.
Public listing bulk-loads a child map for at most 100 recent roots instead of one
query per root. Six focused tests bring the critical suite to **101 tests**.

**Batch 5d - real market schedules (implemented 2026-07-13):** owner and user
schedule routes now read/write `MarketSchedule`, not reservation `ReserveTime`
rows hidden behind a synthetic `Service(name='-')`. The established Flutter
`market/day/start/end` contract is mapped to the canonical model, requires a
complete forward interval, rejects overlap under row locks, treats an exact retry
as idempotent, scopes mutations to the Market owner, and hides schedules for
withdrawn Markets. Seven focused tests bring the critical suite to **108 tests**;
the PostgreSQL-only case also asserts that the Market lock precedes the row lock.
Ordering/overlap is API-enforced until the migration baseline can safely add DB
check/exclusion constraints; direct admin/database schedule writes remain gated.

**Batch 5e - reservation access and state integrity (implemented 2026-07-13):**
client input can no longer set `Reservation.is_paid`; booking locks real service,
time and specialist rows, requires a published Market and verifies the specialist
provides that service. Public service/specialist/time/day-off feeds hide withdrawn
Markets. Owner CRUD is fail-closed by ownership, specialist service replacement
rejects missing/foreign IDs, reservation history blocks cascading service/time/
specialist deletion with 409, and empty unmounted payment placeholder classes were
removed. Ten focused tests bring the critical suite to **114 tests**.

**Batch 5f - referral integrity and privacy (implemented 2026-07-13):** referral
application locks the current user, is idempotent for the same referrer, returns
409 for a conflicting prior code, uses one non-enumerating error for missing/self
codes, and is throttled to ten attempts per hour. The self-scoped summary prefetches
real relationships and exposes referred user IDs without their mobile numbers. Both
operations are present in generated OpenAPI. Six focused tests bring the critical
suite to **120 tests**.

**Batch 5g - real self profile (implemented 2026-07-13):** authenticated users now
have generated-schema `GET/PUT /api/v1/user/profile/`. Mobile/user identity is
server-owned, an absent profile is represented as null, first creation requires a
validated ten-digit national code, and partial updates lock the authenticated user
without allowing cross-user assignment. Five focused tests bring the critical suite
to **125 tests**. Flutter's former hardcoded identity, fake documents and no-op save
controls were replaced by a real BLoC-backed profile form.

**Batch 5h - authoritative market bookmarks (implemented 2026-07-13):** bookmark
writes now use an explicit idempotent desired state instead of a race-prone toggle,
lock the published market, and return the authoritative state. Lists are scoped to
the authenticated user and hide withdrawn markets. Three focused tests bring the
critical suite to **128 tests**. Flutter removes rows optimistically, prevents
duplicate in-flight writes and restores both row/state on failure.

**Batch 5i - real bank-information management (implemented 2026-07-13):** the
authenticated bank CRUD contract now returns one explicit shape without user or
internal model fields, validates canonical card/account/IBAN identifiers, uses UUID
routes and locks destructive writes. Create/update responses match list/detail and
DELETE is a bodyless 204. Four focused tests bring the critical suite to **132
tests**. Flutter's static sample cards and cosmetic finance dashboard were replaced
by tested load/create/update/delete state and a real form.

**Batch 5j - fail-closed shipping boundary (implemented 2026-07-13):** new
customer-paid products and shipping options are rejected until checkout can select
an option and snapshot its price. Cart add and checkout also reject legacy customer-
paid products, preventing silent undercharging. Legacy owner reads now use the real
`ships` relation and explicit IDs; product comment counts no longer return a fixed
placeholder. Six focused tests bring the critical suite to **138 tests**; Flutter
removed the unsupported radio, dead price form and unused API.

**Batch 5k - disable legacy product discounts (implemented 2026-07-13):** the
legacy endpoint now returns deterministic 409 after owner scoping and cannot create
`ProductDiscount` or mutate `Product.main_price`. Checkout continues to consume only
the separate authoritative discount contract repaired in Batch 4. One focused test
brings the critical suite to **139 tests**; Flutter removed the pre-product request,
discount state/events/widget and dead repository/API surface.

**Batch 5l - public product detail honesty (implemented 2026-07-13):** the canonical
`/api/v1/storefront/products?id=` mobile detail route now validates its UUID, exposes only
products whose market and product are published, suppresses unpublished related
products and omits owner-only
prices/workflow fields. Three focused tests are now part of CI and bring the critical
suite to **142 tests**. Flutter uses this public contract instead of the owner-only
route and removes its fabricated discount countdown, local-only bookmark and no-op
edit/share/upload/list/carousel controls. Comment forms now send only the authenticated
identity and content the backend actually accepts.

**Batch 5m - authoritative product-theme writes (implemented 2026-07-13):** theme
creation now accepts only layout order 0-17 and generates the internal layout name
server-side. Assignment is atomic, UUID-typed, validates slots 1-4, and rejects a
product from a different market even when both markets share an owner. Three focused
tests bring the critical suite to **145 tests**. OpenAPI now describes create/list/
update and reduces its unique inference errors from 135 to 132 without adding a
warning.

## 2. Verification baseline

| Check | Result |
|---|---|
| Graphify | Fresh backend graph generated; shared backend/frontend global graph registered. |
| Django system check | Initially failed on an overlong reservation index name; local pending fix shortens it. Current `check` passes. |
| Targeted reservation tests | **4/4 pass**, including URL routing and cross-service specialist rejection. |
| Full `manage.py test` | **Failed at audit time before real coverage**: the now-archived `scripts/archive/legacy-validation/test_performance_complete.py` imported unpinned `psutil`; `tests/test_models.py` imported removed `ChatConversation`. Only two root tests were discovered in that failing run. |
| Migration check | **Fails massively**: initial migrations are missing for almost every domain app. `.gitignore` ignores `**/migrations/0*`, so migration history is effectively absent from version control. |
| OpenAPI validation | **Fails**: many APIViews are omitted because serializers cannot be inferred; generation then crashes by evaluating `ProductKeyword` queryset against an unmigrated database. |
| Dependency audit | **Fails**: 67 vulnerabilities in 17 packages. |
| Infra validation | `docker-compose.production.yml` parses, but referenced files/volumes are missing; `docker-compose.prod.yaml` does not parse. Docker daemon/runtime validation remains pending. |

## 3. Application inventory

Status meanings: **critical** = exploitable/data-loss or fake money/security
path; **buggy** = implemented but known incorrect/incomplete; **thin/dead** =
installed or present without a meaningful active product path; **needs audit** =
no critical issue proven yet, but not sufficiently tested to call healthy.

| App/module | Status | Evidence / reason |
|---|---|---|
| `advertise` | contained / hardened projection | Fake manual payment is 503; no client/Product flag can activate an ad, and public visibility plus Product projection lifecycle are tested. Pricing remains a product decision. |
| `affiliate` | hardened user flow / owner API absent | Source eligibility, owned-market mutation, duplicate rejection and theme/list/detail ownership are tested; the empty owner URLConf remains an explicit product decision. |
| `analytics` | disabled / contained | Batch 2 removes active routes by default and adds staff-only defense in depth; fabricated/broken calculations must be repaired before enablement. |
| `base` | needs audit | UUID base model is foundational; no focused model/migration suite proves compatibility. |
| `cart` | hardened / migration-gated | Draft/placed lifecycle, snapshots, single-market enforcement, locked stock/discount transitions and owner isolation are implemented with focused tests. |
| `category` | needs audit | Active read APIs; schema type warnings and nested serializer/query performance need measurement. |
| `chat` | buggy | REST/WS contract is substantial and token WS auth was repaired earlier, but root tests import removed chat models and OpenAPI omits several views. Ownership and N+1 tests remain. |
| `comment` | hardened / limited surface | Published-target, parent, visibility and update ownership rules are tested; Flutter create/list works. No delete/like API is claimed. |
| `core` | buggy | Rate-limit middleware exists but is inactive; broad fallback/error utilities and cache startup side effects complicate checks/schema; logging is noisy and can expose internals. |
| `discount` | integrated / migration-gated | Checkout pricing and payment/cash consumption are real and locked; secure codes, ownership, validation and audit retention are tested. |
| `flutter` | bank share hardened | Public UUID share exposes an explicit four-field transfer contract; remaining share/schema and route/host history need contract work. |
| `gateway` | thin/dead | Installed model-only app with no mounted product API; payment uses `apps.payment` directly. |
| `index` | thin | Root/index views only; not a business domain. |
| `information` | small/buggy | Terms endpoint is intentionally public, but schema cannot infer it and broad exception handling masks causes. |
| `inventory` | consolidated into cart | Fake uninstalled models/manager removed; locked stock reservation/release/confirmation now lives on the real order/payment path. |
| `market` | schedule hardened / broader audit pending | Schedule routes now use the real model with owner, publication, overlap and idempotency checks. Other Market CRUD/media APIViews still need schema and ownership review. |
| `market_subdomain` | dead/inconsistent | App is installed but `django_hosts` is disabled and its URLs are not mounted through the active root URLConf. |
| `notification` | high / Batch 2 contained | Arbitrary-user create, fake provider success and repeat-queue flaws are fixed; real provider integration and delivery idempotency still need staging validation. |
| `payment` | high / Batch 1 hardened | Direct client-price, target-ownership, duplicate-session and callback-race paths are fixed; Float storage, DB uniqueness, legacy reconciliation and PostgreSQL concurrency validation remain. |
| `price_inquiry` | hardened / needs schema | User and answer ownership, active owner feed, finalize immutability and duplicate-answer locking are tested; OpenAPI annotations remain. |
| `product` | buggy/incomplete | No owner product-update endpoint despite edit expectations; shipping methods lack UI; serializer field evaluates/query-represents data during schema generation. |
| `referral` | relationship hardened / no reward program | Atomic one-time application, privacy-safe summary, throttling, schema and Flutter UI are tested. No points/credit are claimed because no reward ledger or policy exists. |
| `region` | needs audit | Small read API, but bare exception handling remains; seed/migration provenance is unclear. |
| `reserve` | access hardened / product model incomplete | Paid state, publication, cross-service/owner access and destructive history paths are tested. The model still lacks a booking date, capacity and authoritative price/payment lifecycle; owner Flutter CRUD is absent. |
| `sms` | disabled / contained | All commercial sends return 503 at owner/admin layers; provider mocks are explicit debug-only and client billing/provider fields are read-only. Real billing is not implemented. |
| `users` | auth/profile hardened / documents pending | OTP/token protections and Redis requirements are tested; self profile GET/PUT is owner-scoped and wired to Flutter. UserDocument upload/review has no mounted contract and remains disabled. |
| `wallet` | high / Batch 1 hardened | UUID/source ownership and ignored-debit exploits are fixed with consistent locks and tests; Float balance storage still needs a reconciled Decimal migration. |

No app is classified “healthy” yet: the audit has not produced sufficient
contract, permission, migration, and runtime test evidence for that label.

## 4. Confirmed fake, dangerous, or incomplete behavior

### 4.1 Money and order integrity

Items 1-4 below describe the audit baseline and are remediated by Batch 1; item
5 (Float persistence) remains open until the production schema and migration
history are reconciled. Items 6 onward belong to later cart/discount batches.

1. **Wallet transfer IDOR/wrong debit** — `apps/wallet/core.py:71-96` compares a
   database UUID with the caller's string ID and never proves source ownership.
2. **Client-priced payments** — `apps/payment/serializers/user.py:108-112` and
   `apps/payment/core.py:17-43` trust `amount`, `target`, and `target_id`; post
   payment marks objects paid using only that ID (`core.py:218-239`).
3. **Non-atomic wallet purchase** — `apps/payment/core.py:188-215` updates the
   target before debit and ignores debit failure; wallet input accepts arbitrary
   amounts/targets (`apps/wallet/serializer.py:17-20`).
4. **Duplicate gateway processing** — state is read before `atomic()` and never
   locked (`apps/payment/core.py:97-155`), so concurrent callbacks can credit twice.
5. **Float money** — payment and wallet amounts are floats
   (`apps/payment/models.py:30-34`, `apps/wallet/models.py:14-17`).
6. **Discount is cosmetic** — validate does not affect checkout, order pricing
   says discount is unimplemented, and consumption is never recorded
   (`apps/discount/views/user.py:18-81`, `apps/cart/models.py:163-169`).
7. **Order lifecycle is internally broken** — views use nonexistent `DRAFT`,
   write statuses absent from choices, reference undefined `logger`, and pop
   optional items unconditionally (`apps/cart/views/user.py:268-422`,
   `apps/cart/views/owner.py:72-78`, `apps/cart/serializers/user.py:330-331`).
8. **Multi-vendor authorization leak** — a vendor owning one order item can see
   and transition the entire mixed-vendor order (`apps/cart/views/owner.py:25-78,134-179`).
9. **Cart add can report success without creating an item** — the serializer's
   custom `save()` calls `super().create()` without the required order, catches
   every exception, and only attempts a name-based fallback
   (`apps/cart/serializers/user.py:70-97`, `apps/cart/views/user.py:43-82`).

Batch 4 resolves items 6-9: discounts affect immutable payable snapshots and
have locked reserve/consume/release counters; `DRAFT` is distinct from placed
`PENDING`; carts accept only one market; owners cannot list, view or transition
legacy mixed-market orders; and item mutations require a real ID, valid quantity,
published target and sufficient stock.

### 4.2 Auth, permissions, and abuse controls

1. **OTP is not production-safe** — `random.randrange`, PIN/mobile printing,
   swallowed SMS errors, reusable PIN, and permanent DRF token reuse
   (`apps/users/views/user_views.py:166-192,354-380`).
2. **Notification create is arbitrary-target** — only `IsAuthenticated` plus a
   caller-supplied `user_id` (`apps/notification/views.py:37-75`).
3. **SMS is arbitrary/unbilled** — authenticated-only endpoints, hardcoded
   `WALLET_OK=True`, no recipient relationship/quota/throttle
   (`apps/sms/views/owner.py:68-184`).
4. **Analytics leaks and accepts forged data** — global product/market/user
   querysets (`apps/analytics/views.py:150-281`), public CSRF-exempt dashboard
   APIs (`apps/analytics/dashboard_views.py:90-228,337-399`), and writable
   user/event/session fields (`apps/analytics/views.py:29-35,93-99`).
5. **Sensitive scopes are effectively unthrottled** — global authenticated rate
   is 10,000/hour; the custom middleware is inactive and development overrides
   remove OTP-specific scopes (`config/settings/base.py:404-414`,
   `config/settings/development.py:137-145`).
6. **Public bank-card data leak** — `/bank/share/<pk>` is public, fetches any
   UUID, and serializes `UserBankInfo` with `fields='__all__'`, exposing user,
   card/account/IBAN/branch data (`config/urls.py:45-48`,
   `apps/flutter/views.py:166-187`, `apps/users/serializers.py:96-102`).
7. **Price-inquiry IDORs** — owner list/detail expose all inquiries to any
   authenticated account; user detail/update fetch arbitrary inquiry IDs without
   ownership checks (`apps/price_inquiry/views/owner.py:17-68`,
   `apps/price_inquiry/views/user.py:41-64,294-316`).

Batch 5a resolves the public-bank and price-inquiry findings above: public bank
shares use an explicit minimal serializer; all inquiry mutations/answer reads are
owner-scoped; and the owner broadcast feed contains only finalized, unexpired
inquiries for authenticated market owners.

### 4.3 Fake providers and analytics

1. Push/email/SMS notification providers only log and return `True`
   (`apps/notification/services.py:399-441`).
2. Successfully sent notifications remain processable; queue completion only
   clears `is_processing`, enabling repeated sends (`services.py:88-93,489-506`,
   `models.py:524-526`).
3. Missing SMS configuration silently enables mock success and logs verification
   codes (`apps/sms/sms_core.py:24-65`).
4. Analytics includes hardcoded cohort values, constant cache-hit rate, random
   forecasts, and fail-open fraud output (`apps/analytics/advanced_views.py:526-545`,
   `services.py:671-710,906-913`, `ml_models.py:681-708`).
5. Reservation payment views contain only placeholder comments and empty string
   statements (`apps/reserve/views/user/reservation.py`).
6. Comment list filters `parent_id=F('id')`, an implausible self-parent
   condition that normally hides top-level comments (`apps/comment/views.py:65-79`).
7. “Market schedule” endpoints mutate reservation `ReserveTime` records through
   a synthetic service even though a separate `MarketSchedule` model exists
   (`apps/market/views/market_schedule.py:17-80`).

Batch 5c corrects the interpretation of item 6: django-comments-xtd intentionally
rewrites a root comment's `parent_id` and `thread_id` to its own ID. The filter was
retained, while target/parent/visibility/ownership bugs around it were fixed.

Batch 5d fixes item 7 by moving the schedule routes to `MarketSchedule`. No live
data migration from synthetic `ReserveTime` rows is guessed: deployment must first
identify any `Service(name='-')` records and explicitly decide whether they are
legacy opening hours or genuine reservation availability.

Batch 5e removes the unmounted item 5 placeholder classes instead of advertising a
fake payment feature. A real reservation payment target cannot be enabled until the
product defines booking date/capacity, price ownership, cancellation and refund
semantics; `is_paid` is server-owned and remains false on current booking creation.

### 4.4 Error handling and contract quality

- Broad/bare catches are pervasive across affiliate, market, product, region,
  information, payment, analytics, chat, notification, and reserve code. Several
  leak `str(e)` to clients or collapse distinct failures into generic responses.
- HTTP transport and envelope codes disagree: bulk SMS body says 201 but returns
  200; pattern SMS reports success with partial failures and double-encodes JSON;
  invalid payment targets become 500; order creation defaults to 200; some 204s
  include bodies.
- Provider calls lack bounded timeouts and `raise_for_status()` in payment and
  SMS, so workers can hang and ambiguous failures have no reconciliation state.

## 5. OpenAPI contract status

drf-spectacular is installed and schema/docs URLs exist at `/api/schema/` and
`/api/docs/`, but the generated contract is **not currently usable as the source
of truth**.

Batch 3 made schema generation database-independent and structurally valid:

- Dozens of APIViews are omitted because serializer classes cannot be inferred:
  market CRUD/media/schedule, discount, owner orders, price inquiry, terms,
  health, chat search/analytics, notification cleanup, and others.
- Several serializer method fields have unresolved types.
- Custom related fields now have explicit OpenAPI types, and malformed raw
  response dictionaries were replaced with supported response declarations.
- `manage.py spectacular --validate` now exits successfully against an empty
  database. It still reports 154 unique inference errors and 49 unique warnings,
  so the generated file is structurally valid but incomplete.

Required contract batch: make schema generation side-effect-free and database-
independent, annotate every mounted operation, validate the schema in CI, and
add a route/schema parity test. Hand-written endpoint files remain non-authoritative.

## 6. Production hardening findings

### Migrations and tests

- The migration ignore rule has been removed, but the repository still has almost
  no committed domain migrations, and `makemigrations --check --dry-run` proposes initial
  migrations for nearly every app. This makes reproducible deploys and safe
  evolution impossible.
- Root discovery no longer imports the manual performance benchmark and the stale
  model smoke tests now target current models. The production-critical regression
  set passes 56 tests locally.
- `config.settings.ci` builds the disposable current-model schema on PostgreSQL
  (including native `ArrayField` columns) and uses real Redis. Docker is unavailable on this workstation, so this exact
  service-backed run remains for GitHub Actions/independent verification.
- Legacy chat and disabled analytics suites remain red because their services and
  tests reference fields/calculations absent from current models. They are recorded
  debt, not included in the production-critical green subset.

### Settings, logging, and performance

- Dev/prod settings are separated, and production sets `DEBUG=False`, but
  production still contains insecure/fail-open fallbacks and overrides
  env-derived hosts.
- Production host/CSRF configuration conflicts across code and scripts; health
  responses expose raw dependency errors/system details.
- Logging is extensive but not consistently redacted; OTP, SMS recipients/body,
  provider results, and raw exceptions may leak.
- Known N+1 candidates include nested market/product/chat/notification serializers.
  These need query-count tests before blanket `select_related/prefetch_related` edits.
- Several useful indexes exist in models, but missing migration history means
  their actual production presence cannot be proven.

## 7. Infrastructure and CI/CD status

Infrastructure details are expanded in `INFRA_NOTES.md`, which itself must be
updated because earlier assumptions are stale.

Critical facts:

- At least five competing deploy entry points exist. The live path cannot be
  proven from repository contents alone.
- CI builds and pushes `Dockerfile.production`, while production compose builds
  `Dockerfile.prod` and declares no app `image:`. Server `pull`/`up` therefore
  does not consume the CI-built image.
- Production compose references missing pgbouncer/nginx/certificate inputs;
  proxy and ACME volumes are wired inconsistently; nginx healthcheck targets a
  default server that returns 444.
- CI's external healthcheck accepts the root-domain redirect without proving the
  Django API is healthy.
- Backup uses `exec` against a one-shot container. Any failure can trigger
  `git reset --hard HEAD~1`, even before deployment; DB migrations are not rolled back.
- `docker-compose.prod.yaml` is invalid YAML; dev compose targets a nonexistent
  Dockerfile stage; systemd uses WSGI and cannot serve WebSockets.
- `.dockerignore` allows env files, keys, certificates, and the tracked `.venv`
  into every `COPY .` image. About 1,239 `.venv` files are tracked.
- Batch 3 replaced advisory lint/security checks with hard Ruff, pip-audit,
  PostgreSQL/Redis regression, OpenAPI validation and migration-drift jobs.
  `pip-audit` is clean after tested dependency upgrades. The migration job is
  intentionally red (21 apps need baselines).
- Automatic SSH deployment, destructive `git reset --hard` rollback, and image
  publication were removed. Build/publish must stay absent until exposed build
  context is cleaned, credentials are rotated, and runtime/migration state is reconciled.

## 7.1 Batch 3 verification snapshot (2026-07-12)

- Dependency audit: **0 known vulnerabilities** (previously 67 in 17 packages).
- Dependency resolver: `pip check` clean on Python 3.12.
- Regression tests: **56/56 pass** under isolated test settings.
- OpenAPI: empty-database generation and structural validation pass; completeness
  debt remains 154 unique inference errors.
- Migration drift: expected hard failure, initial migrations proposed for **21 apps**.
- Image/deploy: explicitly absent; this is not an incidental freeze that disappears
  when the migration gate becomes green.
- Critical Ruff gate (`E9`, `F63`, `F7`, `F82`) passes outside explicitly disabled
  analytics and legacy core management scripts.

## 8. Missing or incomplete product features

These are proven by backend models/placeholders or the Flutter contract map:

| Feature | Evidence | Classification |
|---|---|---|
| Reservation payment lifecycle | Empty placeholder views in reserve user code; `is_paid` exists. | Required, but pricing/payment semantics need decision. |
| Owner affiliate API | Mounted URL prefix with empty `apps/affiliate/urls/owner.py`. | Ambiguous: implement only if owners manage marketer relationships. |
| Product update | Flutter owner edit need exists; owner product URLConf has no update endpoint. | Required if products are editable after creation. |
| Real discount application | Discount models/API exist, but checkout ignores them. | Required; stacking/consumption semantics need decision. |
| Multi-vendor fulfillment | Current order can contain multiple markets but has one global status. | Required decision: forbid mixed carts or add suborders. |
| Inventory integration | Large inventory manager exists but app is not installed and cart mutates stock separately. | Decide integrate vs remove dead code. |
| Real notification delivery | Provider methods are stubs. | Required if email/SMS/push channels remain advertised. |
| Real owner SMS billing | Models expose costs but wallet billing is hardcoded away. | Required before endpoint enablement. |
| Tenant-scoped analytics | Flutter expects owner analytics; backend currently exposes platform-wide data. | Required; ownership scope needs decision. |
| Auth token lifecycle | Permanent DRF tokens conflict with unused JWT/lockout code. | Required security decision. |

## 9. Proposed execution batches

Order is based on exploitability, data integrity, dependency, and deploy safety.
Each batch ends with tests, independent sub-agent verification, `AUDIT.md` and
`NOTES.md` updates, Graphify refresh, and a separate commit.

1. **Security containment and reproducible baseline**
   - Freeze deploys; identify live runtime; rotate exposed secrets/TLS; untrack
     sensitive artifacts and `.venv`; fix ignore files; plan GHCR/cache cleanup.
   - Repair migration policy, stale test discovery, and make CI baseline genuinely fail.
   - Upgrade vulnerable dependencies with compatibility tests.
2. **Wallet/payment/order integrity**
   - Fix wallet ownership/UUID selection, Decimal money, server-derived pricing,
     atomic target transitions, callback locking/idempotency, provider timeouts.
   - Resolve multi-vendor order semantics before implementing fulfillment changes.
3. **Auth/OTP and abuse controls**
   - Cryptographic one-time OTP, fail-closed delivery, attempt/IP throttles,
     PIN consumption, token lifecycle decision, redacted logs.
4. **Messaging: notification and SMS**
   - Close arbitrary-target permissions, terminal/locked queue processing,
     explicit unavailable providers, real delivery and billing only after policy decisions.
5. **Analytics containment and truthfulness**
   - Immediately gate public/global endpoints; prevent forged finance events;
     remove fabricated metrics; fix UUID/calculation/signal defects; implement tenant scope.
6. **Cart, discount, inventory, and fulfillment**
   - Coherent order statuses, real discount consumption, inventory transaction
     integration, and chosen single-/multi-vendor model.
7. **Domain-by-domain API audit**
   - Users/profile/bank, market/category/product/comment, reservation, inquiry,
     advertise/affiliate/referral/region/information/chat; permissions, IDOR,
     validation, N+1, missing endpoints, and contract tests.
8. **OpenAPI as official contract**
   - Side-effect-free complete schema, annotations/serializers, schema validation
     and route parity in CI; reconcile Flutter map.
9. **CI/CD hard gates**
   - Real lint/security failures, PostgreSQL/Redis tests, migration/schema checks,
     immutable image build, pinned actions, deploy concurrency, migration-first
     release and meaningful health check.
10. **Infrastructure consolidation (independent track after runtime discovery)**
    - One compose/Docker/nginx/cert/backup path, staging validation, production
      observation, then deletion of legacy paths.
11. **Final production verification**
    - Full test/security/schema/migration suite; Docker build/compose/nginx checks;
      staging smoke/load checks; documented release and rollback/restore drill.

## 10. Decisions required at the initial checkpoint

1. **Payments:** authoritative price and payer rules for order, market,
   advertisement, reservation, and wallet top-up.
2. **Orders:** forbid mixed-market carts (safer short-term) or build per-market
   suborders/fulfillment.
3. **Discounts:** stacking/precedence, per-user reuse, and consume-at-checkout vs
   consume-after-payment.
4. **Notifications/SMS:** admin/system-only notifications vs owner-to-own-customer;
   SMS recipient relationship, pricing, refund, quota, and verified-owner rule.
5. **Analytics:** platform analytics admin-only; owner analytics limited to owned
   markets/products/customers (recommended) or another model.
6. **Auth:** retain DRF Token with expiry/rotation or complete and adopt JWT.
7. **Infrastructure:** immutable CI-built image (recommended) vs server build;
   canonical server directory/env source/domains; secret/certificate mechanism;
   forward-only migrations vs restore-based rollback.
8. **Security remediation:** maintenance window and responsibility for credential/
   TLS rotation; history rewrite plus GHCR/Actions cache deletion vs rotation and
   untracking only.

No post-audit implementation batch should begin until this checkpoint is approved.
