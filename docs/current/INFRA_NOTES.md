# Infrastructure status

مسیرهای موازی و متناقض قبلی بازنشسته شده‌اند. وضعیت canonical فعلی:

- `Dockerfile`: build چندمرحله‌ای backend با targetهای `runtime`، `runtime-ml` و
  `runtime-dev-ml`؛ هیچ `COPY .` ندارد.
- `docker-compose.yml`: استک یک‌دست local/dev شامل PostgreSQL، Redis، backend و Flutter web.
- `docker-compose.production.yml`: runtime production با image digest، ASGI، edge TLS و
  secret-file؛ DB/Redis خارجی و بدون migration خودکار.
- `config/nginx/production.conf`: routeهای HTTPS، API، WebSocket، static و media.
- `docs/current/GROUP_1_OPERATIONS_RUNBOOK.md`: تنها راهنمای معتبر deploy، rotation، migration
  reconciliation و schedule.

production هنوز deploy-ready نیست، چون rotation واقعی credential/TLS و reconcile migration
با snapshot production خارج از محیط محلی باقی مانده‌اند. compose معتبر بودن topology را ثابت
می‌کند، نه آماده بودن داده‌ی production را.
