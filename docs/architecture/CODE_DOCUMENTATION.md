# 📚 ASOUD Code Documentation

<div align="center">

![Code Documentation](https://img.shields.io/badge/Code-Documentation-blue?style=for-the-badge&logo=markdown)
![Django](https://img.shields.io/badge/Django-4.2-green?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)

**Comprehensive code documentation for ASOUD platform**

</div>

---

## 📋 **Table of Contents**

- [🏗️ Project Structure](#️-project-structure)
- [🔧 Core Components](#-core-components)
- [📱 Apps Overview](#-apps-overview)
- [🔐 Authentication System](#-authentication-system)
- [🛒 E-commerce Core](#-e-commerce-core)
- [💬 Communication System](#-communication-system)
- [📊 Analytics & ML](#-analytics--ml)
- [🔒 Security Implementation](#-security-implementation)
- [⚡ Performance Optimization](#-performance-optimization)
- [🧪 Testing Strategy](#-testing-strategy)

---

## 🏗️ **Project Structure**

```
asoud-main/
├── config/                     # Django configuration
│   ├── settings/              # Environment-specific settings
│   ├── urls.py               # Main URL configuration
│   └── wsgi.py               # WSGI configuration
├── apps/                      # Django applications
│   ├── users/                # User management
│   ├── market/               # Marketplace core
│   ├── product/              # Product management
│   ├── order/                # Order processing
│   ├── payment/              # Payment processing
│   ├── chat/                 # Real-time chat
│   ├── sms/                  # SMS integration
│   ├── analytics/            # Analytics & ML
│   ├── affiliate/            # Affiliate marketing
│   ├── notification/         # Notification system
│   ├── wallet/               # Wallet management
│   ├── location/             # Location management
│   ├── category/             # Category management
│   ├── inquiry/              # Inquiry system
│   ├── advertisement/        # Advertisement system
│   └── core/                 # Core utilities
├── utils/                     # Utility functions
├── static/                    # Static files
├── media/                     # Media files
├── templates/                 # HTML templates
├── requirements/              # Python dependencies
├── docker-compose.yaml        # Docker configuration
└── manage.py                  # Django management script
```

---

## 🔧 **Core Components**

### **1. Configuration System**

#### **Settings Architecture**
```python
# config/settings/base.py
"""
Base Django settings for ASOUD platform.
Contains common settings shared across all environments.
"""

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'asoud'),
        'USER': os.environ.get('DB_USER', 'asoud'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.users.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.CustomPagination',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
```

#### **Environment-Specific Settings**
- **Development:** Debug enabled, detailed logging
- **Production:** Debug disabled, optimized settings
- **Testing:** In-memory database, fast execution

### **2. URL Configuration**

#### **Main URL Patterns**
```python
# config/urls.py
"""
Main URL configuration for ASOUD platform.
Routes requests to appropriate app-specific URLs.
"""

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.market.urls')),
    path('api/v1/', include('apps.product.urls')),
    path('api/v1/', include('apps.order.urls')),
    path('api/v1/', include('apps.payment.urls')),
    path('api/v1/', include('apps.chat.urls')),
    path('api/v1/', include('apps.sms.urls')),
    path('api/v1/', include('apps.analytics.urls')),
    path('api/v1/', include('apps.affiliate.urls')),
    path('api/v1/', include('apps.notification.urls')),
    path('api/v1/', include('apps.wallet.urls')),
    path('api/v1/', include('apps.location.urls')),
    path('api/v1/', include('apps.category.urls')),
    path('api/v1/', include('apps.inquiry.urls')),
    path('api/v1/', include('apps.advertisement.urls')),
    
    # Health checks
    path('api/v1/health/', include('apps.core.urls')),
    
    # Static and media files
    path('static/', serve, {'document_root': settings.STATIC_ROOT}),
    path('media/', serve, {'document_root': settings.MEDIA_ROOT}),
]
```

---

## 📱 **Apps Overview**

### **1. Users App (`apps/users/`)**

#### **Purpose**
User management, authentication, and profile management.

#### **Key Components**
```python
# apps/users/models.py
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for ASOUD platform.
    Uses mobile number as primary identifier.
    """
    mobile_number = models.CharField(max_length=11, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

# apps/users/authentication.py
class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication class.
    Supports both Bearer and Token authentication schemes.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
        
        # Support both Bearer and Token authentication
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif auth_header.startswith('Token '):
            token = auth_header.split(' ')[1]
        else:
            return None
        
        # Validate token and return user
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            return (user, token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None
```

#### **API Endpoints**
- `POST /api/v1/user/pin/create/` - Create PIN
- `POST /api/v1/user/pin/verify/` - Verify PIN and get token
- `GET /api/v1/user/profile/` - Get user profile
- `PUT /api/v1/user/profile/` - Update user profile

### **2. Market App (`apps/market/`)**

#### **Purpose**
Marketplace core functionality, market management, and location handling.

#### **Key Components**
```python
# apps/market/models.py
class Market(models.Model):
    """
    Market model representing a business/store.
    Each market belongs to a user (owner).
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='markets')
    name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

class MarketLocation(models.Model):
    """
    Market location model for geographic positioning.
    Each market can have multiple locations.
    """
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='locations')
    city = models.ForeignKey('location.City', on_delete=models.CASCADE)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['market', 'city']
```

#### **API Endpoints**
- `GET /api/v1/user/market/public/list/` - Public market list
- `GET /api/v1/owner/market/list/` - Owner market list
- `POST /api/v1/owner/market/create/` - Create market
- `GET /api/v1/owner/market/location/list/` - Market locations
- `POST /api/v1/owner/market/location/create/` - Create location

### **3. Product App (`apps/product/`)**

#### **Purpose**
Product management, inventory, and catalog functionality.

#### **Key Components**
```python
# apps/product/models.py
class Product(models.Model):
    """
    Product model for marketplace items.
    Each product belongs to a market and category.
    """
    market = models.ForeignKey('market.Market', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey('category.Category', on_delete=models.CASCADE)
    subcategory = models.ForeignKey('category.SubCategory', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    main_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
```

#### **API Endpoints**
- `GET /api/v1/user/product/list/` - Product list
- `GET /api/v1/user/product/detail/<id>/` - Product detail
- `POST /api/v1/owner/product/create/` - Create product
- `PUT /api/v1/owner/product/update/<id>/` - Update product
- `DELETE /api/v1/owner/product/delete/<id>/` - Delete product

### **4. Order App (`apps/order/`)**

#### **Purpose**
Order processing, cart management, and order lifecycle.

#### **Key Components**
```python
# apps/order/models.py
class Order(models.Model):
    """
    Order model for customer purchases.
    Each order belongs to a user and contains multiple items.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    market = models.ForeignKey('market.Market', on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    """
    Order item model for individual products in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
```

#### **API Endpoints**
- `GET /api/v1/user/order/list/` - User orders
- `POST /api/v1/user/order/create/` - Create order
- `GET /api/v1/user/order/detail/<id>/` - Order detail
- `PUT /api/v1/owner/order/update/<id>/` - Update order status

---

## 🔐 **Authentication System**

### **1. Authentication Flow**

#### **PIN-based Authentication**
```python
# apps/users/views/user_views.py
class PinCreateAPIView(APIView):
    """
    Create PIN for user authentication.
    Sends SMS with verification code.
    """
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        
        # Validate mobile number
        if not mobile_number or len(mobile_number) != 11:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error={'code': 'validation_error', 'detail': 'Invalid mobile number'}
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate PIN
        pin = generate_pin()
        
        # Send SMS
        sms_result = SMSCoreHandler.send_pattern({
            'mobile': mobile_number,
            'template': 'verify',
            'parameters': {'code': pin}
        })
        
        if sms_result:
            # Store PIN in cache
            cache.set(f"pin_{mobile_number}", pin, 300)  # 5 minutes
            
            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    message='PIN sent successfully'
                ),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error={'code': 'sms_error', 'detail': 'Failed to send SMS'}
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

#### **Token Generation**
```python
# apps/users/views/user_views.py
class PinVerifyAPIView(APIView):
    """
    Verify PIN and generate authentication token.
    """
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        pin = request.data.get('pin')
        
        # Verify PIN
        cached_pin = cache.get(f"pin_{mobile_number}")
        if not cached_pin or cached_pin != pin:
            return Response(
                ApiResponse(
                    success=False,
                    code=401,
                    error={'code': 'pin_not_valid', 'detail': 'Invalid PIN'}
                ),
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create user
        user, created = User.objects.get_or_create(
            mobile_number=mobile_number,
            defaults={
                'first_name': 'کاربر',
                'last_name': 'جدید'
            }
        )
        
        # Generate token
        token = generate_jwt_token(user)
        
        # Clear PIN from cache
        cache.delete(f"pin_{mobile_number}")
        
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data={
                    'token': token,
                    'user': {
                        'id': user.id,
                        'mobile_number': user.mobile_number,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    }
                },
                message='Authentication successful'
            ),
            status=status.HTTP_200_OK
        )
```

### **2. Authorization System**

#### **Role-based Access Control**
```python
# apps/core/permissions.py
class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners to edit their objects.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only for the owner
        return obj.owner == request.user

class IsMarketOwner(BasePermission):
    """
    Permission to only allow market owners to access their markets.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is accessing their own market
        market_id = view.kwargs.get('market_id')
        if market_id:
            try:
                market = Market.objects.get(id=market_id)
                return market.owner == request.user
            except Market.DoesNotExist:
                return False
        
        return True
```

---

## 🛒 **E-commerce Core**

### **1. Product Management**

#### **Product Serialization**
```python
# apps/product/serializers.py
class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for product list view.
    Includes basic product information and market details.
    """
    market_name = serializers.CharField(source='market.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'main_price', 'discount_price',
            'discount_percentage', 'stock_quantity', 'is_active',
            'market_name', 'category_name', 'subcategory_name',
            'created_at', 'updated_at'
        ]
    
    def get_discount_percentage(self, obj):
        if obj.discount_price and obj.main_price:
            return round((1 - obj.discount_price / obj.main_price) * 100, 2)
        return 0
```

#### **Product Filtering**
```python
# apps/product/views/user_views.py
class ProductListAPIView(ListAPIView):
    """
    List products with filtering and search capabilities.
    """
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'subcategory', 'market', 'is_active']
    search_fields = ['name', 'description', 'market__name']
    ordering_fields = ['created_at', 'main_price', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related(
            'market', 'category', 'subcategory'
        )
```

### **2. Order Processing**

#### **Order Creation**
```python
# apps/order/views/user_views.py
class OrderCreateAPIView(CreateAPIView):
    """
    Create a new order from cart items.
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Get cart items
        cart_items = CartItem.objects.filter(user=self.request.user)
        
        if not cart_items.exists():
            raise ValidationError({'detail': 'Cart is empty'})
        
        # Calculate total amount
        total_amount = sum(item.quantity * item.product.main_price for item in cart_items)
        
        # Create order
        order = serializer.save(
            user=self.request.user,
            total_amount=total_amount,
            order_number=generate_order_number()
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.main_price,
                total_price=cart_item.quantity * cart_item.product.main_price
            )
        
        # Clear cart
        cart_items.delete()
        
        return order
```

---

## 💬 **Communication System**

### **1. Real-time Chat**

#### **WebSocket Configuration**
```python
# apps/chat/consumers.py
class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    """
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = text_data_json['user']
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': user
            }
        )
    
    async def chat_message(self, event):
        message = event['message']
        user = event['user']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user': user
        }))
```

### **2. SMS Integration**

#### **SMS Core Handler**
```python
# apps/sms/sms_core.py
class SMSCoreHandler:
    """
    Core SMS handler for sending various types of SMS.
    """
    @staticmethod
    def send_pattern(payload):
        """
        Send pattern-based SMS using SMS.ir API.
        """
        headers = {
            'X-API-KEY': os.environ.get('SMS_API'),
            'Content-Type': 'application/json'
        }
        
        URL = "https://api.sms.ir/v1/send/" + "verify"
        response = requests.post(URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 1:
                return True
            else:
                logger.warning(f"Template SMS failed: {result}, trying bulk SMS...")
                return SMSCoreHandler.send_bulk({
                    'lineNumber': '10008666',
                    'messageText': f"کد تأیید آسود: {payload.get('parameters', {}).get('code')}",
                    'mobiles': [payload.get('mobile')],
                    'sendDateTime': None
                })
        return False
    
    @staticmethod
    def send_bulk(payload):
        """
        Send bulk SMS using SMS.ir API.
        """
        headers = {
            'X-API-KEY': os.environ.get('SMS_API'),
            'Content-Type': 'application/json'
        }
        
        URL = "https://api.sms.ir/v1/send/" + "bulk"
        response = requests.post(URL, json=payload, headers=headers)
        
        return response.status_code == 200
```

---

## 📊 **Analytics & ML**

### **1. Analytics Models**

#### **Event Tracking**
```python
# apps/analytics/models.py
class Event(models.Model):
    """
    Event model for tracking user interactions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=50)
    event_data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

class UserBehavior(models.Model):
    """
    User behavior model for ML analysis.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    behavior_type = models.CharField(max_length=50)
    behavior_data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
```

### **2. ML Models**

#### **Recommendation System**
```python
# apps/analytics/ml_models.py
class RecommendationEngine:
    """
    Machine learning-based recommendation engine.
    """
    def __init__(self):
        self.model = None
        self.vectorizer = None
    
    def train_collaborative_filtering(self, user_ratings):
        """
        Train collaborative filtering model.
        """
        from sklearn.decomposition import NMF
        
        # Create user-item matrix
        user_item_matrix = self._create_user_item_matrix(user_ratings)
        
        # Train NMF model
        self.model = NMF(n_components=50, random_state=42)
        self.model.fit(user_item_matrix)
        
        return self.model
    
    def get_recommendations(self, user_id, n_recommendations=10):
        """
        Get product recommendations for a user.
        """
        if not self.model:
            return []
        
        # Get user's rating vector
        user_ratings = self._get_user_ratings(user_id)
        
        # Predict ratings for all items
        predicted_ratings = self.model.transform(user_ratings)
        
        # Get top recommendations
        recommendations = np.argsort(predicted_ratings[0])[-n_recommendations:][::-1]
        
        return recommendations
```

---

## 🔒 **Security Implementation**

### **1. Input Validation**

#### **Custom Validators**
```python
# config/validators.py
class PasswordValidator:
    """
    Custom password validator for enhanced security.
    """
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        
        if not any(c.isupper() for c in password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        if not any(c.islower() for c in password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        if not any(c.isdigit() for c in password):
            raise ValidationError('Password must contain at least one digit.')
        
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            raise ValidationError('Password must contain at least one special character.')

class MobileNumberValidator:
    """
    Validator for Iranian mobile numbers.
    """
    def __call__(self, value):
        if not re.match(r'^09\d{9}$', value):
            raise ValidationError('Invalid mobile number format.')
        return value
```

### **2. Rate Limiting**

#### **API Rate Limiting**
```python
# apps/core/throttling.py
class CustomAnonRateThrottle(AnonRateThrottle):
    """
    Custom rate limiting for anonymous users.
    """
    scope = 'anon'
    rate = '100/hour'

class CustomUserRateThrottle(UserRateThrottle):
    """
    Custom rate limiting for authenticated users.
    """
    scope = 'user'
    rate = '1000/hour'

class CustomBurstRateThrottle(UserRateThrottle):
    """
    Burst rate limiting for high-frequency endpoints.
    """
    scope = 'burst'
    rate = '10/minute'
```

---

## ⚡ **Performance Optimization**

### **1. Database Optimization**

#### **Query Optimization**
```python
# apps/core/database_optimization.py
class DatabaseOptimizer:
    """
    Database optimization utilities.
    """
    @staticmethod
    def optimize_queries(queryset):
        """
        Optimize queryset with select_related and prefetch_related.
        """
        return queryset.select_related(
            'market', 'category', 'subcategory', 'user'
        ).prefetch_related(
            'images', 'tags', 'reviews'
        )
    
    @staticmethod
    def add_indexes():
        """
        Add database indexes for better performance.
        """
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Add indexes for frequently queried fields
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_product_market_category 
                ON product_product (market_id, category_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_user_status 
                ON order_order (user_id, status);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type_timestamp 
                ON analytics_event (event_type, timestamp);
            """)
```

### **2. Caching Strategy**

#### **Redis Caching**
```python
# apps/core/caching.py
class CacheManager:
    """
    Centralized cache management.
    """
    @staticmethod
    def get_or_set(key, callable_func, timeout=300):
        """
        Get value from cache or set it using callable.
        """
        value = cache.get(key)
        if value is None:
            value = callable_func()
            cache.set(key, value, timeout)
        return value
    
    @staticmethod
    def invalidate_pattern(pattern):
        """
        Invalidate cache keys matching pattern.
        """
        keys = cache.keys(pattern)
        if keys:
            cache.delete_many(keys)
    
    @staticmethod
    def cache_product_list(filters, page, page_size):
        """
        Cache product list with filters.
        """
        cache_key = f"product_list:{hash(str(filters))}:{page}:{page_size}"
        return cache.get(cache_key)
```

---

## 🧪 **Testing Strategy**

### **1. Unit Tests**

#### **Model Tests**
```python
# apps/users/tests/test_models.py
class UserModelTest(TestCase):
    """
    Test cases for User model.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09123456789',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_creation(self):
        self.assertEqual(self.user.mobile_number, '09123456789')
        self.assertEqual(self.user.first_name, 'Test')
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
    
    def test_user_str_representation(self):
        self.assertEqual(str(self.user), '09123456789')
    
    def test_user_full_name(self):
        self.assertEqual(self.user.get_full_name(), 'Test User')
```

#### **View Tests**
```python
# apps/users/tests/test_views.py
class PinCreateAPIViewTest(TestCase):
    """
    Test cases for PIN creation API.
    """
    def setUp(self):
        self.url = reverse('pin-create')
        self.valid_data = {'mobile_number': '09123456789'}
    
    def test_create_pin_success(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
    
    def test_create_pin_invalid_mobile(self):
        invalid_data = {'mobile_number': '123'}
        response = self.client.post(self.url, invalid_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
```

### **2. Integration Tests**

#### **API Integration Tests**
```python
# tests/test_api_integration.py
class APIIntegrationTest(TestCase):
    """
    Integration tests for API endpoints.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09123456789',
            first_name='Test',
            last_name='User'
        )
        self.token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')
    
    def test_product_list_api(self):
        response = self.client.get('/api/v1/user/product/list/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
    
    def test_market_list_api(self):
        response = self.client.get('/api/v1/user/market/public/list/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
```

### **3. Performance Tests**

#### **Load Testing**
```python
# tests/test_performance.py
class PerformanceTest(TestCase):
    """
    Performance tests for critical endpoints.
    """
    def test_product_list_performance(self):
        start_time = time.time()
        response = self.client.get('/api/v1/user/product/list/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 0.5)  # Should respond within 500ms
    
    def test_concurrent_requests(self):
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            response = self.client.get('/api/v1/user/product/list/')
            results.put(response.status_code)
        
        # Create 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all requests succeeded
        while not results.empty():
            self.assertEqual(results.get(), 200)
```

---

## 📝 **Code Standards**

### **1. Python Style Guide**
- **PEP 8 Compliance** - Follow Python style guide
- **Type Hints** - Use type annotations where appropriate
- **Docstrings** - Comprehensive documentation for all functions
- **Error Handling** - Proper exception handling

### **2. Django Best Practices**
- **Model Design** - Proper relationships and constraints
- **View Structure** - Clean, focused views
- **Serializer Usage** - Proper data serialization
- **URL Patterns** - RESTful URL design

### **3. API Design**
- **RESTful Principles** - Follow REST conventions
- **Consistent Responses** - Use ApiResponse utility
- **Error Handling** - Proper HTTP status codes
- **Documentation** - OpenAPI 3.0 compliance

---

## 🔧 **Development Tools**

### **1. Code Quality**
- **Black** - Code formatting
- **Flake8** - Linting
- **isort** - Import sorting
- **mypy** - Type checking

### **2. Testing Tools**
- **pytest** - Testing framework
- **pytest-django** - Django integration
- **coverage** - Code coverage
- **factory_boy** - Test data generation

### **3. Development Environment**
- **Docker** - Containerization
- **Docker Compose** - Multi-container setup
- **PostgreSQL** - Database
- **Redis** - Caching and sessions

---

<div align="center">

**📚 This documentation is maintained by the ASOUD development team**

[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?style=flat-square&logo=github)](https://github.com/your-repo)
[![Documentation](https://img.shields.io/badge/Documentation-Updated-green?style=flat-square)](../api/API_DOCUMENTATION.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>
