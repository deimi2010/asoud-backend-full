# App bootstrap, stores, and invitation flow

This document is the client contract for deciding what to show after authentication.
The client must not derive authorization from `User.type`.

## First launch and authentication

1. A public store or invitation can be opened without authentication.
2. Creating a store, buying, reserving, commenting, or applying referral attribution
   requires authentication.
3. After PIN verification, call `GET /api/v1/user/bootstrap/`.

The bootstrap response always grants an active authenticated account the ability to
buy, create a store, and use the business-card feature. It also returns every store
the account owns or actively collaborates on.

`markets[].access` is one of:

- `owner`: full control over that store.
- `manager`: operational write access.
- `editor`: content and reservation write access.
- `viewer`: read-only operational access.

`is_platform_admin` and `capabilities.manage_platform` are authoritative for the
platform administration UI. Clients must not infer platform administration from a
store role.

## Store invitation

The owner or platform admin creates a link with:

`POST /api/v1/user/referral/invites/`

```json
{
  "market_id": "uuid",
  "expires_at": "2026-12-01T00:00:00+03:30"
}
```

The share URL is `/invite/<token>/`. Resolving that URL is public and returns the
target `market`, `business_id`, expiry, active state, and usage count. The client
should open the storefront immediately. Authentication is deferred until the user
performs an authenticated action.

After authentication, referral attribution is applied once with:

`POST /api/v1/user/referral/create/`

```json
{"code": "invite-token"}
```

Legacy mobile-number referral codes remain accepted for v1 compatibility. A user
has one first-touch referrer; opening other store links is still allowed but does not
replace the original attribution.

## Store colleagues

Only the store owner or a platform admin can add, change, or revoke colleagues:

- `GET/POST /api/v1/owner/market/memberships/<market_id>/`
- `PUT/DELETE /api/v1/owner/market/memberships/detail/<membership_id>/`

Deleting a membership revokes it instead of destroying its audit history.
