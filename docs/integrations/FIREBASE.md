# Firebase integration

The backend uses Firebase only as an optional mobile-support boundary. Django and
PostgreSQL remain authoritative for identity, stores, orders, payments, referrals,
commissions, and notification history.

## Backend features

- FCM push delivery through `firebase-admin`.
- Per-user device registration at `POST /api/v1/devices/`.
- Device removal at `DELETE /api/v1/devices/{id}/`.
- Automatic deactivation of registrations rejected as unregistered by FCM.
- Optional Firebase App Check enforcement for `/api/v1/`.

Set `FIREBASE_ENABLED=true`, `FIREBASE_PROJECT_ID`, and mount a service-account
credential outside the repository through `GOOGLE_APPLICATION_CREDENTIALS`.
Never commit the service-account JSON file. Enable `FIREBASE_APP_CHECK_ENFORCED`
only after every released client sends `X-Firebase-AppCheck`; rollout should first
be verified in staging.

## Client contract

The Flutter client must initialize Firebase, request notification permission,
upload its current FCM registration to `/api/v1/devices/`, refresh that registration
when Firebase rotates it, and deactivate it on logout. It should also initialize:

- Crashlytics for uncaught Flutter/platform failures;
- Performance Monitoring for startup and HTTP traces;
- Remote Config only for non-authoritative presentation flags;
- Analytics only for UI interaction events, never financial truth;
- App Check and the `X-Firebase-AppCheck` header on API requests.

This repository does not contain the Flutter project, so those client SDK changes
must be applied in its own repository before App Check enforcement is enabled.
