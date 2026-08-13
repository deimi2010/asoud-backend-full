# Backend working notes

## SECURITY: repository, image, and registry secret exposure
Tracked env files and multiple TLS private keys have existed in git history.
Because active Dockerfiles use `COPY .` and `.dockerignore` does not exclude
them, assume old image layers, GHCR versions, and Actions caches are exposed too.
Do not print values. Rotation/reissue is mandatory before untracking/history work.

## SECURITY: dependency baseline remediated in Batch 3
The 2026-07-12 baseline had 67 known vulnerabilities in 17 pinned packages.
Pins were upgraded together (including Django 5.2 LTS, crypto/TLS, ASGI, Pillow,
JWT, requests, Twisted and ML dependencies). `pip check`, 145 regression tests and
both installed-environment and requirements-file `pip-audit` now pass with zero
known vulnerabilities.

## Migrations are not reproducible
The ignore rule was removed. A dry-run still proposes initial migrations for 21
domain apps. The CI migration gate deliberately fails; image publication is also
explicitly absent rather than depending on that failure as a safety mechanism.
Reconcile the live production database/migration table before committing or
applying any generated baseline.

## OpenAPI exists but is not the contract yet
drf-spectacular generation is now side-effect-free, empty-database-safe and
structurally valid. It still reports 154 unique inference errors, so it is not yet
the authoritative contract; annotate those domain views during later API batches.

## CI does not currently prove backend health
The critical suite is explicitly enumerated, 56 tests pass, and CI now uses real
PostgreSQL/Redis settings. Security, critical Ruff, OpenAPI and migration checks
are hard gates. Image publication and automated deployment have been removed until
secret/build-context cleanup, migration reconciliation, and runtime discovery.

Legacy chat/analytics tests are not silently ignored: chat services expect removed
participant fields and analytics still has false/broken calculations. Analytics is
route-disabled; both suites remain documented work for their domain batches.

## Production deploy path is not established
Repository evidence contains at least five conflicting entry points. The current
workflow builds an image that production compose does not consume. Identify the
running server's compose/unit/image/env source before deleting or consolidating.

## Financial behavior needs explicit server authority
Batch 1 now enforces wallet ownership, server-derived order totals, a single
gateway session per frozen order, atomic debit/target transition, bounded provider
timeouts, callback locking/idempotency, integrity-marked sessions, and a common
`User -> Order -> Wallet` lock order. Focused tests pass 24/24.

Production is still blocked on PostgreSQL concurrency tests, unique constraints
for gateway authority/reference IDs, and the Float-to-Decimal data migration.
Pre-Batch-1 pending sessions intentionally fail closed because their amount and
target were client-controlled; inventory and reconcile/cancel them before rollout.
Ambiguous provider responses stay `pending` with their order `processing` so an
operator or retry can reconcile them without risking a second charge. Definitive
provider rejection moves the order to `failed` rather than back to `pending`,
which prevents duplicate carts after a replacement cart has already been opened.

## Batch 2 containment state
OTP is cache-hashed, TTL-bound, attempt-limited, issuance-serialized, one-time,
and rotates an expiring DRF token. Production login now requires the built-in
Django Redis cache to be reachable; there is no LocMem fallback. REST and both WS
token resolvers reject expired or inactive users.

Notification creation is admin-only. Stub push/email/SMS providers fail honestly;
immediate sends are not also queued; retry acceptance returns HTTP 202; queue work
uses short claim/finalization locks and terminal rows are deleted.

Commercial SMS is intentionally hard-disabled with 503 in owner and admin views.
Do not restore those paths until atomic pricing/wallet billing, quotas, recipient
policy, provider reconciliation and refund behavior are implemented.

Analytics is intentionally route-disabled with `ANALYTICS_ENABLED = False`.
Defense-in-depth permissions are staff-only and client event writes are removed,
but the full legacy analytics suite still has seven structural/calculation
failures. Do not enable it merely because access control is fixed.

## Batch 4 cart, discount, and inventory authority
`DRAFT` is the mutable cart state; checkout snapshots unit prices, subtotal,
discount and payable total, then moves to `PENDING`. A new draft is created for
subsequent shopping. New orders are single-market; legacy mixed-market orders are
not visible or actionable by any owner.

Stock is decremented only under locked product/affiliate rows when payment begins
(or a cash order is accepted). Gateway/wallet failure releases it; completion
confirms it without another decrement. Discount capacity follows the same
reserved/consumed/released lifecycle and is single-use per buyer. The former
uninstalled inventory code was deleted because it wrote nonexistent fields and
hid failures.

Production rollout requires a forward migration/backfill after inspecting live
data: distinguish old `pending` carts from placed orders, resolve duplicate
discount codes before adding uniqueness, add order/item snapshot and inventory
state columns, add `discount.reserved`, backfill safe historical totals, and audit
invalid order items before enforcing target constraints. No migration was generated
against the unknown live baseline.

`PAYMENT_SESSION_TTL_SECONDS` defaults to 1800. Production must schedule
`manage.py reconcile_stale_payments --limit 100` at least once per minute. It asks
the gateway for the authoritative result: paid sessions complete, definitive
failures release reservations, and network/amount/authority ambiguity remains
pending for manual reconciliation. It never releases merely because a session is old.
The rollout backfill must repair or quarantine targetless and dual-target items
before adding `order_item_exactly_one_target`, and must switch order-item product
and affiliate foreign keys to `PROTECT` so historical orders remain immutable.

## Batch 5a bank-share and inquiry contracts
`/bank/share/<uuid>` remains an intentional public transfer link, but its response
is restricted to `id`, bank name, card number and account-holder name. Never reuse
the authenticated `UserBankInfoListSerializer` there because it includes account,
IBAN, branch, user and audit fields.

An inquiry is mutable while `send` is null. Flutter finalizes with `send: true`,
which maps to the real chat/WebSocket broadcast because commercial SMS is disabled.
After finalization its content/images and received quotes are immutable; expiry can still be renewed.
The owner feed contains only finalized, unexpired inquiries and requires ownership
of a market. A row lock enforces one answer per owner per inquiry. HTTP DELETE and
legacy POST delete are both accepted for compatibility.

## Batch 5b advertisement and affiliate contracts
Manual advertisement creation/payment returns 503 until a real server-owned price
and payment target are defined. `is_paid` is read-only. Product-backed ads are
idempotent unpaid drafts: they mirror the owning Product and cannot be edited or
deleted independently. Client-controlled `Product.is_requirement` never activates
them. Legacy unpaid advertisements remain visible only in the creator's `self` list.

Affiliate listings must be created in a Market owned by the caller and reference a
published Product with `is_marketer=True` in a published source Market. The backend
derives source type and subcategory, creates drafts and keeps status read-only for users,
locks the Market to reject concurrent duplicates, and scopes management list/detail/
theme routes to that Market owner. Source withdrawal immediately blocks cart add and
checkout. The empty affiliate owner URLConf was not fabricated; it remains disabled
until its distinct business purpose is defined.

## Batch 5c comment contract
Comments remain a bare-list Flutter contract backed by `django-comments-xtd`, not
the unused local `apps.comment.models.Comment`. Creation supports only `market` and
`product` targets that are currently published; Product comments also require a
published parent Market. Replies must point to a public, non-removed comment on the
same object. Public list/detail hide moderated comments and withdrawn targets.
Updates are text-only, owner-scoped and row-locked.
The public bare list is capped at the 100 most recent roots and bulk-groups their
direct children, avoiding the former query-per-root amplification.

Do not replace the root filter `parent_id=F('id')` with NULL/zero: XtdComment saves
root nodes with their own ID as both parent and thread ID. Replies use the root ID.

## Batch 5d market schedule contract
Market opening hours live in `apps.market.models.MarketSchedule`; `ReserveTime`
belongs exclusively to a reservable Service. The owner API keeps Flutter's
`market/day/start/end` shape and 1..7 Saturday-to-Friday numbering, while the model
stores 0..6. Both endpoints require `end > start`; intervals for one Market/day
may be adjacent but not overlap. An exact POST retry returns the existing row.
Owner list/update/delete is ownership-scoped and the user list requires a published
Market.

Interval ordering and overlap are enforced on the schedule API. A database check
and PostgreSQL exclusion constraint must be added with the reconciled migration
baseline before direct admin/database writes are supported; until then, schedule
writes must go through these locked API routes.

Do not automatically migrate `ReserveTime` rows belonging to a service named `-`.
That placeholder was created by the old schedule endpoint, but production may also
contain manually-created records with that value. Inventory and classify those
rows during the migration-baseline rollout before any data move or deletion.

## Batch 5e reservation contract and boundary
User catalog endpoints return services, specialists, reserve times and days off only
for published Markets. Reservation creation accepts exactly `reserve` and
`specialist`, verifies their relationship under row locks, assigns the authenticated
user and always stores `is_paid=False`. No client endpoint may promote paid state.
User detail/list is self-scoped; owner detail/list follows the reserve Service's
Market owner. Service, ReserveTime and Specialist deletion returns 409 once a
Reservation references it, preserving history despite the legacy CASCADE models.
Booked ReserveTime rows are also immutable; owner update/upsert returns 409 rather
than rewriting a past reservation's displayed time.
Likewise, a Specialist update may add services but cannot remove a Service referenced
by that Specialist's reservation history.

The present data model is not a complete appointment system: `Reservation` has no
appointment date, duration/capacity, price, cancellation state or refund state.
`ReserveTime.day` alone is a recurring weekday and cannot distinguish occurrences.
Therefore the former unmounted payment placeholder classes were deleted and no
duplicate/capacity/payment behavior was invented. Those fields and lifecycle rules
require a product decision plus reconciled migrations before payment is enabled.

## Batch 5f referral contract
`POST /api/v1/user/referral/create/` accepts the referrer's mobile number as `code`.
The relationship is one-time: an exact retry returns 200 with the existing referral,
while a different later code returns 409. Missing and self codes deliberately share
the same 400 response to reduce mobile-number enumeration. Attempts are scoped to
10/hour per authenticated user.

`GET /api/v1/user/referral/` remains self-scoped and keeps the legacy `referrees`
key for compatibility, but each entry contains only its user ID; mobile numbers are
not disclosed. This feature records relationships only. Do not advertise rewards,
wallet credit or discounts until a real incentive ledger, eligibility window and
reversal policy are defined.

## Batch 5g self-profile contract
`GET /api/v1/user/profile/` returns server-owned `id` and `mobile_number`, plus a
nullable profile. `PUT` creates or partially updates only `address`, `national_code`,
`birth_date` and `picture`; client `user`/mobile fields are ignored and IBAN writes
are explicitly rejected. First creation requires a ten-digit ASCII national code.
Updates lock the authenticated User row and always bind the profile to that user.
The legacy IBAN field remains
read-only until its incorrect 20-character database limit can be reconciled against
production migrations; a valid Iranian Sheba value requires `IR` plus 24 digits.

## Batch 5h market bookmark contract
`GET /api/v1/user/market/bookmark/` returns only the authenticated user's active
bookmarks whose markets are still published. `PUT
/api/v1/user/market/bookmark/{market_id}/` requires `bookmarked: true|false`, is
idempotent, locks the published market before updating its unique user/market row,
and returns `{market_id, bookmarked}`. Unpublished markets deliberately resolve as
404 and are never leaked back through the list.

## Batch 5i user bank-information contract
The public `GET /api/v1/user/bank-info/list/` is the selectable bank catalog.
Authenticated create/list/detail/update/delete routes expose only `id`, bank ID/name,
card/account/IBAN, owner name, branch and description; the owning user and internal
base-model fields are never serialized. Card numbers are 16 ASCII digits with a
valid checksum, account numbers are ASCII digits, and non-empty IBAN values normalize
to `IR` plus 24 digits and must pass the ISO 13616 checksum.
Client user fields are ignored and the authenticated user is always bound server-side.
Update/delete use owner-scoped row locks; DELETE returns an empty HTTP 204.

## Batch 5j shipping contract is intentionally fail-closed
The current Order model has no selected shipping option or immutable shipping amount.
`ship_cost_pay_type=customer` is therefore rejected by product creation and by cart
validation for both direct and affiliate products. The owner shipping-create route
returns 409 `shipping_contract_unavailable` and persists nothing; its list route is
read-only for legacy rows and owner-scoped. Product detail reads those rows from the
actual `ships` relation. Seller-paid/free products remain orderable because they add
no customer payable amount. Re-enable writes only with an order-level option and
price snapshot included in authoritative totals/payment reconciliation.

## Batch 5k legacy ProductDiscount is disabled
`POST /api/v1/owner/product/discount/create/{product_id}/` is retained only as an
owner-scoped compatibility boundary and returns 409
`legacy_product_discount_disabled`. It never creates the legacy duration/position
row and never mutates `Product.main_price`. Product and market discounts must use the
separate `apps.discount` contract whose eligibility, reservation, snapshot and
consumption are enforced by cart/payment. Do not reconnect the legacy model.

## Batch 5l public product detail contract
`GET /api/v1/storefront/products?id={uuid}` is the customer detail boundary. It returns 404
unless both the product and its market are published, hides owner-only
colleague/marketer/maximum prices and workflow metadata, and suppresses unpublished
gift/required products.
`/api/v1/owner/product/detail/{uuid}/` remains owner-only and must not be used by a
customer screen. Public detail is intentionally readable without authentication;
creating a comment still requires the server-authenticated user.

## Batch 5m product-theme write contract
Theme creation accepts only `order` 0-17; `name` is server-owned as `layout-{order}`
and client placeholders are ignored. Assigning a product validates a UUID product and
slot 1-4 under a transaction/row lock, and product/theme market IDs must match. This
prevents an owner with multiple markets from creating a cross-market theme relation.

`UserDocument` still has no mounted upload/review lifecycle. The Flutter rewrite
therefore removes the fake three-document gallery and no-op upload controls instead
of pretending KYC files were persisted.
