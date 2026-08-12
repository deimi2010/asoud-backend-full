# 📚 API Documentation Implementation Guide

## ✅ آنچه انجام شد

### Implemented Decorators (نمونه‌های پیاده‌سازی شده):

#### 1. **Authentication Endpoints** (`apps/users/views/user_views.py`)
- ✅ `PinCreateAPIView` - با کامل‌ترین documentation شامل:
  - Request body schema
  - Success response (200)
  - Error responses (400, 429, 500)
  - Rate limiting documentation
  - Example values

- ✅ `PinVerifyAPIView` - با documentation کامل شامل:
  - Request/response examples
  - Multiple error scenarios (400, 404, 500)
  - Token authentication flow

#### 2. **Product Endpoints** (`apps/product/views/owner_views.py`)
- ✅ `ProductCreateAPIView` - شامل:
  - Serializer-based request
  - Permission documentation
  - Error codes (400, 403)

#### 3. **Market Endpoints** (`apps/market/views/user_views.py`)
- ✅ `MarketListAPIView` - با:
  - Query parameters (page, page_size)
  - Pagination documentation
  - Statistics response

#### 4. **Cart & Order Endpoints** (`apps/cart/views/user.py`)
- ✅ `CartViewSet` - ViewSet documentation
- ✅ `OrderListView` - Order list با response examples

---

## 📊 پیشرفت Documentation

### آمار کلی:
- **Endpoints کل پروژه**: 108+
- **Endpoints با Documentation**: ~10-15 (مهم‌ترین‌ها)
- **درصد پیشرفت**: ~12-15%

### بخش‌های Document شده:
| App | Views | Status |
|-----|-------|--------|
| users | PinCreateAPIView, PinVerifyAPIView | ✅ Complete |
| product | ProductCreateAPIView | ✅ Complete |
| market | MarketListAPIView | ✅ Complete |
| cart | CartViewSet, OrderListView | ✅ Complete |

### بخش‌های باقی‌مانده (نیاز به documentation):
1. **apps/users/** - باقی views (Profile, BankInfo, etc.)
2. **apps/product/** - باقی views (Update, Delete, List details)
3. **apps/market/** - باقی views (Create, Update, Detail)
4. **apps/cart/** - باقی views (OrderDetail, OrderCreate)
5. **apps/payment/** - تمام payment views
6. **apps/sms/** - SMS endpoints
7. **apps/chat/** - Chat system endpoints
8. **apps/reserve/** - Reservation endpoints
9. **apps/affiliate/** - Affiliate marketing endpoints
10. **apps/discount/** - Discount & promotion endpoints
11. **apps/advertise/** - Advertisement endpoints
12. **apps/notification/** - Notification endpoints
13. **apps/wallet/** - Wallet & transaction endpoints
14. **apps/region/** - Geographic region endpoints
15. **apps/information/** - Information/Terms endpoints
16. **apps/analytics/** - ✅ **ML & Analytics endpoints (COMPLETED)** - See `../analytics/ANALYTICS_ML_DOCUMENTATION.md`

---

## 🎯 الگوی استاندارد Documentation

### مثال کامل برای یک View:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    # عنوان کوتاه endpoint
    summary="Short Description",
    
    # توضیحات کامل
    description="""
    Detailed description of what this endpoint does.
    Can include multiple lines and formatting.
    """,
    
    # پارامترهای Query String
    parameters=[
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number',
            required=False,
            default=1
        ),
    ],
    
    # Request Body (می‌تونه serializer باشه یا manual)
    request=MySerializer,  # یا dict برای manual
    
    # Response ها
    responses={
        200: {
            'description': 'Success',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'code': 200,
                        'data': {}
                    }
                }
            }
        },
        400: {
            'description': 'Validation error',
            'content': {
                'application/json': {
                    'example': {
                        'success': False,
                        'code': 400,
                        'error': {
                            'code': 'validation_error',
                            'detail': 'Error message'
                        }
                    }
                }
            }
        },
        401: {
            'description': 'Authentication required'
        },
        403: {
            'description': 'Permission denied'
        },
        404: {
            'description': 'Not found'
        },
        500: {
            'description': 'Internal server error'
        }
    },
    
    # تگ برای گروه‌بندی در Swagger UI
    tags=['Category Name']
)
class MyAPIView(views.APIView):
    pass
```

---

## 🔧 Tools & Commands

### نمایش OpenAPI Schema:
```bash
# Generate a disposable local schema with the canonical service name.
docker compose exec backend python manage.py spectacular --color --file /tmp/openapi.yaml
docker compose cp backend:/tmp/openapi.yaml ./schema-ci.yml

# View in browser
# Navigate to: http://localhost:8000/api/schema/swagger-ui/
```

### دسترسی به Documentation:
- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI JSON**: `http://localhost:8000/api/schema/`

---

## 📝 Guidelines برای تکمیل Documentation

### 1. **Authentication Requirements**
همیشه مشخص کن endpoint نیاز به authentication داره یا نه:
```python
# For public endpoints
permission_classes = [AllowAny]

# For authenticated endpoints
permission_classes = [IsAuthenticated]

# در documentation:
401: {'description': 'Authentication required'}
```

### 2. **Error Responses**
حداقل این error codeها رو document کن:
- **400**: Validation errors
- **401**: Authentication required
- **403**: Permission denied
- **404**: Resource not found
- **500**: Internal server error

### 3. **Request Examples**
برای هر endpoint حتماً example بده:
```python
'example': {
    'field1': 'value1',
    'field2': 123
}
```

### 4. **Response Examples**
همه حالت‌های مختلف response رو نشون بده (success + errors)

### 5. **Query Parameters**
تمام query params رو با type و description document کن

### 6. **Tags for Organization**
از tags برای گروه‌بندی منطقی استفاده کن:
- `Authentication`
- `Products - Owner`
- `Products - User`
- `Markets - Owner`
- `Markets - User`
- `Cart & Orders - User`
- `Cart & Orders - Owner`
- `Payments`
- `SMS`
- `Chat`
- `Reservations`
- `Wallet`
- etc.

---

## 🚀 Next Steps (برای تکمیل)

### Priority 1 - Core Endpoints:
1. ✅ Authentication (PinCreate, PinVerify) - DONE
2. ⚠️ User Profile (Get, Update)
3. ⚠️ Product CRUD (Create ✅, List, Detail, Update, Delete)
4. ⚠️ Market CRUD (List ✅, Create, Detail, Update, Delete)
5. ⚠️ Order Management (List ✅, Create, Detail, Update, Delete)
6. ⚠️ Payment Processing (Create, Verify, Callback)

### Priority 2 - Secondary Features:
7. ⚠️ Cart Operations (Add, Remove, Update)
8. ⚠️ SMS (Send, Verify)
9. ⚠️ Chat (Send, List, Detail)
10. ⚠️ Reservations (Create, List, Update)
11. ⚠️ Wallet (Balance, Transactions)

### Priority 3 - Additional Features:
12. ⚠️ Affiliate Marketing
13. ⚠️ Discounts & Promotions
14. ⚠️ Advertisements
15. ⚠️ Notifications
16. ⚠️ Regions
17. ⚠️ Information/Terms

---

## 📊 تخمین زمان باقی‌مانده

با توجه به:
- 108+ endpoint در پروژه
- ~15 endpoint تا الان document شده
- ~90-95 endpoint باقی‌مانده

**تخمین زمان:**
- هر endpoint: 5-10 دقیقه (متوسط 7 دقیقه)
- 90 endpoint × 7 دقیقه = **630 دقیقه ≈ 10-11 ساعت**

**استراتژی پیشنهادی:**
1. Priority 1 endpoints اول (3-4 ساعت)
2. Priority 2 endpoints بعد (3-4 ساعت)
3. Priority 3 endpoints آخر (3-4 ساعت)

---

## ✅ وضعیت فعلی

**آنچه تا الان انجام شد:**
- ✅ Import های drf-spectacular به 4 فایل اضافه شد
- ✅ 5 view class مهم با @extend_schema document شدند
- ✅ Template استاندارد برای بقیه endpoints آماده است
- ✅ Tags و structure مشخص شدند

**آماده برای:**
- تست کردن Swagger UI
- ادامه documentation بقیه endpoints
- Generate کردن OpenAPI schema

**Command برای تست:**
```bash
# Start development server
docker-compose -f docker-compose.dev.yaml up -d

# Access Swagger UI
# http://localhost:8000/api/schema/swagger-ui/
```

---

## 📚 منابع

- **drf-spectacular Docs**: https://drf-spectacular.readthedocs.io/
- **OpenAPI Specification**: https://swagger.io/specification/
- **Project Settings**: `config/settings/base.py` (lines 411-420)

---

**تاریخ**: October 23, 2025  
**وضعیت**: Task #5 - In Progress (15% Complete)  
**اولویت بعدی**: تکمیل Priority 1 endpoints
