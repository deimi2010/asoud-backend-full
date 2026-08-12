# گزارش اجرای گروه ۱ — زیرساخت و امنیت

تاریخ: ۲۲ تیر ۱۴۰۵ / ۱۳ ژوئیهٔ ۲۰۲۶

## نتیجهٔ صریح

بخش قابل‌اجرا و قابل‌آزمایش محلی گروه ۱ پیاده‌سازی و با PostgreSQL و Redis واقعی dev
اعتبارسنجی شده است. با این حال گروه ۱ از نظر عملیاتی production هنوز بسته نیست، چون دو
کار عمداً خارج از محیط محلی و در اختیار owner/operator باقی مانده است:

1. rotate/reissue و revoke واقعی همهٔ credentialهای در معرض و TLS؛
2. reconcile تاریخچهٔ migration با snapshot ناشناس‌شده و representative از production.

تا ارائهٔ مدرک هر دو مورد، commit/push حذف فایل‌های حساس، بازنویسی history، اجرای migration
روی production و deploy عمومی مجاز نیست. هیچ‌کدام از این عملیات در این اجرا انجام نشد.

## تغییرات انجام‌شده

### Auth و WebSocket

- روش فعال REST همان opaque DRF token با TTL مانده و implementation مردهٔ JWT حذف شده است.
- logout اکنون token سمت سرور را revoke می‌کند و Flutter قبل از پاک‌کردن session محلی آن را
  فراخوانی می‌کند.
- token بلندمدت دیگر در query string وب‌سوکت مرورگر قرار نمی‌گیرد. API یک ticket با عمر ۶۰
  ثانیه، یک‌بارمصرف و محدود به path صادر می‌کند؛ replay رد می‌شود.
- inactive-user و expiry در REST و WebSocket یکسان enforce می‌شوند.

### Rate limit، هویت درخواست و health

- rate limit حساس با Lua در Redis، به‌شکل atomic و configurable پیاده‌سازی شد؛ scopeهای حساس
  در خطای Redis fail-closed و public readها fail-open هستند.
- کلیدهای identity با HMAC ذخیره می‌شوند و IP فقط از proxy CIDR صریح و مورد اعتماد پذیرفته
  می‌شود؛ `X-Forwarded-For` کلاینت authoritative نیست.
- `/livez` فقط سلامت process و `/readyz` فقط آمادگی DB/cache را با پاسخ حداقلی منتشر می‌کنند.
  diagnosticهای جزئی فقط staff هستند.

### محاسبات مالی

- `Payment.amount`، `Wallet.balance` و `Wallet.Transaction.amount` از float به
  `Decimal(18,0)` با واحد canonical IRT منتقل شدند.
- validation، constraint، serializer و Flutter هیچ مسیر مالی مبتنی بر `double` ندارند و
  قیمت/مبلغ/وضعیت پرداخت همچنان server-owned است.
- migrationهای زیر فقط برای dev ساخته و روی دیتابیس محلی تازه اعمال شدند:
  - `dev_migrations/payment/0003_alter_payment_amount_and_more.py`
  - `dev_migrations/wallet/0002_alter_transaction_amount_alter_wallet_balance_and_more.py`
- این دو migration، migration امن production نیستند؛ تبدیل دادهٔ واقعی باید بعد از profiling
  و با الگوی expand/reconcile/contract در snapshot انجام شود.

### Docker و production topology

- تنها Dockerfile بکند چندمرحله‌ای است و targetهای `runtime`، `runtime-ml`،
  `runtime-dev-ml` و test دارد. هیچ `COPY .` ندارد و base با digest ثابت pin شده است.
- base نهایی بکند Alpine است. base قبلی Debian به‌علت CVEهای Critical/High بدون patch در
  `perl-base` کنار گذاشته شد؛ حذف اجباری کتابخانهٔ سیستمی انجام نشد. packaging toolهای build
  نیز در image نهایی وجود ندارند.
- target production شامل `dev_migrations/` نیست؛ ML به‌صورت dependency group جدا در
  `requirements-ml.txt`، dependencyهای سیستمی جدا و image جدا نگه داشته شده است.
- runtime با UID/GID ثابت 10001 و بدون root اجرا می‌شود؛ startup هیچ migrate یا seed خودکار
  انجام نمی‌دهد.
- `docker-compose.yml` استک محلی PostgreSQL، Redis، Daphne backend و Flutter web را با یک
  `docker compose up` بالا می‌آورد.
- `docker-compose.production.yml` مسیر canonical production است: edge TLS، backend ASGI،
  frontend و DB/Redis managed خارجی. فقط image referenceهای immutable از نوع digest می‌پذیرد.
- production settings فقط env یا secret file بیرون repo می‌خواند و مقدار یا مسیر secret را
  log نمی‌کند.
- Flutter runtime و edge test روی digest ثابت Nginx 1.30.3 هستند. فونت رسمی Cupertino که در
  graph ساخت استفاده می‌شد ولی bundle نشده بود اضافه شد.

### CI و dependency audit

- CI کل suite تعریف‌شدهٔ بکند، ML، migration drift، production security settings، production
  Compose، Nginx syntax و build targetهای core/ML را اجرا می‌کند.
- `pip-audit` برای core و ML و image scan برای core، ML و Flutter به gate تبدیل شدند. image
  scan هر finding سطح Critical/High را، مستقل از موجودبودن fix، باعث شکست build می‌کند.
- Click/Celery و PyJWT بدون مصرف runtime بعد از reference audit حذف شدند؛ finding وابسته به
  Click نیز با حذف مسیر مرده از dependency graph حذف شد.

## فایل‌ها و مسیرهای بازنشسته‌شده

- Docker/Compose موازی: `Dockerfile.complete*`، `Dockerfile.development`، `Dockerfile.prod`،
  `Dockerfile.production`، `docker-compose.dev*.yaml` و `docker-compose.prod.yaml`؛ دلیل:
  جایگزینی با یک Dockerfile و دو compose صریح local/production.
- deploy/validation قدیمی: اسکریپت‌های ریشه و `scripts/deployment`/`production-*` که به WSGI،
  compose یا فایل‌های غایب ارجاع داشتند؛ دلیل: جلوگیری از اجرای مسیر deployment متناقض.
- `.venv/` تراک‌شده: artifact محلی و platform-specific بود، نه source؛ dependencyها اکنون فقط
  از فایل‌های requirements نسخه‌بندی‌شده در build/test بازتولید می‌شوند.
- `apps/cart/tests/test_idor_fixes.py`: fixture و فیلدهای مالی/بانکی منسوخ آن حذف و پوشش واقعی‌اش
  در `apps/users/tests.py` و `apps/cart/tests/test_integrity.py` با contract فعلی جایگزین شد؛
  سناریوهای own، cross-user و anonymous سفارش صریحاً در suite باقی مانده‌اند.
- `apps/users/authentication.py`: framework بلااستفادهٔ JWT؛ روش auth فعال تک‌منبع شد.
- `config/middleware.py`: rate-limit غیراتمیک و غیرفعال قدیمی؛ با implementation Redis جایگزین شد.
- `apps/market/signals.py`: mutation ناامن و runtimeای `ALLOWED_HOSTS`؛ allowlist اکنون فقط از
  config صریح می‌آید.
- implementationهای موازی و قدیمی Analytics شامل dashboard/fraud/optimization/ML commandهای
  legacy؛ با مدل، service، API و commandهای تست‌شدهٔ فعلی جایگزین شدند، نه اینکه فیچر حذف شود.

## شواهد اجرای واقعی

| بررسی | نتیجه |
|---|---|
| backend روی PostgreSQL + Redis dev | 230/230 pass، صفر fail، صفر skip |
| Flutter tests | 133/133 pass |
| Flutter format | 324 فایل بررسی، صفر تغییر لازم |
| Flutter analyze | صفر error، صفر warning، 38 info |
| migration drift | `No changes detected` |
| production security checks | صفر issue |
| OpenAPI generation | exit code صفر؛ 112 warning و 652 inference error (بدهی باز، schema ناقص) |
| pip-audit core / ML | صفر vulnerability شناخته‌شده |
| pip dependency consistency | صفر requirement شکسته |
| runtime core image | 69 MB، 0 Critical/High/Medium/Low |
| runtime ML image | 178 MB، 0 Critical/High/Medium/Low |
| Flutter/Nginx image | 44 MB، 0 Critical/High، 2 Medium، 2 Low، 1 Unspecified؛ همگی فعلاً بدون fix |
| production compose | parse/config معتبر |
| production Nginx | syntax و TLS test معتبر |
| local Compose | هر چهار سرویس healthy |
| local smoke | `live=ok`، `ready=ready`، frontend HTTP 200 |
| OTP/WS/logout smoke | Redis واقعی، OTP local، ticket یک‌بارمصرف، replay reject و revoke موفق |

توضیح: اسکن‌های CVE فوق snapshot پایگاه دادهٔ scanner در زمان همین اجرا هستند و باید در CI
دائماً تکرار شوند؛ تضمین دائمی نبودن CVE نیستند.

## موارد باز و خارج از ادعای تکمیل

1. **Rotation و history cleanup:** هیچ مدرک rotation وجود ندارد. history/registry/cache نباید
   قبل از revoke پاک یا بازنویسی شوند.
2. **Migration production:** هیچ snapshot ناشناس‌شده ارائه نشده و هیچ migration روی production
   ساخته یا اجرا نشده است. baseline موجود صرفاً dev است.
3. **Deploy واقعی:** topology و config تست شده‌اند، اما deploy روی سرور، TLS واقعی، DB/Redis
   managed و providerهای واقعی تست نشده‌اند.
4. **OpenAPI legacy:** generation/validation exit code صفر دارد، اما اجرای تازهٔ
   `drf-spectacular` تعداد ۱۱۲ warning (۵۶ unique) و ۶۵۲ error (۱۴۶ unique) در inference
   serializer، path type و operation-id ثبت می‌کند. این‌ها crash/runtime error نیستند، ولی
   بخش‌هایی از schema را ناقص می‌کنند؛ بنابراین OpenAPI فعلی قرارداد کامل و قابل اتکای v1 نیست.
5. **Flutter lint:** ۳۸ مورد سطح info باقی است؛ صفر error/warning. بیشترشان deprecation مربوط به
   RadioGroup جدید هستند و در گروه کیفیت فرانت باید با تست رفتاری رفع شوند.
6. **فیچرهای گروه‌های بعدی:** Payment production، refund، reservation جدید، advertisement،
   affiliate، shipping، KYC، SMS تجاری و سایر گروه‌ها با این زیرساخت خودبه‌خود production-ready
   نشده‌اند و ادعای تکمیل آن‌ها در این گزارش وجود ندارد.

## مسیرهای مرجع

- طرح تأییدشده: `docs/current/GROUP_1_PRODUCTION_FOUNDATION_PLAN.md`
- runbook عملیات: `docs/current/GROUP_1_OPERATIONS_RUNBOOK.md`
- runtime محلی: `docker-compose.yml`
- runtime production: `docker-compose.production.yml`
- زمان‌بندی نمونه: `scripts/cron/asoud-production.cron.example`
