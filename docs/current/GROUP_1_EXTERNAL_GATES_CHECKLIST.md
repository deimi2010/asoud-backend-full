# Checklist دو gate بیرونی Group 1

تاریخ: ۲۳ تیر ۱۴۰۵ / ۱۴ ژوئیهٔ ۲۰۲۶
دامنه: عملیات owner/operator روی credentialها و snapshot production
وضعیت: هیچ دستور این سند روی production توسط Codex اجرا نشده است.

این سند دو gate باقی‌مانده را به evidence قابل بررسی تبدیل می‌کند. مقدار secret، DSN، دادهٔ
کاربر، authority پرداخت، token و private key نباید در ticket، terminal transcript، CI artifact
یا پاسخ به Codex قرار گیرد.

## Gate A — Rotation، revoke و پاک‌سازی exposure

### A0. توقف و inventory

- [ ] یک incident/change ticket با owner، زمان شروع، maintenance window و rollback owner بسازید؛
      فقط شناسه و زمان ثبت شود، نه مقدار credential.
- [ ] تا پایان revoke هیچ history rewrite، force-push، حذف registry/cache یا commit حذف فایل‌های
      حساس انجام ندهید. پاک‌کردن history جای revoke را نمی‌گیرد.
- [ ] همهٔ branch/tag/fork، release artifact، CI log/cache، registry layer، backup و cloneهایی را که
      ممکن است فایل‌های زیر را داشته باشند inventory کنید:
  - `.env.backup`
  - `.env.development`
  - `.env.production`
  - `data/nginx/ssl/privkey.pem`
  - `data/ssl/asoud.key`
  - `ssl/asoud.key`
  - certificateهای متناظر؛ certificate عمومی secret نیست، ولی private key متناظر compromise شده است.
- [ ] فایل `.env.example` فقط در صورتی آلوده محسوب شود که scanner مقدار غیر-placeholder گزارش کند؛
      template سالم نباید کورکورانه حذف شود.
- [ ] نام متغیرهای دیگری که در env تاریخی بوده‌اند، بدون نمایش مقدار، استخراج و به inventory اضافه
      شوند. هر credential ناشناخته تا تعیین owner و مصرف‌کننده exposed فرض شود.

### A1. فهرست قطعی credentialها

| مورد | اقدام الزامی | اثر cutover |
|---|---|---|
| `DJANGO_SECRET_KEY` | کلید مستقل و کاملاً تازه در secret manager | session/cookie و لینک‌های امضاشدهٔ قبلی نامعتبر می‌شوند |
| `ASOUD_RATE_LIMIT_KEY_SECRET` | کلید HMAC مستقل؛ fallback به Django key ممنوع | counterهای قدیمی دیگر قابل آدرس‌دهی نیستند و با TTL حذف می‌شوند |
| PostgreSQL app login | ترجیحاً login role تازه با grant حداقلی؛ سپس revoke role/password قدیم | backend و migration operator باید جداگانه تست شوند |
| Redis credential/URL | ACL user یا instance/logical DB تازه؛ credential قدیم revoke شود | cache، OTP، channel state، WS ticket و rate counter موقت از نو شروع می‌شوند |
| `SMS_API` | API key تازه از provider؛ key قدیمی revoke | فقط OTP واقعی تست شود؛ این rotation مجوز فعال‌کردن SMS تجاری نیست |
| `ZARINPAL_MERCHANT_ID` | از provider درخواست reissue/revoke یا تأیید رسمی non-secret بودن شود | یک پرداخت sandbox/کنترل‌شده باید با credential مقصد pass شود |
| TLS private key/certificate | private key تازه ساخته و certificate تازه issue شود؛ certificate قبلی revoke | edge باید chain، hostname و expiry تازه را ارائه کند |
| Git/CI credential | PAT، deploy key، webhook secret و CI runner token در صورت وجود rotate | workflow و checkout/publish با identity تازه تست شود |
| Registry credential | robot token/password و signing key در صورت وجود rotate | push/pull digest تازه تست و credential قدیم رد شود |
| Server/cloud access | SSH key، cloud API، DNS/CDN/ACME token در صورت وجود در env/history rotate | دسترسی قدیمی حذف و audit log provider بررسی شود |
| سایر providerها | object storage، SMTP، monitoring/error tracking فقط اگر در env/history وجود داشته‌اند | positive/negative test provider-specific |

نکتهٔ Zarinpal: کد فعلی فقط merchant identifier مصرف می‌کند. اگر provider آن را secret یا قابل
rotation نمی‌داند، چیزی جعل نشود؛ پاسخ رسمی provider، scope واقعی credential و نتیجهٔ incident
review به‌عنوان evidence ثبت شود.

### A2. ترتیب صحیح ایجاد و cutover

ترتیب زیر وابستگی را کم می‌کند. «ایجاد» credential تازه قبل از «revoke» قدیمی انجام می‌شود، مگر
provider overlap را ممنوع کند که در آن صورت maintenance window لازم است.

1. [ ] ابتدا accessهای با blast radius بالا را آماده کنید: Git/CI، registry، deploy/SSH، cloud،
       DNS/CDN/ACME. identity تازه least-privilege باشد.
2. [ ] PostgreSQL login تازه را بسازید و فقط `CONNECT`، `USAGE` و مجوزهای لازم app را از یک role
       گروهی بگیرد؛ app هرگز owner/superuser نباشد. اتصال TLS و یک transaction read-only و یک
       write کنترل‌شده در staging تست شود.
3. [ ] Redis ACL/endpoint تازه را آماده کنید. به admin/config/flush دسترسی ندهید و command set واقعی
       Cache، Channels، Lua rate limit و WS ticket را در staging تست کنید.
4. [ ] SMS key و credential پرداخت تازه را از provider بگیرید و positive test staging/sandbox بزنید.
5. [ ] private key تازهٔ TLS را روی host/secret manager امن ایجاد و certificate تازه issue کنید؛
       private key هرگز از مسیر امن خارج نشود.
6. [ ] `DJANGO_SECRET_KEY` و `ASOUD_RATE_LIMIT_KEY_SECRET` تازه و مستقل تولید و فقط در secret
       store ثبت کنید.
7. [ ] Compose را با path فایل‌های تازه و image digest تأییدشده parse کنید؛ هیچ secret به‌صورت
       environment dump یا command-line argument قرار نگیرد.
8. [ ] ابتدا staging را با مجموعهٔ کاملاً تازه بالا بیاورید و همهٔ smoke testهای A3 را اجرا کنید.
9. [ ] در maintenance/canary production، backend را با DB/Redis/SMS/payment/Django/rate key تازه
       و edge را با TLS تازه cutover کنید. credential قدیمی هنوز فقط در overlap کوتاه provider معتبر است.
10. [ ] بعد از observation موفق، همهٔ credentialهای قدیمی را revoke کنید و از یک client ایزوله
        ثابت کنید credential قدیمی fail و credential تازه pass می‌شود.

### A3. smoke test قبل از revoke

- [ ] `docker compose -f docker-compose.production.yml config --quiet` بدون نمایش config کامل pass.
- [ ] backend با user غیر-root بالا بیاید؛ `/livez` و `/readyz` پاسخ مورد انتظار بدهند.
- [ ] اتصال app به PostgreSQL و Redis TLS pass؛ هیچ port دیتابیس/Redis عمومی نشده باشد.
- [ ] OTP واقعی برای شمارهٔ تست سازمانی ارسال و یک‌بار مصرف شود؛ OTP در log/ticket ثبت نشود.
- [ ] login جدید token قبلی همان کاربر را طبق single-session policy باطل کند.
- [ ] WS ticket صادر، یک بار مصرف و replay آن رد شود؛ `?token=` قدیمی رد شود.
- [ ] logout سمت سرور token را revoke کند.
- [ ] payment فقط با sandbox یا تراکنش کنترل‌شده و مبلغ server-owned تست شود؛ authority/reference گزارش نشود.
- [ ] TLS با hostname، chain و expiry درست ارائه شود؛ فقط fingerprint عمومی certificate قابل ثبت است.
- [ ] logهای edge/app/CI برای secret/token/OTP scan شوند و finding صفر باشد.

### A4. invalidate کردن state قابل سوءاستفاده

چون credential دیتابیس قبلاً exposed بوده، صرف تغییر password تضمین نمی‌کند tokenهای ذخیره‌شده
قبلاً کپی نشده باشند. پس از cutover موفق و در maintenance window:

- [ ] همهٔ DRF tokenها revoke و همهٔ Django sessionها حذف شوند؛ کاربران دوباره login می‌کنند.
- [ ] `user.pin` و `user.pin_expiry` legacy برای تمام کاربران پاک شود.
- [ ] Redis ترجیحاً به logical DB/instance تازه و خالی cutover شود. اگر همان Redis باقی می‌ماند،
      فقط پس از اثبات dedicated بودن logical DB، state موقت app purge شود. `FLUSHALL` و `KEYS *`
      ممنوع است؛ DB یا namespace مشترک نباید پاک شود.
- [ ] حداقل namespaceهای موقت شناخته‌شده منقضی/پاک شوند: Django cache با prefix `asoud`،
      `auth:otp:*` زیر همان cache prefix، `asoud:ws-ticket:v1:*`، `asoud:rate:v1:*` و channel
      state مربوط به deployment قبلی.

اجرای revoke session/token یک write آگاهانهٔ production است و باید count قبل/بعد و transaction
موفق ثبت کند، نه مقدار token. استفاده از ORM همان backend digest تأییدشده از SQL خام امن‌تر است.

پس از backup، cutover کلیدهای تازه و شروع maintenance window، operator می‌تواند دستور زیر را روی
همان digest تأییدشده اجرا کند. این دستور فقط count تجمیعی چاپ می‌کند، تمام تغییرها را در یک
transaction انجام می‌دهد و در صورت خطا rollback می‌شود. قبل از اجرا مطمئن شوید `backend` به
production مورد نظر وصل است؛ اجرای آن روی مقصد اشتباه نیز همهٔ session/tokenهای همان مقصد را
باطل می‌کند.

```sh
docker compose -f docker-compose.production.yml run --rm -T backend \
  python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models import Q
from rest_framework.authtoken.models import Token

User = get_user_model()
with transaction.atomic():
    token_count = Token.objects.count()
    session_count = Session.objects.count()
    legacy_pin_count = User.objects.filter(
        Q(pin__isnull=False) | Q(pin_expiry__isnull=False)
    ).count()
    Token.objects.all().delete()
    Session.objects.all().delete()
    User.objects.filter(
        Q(pin__isnull=False) | Q(pin_expiry__isnull=False)
    ).update(pin=None, pin_expiry=None)

print(f"revoked_drf_tokens={token_count}")
print(f"deleted_django_sessions={session_count}")
print(f"cleared_legacy_pin_rows={legacy_pin_count}")
PY
```

بعد از دستور، یک token و session قبل از maintenance باید `401`/نامعتبر شوند و login تازه باید
token تازه بسازد. عددهای خروجی evidence هستند؛ stdout کامل app یا database log ارسال نشود.

### A5. revoke، history rewrite و purge

- [ ] password/role قدیمی DB disable/revoke و connectionهای قدیمی terminate شوند.
- [ ] Redis ACL user/password قدیمی revoke شود.
- [ ] SMS/payment/Git/CI/registry/SSH/cloud/DNS credentialهای قدیمی revoke شوند.
- [ ] certificate قبلی نزد CA revoke و TLS تازه از بیرون شبکه verify شود.
- [ ] audit log همهٔ providerها از زمان اولین commit آلوده تا revoke بررسی و رویداد مشکوک جداگانه
      incident-response شود.
- [ ] فقط اکنون mirror clone آفلاین گرفته، branch/tagها inventory و history با `git filter-repo`
      برای envها و private-key pathهای آلوده بازنویسی شود.
- [ ] scanner تمام refs بازنویسی‌شده را بدون چاپ value اسکن کند و finding صفر باشد.
- [ ] force-push در maintenance window؛ branch protection موقت و کنترل‌شده مدیریت شود.
- [ ] همهٔ cloneها حذف و re-clone شوند؛ clone قدیمی اجازهٔ push نداشته باشد.
- [ ] image/layer قدیمی registry، CI artifact/cache و runner workspace purge شوند؛ imageها از commit
      پاک rebuild، scan و با digest تازه منتشر شوند.
- [ ] fork یا cache خارج از کنترل به‌عنوان residual exposure ثبت شود؛ revoke قبلی کنترل اصلی آن است.

دستور پایهٔ history rewrite برای pathهای قطعی فعلی در یک mirror clone تازه به‌شکل زیر است. URL
نباید PAT/password درون خودش داشته باشد. اگر secret scanner path دیگری پیدا کرد، قبل از اجرا یک
`--path` مستقل برای همان path اضافه کنید؛ `.env.example` فقط با finding واقعی اضافه شود.

```sh
git clone --mirror "$REPO_URL_WITHOUT_EMBEDDED_CREDENTIAL" asoud-cleanup.git
cd asoud-cleanup.git
git show-ref > ../refs-before-rewrite.txt

git filter-repo --force --invert-paths \
  --path .env.backup \
  --path .env.development \
  --path .env.production \
  --path data/nginx/ssl/privkey.pem \
  --path data/ssl/asoud.key \
  --path ssl/asoud.key
```

سپس scanner تأییدشده باید **تمام refs** این mirror را با redaction فعال اسکن کند. فقط وقتی finding
صفر، backup mirror موجود، فهرست refs بررسی و approval کتبی ثبت شد، remote پاک با SSH/deploy key
تازه افزوده و بازنویسی منتشر شود:

```sh
git remote add clean-origin "$CLEAN_REMOTE_URL_WITHOUT_EMBEDDED_CREDENTIAL"
git push --force --mirror clean-origin
```

`--mirror` و `--force` تمام branch/tag/refهای مقصد را بازنویسی می‌کنند؛ این دستور روی clone کاری
یا بدون maintenance/approval اجرا نشود. پس از push، protectionها برگردند و هر collaborator از
fresh clone ادامه دهد؛ merge کردن clone قدیمی می‌تواند history آلوده را برگرداند.

### A6. evidence قابل ارسال به Codex — بدون مقدار حساس

برای هر ردیف فقط این فیلدها را گزارش کنید:

```text
credential_kind:
provider_or_scope:
owner:
new_issued_at_utc:
cutover_at_utc:
old_revoked_at_utc:
new_positive_test: pass|fail
old_negative_test: pass|fail|provider_not_supported
provider_audit_review: clean|incident_opened
notes_without_values:
```

و یک summary:

```text
all_runtime_credentials_rotated: yes|no
all_old_credentials_revoked: yes|no
drf_tokens_and_sessions_invalidated: yes|no
legacy_pin_state_cleared: yes|no
tls_reissued_and_old_certificate_revoked: yes|no
history_rewritten_after_revoke: yes|no
all_refs_secret_scan_findings: <count>
registry_ci_runner_caches_purged: yes|no
fresh_clone_build_and_tests: pass|fail
```

## Gate B — Migration reconciliation روی snapshot

### B0. backup، restore و anonymization

- [ ] PostgreSQL server major/minor و extensionها ثبت شوند؛ مقدار host/user/DSN گزارش نشود.
- [ ] backup قابل restore قبل از هر کار تهیه شود. password در command line یا process list نباشد؛
      از `PGSERVICE`/`PGPASSFILE` با permission `0600` یا secret manager استفاده شود.
- [ ] برای snapshot سازگار، custom-format dump و در صورت وجود write هم‌زمان گزینهٔ
      `--serializable-deferrable` استفاده شود. archive شامل PII است و فقط encrypted و owner-side بماند.
- [ ] restore drill روی PostgreSQL هم‌نسخه یا نسخهٔ پشتیبانی‌شده pass و hash archive ثبت شود.
- [ ] anonymization فقط روی clone انجام شود، نه production. UUID/FK، status، timestamp و توزیع
      مبلغ لازم برای reconciliation حفظ شوند، ولی این داده‌ها حذف/توکن‌سازی شوند:
  - mobile/email/password hash، national code، address، birth date؛
  - card/account/IBAN/full name و اطلاعات بانکی؛
  - IP/user-agent؛
  - chat/comment/notification/SMS text، file/media path و payload؛
  - payment `verification_data` و هر provider payload/reference قابل شناسایی؛
  - market contact/location یا هر متن آزاد دارای PII.
- [ ] uniqueness با tokenization deterministic حفظ شود؛ مقدار ساختگی نباید با دادهٔ واقعی قابل
      برگشت باشد. mapping anonymization جداگانه ذخیره نشود.
- [ ] snapshot ناشناس در شبکهٔ ایزوله، بدون outbound provider access و با credential مستقل restore شود.

نمونهٔ command shape؛ مقادیر اتصال از service file خوانده می‌شوند:

```sh
PGSERVICE=production_backup pg_dump \
  --format=custom \
  --serializable-deferrable \
  --no-owner \
  --no-acl \
  --file=/secure/encrypted/asoud-production.snapshot

PGSERVICE=snapshot_admin pg_restore \
  --exit-on-error \
  --no-owner \
  --no-acl \
  --dbname=asoud_snapshot_isolated \
  /secure/encrypted/asoud-production.snapshot
```

### B1. inventory read-only دقیق

دو script نسخه‌بندی‌شدهٔ زیر روی snapshot anonymized اجرا شوند:

- `scripts/production/snapshot_inventory.sql`
- `scripts/production/snapshot_financial_audit.sql`

هر دو با `BEGIN ... READ ONLY` اجرا می‌شوند. خروجی شامل metadata ساختاری، نام/statusهای
دسته‌بندی‌شده و countهای تجمیعی است؛ هیچ شناسهٔ رکورد کسب‌وکاری/کاربر، authority، token یا
payload خام را select نمی‌کنند:

```sh
PGSERVICE=snapshot_audit psql \
  -X \
  --set=ON_ERROR_STOP=1 \
  --file=scripts/production/snapshot_inventory.sql \
  > snapshot-inventory.txt

PGSERVICE=snapshot_audit psql \
  -X \
  --set=ON_ERROR_STOP=1 \
  --file=scripts/production/snapshot_financial_audit.sql \
  > snapshot-financial-audit.txt

PGSERVICE=snapshot_audit pg_dump \
  --schema-only \
  --no-owner \
  --no-acl \
  --file=snapshot-schema.sql
```

artifactها internal محسوب شوند. پیش از اشتراک `snapshot-schema.sql` باید function/default/comment
برای literal حساس scan شود؛ در مرحلهٔ اول فقط hash و summary فرستاده شود.

### B2. چه چیزهایی باید از inventory معلوم شود

- [ ] `transaction_read_only=on` و exit code هر دو script صفر است.
- [ ] نسخهٔ server، extensionها، تمام schema/table/column/type/null/default/identity ثبت شده‌اند.
- [ ] row count دقیق همهٔ tableها و size آنها ثبت شده است.
- [ ] constraint، index، trigger، RLS policy و sequenceها ثبت شده‌اند.
- [ ] invalid/unready index و unvalidated constraintها صفر یا تک‌به‌تک طبقه‌بندی شده‌اند.
- [ ] orphan count تمام FKها و duplicate count تمام PK/Unique constraintها صفر یا دارای anomaly ID است.
- [ ] `django_migrations` وجود/عدم وجود، تمام `app/name/applied`ها و duplicate entry count ثبت شده است.
- [ ] وضعیت این ۲۵ app پروژه جداگانه map شده است:
  `advertise`, `affiliate`, `analytics`, `base`, `cart`, `category`, `chat`, `comment`,
  `core`, `discount`, `flutter`, `gateway`, `information`, `market`, `market_subdomain`,
  `notification`, `payment`, `price_inquiry`, `product`, `referral`, `region`, `reserve`,
  `sms`, `users`, `wallet`.
- [ ] migrationهای built-in Django و packageها نیز در history باقی می‌مانند و حذف/rename نمی‌شوند.

برای هر table/model یک سطر reconciliation matrix بسازید:

```text
app/model:
snapshot_table:
snapshot_history_state:
target_model_state:
classification: exact|additive|transform_required|legacy_orphan|decision_required
row_count_before:
schema_differences_without_values:
data_anomaly_counts:
proposed_action: baseline|add|backfill|quarantine|retain|archive|product_decision
```

وجود table به‌تنهایی مجوز `--fake-initial` نیست. type، nullability، default، index، constraint،
column set و migration dependency باید کامل match شوند؛ fake کور ممنوع است.

### B3. بررسی‌های مالی اجباری

خروجی `snapshot_financial_audit.sql` باید حداقل این موارد را تعیین کند:

- [ ] type واقعی `payment_payment.amount`, `wallet_wallet.balance` و
      `wallet_transaction.amount`: float، numeric قدیمی یا Decimal مقصد.
- [ ] تعداد NaN/Infinity، null، صفر/منفی، مقدار کسری IRT و خارج از `Decimal(18,0)`.
- [ ] duplicate authority/transaction ID زَرین‌پال، payment بدون gateway row و تناقض status/reference.
- [ ] wallet تکراری برای user، transaction action ناشناخته، مالک source ناسازگار و self-transfer.
- [ ] اختلاف balance با ledger موجود. اختلاف به‌تنهایی corruption نیست؛ ممکن است opening balance
      legacy باشد و باید منبع آن مشخص شود، نه اینکه خودکار balance بازنویسی شود.
- [ ] وجود frozen totals سفارش، arithmetic آنها، item snapshot و fractional IRT.
- [ ] payment/order amount mismatch، paid order بدون completed gateway payment و چند completed
      payment برای یک order.
- [ ] وضعیت جدول legacy `gateway` و duplicate invoice/reference/track ID.

هر مقدار fractional، non-finite یا mismatch به quarantine report با شناسهٔ داخلی owner-side می‌رود؛
Codex فقط count هر category را لازم دارد. rounding یا حذف خودکار ممنوع است.

### B4. طراحی graph بعد از inventory — هنوز بدون اجرای production

- [ ] graph استاندارد production از state واقعی snapshot طراحی شود؛ `dev_migrations/` فقط target
      مدل فعلی را نشان می‌دهد و baseline production نیست.
- [ ] هر transform مالی expand/backfill/verify/cutover/contract باشد. ستون قدیمی در همان release
      اول drop نشود.
- [ ] backfill chunked، idempotent، قابل resume و دارای quarantine count باشد.
- [ ] `RunPython` فقط historical model از `apps.get_model()` استفاده کند و dependency همهٔ appهای
      درگیر صریح باشد.
- [ ] constraint سنگین ابتدا در صورت نیاز `NOT VALID` اضافه و بعد جداگانه validate شود؛ lock budget
      ثبت شود.
- [ ] migration هیچ provider call، network access یا client-authoritative financial write نداشته باشد.

### B5. rehearsal و معیار pass

- [ ] دو restore مستقل از snapshot anonymized ساخته شود؛ هر rehearsal از clone تازه شروع شود.
- [ ] preflight روی snapshot صحیح pass و روی schema دست‌کاری‌شدهٔ آزمایشی عمداً fail کند.
- [ ] migration candidate دو بار با نتیجهٔ یکسان اجرا شود؛ rerun backfill تغییر اضافه ایجاد نکند.
- [ ] قبل/بعد: row count، orphan/duplicate/anomaly count و fingerprint مالی مقایسه شود.
- [ ] lock duration، statement duration، disk growth و بزرگ‌ترین table ثبت شود.
- [ ] `showmigrations --plan`, `migrate --plan` و `makemigrations --check --dry-run` clean باشند.
- [ ] fresh empty DB نیز از صفر تا head migrate شود؛ فقط snapshot path کافی نیست.
- [ ] test suite کامل backend روی schema migrated pass شود.
- [ ] rollback app image و restore database از backup عملاً rehearsal شود.
- [ ] تا approval کتبی owner/DBA/backup owner هیچ migration روی production اجرا نشود.

### B6. evidence قابل ارسال به Codex — بدون دادهٔ حساس

```text
postgres_server_version:
snapshot_captured_at_utc:
snapshot_restore_test: pass|fail
snapshot_anonymization_review: pass|fail
outbound_network_disabled: yes|no
inventory_script_exit_code:
financial_script_exit_code:
schema_artifact_sha256:
django_migrations_present: yes|no
project_apps_in_history: <count>/25
duplicate_migration_entries: <count>
invalid_or_unready_indexes: <count>
unvalidated_constraints: <count>
fk_orphan_categories_nonzero: <count>
unique_duplicate_categories_nonzero: <count>
financial_anomaly_counts:
  non_finite:
  non_positive:
  fractional_irt:
  outside_decimal_18_0:
  duplicate_gateway_identifiers:
  payment_order_mismatch:
  wallet_ledger_difference:
  order_snapshot_mismatch:
schema_difference_matrix_attached_and_sanitized: yes|no
rehearsal_1: pass|fail|not_started
rehearsal_2: pass|fail|not_started
fresh_database_migration: pass|fail|not_started
backup_restore_drill: pass|fail
```

اگر هر shape در financial script با `structurally incompatible` گزارش شد، این failure ابزار نیست؛
همان اختلاف schema یکی از خروجی‌های اصلی reconciliation است. inventory ستون‌های همان table را
بفرستید و قبل از هر migration متوقف بمانید.

## معیار عبور به Group 2

ورود به Group 2 فقط پس از این چهار تأیید انجام می‌شود:

1. همهٔ credentialهای exposed cutover و credentialهای قدیمی revoke شده‌اند؛
2. history/cache/registry پس از revoke پاک و fresh-clone test شده است؛
3. snapshot anonymized و inventory کامل بدون دادهٔ حساس ارائه شده و graph production بر اساس آن
   طراحی/دو بار rehearsal شده است؛
4. restore/rollback evidence و approval owner/DBA وجود دارد.

این checklist به‌تنهایی مجوز deploy یا migration production نیست.
