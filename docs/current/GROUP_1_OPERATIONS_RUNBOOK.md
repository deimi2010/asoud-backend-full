# Runbook عملیاتی گروه ۱ — پایه‌ی Production

این سند مسیر canonical عملیات است. هیچ دستور production این سند در محیط محلی اجرا نشده است.
دو gate زیر هنوز بیرونی و مسدودکننده‌ی انتشارند:

1. rotation/reissue واقعی همه‌ی credentialهای در معرض و TLS توسط مالک سرویس‌ها؛
2. reconcile تاریخچه‌ی migration با snapshot ناشناس‌شده‌ی production.

checklist اجرایی قدم‌به‌قدم، queryهای read-only snapshot و قالب evidence در
[GROUP_1_EXTERNAL_GATES_CHECKLIST.md](GROUP_1_EXTERNAL_GATES_CHECKLIST.md) قرار دارد. آن سند
مکمل الزامی این Runbook است.

تا وقتی هر دو gate با مدرک تأیید نشده‌اند، push کردن حذف secretها، بازنویسی history، اجرای
`migrate` روی production و deploy عمومی ممنوع است.

## ۱. قرارداد runtime نهایی

- local/dev: `docker compose up` با `docker-compose.yml`؛ PostgreSQL و Redis فقط محلی.
- production: `docker-compose.production.yml`؛ فقط `edge`، `backend` و `frontend`.
- DB و Redis در production خارجی/managed هستند و port دیتابیس یا Redis publish نمی‌شود.
- backend با Daphne/ASGI اجرا می‌شود؛ `/ws/` واقعاً به ASGI route می‌شود.
- imageها روی سرور build نمی‌شوند. `BACKEND_IMAGE`، `FRONTEND_IMAGE` و `EDGE_IMAGE` باید
  reference کامل و immutable از نوع `name@sha256:...` باشند.
- startup هیچ migration یا seed اجرا نمی‌کند. `migration-plan` فقط read-only است.
- `dev_migrations/` فقط در target محلی `runtime-dev-ml` وجود دارد و داخل image production نیست.

## ۲. ورودی‌های non-secret و secret

مقادیر non-secret لازم:

| نام | توضیح |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | hostهای واقعی، به‌همراه wildcard کنترل‌شده مثل `.asoud.ir` در صورت نیاز |
| `CSRF_TRUSTED_ORIGINS` | فقط originهای HTTPS کامل |
| `CORS_ALLOWED_ORIGINS` | فقط originهای HTTPS کلاینت |
| `DATABASE_NAME/USERNAME/HOST/PORT` | مشخصات endpoint مدیریت‌شده |
| `DATABASE_SSLMODE` | پیش‌فرض `require`؛ در سرویس پشتیبان TLS معتبر ترجیحاً `verify-full` |

فایل‌های secret لازم، همگی خارج از repository و با دسترسی حداقلی:

| متغیر مسیر فایل | محتوا |
|---|---|
| `DJANGO_SECRET_KEY_FILE` | کلید تازه‌ی Django |
| `DATABASE_PASSWORD_FILE` | رمز تازه‌ی role محدود DB |
| `REDIS_URL_FILE` | URL کامل Redis مدیریت‌شده با TLS و credential تازه |
| `ASOUD_RATE_LIMIT_KEY_SECRET_FILE` | کلید HMAC مستقل برای identityهای rate limit |
| `SMS_API_FILE` | credential تازه‌ی provider پیامک |
| `ZARINPAL_MERCHANT_ID_FILE` | merchant credential تازه |
| `TLS_FULLCHAIN_FILE` / `TLS_PRIVATE_KEY_FILE` | certificate chain و private key تازه |

Compose این فایل‌ها را زیر `/run/secrets` mount می‌کند. entrypoint و settings مقدار هیچ‌کدام
را چاپ نمی‌کنند و تنظیم هم‌زمان `NAME` و `NAME_FILE` را رد می‌کنند.

## ۳. rotation و پاک‌سازی exposure

قبل از اجرا، بخش Gate A در
[GROUP_1_EXTERNAL_GATES_CHECKLIST.md](GROUP_1_EXTERNAL_GATES_CHECKLIST.md) را کامل کنید؛ فهرست آن سند
علاوه بر secretهای runtime، credentialهای Git/CI، registry، deploy/SSH، DNS/CDN و invalidation
اجباری token/session را پوشش می‌دهد.

این ترتیب باید توسط owner/operator انجام شود و قابل جابه‌جایی نیست:

1. inventory حساب‌ها و مصرف‌کنندگان: Django signing، DB، Redis، SMS، درگاه پرداخت، TLS،
   registry و هر CI/deploy credential قدیمی؛ بدون کپی مقدارها در ticket یا log.
2. ایجاد credential جدید با least privilege. هرجا provider overlap می‌دهد، قدیم و جدید فقط
   به‌اندازه‌ی rollout هم‌زمان معتبر بمانند.
3. قرار دادن credentialهای جدید در secret store/فایل خارج repo، deploy در staging و تست
   `/readyz`، OTP واقعی، WebSocket ticket و تراکنش sandbox/کنترل‌شده‌ی provider.
4. rollout production با observation، سپس revoke قطعی credentialهای قدیمی و reissue TLS.
5. ثبت فقط شناسه/زمان rotation و owner؛ هرگز مقدار secret ثبت نشود.
6. بعد از تأیید revoke همه‌ی موارد، history با `git filter-repo` روی مسیرهای env/TLS آلوده
   بازنویسی شود، تمام cloneها دوباره clone شوند و tag/branchهای قدیمی حذف شوند.
7. همه‌ی image/layerهای registry و cacheهای CI/build که قبل از rotation ساخته شده‌اند پاک و
   imageها از commit پاک بازسازی شوند. digestهای تازه ثبت شوند.
8. secret scanning کامل history پاک‌شده به CI اضافه و required شود.

نکته: فایل‌های حساس فعلاً در worktree به‌شکل حذف‌شده دیده می‌شوند، اما تا قبل از مدرک rotation
نباید این حذف‌ها commit/push یا history rewrite شوند.

## ۴. reconcile migration production

queryهای catalog/integrity و مالی این مرحله در فایل‌های زیر هستند و فقط روی snapshot ایزوله و
ناشناس‌شده اجرا می‌شوند:

- [`scripts/production/snapshot_inventory.sql`](../../scripts/production/snapshot_inventory.sql)
- [`scripts/production/snapshot_financial_audit.sql`](../../scripts/production/snapshot_financial_audit.sql)

هر دو transaction صریح read-only دارند. schema/migration metadata، دسته‌های status و countهای
تجمیعی را خروجی می‌دهند، اما هیچ شناسهٔ رکورد کسب‌وکاری/کاربر یا payload حساس را خروجی نمی‌دهند.

`dev_migrations/` baseline دیتابیس تازه است و به‌هیچ‌وجه migration production نیست. مسیر امن:

1. operator یک backup قابل restore و یک snapshot ناشناس‌شده‌ی schema+data representative
   تهیه کند؛ دسترسی Codex/توسعه‌دهنده فقط به staging ایزوله باشد.
2. `django_migrations`، schema-only dump، extensionها، constraint/index/default/nullability و
   row-countهای بدون PII از snapshot ثبت شوند.
3. هر ۲۵ app نصب‌شده با state مدل فعلی map شود. جدول/ستون orphan یا drift به‌صورت صریح
   طبقه‌بندی شود؛ `--fake` یا `--fake-initial` کور ممنوع است.
4. migration graph استاندارد production از state واقعی ساخته شود. تغییرات مالی Float→Decimal
   باید expand/contract باشد: ستون shadow، گزارش NaN/Infinity/مقادیر کسری یا خارج range،
   backfill chunked بدون rounding خاموش، reconciliation با ledger/order/gateway، cutover و
   حذف ستون قدیمی در release بعدی.
5. migrationها حداقل دو بار روی clone تازه‌ی snapshot اجرا شوند؛ مدت lock، row count، constraint،
   aggregate مالی و قابلیت restart/rollback ثبت شود.
6. backup فوری قبل از rollout، maintenance plan و owner rollback تأیید شوند.
7. فقط پس از approval کتبی، ابتدا plan و سپس migration دقیق همان backend digest اجرا شود:

```sh
docker compose -f docker-compose.production.yml --profile operations run --rm migration-plan
docker compose -f docker-compose.production.yml run --rm backend python manage.py migrate --noinput
```

دستور دوم در وضعیت فعلی مجاز نیست؛ graph استاندارد production هنوز reconcile نشده است.

## ۵. deploy پس از باز شدن gateها

1. digestها و مسیر فایل‌های secret/TLS را در محیط operator تنظیم کنید.
2. `docker compose -f docker-compose.production.yml config --quiet` را اجرا کنید.
3. backup و migration procedure تأییدشده‌ی بخش قبل را اجرا کنید.
4. imageهای immutable را pull و stack را بالا بیاورید:

```sh
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml ps
```

5. `/livez` باید فقط process را نشان دهد و `/readyz` باید DB و Redis را بدون افشای جزئیات
   تأیید کند. سپس smoke flowهای OTP/login/logout، WebSocket ticket، cart/checkout، payment
   کنترل‌شده، profile و Analytics staff/owner اجرا شوند.
6. rollback کد فقط با بازگرداندن digest قبلی انجام می‌شود. rollback دیتابیس خودکار نیست و باید
   دقیقاً از plan تأییدشده/backup پیروی کند.

## ۶. schedule مدیریت‌شده

template قابل نسخه‌بندی در `scripts/cron/asoud-production.cron.example` است:

- هر دقیقه: `reconcile_stale_payments --limit 100`؛
- هر روز ساعت ۰۲:۱۵ تهران: rebuild پنجره‌ی ۷روزه‌ی daily metrics؛
- دوشنبه‌ها ساعت ۰۳:۳۰ تهران: training هر سه مدل با `--activate-if-better`.

`flock` از overlap روی host جلوگیری می‌کند و training علاوه بر آن Redis lock دارد. فایل log باید
`0640`، تحت logrotate و فاقد payload/credential باشد. بعد از اولین ماه، زمان‌بندی بر اساس مدت
واقعی job، حجم داده و freshness موردنیاز بازبینی می‌شود.

## ۷. کنترل‌های پس از deploy

- query parameter قدیمی `?token=` برای WebSocket رد می‌شود؛ فقط ticket یک‌بارمصرف ۶۰ثانیه‌ای.
- `X-Real-IP` فقط از subnet edge قابل اعتماد است؛ اگر CDN دیگری جلوی edge قرار گرفت، real-IP
  allowlist آن باید در Nginx تنظیم و تست spoofing دوباره اجرا شود.
- endpointهای rate/security diagnostics فقط staff هستند؛ health عمومی هیچ exception، نسخه،
  memory، disk یا نام dependency خراب را برنمی‌گرداند.
- media volume باید backup مستقل داشته باشد. ML artifact volume نیز پایدار است، اما artifact
  فقط بعد از ارزیابی command فعال می‌شود.
