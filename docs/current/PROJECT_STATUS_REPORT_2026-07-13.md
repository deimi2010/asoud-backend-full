# گزارش صادقانه وضعیت فعلی کل پروژه

> یادداشت به‌روزرسانی: این گزارش baseline پیش از اجرای گروه ۱ است. وضعیت جدید زیرساخت،
> auth/WebSocket، rate limit و Decimal در `GROUP_1_OPERATIONS_RUNBOOK.md` ثبت شده؛ آمار و
> blockerهای سایر فیچرها در این snapshot همچنان مرجع تاریخی‌اند.

تاریخ بررسی: ۱۳ ژوئیهٔ ۲۰۲۶ / ۲۲ تیر ۱۴۰۵
دامنه: بکند `asoud-project-full`، فرانت Flutter در `fluter-sina`، استک Docker محلی
مخاطب: Product Owner

## روش و سطح اطمینان

در این گزارش از این برچسب‌ها استفاده شده است:

- **[T] تست واقعی:** دستور تست در همین وضعیت فعلی اجرا شده است.
- **[R] اجرای واقعی محلی:** سرویس یا فلو روی Docker Compose محلی با PostgreSQL و Redis واقعی اجرا شده است.
- **[C] بررسی کد:** نتیجه از روی route، serializer، model، service یا UI فعلی به‌دست آمده؛ E2E نیست.
- **[I] استنباط:** ریسک یا نتیجه‌ای که از کنار هم گذاشتن contractها به دست آمده ولی با اجرای کامل کاربر نهایی تأیید نشده است.
- **[?] نامعلوم:** از repository یا محیط محلی قابل اثبات نبوده است.

هیچ دیتابیس، Redis یا سرویس production در این بررسی استفاده نشد. هیچ secretی خوانده یا چاپ نشد.

## ۱. خلاصهٔ وضعیت کلی

### حکم کوتاه

پروژه برای **توسعه و تست محلی قابل اجرا با یک دستور** است، اما برای **انتشار عمومی production آماده نیست**. تست‌های خودکار فعلی سبزند، ولی این با E2E واقعی کاربر نهایی برابر نیست. در حال حاضر هیچ فلو اصلی را نمی‌توان با صداقت «Flutter UI تا backend و سرویس خارجی، روی محیط production-like، کاملاً E2E شده» نامید.

### شواهد پایهٔ فعلی

- **[T] بکند:** ۲۱۲ تست پیدا شد؛ **۲۱۲ pass، صفر fail** در ۳۱٫۲ ثانیه، روی PostgreSQL و Redis محلی. این مجموعه شامل Chat، Analytics/ML و Product هم بود.
- **[T] فرانت:** ۱۲۸ تست؛ **۱۲۸ pass، صفر fail**.
- **[T] Flutter analyze:** صفر error، صفر warning، ولی **۳۸ مورد info lint** باقی است.
- **[R] Docker:** PostgreSQL، Redis، backend و frontend همگی healthy هستند؛ backend روی `127.0.0.1:8000` و frontend روی `127.0.0.1:8080`.
- **[R] Chat API lifecycle:** ۹ مرحلهٔ create/add/change-role/transfer/remove/leave/archive با status مورد انتظار اجرا شده است؛ این تست HTTP/API است، نه کلیک واقعی داخل Flutter.
- **[R] OTP issuance:** درخواست از proxy فرانت HTTP 200 گرفت و تعداد keyهای Redis زیاد شد؛ مقدار OTP نه لاگ شد و نه در response برگشت. verify واقعی با OTP دریافتی در مرورگر/موبایل دستی انجام نشده است.
- **[T] migration محلی dev:** drift صفر و pending operation صفر.
- **[T] production-style migration graph:** با settings معمول development هنوز برای **۲۱ app** initial migration پیشنهاد می‌شود و command با exit 1 تمام می‌شود.
- **[T] OpenAPI:** فایل structurally تولید می‌شود و command exit 0 دارد، اما **۱۴۳ خطای unique و ۵۴ warning unique** دارد؛ source of truth نیست.
- **[T] dependency audit فعلی:** `requirements-ml.txt` آسیب‌پذیری شناخته‌شده ندارد؛ در runtime اصلی، `click==8.1.8` یک vulnerability ثبت‌شده دارد و نسخهٔ fix اعلام‌شده `8.3.3` است.

### وضعیت فیچرهای اصلی

| بخش | وضعیت صادقانه | دلیل و منبع |
|---|---|---|
| اجرای محلی یک‌دست | **کامل و تست‌شده در محیط local** | [R] `docker compose up` چهار سرویس healthy؛ DB/Redis به host publish نشده‌اند. |
| Auth/OTP | **کد کامل، E2E ناقص** | [T] ۱۸ تست بکند + ۶ تست AuthBloc + ۴ تست session؛ [R] issuance از nginx تا Redis؛ verify دستی با SMS واقعی انجام نشده. |
| Chat و مدیریت اعضا | **backend/API کامل و تست‌شده؛ UI E2E ناقص** | [T] ۴۸ تست بکند و ۲۰ تست فرانت مرتبط؛ [R] lifecycle نه‌مرحله‌ای API؛ کلیک/UI و socket واقعی از build مرورگر تست نشده. |
| Cart | **backend قوی، فرانت ناقص** | [T] ۱۸ تست integrity بکند؛ [C] فرانت cart تست اختصاصی ندارد و قیمت هر item با contract فعلی معمولاً «نامشخص» می‌شود. |
| Checkout/پرداخت سفارش | **نصفه و blocker** | [C] checkout سفارش را ثبت می‌کند ولی به `PaymentScreen` وصل نمی‌شود؛ callback درگاه به state اپ برنمی‌گردد. |
| Gateway payment | **کد backend تست‌شده با mock، نه سرویس واقعی** | [T] ۱۸ تست؛ provider HTTP mock شده است. [C] redirect واقعی وجود دارد، اما production merchant/callback E2E نشده. |
| Wallet | **backend تست‌شده، UI عملاً unreachable** | [T] ۶ تست بکند؛ [C] screen و bloc وجود دارد ولی route/menu فعلی آن را باز نمی‌کند و تست فرانت ندارد. |
| Reservation | **نصفه/مدل محصول ناقص** | [T] ۱۰ تست بکند + ۵ تست bloc؛ [C] API/UI رزرو ساده وصل است، ولی تاریخ رخداد، ظرفیت، قیمت، لغو و refund ندارد و route از UI قابل دسترسی نیست. |
| Comment | **سطح محدود کامل، E2E ناقص** | [T] ۶ تست بکند + تست‌های model/product فرانت؛ create/list/reply/update واقعی است؛ delete/like وجود ندارد. |
| Bookmark | **کد کامل، تست واحد خوب، بدون E2E** | [T] contract بکند داخل market suite و ۷ تست فرانت؛ UI از منو reachable است. |
| Profile | **کد کامل برای فیلدهای محدود** | [T] users/profile tests؛ [C] IBAN پروفایل عمداً rejected است و UserDocument حذف شده. |
| Bank information | **کد کامل، تست واحد، بدون E2E** | [T] validation/ownership در users و ۷ تست فرانت bank؛ UI از Finance reachable است. |
| Advertisement | **خواندن/projection فعال؛ خرید عمداً 503** | [T] ۵ تست؛ [C] create/payment دستی fail-closed و فرانت صفحهٔ واقعی ندارد. |
| Affiliate | **نصفه** | [T] ۵ تست بکند + ۳ فرانت؛ [C] UI فقط eligible products را list می‌کند، create/manage در UI نیست و route از منو reachable نیست؛ owner API خالی است. |
| Analytics/ML | **local backend کامل؛ فرانت حداقلی؛ production غیرفعال** | [T] ۱۹ تست بکند + ۴ فرانت؛ [C] UI فقط summary را نمایش می‌دهد و route از منو reachable نیست؛ base/production همچنان `False`. |
| Notification | **WebSocket/REST موجود؛ delivery خارجی ناقص** | [T] ۹ بکند + ۴ فرانت؛ [C] push/email/SMS provider صریحاً false می‌دهند، frontend فقط REST list دارد. |
| Commercial SMS | **عمداً غیرفعال/fail-closed** | [T] ۳ تست؛ owner/admin sendها 503 تا تعریف billing/quota/reconciliation/refund. |
| Price inquiry | **کد کامل و تست‌شده در سطح API/unit** | [T] ۸ بکند + ۷ فرانت؛ finalize و پاسخ owner واقعی است؛ E2E UI انجام نشده. |
| Referral | **فقط رابطه کامل؛ reward شروع نشده** | [T] ۶ بکند + ۴ فرانت؛ هیچ points/credit/discount ledger وجود ندارد. |
| Market/workspace | **کد زیاد، تست پوشش ناقص** | [T] ۱۰ تست market عمدتاً schedule/bookmark و ۱۱ تست فرانت مرتبط؛ create/edit/media/location end-to-end نشده. |
| Product | **create/detail/theme فعال؛ update شروع نشده** | [T] ۸ بکند + ۸ فرانت detail؛ [C] فایل edit خالی و endpoint update محصول وجود ندارد. |
| Shipping customer-paid | **عمداً 409** | [T/C] order-level shipping selection/snapshot وجود ندارد؛ write نباید فعال شود. |
| Legacy ProductDiscount | **عمداً 409** | [T/C] contract جدید discount جداگانه فعال است؛ مدل legacy نباید وصل شود. |
| UserDocument/KYC | **اصلاً شروع نشده/حذف عمدی placeholder** | [C] model lifecycle و upload/review contract کامل وجود ندارد. |
| Reservation payment/refund | **اصلاً شروع نشده** | [C] placeholder حذف شده و مدل لازم وجود ندارد. |
| Production deploy | **حل‌نشده و در وضعیت فعلی غیرقابل اجرا** | [T] production compose parse نمی‌شود؛ migration و secret rotation و مسیر deploy حل نشده‌اند. |

## ۲. بکند — وضعیت هر ماژول

### نکتهٔ مهم دربارهٔ discovery تست

دستور سادهٔ `python manage.py test` به‌علت layout فعلی فقط ۷ smoke test ریشه را پیدا می‌کند. مجموعهٔ ۲۱۲تایی با labelهای صریح اجرا شد. workflow فعلی CI نیز فقط subset قدیمی **۱۳۷ تست** را صدا می‌زند و Chat/Analytics/Product جدید را وارد نکرده است. بنابراین سبز بودن `manage.py test` یا CI فعلی به‌تنهایی کل suite را ثابت نمی‌کند. **[T/C]**

### inventory ماژول‌ها، endpointها و تست‌ها

| App | endpointهای mounted فعلی | نتیجهٔ تست واقعی | وضعیت و شکاف |
|---|---|---:|---|
| `advertise` | `/api/v1/advertisements/`: list، detail، self، create، payment، update، delete | ۵/۵ | Public/product projection کار می‌کند؛ manual create/payment عمداً 503؛ product-backed ad مستقل edit/delete نمی‌شود. [T/C] |
| `affiliate` | user: eligible products/detail، create، per-market list، detail/update/delete، theme create/list/update؛ owner prefix mounted ولی خالی | ۵/۵ | ownership/source eligibility/duplicate/history محافظت شده؛ owner contract تصمیم‌گیری نشده. [T/C] |
| `analytics` | ۱۳ route: compatibility dashboard، platform dashboard/time-series/top/events/sessions، owner summary/time-series/products/forecast، recommendations/similar | ۱۹/۱۹ | local کامل و read-only/scoped؛ production disabled؛ refund فقط disclaimer دارد، lifecycle refund ندارد. [T/C] |
| `base` | endpoint مستقل ندارد؛ UUID base model | ۰ | foundation است ولی test/migration compatibility اختصاصی ندارد. [C] |
| `cart` | user: draft cart، add/update/remove، checkout، legacy create/list/detail/update/delete؛ owner: list/detail/verify | ۱۸/۱۸ + بخشی از ۷ smoke | server-authoritative snapshot/stock/discount و single-market فعال؛ production constraints/backfill هنوز reconcile نشده. [T/C] |
| `category` | ۹ read route برای group/category/subcategory/slider و product group/category/sub lists | ۰ | mounted و مصرف‌شده در فرانت، اما contract/query-count/seed provenance تست نشده. [C] |
| `chat` | room/message ViewSetها، participants، role/remove/leave/transfer، search/analytics، support tickets و actions | ۴۸/۴۸ + smoke | roles و socket revocation کار می‌کند؛ API E2E شده؛ browser Flutter E2E نشده. Group عمومی/خصوصی جداگانه وجود ندارد؛ فقط room typeهای private/group/support/market. [T/R/C] |
| `comment` | create، detail، text update، list برحسب content type/object | ۶/۶ | API از `django-comments-xtd` استفاده می‌کند؛ delete/like ندارد. مدل محلی `apps.comment.Comment` هم‌زمان به Market/Product وصل است و دوگانگی مدل ایجاد کرده. [T/C] |
| `core`/`config` | health، API index، security/audit، csrf-failure، rate-limit، schema/docs | تست متمرکز ندارد | `RateLimitView.is_rate_limited()` همیشه false است و security/audit ادعای rate limiting enabled می‌کند؛ health خطای raw dependency و آمار memory/disk را public می‌کند. [C] |
| `discount` | owner create/list/detail/delete؛ user validate | ۵/۵ | contract جدید با cart/payment یکپارچه است؛ prod uniqueness/backfill لازم دارد. [T/C] |
| `flutter` public API | market/product/theme/advertisement/visit business-card + legacy aliases؛ `/bank/share/<uuid>` | ۳/۳ | product detail و bank share حداقلی harden شده؛ aliasهای versioned/unversioned هنوز دو سطح contract نگه می‌دارند. [T/C] |
| `gateway` | هیچ API mounted ندارد | ۰ | model-only و عملاً dead؛ payment مستقیماً از `apps.payment` و Zarinpal استفاده می‌کند. [C] |
| `index` | root landing | ۰ | business module نیست. [C] |
| `information` | terms | ۰ | فرانت واقعی وصل است؛ broad exception/schema gap دارد و E2E نشده. [C] |
| `market` | حدود ۲۰ owner route برای CRUD/contact/location/status/media/slider/theme/schedule؛ ۶ user route برای public list/report/bookmark/schedule | ۱۰/۱۰ | schedule و bookmark خوب تست شده‌اند؛ CRUD/media و query performance پوشش کافی ندارند؛ DB exclusion/check constraint schedule در prod نیست. [T/C] |
| `market_subdomain` | URLConf جدا دارد ولی active root/host middleware آن را mount نمی‌کند | ۰ | installed اما dead/inconsistent؛ `django_hosts` و host middleware غیرفعال‌اند. [C] |
| `notification` | notifications/templates/preferences ViewSetها؛ bulk/queue/stats/cleanup؛ WebSocket route | ۹/۹ | REST و websocket داخلی موجود؛ push/email/SMS provider واقعی نیست؛ staging delivery/idempotency اثبات نشده. [T/C] |
| `payment` | create، redirect/pay، callback verify، list، detail | ۱۸/۱۸ | ownership/amount/idempotency/lock harden شده؛ provider در تست mock است؛ Float storage، uniqueness و legacy session reconciliation باز است. [T/C] |
| `price_inquiry` | ۱۰ user route برای CRUD/image/send/expiry/answers؛ ۵ owner route برای feed/detail/answer | ۸/۸ | ownership/finalization/one-answer قفل شده؛ OpenAPI ناقص و UI E2E نشده. [T/C] |
| `product` | owner create/detail/list، legacy discount، shipping create/list، theme CRUD؛ public detail در `flutter` | ۸/۸ | create/detail/theme فعال؛ customer-paid shipping و legacy discount عمداً 409؛ product update endpoint وجود ندارد. [T/C] |
| `referral` | create و self list | ۶/۶ | فقط رابطهٔ one-time و privacy-safe؛ reward program/ledger وجود ندارد. [T/C] |
| `region` | country/province/city و دو read list دیگر | ۰ | مصرف‌شده در workspace، ولی seed/migration provenance و error paths تست نشده. [C] |
| `reserve` | ۲۰ owner route برای service/specialist/reserve-time/dayoff/reservation؛ ۷ user route برای catalog/create/list/detail | ۱۰/۱۰ | دسترسی و حفظ history تست شده؛ مدل appointment کامل نیست و payment عمداً ساخته نشده. [T/C] |
| `sms` | ۱۳ admin route برای line/template/bulk/pattern و ۴ owner route | ۳/۳ | commercial sendها عمداً 503؛ provider mock فقط flag صریح dev/test؛ billing/quota/refund نیست. [T/C] |
| `users` | pin create/verify، self profile، bank catalog و bank-info CRUD | ۱۸/۱۸ | OTP Redis-only و token expiry/rotation تست شده؛ profile IBAN write rejected؛ UserDocument route ندارد. [T/C] |
| `wallet` | balance، check، pay، transactions | ۶/۶ | ownership/lock/payment harden شده؛ Float balance و prod migration باز؛ frontend این flow را expose نمی‌کند. [T/C] |

۷ smoke test ریشه فقط `ChatConversation/ChatMessage/Cart/Order` model behavior را پوشش می‌دهند. Coverage percentage به‌روز در این ممیزی تولید نشد؛ بنابراین از pass count نباید coverage بالا نتیجه گرفت. **[T]**

### migrationهای dev-only

`config.settings.migration_dev` تمام migrationهای زیر را به `dev_migrations/` نگاشت می‌کند. این graph یک baseline کامل برای دیتابیس تازهٔ disposable است، نه دنبالهٔ migration امن برای production:

- `advertise` 0001–0003
- `affiliate` 0001–0002
- `analytics` 0001–0004
- `cart` 0001–0002
- `category` 0001
- `chat` 0001–0002
- `comment` 0001–0002
- `discount` 0001–0002
- `gateway` 0001
- `information` 0001
- `market` 0001–0002
- `notification` 0001–0002
- `payment` 0001–0002
- `price_inquiry` 0001–0002
- `product` 0001–0002
- `referral` 0001–0002
- `region` 0001
- `reserve` 0001–0002
- `sms` 0001–0002
- `users` 0001
- `wallet` 0001

**[T]** روی دیتابیس dev فعلی `makemigrations --check --dry-run` می‌گوید No changes و `migrate --plan` می‌گوید No planned operations.
**[T]** با graph عادی development، همان ۲۱ app initial migration می‌خواهند و gate قرمز است.
**نتیجه:** هیچ‌یک از migrationهای dev بالا نباید مستقیم روی production اعمال شود. ابتدا schema، جدول `django_migrations` و دادهٔ واقعی باید inventory و reconcile شوند؛ سپس backfill/constraintها طراحی شوند.

### مدل‌ها و تصمیم‌های معماری باز در بکند

- **Shipping:** Order فیلد selected shipping option و immutable shipping amount ندارد؛ customer-paid write باید 409 بماند. [C]
- **Legacy ProductDiscount:** duration/position مدل قدیمی با discount واقعی cart سازگار نیست؛ endpoint باید 409 بماند. [C]
- **Profile IBAN:** فیلد legacy محدودیت طول اشتباه دارد؛ write پروفایل rejected است. BankInfo جداگانه IBAN معتبر را پشتیبانی می‌کند. [T/C]
- **Reservation:** تاریخ دقیق appointment، duration/capacity، price authority، cancellation و refund وجود ندارد. [C]
- **Payment/Wallet money:** چند مبلغ هنوز Float هستند و به Decimal migration نیاز دارند. [C]
- **Gateway constraints:** unique DB constraint برای authority/reference و reconcile sessionهای قدیمی لازم است. [C]
- **Cart production data:** pending قدیمی، mixed-market، duplicate discount code، invalid/dual target item و snapshot backfill باید inventory شوند. [C]
- **Refund:** analytics صریحاً gross بدون کسر refund است، چون مدل authoritative refund و lifecycle برگشت پول وجود ندارد. [C]
- **Notification external delivery:** push/email/SMS واقعی تعریف نشده است. [C]
- **Advertisement pricing:** manual purchase بدون server-owned price/target تعریف نشده است. [C]
- **Affiliate owner API:** prefix موجود ولی URLConf خالی است؛ purpose محصولی روشن نیست. [C]
- **Product edit:** endpoint update محصول وجود ندارد. [C]
- **UserDocument:** upload/review lifecycle وجود ندارد. [C]

## ۳. فرانت — وضعیت صفحات و flowها

### build، analyze و test

- **[T]** ۱۲۸/۱۲۸ تست pass.
- **[T]** analyze: صفر error، صفر warning، ۳۸ info. موارد اصلی: APIهای deprecated مربوط به Radio، چند `use_build_context_synchronously`، containerهای غیرضروری و دو field بدون type صریح.
- **[R]** Flutter web release در image فعلی build شده و nginx frontend healthy است.
- **[?]** APK/AAB Android، iOS build، signing، permissionهای device و تست روی دستگاه واقعی در این ممیزی انجام نشده است.
- **[?]** browser automation/Playwright/Flutter integration test وجود ندارد یا اجرا نشده است.

توزیع ۱۲۸ تست نشان می‌دهد وزن تست روی API parser، bloc/cubit و contractهای محدود است. تست فرانت اختصاصی برای user cart، wallet، payment، create workspace، category/job-management، product creation و navigation کامل وجود ندارد.

### flowهای اصلی

| flow | اتصال به backend | reachability و completeness | مدرک |
|---|---|---|---|
| Login/OTP | واقعی (`user/pin/create`, `verify`)؛ token در secure storage | reachable؛ issuance واقعی محلی شده، verify دستی و SMS واقعی نشده | [T/R/C] |
| Logout | فقط token محلی را پاک می‌کند؛ server logout endpoint ندارد | برای DRF token فعلی قابل قبول، ولی revoke فوری سمت سرور ندارد | [C] |
| Public market browsing | واقعی (`user/market/public/list`) | reachable از داشبورد؛ E2E نشده | [T/C] |
| Create/edit workspace | APIهای واقعی market/contact/location/media/theme/schedule | reachable؛ کد زیاد ولی تست و E2E ناقص | [C] |
| Category/region selection | API واقعی | در create flow مصرف می‌شود؛ تست frontend/backend متمرکز ندارد | [C] |
| Product create | multipart API واقعی owner product/create + theme update | reachable از market؛ تست کامل UI ندارد | [C] |
| Product detail | public `products?id=` واقعی | cubit/API tests دارد؛ UI detail/comment وصل است | [T/C] |
| Product edit | ندارد | فایل `edit_product_detail.dart` تقریباً خالی و backend endpoint ندارد | [C] |
| Comment/reply | API واقعی | در ProductScreen کار شده؛ delete/like UI/API ندارد؛ E2E نشده | [T/C] |
| Cart add/update/remove | API واقعی | UI دارد، ولی test frontend ندارد و item price contract mismatch دارد | [C] |
| Checkout | API واقعی cart/checkout | order ثبت می‌شود، اما online order به PaymentScreen هدایت نمی‌شود | [C] |
| Payment | API/redirect واقعی | PaymentScreen فقط از WalletScreen صدا زده می‌شود؛ order payment وصل نیست؛ callback app flow ناقص | [C] |
| Wallet | API و UI واقعی | `WalletScreen` route/menu ندارد؛ در عمل برای کاربر عادی unreachable | [C] |
| Chat rooms/messages | REST + WebSocket واقعی | chat list از bottom nav reachable؛ unit و API lifecycle قوی؛ UI E2E نشده | [T/R/C] |
| Group membership | add/remove/role/transfer/leave واقعی | UI کامل نوشته شده؛ create inviteها sequential و partial-success ممکن است | [T/R/C] |
| Support ticket | API واقعی و chat room واقعی | reachable از Chat/Menu؛ tests cubit دارد؛ E2E نشده | [T/C] |
| Reservation | API واقعی | screen نوشته شده ولی هیچ navigation فعلی به route آن نیست؛ مدل backend ناقص | [T/C] |
| My reservations | API و bloc method دارد | screen فعلی list رزروهای من را نمایش نمی‌دهد | [C] |
| Bookmarks | API واقعی | reachable از menu/home؛ تست cubit خوب؛ E2E نشده | [T/C] |
| Profile | API واقعی | reachable؛ فقط فیلدهای پشتیبانی‌شده؛ IBAN/KYC حذف شده | [T/C] |
| Bank info | API واقعی | Finance مستقیماً BankCardList را نشان می‌دهد؛ validations تست شده | [T/C] |
| Price inquiry | API واقعی | inquiry routes از dashboard reachable؛ unit tests دارد؛ E2E نشده | [T/C] |
| Advertisement | backend read وجود دارد | صفحه/service واقعی در فرانت وجود ندارد؛ constant قدیمی استفاده نمی‌شود | [C] |
| Affiliate | API واقعی | screen فقط eligible list؛ create/delete service نوشته شده ولی UI action ندارد؛ route از menu باز نمی‌شود | [T/C] |
| Analytics | API واقعی local | dashboard summary و disclaimer نوشته شده؛ route registered ولی navigation ندارد؛ سایر ۱۲ API UI ندارند | [T/C] |
| Notifications | REST واقعی | list/mark-read از menu reachable؛ frontend notification WebSocket client ندارد | [T/C] |
| Owner orders | API و screen واقعی | tests cubit دارد، ولی هیچ navigation فعلی به route نیست | [T/C] |
| Discount settings | API جدید واقعی | cubit/tests دارد؛ route به `extra marketId` وابسته است؛ E2E نشده | [T/C] |
| Referral | API واقعی relationship | از profile menu قابل دسترسی؛ reward نمایش داده نمی‌شود | [T/C] |

### mock/placeholderهای باقی‌مانده

- شبکهٔ اصلی فرانت mock نیست؛ serviceها از `DioClient` واقعی استفاده می‌کنند. [C]
- asset `placeholder.jpg` صرفاً fallback تصویر است، نه دادهٔ جعلی business. [C]
- چند TODO مربوط به `initState` و یک TODO navigation product detail باقی است؛ build را نمی‌شکنند ولی debt هستند. [C]
- `WalletScreen`، Analytics، Affiliate، Reservation و OwnerOrders کد دارند ولی از navigation معمول قابل دسترسی نیستند؛ این‌ها را «کامل» حساب نمی‌کنیم. [C]
- routeهایی که `state.extra as ...` می‌زنند (reservation، product، store detail/preview، create product، discount و edit market) در deep-link/refresh وب بدون extra می‌توانند runtime cast crash بدهند. این مورد از روی کد قطعی است ولی browser E2E نشده. [C/I]

## ۴. یکپارچگی backend و frontend

### mismatchها و شکاف‌های قطعی یا محتمل

| موضوع | وضعیت |
|---|---|
| قیمت item سبد | backend `Order2Serializer` برای item فقط id/name/images/quantity می‌دهد؛ frontend دنبال `price` یا `product.main_price` است. در نتیجه قیمت ردیف غالباً «نامشخص» می‌شود، هرچند total کلی server-derived درست است. [C] |
| پرداخت سفارش آنلاین | frontend بعد از checkout فقط success و pop می‌کند؛ هیچ `PaymentScreen(target=order)` ندارد. [C] |
| verify payment | frontend method با POST body نوشته شده؛ backend callback فقط GET query `Authority/Status` می‌پذیرد. این method فعلاً مصرف نمی‌شود، اما contract مرده/غلط است. [C] |
| برگشت از gateway | external browser باز می‌شود؛ deep-link/callback به app و refresh state پیاده نشده است. [C] |
| Chat capacity | server cap configurable با default 100 است؛ Flutter slider همیشه max=100. اگر config کمتر شود server 409 می‌دهد؛ اگر بیشتر شود UI اجازه نمی‌دهد. [C] |
| Group initial invites | Flutter اول room می‌سازد و سپس mobileها را یکی‌یکی add می‌کند؛ failure باعث rollback room/members قبلی نمی‌شود و فقط partial warning می‌دهد. [C] |
| Analytics | frontend فقط compatibility dashboard را مصرف می‌کند؛ time-series/top-products/recommendations/forecast UI ندارند. Production route هم disabled است. [C] |
| Affiliate | backend create/manage دارد؛ screen فقط list eligible را نشان می‌دهد. [C] |
| Reservation | backend my-reservations دارد؛ screen فقط create flow را نشان می‌دهد؛ خود route نیز در navigation نیست. [C] |
| Notification live | backend WebSocket notification دارد؛ frontend فقط REST polling/load دارد. [C] |
| Product edit | UI file خالی و API backend غایب است. [C] |
| Deep links | GoRouter برای چند route به object/string extra اجباری وابسته است؛ refresh مستقیم وب می‌تواند crash کند. [C/I] |
| OpenAPI | ۱۴۳ error unique و ۵۴ warning unique دارد؛ برای کشف خودکار mismatch قابل اتکا نیست. [T] |

### فیچرهای backend-only یا frontend-only

- backend-only/بدون UI کامل: platform analytics، owner analytics جز summary، ML recommendations/forecast، advertisement browsing/purchase boundary، affiliate management، owner reservation CRUD، notification templates/preferences/bulk/queue/stats، SMS admin/owner، wallet pay، owner orders، market schedules کامل. [C]
- frontend code موجود ولی backend/product ناقص: product edit، reservation payment expectation، برخی store styling flows قدیمی. [C]
- هیچ فلو غیر از Chat API lifecycle و OTP issuance به‌صورت composed runtime بررسی نشده است؛ Cart/Checkout/Payment/Profile/Bookmark/Comment/Reservation/Advertisement/Affiliate از داخل browser Flutter به backend واقعی دستی تأیید نشده‌اند. [R/?]

## ۵. Docker و زیرساخت

### local/v1 compose فعلی

- **[R]** `docker compose up --build` استک PostgreSQL 15 Alpine، Redis 7 Alpine، Daphne backend و Flutter web/nginx را بالا می‌آورد.
- **[R]** هر چهار سرویس healthy هستند.
- **[C]** PostgreSQL و Redis به host publish نشده‌اند؛ auth سادهٔ dev داخل network محلی است.
- **[C]** backend با user غیر root `asoud` اجرا می‌شود.
- **[C]** backend Dockerfile multi-stage است و `COPY .` ندارد؛ فایل‌ها و folderها explicit copy می‌شوند.
- **[C]** `.dockerignore` deny-by-default است و env/key/certificate/git/venv/data را حذف می‌کند.
- **[C]** frontend Dockerfile multi-stage Flutter builder → nginx است و context explicit دارد.
- **[R]** Docker CLI اندازهٔ unpacked/shared فعلی را حدود **۱٫۱۹ GB برای backend runtime-ml** و **۱۴۱ MB برای frontend** نشان می‌دهد. جمع layer content از image inspect حدود ۳۲۷ MB و ۳۸٫۷ MB است؛ تفاوت ناشی از نحوهٔ گزارش shared/unpacked layerهاست.
- **[C]** backend core/test بدون ML در image list حدود ۵۶۴ MB دیده می‌شود؛ runtime-ml به‌خاطر NumPy/Pandas/scikit-learn بزرگ‌تر است.

### Analytics/ML runtime

- dependencyهای ML در `requirements-ml.txt` جدا هستند: NumPy، Pandas، scikit-learn. [C]
- compose محلی عمداً target `runtime-ml` را می‌سازد؛ runtime اصلی می‌تواند بدون ML ساخته شود. [C]
- artifact volume جدا و commandهای rebuild/train وجود دارند. [C]
- cron پیشنهادی در runbook ثبت شده، اما روی هیچ production scheduler واقعی نصب یا مشاهده نشده است. [?]

### production infrastructure

- **[T] blocker:** `docker compose -f docker-compose.production.yml config --quiet` با exit 1 شکست می‌خورد؛ `docker-compose.monitoring.yml` وجود ندارد. متغیرهای لازم نیز در این بررسی عمداً بدون مقدار بودند.
- **[C]** حداقل سه مسیر متناقض باقی است: GitHub Actions/production compose، manual deploy scripts/other compose files، و systemd WSGI. مسیر systemd WebSocket را سرو نمی‌کند.
- **[C]** production compose هنوز `Dockerfile.prod` را build می‌کند، نه Dockerfile local نهایی؛ چند compose و Dockerfile قدیمی همچنان وجود دارند.
- **[C]** workflow فعلی image publish و deploy ندارد؛ این حذف عمدی بوده تا migration/secrets/runtime حل شود.
- **[C]** CI جدیدترین Chat/Analytics/Product tests و `requirements-ml.txt` را اجرا/نصب نمی‌کند.
- **[C]** local `.dockerignore` فعلی secret-safe است، ولی imageهای تاریخی، GHCR/Actions cache و git history قبلی را پاک یا امن نمی‌کند.

## ۶. بدهی فنی و تصمیم‌های معلق

### امنیت و عملیات

1. **Rotation/reissue سکرت‌ها و TLS:** envها و private keyها قبلاً در history بوده‌اند؛ هیچ مدرکی از rotation وجود ندارد. worktree فعلی حذف staged آن فایل‌ها را نشان می‌دهد، اما حذف فایل بدون rotation مشکل history/image cache را حل نمی‌کند. قبل از untrack/history rewrite باید rotation انجام شود.
2. **Git history/registry/cache cleanup:** بعد از rotation باید دربارهٔ rewrite history، GHCR image layers و Actions cache تصمیم گرفته شود.
3. **Python vulnerability:** `click==8.1.8` یک finding فعلی دارد؛ upgrade و compatibility test لازم است.
4. **WebSocket token در query string:** browser WebSocket از `?token=` استفاده می‌کند. nginx local برای `/ws/` access log را خاموش کرده و app فقط path را log می‌کند، ولی URL ممکن است در proxyهای دیگر، browser tooling یا infrastructure history دیده شود. header/subprotocol/cookie strategy نیاز به تصمیم دارد.
5. **Health endpoint exposure:** raw exception، memory و disk details را public می‌کند؛ production health باید کمینه شود.
6. **Rate limiting misleading/dead code:** endpoint نمونه همیشه false است و security audit status ادعای فعال بودن می‌کند؛ DRF throttle واقعی جداگانه وجود دارد ولی نرخ عمومی بسیار باز است.
7. **Dead auth framework:** `JWTAuthentication`، blacklist، password helpers و lockout classes در `apps/users/authentication.py` فعال نیستند؛ auth واقعی DRF Token است. این کد و docs قدیمی باعث برداشت غلط می‌شوند.
8. **No production observability proof:** alerting، SLO، log redaction، retention و incident process در محیط واقعی تأیید نشده.
9. **Backup/restore:** فایل‌های متناقض وجود دارد؛ restore drill و RPO/RTO اثبات نشده.

### داده و migration

10. **Production migration reconciliation برای ۲۱ app:** بزرگ‌ترین blocker داده‌ای است.
11. **Chat backfill:** owner/role و audit relation برای roomهای واقعی باید backfill و constraintها validate شوند.
12. **Analytics backfill/validation:** relationهای event/session و aggregate مالی باید با orderهای واقعی reconcile شوند.
13. **Float → Decimal:** Payment و Wallet و هر historical amount وابسته باید data migration کنترل‌شده داشته باشد.
14. **Order/cart constraints:** stateهای قدیمی، snapshot totals، inventory state و XOR target نیاز به quarantine/backfill دارند.
15. **Gateway uniqueness/legacy sessions:** authority/reference و sessionهای client-controlled قدیمی باید reconcile شوند.
16. **Market schedule constraints:** check/exclusion DB constraint و classification رکوردهای synthetic قدیمی لازم است.
17. **Dual comment model:** API از XtdComment استفاده می‌کند ولی Market/Product GenericRelation به مدل محلی Comment دارند؛ باید یک منبع حقیقت انتخاب شود.

### تصمیم‌های محصولی/مالی

18. **Payment production:** merchant، callback domain، sandbox/staging، cancellation، reconciliation و operational ownership باید تأیید شود.
19. **Refund lifecycle:** refund state/amount/reference/stock/discount reversal و اثر analytics تعریف نشده است.
20. **Shipping:** انتخاب روش، server price، snapshot، change/cancel/refund تعریف نشده است.
21. **Reservation:** occurrence date، timezone، capacity، duration، price، cancellation، no-show و refund نیاز به مدل محصولی دارد.
22. **Advertisement pricing/payment:** تا تعریف server-owned target/price باید 503 بماند.
23. **Commercial SMS:** recipient policy، quota، pricing، wallet debit، provider reconcile و refund تعریف نشده.
24. **Referral rewards:** eligibility window، ledger، reversal و abuse policy تعریف نشده.
25. **Affiliate owner API:** معلوم نیست owner چه نقش متفاوتی از marketer دارد.
26. **Product update:** immutable fields، stock/price edit semantics و historical order effect باید تعیین شود.
27. **Profile IBAN در برابر BankInfo:** باید تصمیم گرفته شود آیا profile IBAN حذف می‌شود یا schema آن reconcile می‌شود.
28. **UserDocument/KYC:** document types، storage، encryption، retention، review permissions و privacy policy تعریف نشده.
29. **Notification channels:** آیا v1 فقط in-app/WebSocket است یا push/email هم وعده داده می‌شود.
30. **Analytics production scope:** اگر v1 لازم است، migration/deploy/scheduler/artifact storage باید نهایی شود؛ اگر لازم نیست route/UI باید از release مخفی بماند.

### فرانت و کیفیت

31. **Order payment UX:** checkout → payment → callback → refresh order باید کامل شود.
32. **Cart item price contract:** serializer و UI باید روی field server-owned مشترک توافق کنند.
33. **Unreachable pages:** Wallet، Analytics، Affiliate، Reservation و OwnerOrders باید یا navigation واقعی داشته باشند یا از route table release حذف شوند.
34. **Deep-link safety:** route parameterها باید path/query/state قابل بازسازی داشته باشند، نه cast اجباری `extra`.
35. **Mobile builds:** Android/iOS build، signing، permissions، secure-storage behavior و device tests انجام نشده.
36. **E2E automation:** auth، browse، cart، checkout، payment sandbox، bookmark، comment، chat socket و reservation باید browser/device E2E شوند.
37. **Performance/load:** N+1 و query-count برای market/product/chat/notification و WebSocket fanout/capacity load-test نشده است.
38. **Flutter lint debt:** ۳۸ info و deprecated Radio APIs باید قبل از upgradeهای بعدی مدیریت شوند.

### repository و release engineering

39. **Worktree بسیار dirty است:** تغییرات بزرگ backend/frontend، حذف‌های staged و فایل‌های untracked هنوز commit/review نشده‌اند؛ release provenance و rollback commit مشخص نیست.
40. **CI suite ناقص است:** ۱۳۷ تست قدیمی اجرا می‌شود، نه ۲۱۲ تست کامل؛ ML dependencies/tests هم در CI نیست.
41. **Test discovery ناقص:** `manage.py test` فقط ۷ test پیدا می‌کند.
42. **OpenAPI ناقص:** ۱۴۳ error unique و ۵۴ warning unique؛ contract رسمی نیست.
43. **چند Docker/compose/deploy path قدیمی:** cleanup نهایی production انجام نشده و canonical path تأیید نشده است.
44. **Production compose invalid:** includeهای غایب و topology قدیمی آن را غیرقابل اجرا کرده است.

## ۷. آیا امروز آمادهٔ انتشار عمومی است؟

### پاسخ صریح

**خیر.** انتشار امروز با کاربر و پول واقعی ریسک غیرقابل قبول دارد.

### blockerهای جدی قبل از انتشار

1. rotation/reissue همهٔ secretها و TLS که در history/imageها در معرض بوده‌اند؛ سپس cleanup کنترل‌شده.
2. تعیین مسیر canonical production و ساخت compose/image واقعی که parse، build و deploy شود و ASGI/WebSocket را پشتیبانی کند.
3. reconcile کامل migration/schema/data production برای ۲۱ app و اجرای rehearsal روی snapshot ناشناس‌شده/staging.
4. تکمیل checkout→payment سفارش در فرانت و E2E با sandbox واقعی gateway، callback، failure/retry/reconcile.
5. Float→Decimal و constraint/backfillهای مالی و gateway قبل از پول واقعی.
6. اثبات OTP با provider واقعی production/staging؛ login بدون آن قابل اتکا نیست.
7. اضافه‌کردن suite کامل ۲۱۲تایی و ML به CI و سبزکردن migration gate صحیح.
8. رفع finding فعلی `click` و اجرای دوباره dependency audit.
9. حداقل E2E واقعی برای auth، browse، cart، checkout/payment، profile/bank، comment/bookmark و Chat WebSocket.
10. backup/restore drill، monitoring/alerting، health endpoint کمینه، domain/TLS/CORS/CSRF/AllowedHosts validation.
11. تصمیم release دربارهٔ routeهای unreachable/نصفه تا کاربر با صفحهٔ بن‌بست یا crash مواجه نشود.
12. commit/review/release tagging وضعیت فعلی؛ worktree dirty برای deploy قابل اعتماد نیست.

### مواردی که می‌توان بعد از انتشار اضافه کرد، فقط اگر در v1 پنهان/صادقانه scope-out شوند

- commercial SMS owner/admin
- customer-paid shipping
- paid/manual advertisements
- reservation payment و appointment کامل
- referral rewards
- UserDocument/KYC
- profile IBAN write
- owner affiliate API
- push/email notifications
- analytics پیشرفته/ML production و UIهای forecast/recommendation
- product edit، اگر در v1 محصول immutable پذیرفته و UI edit حذف شود
- delete/like comment
- public/private distinction اضافه برای group chat، چون مدل فعلی چنین محصولی ندارد

این موارد فقط وقتی قابل تعویق‌اند که route/menu/marketing آن‌ها وعدهٔ عملکردی ندهد. در غیر این صورت خودشان blocker تجربهٔ کاربر می‌شوند.

## مواردی که در این ممیزی کامل بررسی نشد

- هیچ production host، database، Redis، registry، Actions secret یا server process مشاهده نشد. [?]
- صحت rotation قبلی secretها قابل اثبات نبود. [?]
- gateway و SMS واقعی به‌دلیل نبودن/نبایدخواندن credentials اجرا نشدند. [?]
- Android/iOS native build و device testing انجام نشد. [?]
- load/performance، accessibility، localization visual QA و browser matrix اجرا نشد. [?]
- correctness داده‌های historical production و aggregateهای analytics قابل بررسی نبود. [?]
- vulnerability audit مستقل برای اکوسیستم Dart/Flutter انجام نشد؛ فقط Python requirements audit شد. [?]

## نتیجهٔ نهایی برای Product Owner

کد از وضعیت «نمونهٔ صرف» جلوتر رفته است: local stack واقعی بالا می‌آید، ۲۱۲ تست بکند و ۱۲۸ تست فرانت سبزند، Chat membership و Analytics/ML در local واقعاً پیاده‌سازی شده‌اند، و چند مسیر مالی/دسترسی مهم harden شده‌اند. با این حال سه لایه هنوز پروژه را از release عمومی جدا می‌کنند:

1. **production engineering حل‌نشده**: secret rotation، migration، deploy path و compose؛
2. **فلو پول واقعی ناقص**: frontend order payment، provider E2E و data constraints؛
3. **فاصلهٔ زیاد بین unit/API test و تجربهٔ واقعی کاربر**: صفحات unreachable، deep-link crash risk و نبود E2E browser/device.

بنابراین برچسب درست امروز این است: **«نسخهٔ توسعهٔ محلی قابل اجرا و دارای بخش‌های backend قوی؛ هنوز نه یک v1 production-ready.»**
