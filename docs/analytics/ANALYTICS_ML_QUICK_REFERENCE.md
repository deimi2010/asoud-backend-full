# 🚀 Analytics & ML Quick Reference
## راهنمای سریع - ASOUD Platform

---

## 📦 نصب و راه‌اندازی

### 1. فعال‌سازی Analytics App

```python
# config/settings/base.py
INSTALLED_APPS = [
    # ...
    'apps.analytics',  # ✅ Already added
]
```

### 2. نصب Dependencies

```bash
# همه dependencies موجود در requirements.txt
pip install -r requirements.txt

# یا فقط ML libraries
pip install numpy pandas scikit-learn tensorflow torch
```

### 3. Migrate Database

```bash
python manage.py migrate analytics
```

### 4. Train Models (اولین بار)

```bash
# Train همه models
python manage.py train_ml_models --model all --days 90

# یا هر کدوم جداگانه
python manage.py train_ml_models --model collaborative --days 60
python manage.py train_ml_models --model fraud --days 30
```

---

## ⚡ دستورات سریع

### Training Commands

```bash
# Train همه models با 90 روز data
python manage.py train_ml_models --model all --days 90

# Train Collaborative Filtering
python manage.py train_ml_models --model collaborative --days 60

# Train Fraud Detection
python manage.py train_ml_models --model fraud --days 30

# Update Recommendations
python manage.py update_ml_recommendations

# Generate Analytics
python manage.py generate_advanced_analytics
```

### Testing APIs

```bash
# Get Recommendations
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/analytics/recommendations/?type=collaborative&limit=5"

# Track Event
curl -X POST http://localhost:8000/api/v1/analytics/events/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"product_view","object_type":"product","object_id":"UUID"}'

# Fraud Detection
curl -X POST http://localhost:8000/api/v1/analytics/fraud-detection/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"transaction_id":"UUID","amount":1000000,"user_id":123}'
```

---

## 🎯 ML Models - Quick Usage

### 1. Collaborative Filtering (Recommendations)

```python
from apps.analytics.ml_models import CollaborativeFilteringModel
from django.core.cache import cache

# Get cached model
model = cache.get('collaborative_filtering_model')

if model:
    # Get recommendations
    recs = model.get_recommendations(user_id=123, n=10)
    # [{'product_id': UUID, 'score': 0.85}, ...]
```

### 2. Content-Based Filtering (Similar Products)

```python
from apps.analytics.ml_models import ContentBasedFilteringModel

model = cache.get('content_based_model')

if model:
    similar = model.get_similar_products(product_id=UUID, n=5)
    # [{'product_id': UUID, 'similarity': 0.92}, ...]
```

### 3. Fraud Detection

```python
from apps.analytics.fraud_detection import FraudDetectionEngine

engine = FraudDetectionEngine()

result = engine.detect_fraud([{
    'id': 'payment_uuid',
    'amount': 1000000,
    'user_id': 123,
    'timestamp': timezone.now()
}])

if result['fraud_count'] > 0:
    # Handle suspicious transaction
    pass
```

### 4. Customer Segmentation

```python
from apps.analytics.ml_models import CustomerSegmentationModel

model = cache.get('segmentation_model')

if model:
    segment = model.predict_segment(user_id=123)
    # {'segment_id': 0, 'segment_name': 'Champions'}
```

### 5. Price Optimization

```python
from apps.analytics.ml_models import PriceOptimizationModel

model = cache.get('price_optimization_model')

if model:
    optimal = model.optimize_price(
        product_id=UUID,
        current_price=1000000,
        target_metric='revenue'
    )
    # {'optimal_price': 950000, 'expected_change': {...}}
```

### 6. Demand Forecasting

```python
from apps.analytics.ml_models import DemandForecastingModel

model = cache.get('demand_forecasting_model')

if model:
    forecast = model.forecast(product_id=UUID, periods=30)
    # {'forecast': [100, 105, 98, ...], 'trend': 'increasing'}
```

---

## 🔌 API Endpoints Quick Reference

### Base URL
```
Production: https://api.asoud.ir/api/v1/analytics/
Local: http://localhost:8000/api/v1/analytics/
```

### Headers (All Requests)
```http
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/events/` | Track user events |
| GET | `/recommendations/` | Get ML recommendations |
| POST | `/fraud-detection/` | Check transaction fraud |
| GET | `/customer-segmentation/` | Get user segment |
| POST | `/price-optimization/` | Get optimal price |
| GET | `/demand-forecasting/` | Forecast demand |
| GET | `/sales/` | Sales analytics |
| GET | `/dashboard/` | Analytics dashboard |

---

## 📊 Event Tracking

### Event Types

```python
EVENT_TYPES = [
    'product_view',        # مشاهده محصول
    'add_to_cart',        # افزودن به سبد
    'remove_from_cart',   # حذف از سبد
    'purchase',           # خرید
    'search',             # جستجو
    'page_view',          # بازدید صفحه
    'click',              # کلیک
]
```

### Track Event (Python)

```python
from apps.analytics.models import UserBehaviorEvent

UserBehaviorEvent.objects.create(
    user=request.user,
    event_type='product_view',
    object_type='product',
    object_id=product_id,
    metadata={'source': 'search', 'query': 'laptop'}
)
```

### Track Event (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/analytics/events/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "product_view",
    "object_type": "product",
    "object_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {"source": "homepage"}
  }'
```

---

## 🔧 Celery Tasks (Auto Training)

### Setup Celery Beat

```python
# config/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Train models روزانه ساعت 2 صبح
    'train-ml-models-daily': {
        'task': 'apps.analytics.tasks.train_all_models',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Update recommendations هر 6 ساعت
    'update-recommendations': {
        'task': 'apps.analytics.tasks.update_recommendations',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # Calculate analytics هر ساعت
    'calculate-analytics': {
        'task': 'apps.analytics.tasks.calculate_analytics',
        'schedule': crontab(minute=0),
    },
}
```

### Create Tasks

```python
# apps/analytics/tasks.py
from celery import shared_task
from apps.analytics.ml_models import CollaborativeFilteringModel

@shared_task
def train_collaborative_model():
    model = CollaborativeFilteringModel()
    events = get_training_data()
    model.fit(events)
    cache.set('collaborative_model', model, 7200)
    return f"Trained with {len(events)} events"

@shared_task
def train_all_models():
    # Train all 6 models
    train_collaborative_model()
    train_content_based_model()
    train_price_optimization_model()
    # ...
```

### Run Celery

```bash
# Start worker
celery -A config worker -l info

# Start beat (scheduler)
celery -A config beat -l info

# Both در production
celery -A config worker -B -l info
```

---

## 💾 Caching Strategy

### Model Caching

```python
from django.core.cache import cache

# Cache trained model (2 hours)
cache.set('collaborative_model', model, timeout=7200)

# Get cached model
model = cache.get('collaborative_model')

# Cache predictions (5 minutes)
cache_key = f'recs:user:{user_id}'
recommendations = cache.get(cache_key)

if not recommendations:
    recommendations = model.get_recommendations(user_id, n=10)
    cache.set(cache_key, recommendations, timeout=300)
```

### Cache Keys Pattern

```python
# Models
'collaborative_model'
'content_based_model'
'fraud_detection_model'
'segmentation_model'

# Predictions
f'recs:user:{user_id}'
f'similar:product:{product_id}'
f'segment:user:{user_id}'
f'price:product:{product_id}'
```

---

## 🎨 Integration Snippets

### Django View

```python
from rest_framework.views import APIView
from django.core.cache import cache

class ProductDetailView(APIView):
    def get(self, request, pk):
        product = Product.objects.get(id=pk)
        
        # Track view
        UserBehaviorEvent.objects.create(
            user=request.user,
            event_type='product_view',
            object_id=pk
        )
        
        # Get recommendations
        model = cache.get('content_based_model')
        recommendations = []
        
        if model:
            similar = model.get_similar_products(pk, n=5)
            recommendations = Product.objects.filter(
                id__in=[r['product_id'] for r in similar]
            )
        
        return Response({
            'product': ProductSerializer(product).data,
            'recommendations': ProductSerializer(recommendations, many=True).data
        })
```

### Flutter/Dart

```dart
// Track event
await dio.post('/analytics/events/', data: {
  'event_type': 'product_view',
  'object_type': 'product',
  'object_id': productId,
});

// Get recommendations
final response = await dio.get('/analytics/recommendations/',
  queryParameters: {'type': 'hybrid', 'limit': 10}
);

final recs = (response.data['data']['recommendations'] as List)
  .map((r) => Product.fromJson(r))
  .toList();
```

---

## 📈 Performance Monitoring

### Check Model Status

```python
from django.core.cache import cache

models = [
    'collaborative_filtering_model',
    'content_based_model',
    'fraud_detection_model',
    'segmentation_model',
    'price_optimization_model',
    'demand_forecasting_model',
]

for model_key in models:
    model = cache.get(model_key)
    status = '✅ Cached' if model else '❌ Missing'
    print(f'{model_key}: {status}')
```

### Check Analytics Data

```python
from apps.analytics.models import UserBehaviorEvent

# Count events by type
from django.db.models import Count

stats = UserBehaviorEvent.objects.values('event_type').annotate(
    count=Count('id')
).order_by('-count')

for stat in stats:
    print(f"{stat['event_type']}: {stat['count']}")
```

### API Performance

```bash
# Test response times
time curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/analytics/recommendations/"

# Expected: <100ms
```

---

## ⚠️ Troubleshooting

### Model Not Found

```python
# Problem
model = cache.get('collaborative_model')  # None

# Solution
python manage.py train_ml_models --model collaborative --days 60
```

### Insufficient Data

```python
# Check data count
from apps.analytics.models import UserBehaviorEvent

count = UserBehaviorEvent.objects.filter(
    event_type='purchase'
).count()

print(f'Purchase events: {count}')
# Need: >1000 for good results
```

### High Memory Usage

```python
# Use batch processing
from django.core.paginator import Paginator

queryset = UserBehaviorEvent.objects.all()
paginator = Paginator(queryset, 10000)

for page_num in paginator.page_range:
    batch = list(paginator.page(page_num))
    model.partial_fit(batch)
```

### Slow API Response

```python
# Add caching
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

@method_decorator(cache_page(300))
class RecommendationsView(APIView):
    def get(self, request):
        # ...
```

---

## 🔗 Quick Links

- 📖 Full Documentation: `ANALYTICS_ML_DOCUMENTATION.md`
- 🔧 API Docs: https://api.asoud.ir/docs/
- 📊 Dashboard: https://analytics.asoud.ir/
- 📈 Grafana: https://grafana.asoud.ir/

---

## 🎯 Common Use Cases

### 1. Add Recommendations to Product Page
```python
# View
model = cache.get('content_based_model')
similar_products = model.get_similar_products(product_id, n=5)

# Response
{
  'product': {...},
  'recommendations': [...]
}
```

### 2. Personalized Homepage
```python
model = cache.get('collaborative_filtering_model')
recommendations = model.get_recommendations(user_id, n=20)
```

### 3. Fraud Check at Checkout
```python
engine = FraudDetectionEngine()
result = engine.detect_fraud([transaction])

if result['fraud_count'] > 0:
    # Block or review
    payment.status = 'pending_review'
```

### 4. Dynamic Pricing
```python
model = cache.get('price_optimization_model')
optimal = model.optimize_price(product_id, current_price, 'revenue')

# Show suggestion to owner
suggested_price = optimal['optimal_price']
```

### 5. Customer Segmentation Dashboard
```python
model = cache.get('segmentation_model')
segments = model.get_segments()

# Show segment distribution
for segment in segments['segments']:
    print(f"{segment['name']}: {segment['count']} customers")
```

---

**Version:** 1.0.0  
**Last Updated:** October 24, 2025  
**For:** Quick reference and daily use
