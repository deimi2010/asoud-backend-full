# پلن گروه ۱ — پایهٔ امن و قابل استقرار Production

وضعیت سند: **تأییدشده و در حال اجرا؛ بخش‌های وابسته به production در انتظار rotation و snapshot هستند**
تاریخ: ۲۲ تیر ۱۴۰۵ / ۱۳ ژوئیهٔ ۲۰۲۶
دامنه: backend، بخش لازم از Flutter، migration/data، Docker/CI/CD و عملیات امنیتی مرتبط با انتشار v1

وضعیت عملیاتی و gateهای باقیمانده در `GROUP_1_OPERATIONS_RUNBOOK.md` ثبت می‌شوند.

## ۱. هدف و خط قرمزها

خروجی این گروه باید یک پایهٔ production واقعی بسازد که روی آن بتوان بقیهٔ فیچرهای v1 را کامل کرد:

1. تمام credentialها و کلیدهای در معرض، از جمله TLS، rotate/reissue شوند؛ سپس history، registry و cacheهای آلوده پاک شوند.
2. تاریخچهٔ migration با schema و دادهٔ واقعی production برای همهٔ appها reconcile شود؛ هیچ migration بر اساس فرض «دیتابیس خالی است» روی production اجرا نشود.
3. فقط یک مسیر canonical برای build و deploy production باقی بماند و HTTP و WebSocket را با ASGI سرو کند.
4. محاسبات Payment و Wallet از `float` خارج شوند و exact Decimal، constraint و reconciliation مالی داشته باشند.
5. finding فعلی Click و auditهای dependency/image برطرف و به CI تبدیل به gate شوند.
6. rate limiting واقعاً atomic، قابل تنظیم و قابل مشاهده باشد؛ health عمومی حداقلی و غیرنشت‌دهنده باشد.
7. auth دوگانه نشود: مسیر فعال به‌صورت اصولی کامل و کد JWT مرده حذف شود.

خط قرمزها:

- هیچ secret یا key در stdout، log، patch، artifact یا گزارش چاپ نمی‌شود.
- قبل از تأیید rotation همهٔ موارد در معرض، هیچ untrack، commit/push مربوط به حذف secret، rewrite تاریخچه یا حذف registry انجام نمی‌شود.
- هیچ اتصال یا write به production بدون دسترسی صریح جداگانه و اجرای runbook تأییدشده انجام نمی‌شود.
- همهٔ آزمایش migration ابتدا روی snapshot امن و staging انجام می‌شوند؛ production آخرین gate است.
- قیمت، مبلغ نهایی، وضعیت پرداخت و موجودی از payload کلاینت authoritative نمی‌شوند.
- این گروه هیچ فیچر v1 را حذف، پنهان یا fail-closed نمی‌کند. حذف فقط برای implementationهای واقعاً dead و بدون مصرف‌کننده است و پیش از آن reference audit اجباری است.

## ۲. مبنای واقعی پلن

این موارد از اجرای واقعی یا بررسی کد فعلی آمده‌اند:

- baseline فعلی backend: **۲۱۲/۲۱۲ تست pass** روی PostgreSQL و Redis محلی.
- baseline فعلی Flutter: **۱۲۸/۱۲۸ تست pass**؛ analyze دارای صفر error و صفر warning و ۳۸ info است.
- local Compose سالم است، اما `docker-compose.production.yml` به‌علت include فایل monitoring غایب parse نمی‌شود.
- production compose از `Dockerfile.prod` استفاده می‌کند؛ این Dockerfile هنوز `COPY .` دارد. مسیر systemd موجود WSGI است و WebSocket را سرو نمی‌کند.
- standard migration graph برای ۲۱ app مدل‌دار initial migration پیشنهاد می‌کند. دامنهٔ کامل reconcile، هر ۲۵ migration module نصب‌شده است: `advertise`، `affiliate`، `analytics`، `base`، `cart`، `category`، `chat`، `comment`، `core`، `discount`، `flutter`، `gateway`، `information`، `market`، `market_subdomain`، `notification`، `payment`، `price_inquiry`، `product`، `referral`، `region`، `reserve`، `sms`، `users` و `wallet`.
- `dev_migrations/` فقط baseline دیتابیس تازهٔ dev است و evidence معتبر برای production نیست.
- `Payment.amount` و `Wallet.balance` از نوع Float هستند؛ ledger مربوط به Wallet و totals جدید Cart/Order از Decimal سه‌رقم اعشار استفاده می‌کنند. gateway مبلغ whole IRT می‌خواهد.
- auth واقعی `ExpiringTokenAuthentication` و DRF Token با TTL سی‌روزه است. `JWTAuthentication` و helperهای blacklist/session/lockout در `apps/users/authentication.py` به مسیر runtime وصل نیستند.
- logout فعلی Flutter فقط token محلی را پاک می‌کند؛ revoke سمت سرور وجود ندارد.
- browser WebSocket token بلندمدت را در `?token=` می‌فرستد.
- DRF throttle فعال است، اما middleware سفارشی rate-limit غیرفعال و non-atomic است؛ `RateLimitView.is_rate_limited()` همیشه false برمی‌گرداند و audit وضعیت گمراه‌کننده دارد.
- health عمومی جزئیات DB/cache، exception خام، memory، disk و version را برمی‌گرداند.
- audit محلی `requirements.txt` یک finding برای `click==8.1.8` با شناسهٔ `PYSEC-2026-2132` و نسخهٔ fix اعلام‌شدهٔ `8.3.3` نشان داده؛ ML audit فعلی clean است. PyPI اکنون نسخه‌های جدیدتری هم دارد، ولی برای این fix کم‌ریسک‌ترین candidate ابتدا 8.3.3 است.
- CI فعلی فقط subset قدیمی ۱۳۷تایی را اجرا می‌کند و ML و suiteهای جدید Chat/Analytics/Product را کامل پوشش نمی‌دهد.
- worktree فعلی بسیار dirty است و حذف فایل‌های حساس staged شده، اما مدرکی از rotation وجود ندارد؛ بنابراین push/commit آن حذف‌ها فعلاً ممنوع است.

## ۳. تصمیم‌های پیشنهادی

### ۳.۱ Auth

**پیشنهاد:** برای v1، `ExpiringTokenAuthentication` فعلی به‌عنوان تنها روش REST حفظ و کامل شود و framework بلااستفادهٔ JWT حذف شود.

دلیل:

- Flutter، REST و WebSocket فعلی همگی با DRF Token کار می‌کنند.
- فعال‌کردن JWT به‌معنی ساخت refresh rotation، revocation، logout، مهاجرت کلاینت و پشتیبانی هم‌زمان دو auth model است، بدون اینکه نیاز محصولی اثبات‌شده‌ای حل کند.
- helperهای JWT فعلی integration و test production ندارند؛ فعال‌کردن آن‌ها patch امن محسوب نمی‌شود.

تکمیل لازم برای token فعلی:

- logout واقعی سمت سرور؛
- enforce یکسان expiry و inactive-user در REST و WebSocket؛
- ticket کوتاه‌عمر و یک‌بارمصرف برای WebSocket؛
- تست replay، revoke و log redaction.

تصمیم محصولی باقی‌مانده: آیا v1 عمداً فقط **یک session فعال به‌ازای هر کاربر** دارد؟ پیشنهاد برای v1 «بله» است. در این حالت login جدید token قبلی را باطل می‌کند. اگر multi-device لازم باشد، به‌جای روشن‌کردن JWT مرده، یک مدل opaque session مستقل و hash‌شده طراحی می‌شود و این تصمیم migration جدیدی به scope اضافه می‌کند.

### ۳.۲ واحد پول و precision

**پیشنهاد:** واحد canonical کل سامانه `IRT` و تمام مبلغ‌های قابل پرداخت whole IRT باشند؛ در نتیجه فیلدهای مالی canonical `DecimalField(..., decimal_places=0)` و JSON آن‌ها string باشد.

این انتخاب با validation فعلی gateway و checkout سازگار است، ولی با امکان `0.001` در Wallet فعلی تعارض دارد. بنابراین تا Product Owner این تصمیم را تأیید نکند، migration مالی نوشته نمی‌شود.

گزینهٔ جایگزین، اگر واقعاً مبلغ کسری یک نیاز کسب‌وکار است: `DecimalField(max_digits=18, decimal_places=3)` در کل domain مالی، همراه با تبدیل صریح و بدون float در مرز gateway. ترکیب scaleهای متفاوت بدون policy واحد پذیرفته نیست.

در هر دو حالت:

- order/payment amount از state سمت سرور resolve می‌شود؛
- مبلغ top-up فقط «درخواست کاربر» است و server آن را با min/max و currency policy resolve و freeze می‌کند؛
- client هرگز balance، payable total یا payment status را set نمی‌کند.

### ۳.۳ Production topology

**پیشنهاد:** image immutable در CI ساخته، scan و با digest منتشر شود؛ سرور فقط همان digest را pull کند و روی سرور `git pull` یا build انجام نشود.

یک compose canonical این سرویس‌ها را تعریف می‌کند:

- `edge`: Nginx با TLS، proxy امن و route کردن `/api/` و `/ws/` به backend و `/` به frontend؛
- `backend`: Daphne/ASGI از image غیر-root؛
- `frontend`: Flutter web release به‌صورت image read-only؛
- `migrate`: job یک‌بارمصرف از همان digest backend؛
- `scheduler`: اجرای versioned management-command schedule با lock و بدون overlap؛
- DB و Redis: ترجیحاً managed/external؛ اگر self-hosted تأیید شود، در همان compose و فقط با profile صریح، volume پایدار، backup و بدون publish port.

Celery worker/beat فعلی در topology نهایی صرفاً به‌خاطر وجود compose قدیمی حفظ نمی‌شود: پروژه Celery app قابل اتکایی ندارد. این حذف فیچر نیست؛ management commandهای واقعی با scheduler نسخه‌بندی‌شده اجرا می‌شوند. اگر بعداً queue واقعی لازم شد، در گروه مربوط با مدل delivery/retry خودش طراحی می‌شود.

### ۳.۴ Rate limiting

**پیشنهاد:** یک throttle مرکزی مبتنی بر Redis و Lua atomic ساخته شود که همهٔ keyهای یک درخواست را قبل از increment بررسی کند. rateها از settings/env قابل تنظیم هستند، اما default نسخه‌بندی‌شده دارند.

default پیشنهادی اولیه:

| Scope | محدودیت پیشنهادی |
|---|---:|
| OTP create | ۵ در ساعت برای mobile + ۲۰ در ساعت برای IP معتبر |
| OTP verify | حداکثر ۵ تلاش برای هر OTP + ۲۰ در ساعت برای mobile + ۶۰ در ساعت برای IP |
| WebSocket ticket | ۲۰ در دقیقه برای user |
| Chat member mutations | ۲۰ در ساعت برای user |
| Payment create / wallet mutation | ۱۰ در دقیقه برای user، علاوه بر idempotency |
| Upload | ۶۰ در ساعت برای user |
| anonymous read | ۱۲۰ در دقیقه برای IP |
| authenticated read | ۶۰۰ در دقیقه برای user |

این اعداد configurable هستند چون ترافیک واقعی، رفتار SMS provider و ساختار CDN هنوز معلوم نیست؛ تغییرشان نیاز به deploy کد ندارد، اما تغییر production باید audit trail داشته باشد.

برای OTP، payment mutation، wallet mutation، WS ticket و operationهای امنیتی، خطای Redis باید fail-safe باشد: پاسخ stable `503 rate_limit_unavailable`، نه عبور بدون کنترل. برای read عمومی، policy پیشنهادی availability-first با limit لایهٔ edge است. این تفکیک صریح تست و مستند می‌شود.

## ۴. مدل داده و migrationهای پیشنهادی

### ۴.۱ Reconciled production migration graph

تا پیش از snapshot، هیچ migration نهایی قابل نوشتن نیست. خروجی مورد انتظار بعد از دسترسی امن:

1. یک migration graph استاندارد در `apps/<app>/migrations/` برای همهٔ appهای نصب‌شده؛
2. baselineای که state واقعی production را بازنمایی کند، نه state فرضی dev؛
3. forward migrationهای کوچک برای رساندن baseline به مدل مقصد؛
4. fingerprint و preflight اجباری قبل از mark کردن baseline روی دیتابیس موجود؛
5. مسیر fresh install که همان graph را از صفر واقعاً create کند؛
6. حذف وابستگی runtime/CI به `dev_migrations/` فقط بعد از اثبات دو مسیر بالا.

`--fake-initial` یا `--fake` فقط وقتی مجاز است که preflight دقیق table/column/type/nullability/default/index/constraint و migration history را match کند و artifact نتیجه ذخیره شود؛ استفادهٔ کور ممنوع است.

### ۴.۲ Payment و Wallet

مدل مقصد، در صورت تأیید whole IRT:

- `Payment.amount`: `DecimalField(max_digits=18, decimal_places=0)`، مثبت و پس از create immutable؛
- `Wallet.balance`: `DecimalField(max_digits=18, decimal_places=0)`، non-negative؛
- `Wallet.Transaction.amount`: align با همین scale، مثبت و immutable؛
- تمام operationهای credit/debit/transfer در `transaction.atomic()` و با row lock یا update شرطی؛
- تمام serializerها monetary value را string می‌دهند و هیچ `float(...)` در مسیر مالی باقی نمی‌ماند؛
- gateway authority/reference پس از audit duplicateها constraint یکتایی شرطی می‌گیرد، اگر contract provider یکتایی را تضمین کند.

روش migration، expand/contract و قابل resume:

1. افزودن shadow columnهای nullable Decimal؛
2. inventory رکوردهای `NaN`، `Infinity`، منفی، خارج از range و دارای precision خلاف policy؛
3. backfill chunked و idempotent؛ موارد مبهم به quarantine report می‌روند و silently round نمی‌شوند؛
4. reconciliation row-by-row و aggregate بین Float قدیم، ledger، Payment، Order و gateway request؛
5. dual-write موقت و verification روی staging در صورت نیاز به rollout بدون downtime؛
6. cutover read به Decimal؛
7. افزودن `NOT NULL` و check constraint پس از validate؛
8. حذف column قدیمی فقط در release بعدی و پس از observation window و backup قابل restore.

اگر scale سه‌رقم تأیید شود، همین الگوریتم با `decimal_places=3` اجرا می‌شود و whole-value check فقط در gateway boundary باقی می‌ماند.

### ۴.۳ Auth و WebSocket

در پیشنهاد single-session، migration دیتابیسی جدید لازم نیست؛ DRF Token موجود source of truth می‌ماند.

WebSocket ticket در Redis ذخیره می‌شود، نه در DB:

- فقط hash ticket ذخیره می‌شود؛
- payload: user id، scope (`chat` یا `notification`)، room id اختیاری، issued-at و expiry؛
- TTL پیشنهادی: ۶۰ ثانیه؛
- مصرف atomic و یک‌بارمصرف؛
- بعد از handshake نیز active بودن user و membership همان room دوباره بررسی می‌شود.

اگر multi-device تأیید شود، مدل جایگزین نیاز است:

- `AuthSession(id UUID, user FK, token_hash unique, created_at, expires_at, revoked_at, last_seen_at, device_label optional)`؛
- token خام فقط یک بار برمی‌گردد؛
- logout current و logout-all جدا؛
- سقف session فعال قابل تنظیم.

این alternative بدون تأیید جداگانه پیاده‌سازی نمی‌شود.

### ۴.۴ Rate limit و health

Rate limit migration دیتابیسی ندارد. Redis keyها versioned، TTLدار و HMAC‌شده‌اند تا mobile/IP خام در key یا log دیده نشود. metric فقط scope/result/retry bucket دارد و PII ندارد.

Health migration دیتابیسی ندارد و فقط contract API تغییر می‌کند.

## ۵. endpointها و contractهای پیشنهادی

### ۵.۱ Auth

#### `POST /api/v1/user/logout/`

- Permission: user فعال و authenticated.
- ورودی: ندارد.
- رفتار: token جاری را revoke/delete می‌کند؛ idempotent است.
- خروجی موفق: `204 No Content`.
- token منقضی/نامعتبر: `401 invalid_token`.
- هیچ tokenی log یا echo نمی‌شود.

#### `POST /api/v1/user/ws-ticket/`

- Permission: user فعال و authenticated.
- ورودی: `scope` و برای chat، `room_id`.
- server room membership را بررسی می‌کند.
- خروجی `201`: `ticket` یک‌بارمصرف، `expires_in` و path مجاز. ticket تنها secret موقت response است و هرگز log نمی‌شود.
- `403`: عضو room نیست یا scope مجاز نیست.
- `404`: room وجود ندارد یا برای جلوگیری از enumeration قابل مشاهده نیست.
- `429`: rate limit.
- `503`: Redis/rate-limit backend unavailable.

WebSocket جدید: `wss://<host>/ws/.../?ticket=<opaque>`؛ query token بلندمدت ابتدا با telemetry بدون مقدار deprecate و پس از به‌روزرسانی تمام clientها رد می‌شود. Authorization نهایی همچنان server-side membership است.

### ۵.۲ Health

#### `GET /livez`

- Public، بدون auth؛ فقط زنده بودن process.
- `200 {"status":"ok"}` حتی اگر DB/Redis down باشند.

#### `GET /readyz`

- Public برای orchestrator؛ خروجی حداقلی.
- `200 {"status":"ready"}` یا `503 {"status":"not_ready"}`.
- نام dependency خراب، exception، memory، disk، version و config را افشا نمی‌کند.

#### compatibility

- `/health`، `/health/` و `/api/v1/health/` در دورهٔ انتقال همان contract حداقلی readiness را می‌دهند تا Docker/Nginx نشکنند.
- diagnostic تفصیلی، اگر واقعاً لازم باشد، زیر `/api/v1/internal/health/` با `IsAdminUser` و network allowlist قرار می‌گیرد و secret/raw exception باز هم نمی‌دهد.

### ۵.۳ Security/rate diagnostics

- `/rate-limit/` از endpoint نمایشیِ همیشه-false به diagnostic واقعی staff-only تبدیل می‌شود؛ raw IP/mobile/key نشان نمی‌دهد.
- `/security/audit/` staff-only می‌شود و فقط وضعیت واقعی controlها و timestamp آخرین check را می‌دهد؛ ادعای ساختگی حذف می‌شود.
- پاسخ مشترک rate limit:

```json
{
  "detail": "Too many requests.",
  "code": "rate_limited",
  "scope": "otp_create",
  "retry_after": 42
}
```

Header استاندارد `Retry-After` نیز برمی‌گردد. هیچ identifier کاربر در response نیست.

### ۵.۴ قراردادهای مالی

- endpointهای Payment/Wallet فعلی حفظ می‌شوند تا feature حذف نشود.
- response amount/balance به string canonical تغییر می‌کند و Flutter parser هم‌زمان قبل از cutover با هر دو شکل legacy number و string سازگار می‌شود؛ پس از observation window فقط string contract باقی می‌ماند.
- order payment، amount را از Order snapshot سمت سرور می‌گیرد و mismatch payload را رد می‌کند.
- top-up request از min/max و currency policy سمت سرور عبور می‌کند و Payment فقط resolved amount را freeze می‌کند.
- هیچ endpoint عمومی status، balance، paid flag یا stock را از client نمی‌پذیرد.

## ۶. Permission ruleهای دقیق

| عمل | ناشناس | user فعال | staff | قانون تکمیلی |
|---|---|---|---|---|
| `livez`/`readyz` | مجاز | مجاز | مجاز | پاسخ حداقلی، rate در edge |
| internal health | ممنوع | ممنوع | مجاز | به‌علاوهٔ network allowlist |
| logout current | ممنوع | فقط token خودش | token خودش | revoke کاربر دیگر ممنوع |
| WS ticket | ممنوع | فقط scope/room خودش | مثل user مگر endpoint مدیریتی جدا | membership هنگام issue و connect چک می‌شود |
| rate-limit diagnostic | ممنوع | ممنوع | read-only | key/PII/raw config نمایش داده نمی‌شود |
| security audit | ممنوع | ممنوع | read-only | نتیجهٔ واقعی، نه control ادعایی |
| Payment/Wallet mutations | ممنوع | فقط resource خودش | از endpoint کاربری bypass ندارد | amount/status/balance server authoritative |
| migration job | ممنوع | ممنوع | API ندارد | فقط deploy principal محدود |
| secret rotation/history cleanup | ممنوع | ممنوع | API ندارد | فقط owner/operatorهای نام‌گذاری‌شده با two-person check |

Proxy rule: application هر `X-Forwarded-For` دلخواه را trust نمی‌کند. Edge header ورودی client را پاک و IP را از proxy/CDN allowlistشده استخراج می‌کند؛ backend فقط header بازنویسی‌شده از Nginx داخلی یا `REMOTE_ADDR` را می‌پذیرد.

## ۷. مراحل اجرا و gateها

### فاز ۰ — Freeze، owner matrix و evidence

1. تعیین افراد مسئول rotation، DNS/TLS، DB، Redis، payment/SMS، registry، GitHub و deploy.
2. freeze موقت push/deploy/history cleanup.
3. ثبت manifest بدون مقدار از secret type/path/commit/image/artifact در معرض.
4. تهیهٔ backup رمزگذاری‌شده و خارج از repo از worktree dirty، سپس ساخت release baseline قابل بازتولید؛ patch احتمالی قبل از جابه‌جایی با secret scanner بررسی می‌شود.
5. تعیین RPO/RTO، maintenance window و rollback authority.

Gate 0: تصمیم‌های بخش ۱۰ پاسخ داده شده و هیچ staged secret deletion push نشده باشد.

### فاز ۱ — Rotation/reissue قبل از cleanup

ترتیب عملیاتی اجباری:

1. inventory redacted با scannerهایی که فقط type/path/commit را گزارش می‌کنند؛
2. rotate/reissue کردن Django signing key، DB credential، Redis password/ACL، SMS/provider، payment merchant/API، registry/cloud/SSH/Actions secrets، TLS private key/certificate و هر مورد دیگری که scanner پیدا کند؛
3. deploy referenceهای جدید با روش dual credential، اگر provider پشتیبانی کند؛
4. smoke test بدون چاپ مقدار؛
5. revoke credential قدیمی و اثبات عدم کارکرد آن؛
6. فقط پس از sign-off تمام موارد: untrack فایل‌ها و نگه‌داشتن template صرفاً با نام متغیرها؛
7. rewrite همهٔ branch/tagهای مجاز با `git filter-repo` در maintenance window؛ force-push کنترل‌شده و الزام re-clone برای همهٔ همکاران؛
8. حذف manifest/layerهای registry، Actions artifacts/cache، runner/server build cache و imageهای قدیمی؛
9. rebuild image از history پاک و scan دوباره.

محدودیت واقع‌بینانه: rewrite repository نمی‌تواند clone/fork یا artifact خارج از کنترل ما را پاک کند؛ به همین دلیل rotation مهم‌ترین control است و cleanup جایگزین آن نیست.

Gate 1: همهٔ old credentialها reject، credentialهای جدید healthy، TLS chain معتبر، scanner redacted clean و image layers/config فاقد secret باشند.

### فاز ۲ — Canonical build/deploy

1. نهایی‌کردن Dockerfile backend multi-stage با copy-list صریح؛ هیچ `COPY .`.
2. stageهای جدا برای core runtime و `runtime-ml`؛ backend analytics موردنیاز با image/tag صریح خودش deploy می‌شود، نه نصب تصادفی در startup.
3. build Flutter web با API origin production و image static غیر-root/read-only تا حد امکان.
4. ساخت compose canonical با ASGI/Daphne، edge WebSocket upgrade، migration job و scheduler.
5. secretها از secret manager یا Docker secret file خوانده می‌شوند؛ هیچ env file واقعی داخل repo/image نیست.
6. root filesystem read-only، `cap_drop: ALL`، `no-new-privileges`، tmpfs لازم، network segmentation، log به stdout و limit منابع.
7. image با commit SHA و digest؛ تولید SBOM و provenance؛ عدم استفاده از `latest`.
8. deploy pipeline: pull by digest → backup/preflight → one-shot migrate → rollout → readiness → smoke → promote.
9. rollback app با digest قبلی؛ rollback schema فقط طبق runbook migration/restore و نه reverse کور.
10. پس از دو rehearsal موفق، مسیرهای compose/Docker/systemd قدیمی که هیچ reference runtime ندارند حذف می‌شوند و redirect مستندات به مسیر canonical ثبت می‌شود.

Gate 2: compose parse، image build، non-root/read-only checks، HTTP/WS smoke، migration job exactly-once و rollback staging موفق.

### فاز ۳ — Snapshot امن و production migration reconciliation

1. Product Owner یک snapshot سازگار یا دسترسی محدود staging فراهم می‌کند؛ Codex مستقیم به production وصل نمی‌شود مگر با مجوز صریح جداگانه.
2. schema-only inventory شامل tables، columns، types، defaults، nullability، indexes، constraints، extensions، triggers و `django_migrations` گرفته می‌شود؛ row count و distributionها بدون PII ثبت می‌شوند.
3. restore در محیط ایزوله با network egress بسته و providerهای SMS/payment جعلی.
4. anonymization deterministic و referential-integrity-preserving برای mobile، نام، آدرس، bank، پیام‌ها و media metadata؛ دادهٔ اصلی retention محدود و encrypted دارد.
5. برای هر ۲۵ module یک matrix «model فعلی / dev baseline / live schema / live migration state / اختلاف / repair» ساخته می‌شود.
6. baseline production بازسازی و fingerprint guard نوشته می‌شود.
7. data repairها chunked، idempotent، resumable و audit-only-first هستند؛ ردیف مبهم quarantine می‌شود.
8. fresh DB و restored snapshot هر دو تا head migrate می‌شوند.
9. rehearsal حداقل دوبار با اندازه‌گیری lock، duration، row counts، checksum و downtime اجرا می‌شود.
10. staging smoke همهٔ flowهای حساس، به‌خصوص auth، chat WS، cart/order، Payment، Wallet و Analytics را اجرا می‌کند.

Gate 3: graph برای همهٔ moduleها complete، fresh و snapshot هر دو سبز، pending migration صفر و گزارش اختلاف داده امضاشده باشد.

### فاز ۴ — Decimal cutover

1. policy پول تأیید و تمام float boundaryها inventory می‌شوند.
2. shadow schema بعد از baseline reconciled ساخته می‌شود.
3. audit-only conversion و quarantine report تولید می‌شود.
4. backfill و dual-write staging؛ aggregate reconciliation.
5. Flutter به string money contract به‌صورت backward-compatible ارتقا می‌یابد.
6. read cutover، constraint validation و observation window.
7. حذف Float قدیمی در release بعدی همین گروه فقط پس از sign-off داده.

Gate 4: هیچ float در path مالی، aggregate difference صفر یا دارای تک‌تک sign-offهای anomaly، و concurrency tests سبز.

### فاز ۵ — Auth، WebSocket، rate limit و health

1. logout server-side و WS ticket contract پیاده می‌شود.
2. Flutter ابتدا ticket را از REST می‌گیرد و سپس socket را باز می‌کند؛ reconnect ticket جدید می‌گیرد.
3. پس از telemetry و تأیید همهٔ clientها، `?token=` بلندمدت reject می‌شود.
4. Redis atomic throttle و trusted-proxy chain پیاده می‌شوند.
5. health به live/readiness حداقلی split می‌شود.
6. security/rate diagnosticها staff-only و truthful می‌شوند.
7. reference audit کامل انجام و سپس `apps/users/authentication.py` و docs/settings قدیمی JWT حذف می‌شوند؛ `ExpiringTokenAuthentication` تنها source of truth مستند می‌شود.

Gate 5: تست replay/revoke/outage/proxy spoof سبز و log scan فاقد token/mobile/raw exception.

### فاز ۶ — Dependency و CI/CD gates

1. Click ابتدا روی 8.3.3 pin و با Celery-related transitive dependencies، management commands و کل suite تست می‌شود؛ رفتن به release جدیدتر فقط با compatibility evidence.
2. `pip check` و `pip-audit` برای runtime core، ML و dev/test lockها.
3. audit ecosystem Flutter/Dart و بررسی packageهای discontinued/outdated با policy ثبت‌شده.
4. scan base image و OS packages، SBOM، license inventory و Trivy/Grype image scan.
5. secret scanning در pre-commit و CI با redacted output.
6. CI کل ۲۱۲ تست موجود و همهٔ تست‌های جدید Group 1 را اجرا می‌کند؛ ML dependencies هم نصب می‌شوند.
7. migration gate روی fresh DB و fixture/snapshot کوچک‌شده؛ production migration file بدون preflight ممنوع.
8. Docker build/compose config، ASGI WebSocket smoke، readiness و non-root check.
9. image publication فقط بعد از تمام gateها؛ staging و production approval جدا.

Gate 6: finding شناخته‌شدهٔ runtime صفر، CI کامل سبز و artifact فقط با digest قابل promote باشد.

### فاز ۷ — Release rehearsal و production go/no-go

1. backup و restore drill واقعی staging؛
2. deploy کامل از digest بدون checkout کد روی سرور؛
3. migration با زمان/lock ثبت‌شده؛
4. smoke HTTP، WebSocket، OTP با provider staging، Payment sandbox و Wallet reconciliation؛
5. rollback image و restore drill؛
6. canary/maintenance-window production با approval دستی؛
7. post-deploy reconciliation و monitoring حداقل یک observation window.

هیچ production migration خودکار قبل از sign-off Product Owner، DBA/operator و backup owner اجرا نمی‌شود.

## ۸. برنامهٔ تست دقیق

### ۸.۱ Secret/TLS/history

- scanner تمام branch/tagها، imageها و artifactهای در کنترل را بدون نمایش value بررسی کند.
- credential جدید برای هر provider موفق و قدیمی ناموفق باشد.
- TLS private key/certificate واقعاً reissue شده و chain/domain/expiry درست باشد.
- image `history`، filesystem، config/env metadata و logs هیچ secretی نداشته باشند.
- fresh clone پس از rewrite build/test شود؛ clone قدیمی push نتواند history آلوده را برگرداند.
- template env فقط نام و توضیح داشته باشد.
- runner، registry و Actions cache پس از purge با image جدید بازسازی شوند.

### ۸.۲ Migration reconciliation

- inventory هر ۲۵ module و dependency graph کامل باشد.
- preflight روی snapshot صحیح pass و روی یک schema دست‌کاری‌شده عمداً fail کند.
- fresh DB از صفر تا head migrate شود.
- snapshot restored از state واقعی تا head migrate شود.
- اجرای دوبارهٔ repair/backfill idempotent باشد.
- row count، FK integrity، unique/check constraints و checksumهای منتخب قبل/بعد reconcile شوند.
- orphan، duplicate، invalid enum/status و money anomaly quarantine شوند، نه حذف یا حدس.
- concurrent/read load آزمایشی lock time و timeout قابل قبول داشته باشد.
- rollback application و restore database از backup اثبات شود.
- `makemigrations --check` و `migrate --plan` در release head clean باشند.

### ۸.۳ Decimal و قدرت مالی سرور

- جمع/تفریق/انتقال دقیق، بدون binary float drift.
- minimum، maximum، zero، negative، overflow و precision اضافی.
- NaN/Infinity و legacy value خارج از policy quarantine شوند.
- amount client برای order نتواند server total را تغییر دهد.
- payment status، wallet balance و stock از serializer عمومی writable نباشند.
- debit ناکافی atomic fail کند و balance منفی نشود.
- دو debit/transfer هم‌زمان double-spend ایجاد نکنند.
- ledger و balance در یک transaction commit/rollback شوند.
- gateway amount exact و whole IRT باشد، اگر policy پیشنهادی تأیید شود.
- serialization string بین Django و Flutter round-trip دقیق باشد.
- aggregate Payment/Wallet/Order قبل و بعد برابر باشد؛ هر exception نیاز به شناسهٔ anomaly و sign-off دارد.

### ۸.۴ Rate limit

- درخواست N مجاز و N+1 دارای `429` و `Retry-After` صحیح.
- درخواست‌های parallel نتوانند از limit عبور کنند.
- mobile، IP و user keyهای مستقل و multi-key atomic باشند.
- spoof کردن `X-Forwarded-For` rate را دور نزند.
- proxy/CDN واقعی IP درست را منتقل کند.
- Redis outage برای scopeهای حساس `503` و برای read مطابق policy مصوب عمل کند.
- TTL و reset boundary درست باشد.
- OTP attempt limit مستقل از issuance limit باشد.
- rate config نامعتبر startup check را fail کند.
- key/log/metric فاقد mobile/IP خام باشد.
- response contract در Flutter به countdown/retry UX قابل نگاشت باشد.

### ۸.۵ Health

- `livez` با DB/Redis down همچنان 200 باشد.
- `readyz` با DB یا Redis down مقدار 503 حداقلی بدهد.
- exception خام، hostname، memory، disk، version و credential fragment در response نباشد.
- public health query ارزان و دارای timeout کوتاه باشد.
- Docker/Nginx/deploy pipeline از endpoint درست استفاده کنند.
- internal diagnostic بدون staff و خارج allowlist رد شود.

### ۸.۶ Auth و WebSocket

- login جدید طبق تصمیم single-session token قبلی را باطل کند.
- logout current فوراً REST و WS reconnect را رد کند و idempotent باشد.
- token expired و user inactive در REST، chat WS و notification WS رد شوند.
- WS ticket فقط یک بار مصرف شود؛ replay، expiry، scope اشتباه و room اشتباه رد شوند.
- membership بعد از issue و قبل/حین connect دوباره کنترل شود؛ عضو حذف‌شده socket معتبر نداشته باشد.
- Redis outage هنگام ticket issue `503` بدهد.
- ticket/token در Nginx/app/error/analytics logs ظاهر نشود.
- Flutter reconnect ticket جدید بگیرد و logout storage و server را هر دو پاک کند.
- پس از migration client، query `?token=` رد شود.
- static/runtime reference audit ثابت کند حذف JWT dead code هیچ import یا endpointی را نمی‌شکند.

### ۸.۷ Docker/deploy/dependencies

- Dockerfile هیچ `COPY .` نداشته باشد و deny-list تنها دفاع build context نباشد.
- core و ML image reproducible، non-root و بدون source/dev/test/secret اضافی باشند.
- compose بدون env value واقعی parse شود و missing required variable واضح fail کند.
- `/ws/` upgrade، reconnect و graceful shutdown روی ASGI واقعی تست شوند.
- migrate job فقط یک بار اجرا و backend قبل از readiness به schema head متصل شود.
- deploy by digest و rollback به digest قبلی موفق باشد.
- `pip check` و auditهای core/ML/dev clean؛ Flutter audit و image scan بدون finding بلاک‌کننده.
- suite موجود **۲۱۲ backend + ۱۲۸ Flutter** بدون regression و همهٔ تست‌های جدید سبز باشند.

## ۹. معیار پایان Group 1

Group 1 فقط وقتی Done است که همهٔ موارد زیر evidence داشته باشند:

- rotation/reissue و revoke همهٔ secretهای در معرض؛ سپس history/registry/cache cleanup کامل؛
- دو rehearsal موفق migration روی snapshot anonymized و یک staging deployment کامل؛
- migration graph استاندارد برای همهٔ appها، fresh DB و production-like DB هر دو سبز؛
- هیچ Float یا `float()` در مسیر Payment/Wallet؛ داده و aggregate reconciled؛
- یک production compose canonical با ASGI/WebSocket و image immutable؛
- rate limit atomic، health حداقلی، logout واقعی و WS ticket یک‌بارمصرف؛
- JWT dead code پس از reference audit حذف و auth source of truth یکتا؛
- Click finding رفع و CI همهٔ suiteها/dependency/image/migration gates را اجرا کند؛
- backup/restore و app rollback اثبات‌شده؛
- گزارش نهایی شامل exact pass/fail، migrationها، anomalyها، image digest، audit result و هر کار دستی production باشد.

## ۱۰. تصمیم‌ها و ورودی‌های لازم از Product Owner

برای شروع implementation بعد از تأیید این پلن، پاسخ این موارد لازم است:

1. **پول:** whole `IRT` بدون اعشار را تأیید می‌کنید؟ سقف مبلغ تجاری موردنیاز چقدر است؟ اگر مبلغ کسری یا IRR لازم است، use case دقیق چیست؟
2. **Session:** single-session فعلی برای v1 تأیید است، یا ورود هم‌زمان چند دستگاه الزام محصولی است؟ پیشنهاد این پلن single-session است.
3. **Data services:** production از PostgreSQL/Redis managed استفاده می‌کند یا باید روی همان سرور Compose self-host شوند؟ پیشنهاد managed/external است.
4. **Secret manager و عملیات:** secret manager/registry/DNS/TLS provider کدام است و چه کسی برای هر credential rotation را انجام می‌دهد؟ Codex مقدار secret را دریافت یا چاپ نمی‌کند.
5. **Snapshot/staging:** آیا snapshot anonymized یا staging محدود فراهم می‌شود؟ مسئول anonymization، retention و حذف snapshot چه کسی است؟
6. **Rate/proxy:** defaultهای rate جدول بالا و topology واقعی IP، مثل Cloudflare → Nginx، تأیید می‌شوند؟ ترافیک مورد انتظار OTP و API چقدر است؟
7. **History cleanup:** force-push، بازسازی tagها، الزام re-clone و purge registry/Actions cache در maintenance window تأیید است؟
8. **Recovery:** RPO، RTO و downtime قابل قبول برای migration نهایی چند دقیقه است و backup production کجا نگه‌داری می‌شود؟
9. **Media:** media production روی object storage قرار می‌گیرد یا volume همان سرور؟ پیشنهاد object storage سازگار با S3 است؛ این تصمیم روی compose و backup اثر دارد.

## ۱۱. ترتیب تأیید

تأیید این سند به‌تنهایی مجوز اتصال یا write به production نیست. پس از پاسخ بخش ۱۰:

1. implementation محلی و staging طبق فازها شروع می‌شود؛
2. پیش از هر عملیات rotation، history rewrite، registry purge، snapshot production و migration production، runbook همان عملیات جداگانه برای sign-off ارائه می‌شود؛
3. در صورت مشاهدهٔ اختلافی فراتر از تصمیم‌های این سند، کار در همان gate متوقف و تصمیم جدید از Product Owner گرفته می‌شود.
