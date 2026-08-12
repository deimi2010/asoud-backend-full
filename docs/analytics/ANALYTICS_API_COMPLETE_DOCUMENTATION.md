# 📊 Analytics & ML API - Complete Documentation

## Base URL
```
Production: https://api.asoud.ir/api/v1/analytics/
Development: http://localhost:8000/api/v1/analytics/
```

## Authentication
All endpoints require JWT authentication:
```http
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 📑 Table of Contents

1. [User Behavior Events](#1-user-behavior-events)
2. [User Sessions](#2-user-sessions)
3. [Product Analytics](#3-product-analytics)
4. [Market Analytics](#4-market-analytics)
5. [User Analytics](#5-user-analytics)
6. [Analytics Dashboard](#6-analytics-dashboard)
7. [ML Recommendations](#7-ml-recommendations)

---

## 1. User Behavior Events

### 1.1 List Events
**Endpoint:** `GET /events/`

**Description:** Get list of user behavior events (filtered for non-admin users)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Items per page (default: 20) |
| event_type | string | No | Filter by event type |
| start_date | datetime | No | Filter from date |
| end_date | datetime | No | Filter to date |

**Response 200:**
```json
{
  "count": 150,
  "next": "http://api.asoud.ir/api/v1/analytics/events/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 123,
        "username": "user123",
        "email": "user@example.com"
      },
      "event_type": "product_view",
      "object_type": "product",
      "object_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {
        "source": "homepage",
        "category": "electronics"
      },
      "timestamp": "2025-10-24T10:30:00Z",
      "session_id": "session-uuid-here"
    }
  ]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/events/?event_type=product_view&page=1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 1.2 Create Event
**Endpoint:** `POST /events/`

**Description:** Track a new user behavior event

**Request Body:**
```json
{
  "event_type": "product_view",
  "object_type": "product",
  "object_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "source": "search",
    "query": "laptop",
    "position": 3
  }
}
```

**Event Types:**
- `product_view` - User viewed a product
- `add_to_cart` - User added item to cart
- `remove_from_cart` - User removed item from cart
- `purchase` - User completed purchase
- `search` - User performed search
- `page_view` - User viewed a page
- `click` - User clicked on element

**Response 201:**
```json
{
  "id": 151,
  "user": {
    "id": 123,
    "username": "user123"
  },
  "event_type": "product_view",
  "object_type": "product",
  "object_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "source": "search",
    "query": "laptop",
    "position": 3
  },
  "timestamp": "2025-10-24T11:00:00Z",
  "session_id": "auto-generated-uuid"
}
```

**cURL Example:**
```bash
curl -X POST "https://api.asoud.ir/api/v1/analytics/events/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "product_view",
    "object_type": "product",
    "object_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {"source": "homepage"}
  }'
```

---

### 1.3 Events by Type
**Endpoint:** `GET /events/by_event_type/`

**Description:** Get events grouped by event type with statistics

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| event_type | string | No | Filter specific event type |
| days | integer | No | Days to look back (default: 30) |

**Response 200:**
```json
[
  {
    "event_type": "product_view",
    "count": 1250,
    "unique_users": 450
  },
  {
    "event_type": "add_to_cart",
    "count": 320,
    "unique_users": 180
  },
  {
    "event_type": "purchase",
    "count": 89,
    "unique_users": 75
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/events/by_event_type/?days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 1.4 Events Timeline
**Endpoint:** `GET /events/timeline/`

**Description:** Get events timeline grouped by hour

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| event_type | string | No | Filter specific event type |
| days | integer | No | Days to look back (default: 7) |

**Response 200:**
```json
[
  {
    "hour": "2025-10-24T10:00:00Z",
    "count": 45
  },
  {
    "hour": "2025-10-24T11:00:00Z",
    "count": 67
  },
  {
    "hour": "2025-10-24T12:00:00Z",
    "count": 89
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/events/timeline/?event_type=purchase&days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 2. User Sessions

### 2.1 List Sessions
**Endpoint:** `GET /sessions/`

**Description:** Get user sessions (filtered for non-admin users)

**Response 200:**
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 123,
        "username": "user123"
      },
      "session_id": "session-uuid-here",
      "start_time": "2025-10-24T10:00:00Z",
      "end_time": "2025-10-24T10:45:00Z",
      "duration": 2700,
      "page_views": 15,
      "events_count": 8,
      "converted": true,
      "conversion_value": 1500000,
      "device_type": "mobile",
      "device_info": {
        "os": "Android",
        "browser": "Chrome",
        "version": "120.0"
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  ]
}
```

---

### 2.2 Active Sessions
**Endpoint:** `GET /sessions/active_sessions/`

**Description:** Get currently active sessions

**Response 200:**
```json
[
  {
    "id": 52,
    "user": {
      "id": 125,
      "username": "active_user"
    },
    "session_id": "active-session-uuid",
    "start_time": "2025-10-24T11:30:00Z",
    "end_time": null,
    "duration": null,
    "page_views": 5,
    "events_count": 3
  }
]
```

---

### 2.3 Conversion Analysis
**Endpoint:** `GET /sessions/conversion_analysis/`

**Description:** Get session conversion statistics

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to analyze (default: 30) |

**Response 200:**
```json
{
  "total_sessions": 1500,
  "converted_sessions": 180,
  "conversion_rate": 12.0,
  "avg_session_duration": 1800,
  "avg_conversion_value": 850000
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/sessions/conversion_analysis/?days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 3. Product Analytics

### 3.1 List Product Analytics
**Endpoint:** `GET /product-analytics/`

**Description:** Get analytics for all products

**Response 200:**
```json
{
  "count": 100,
  "results": [
    {
      "id": 1,
      "product": {
        "id": "uuid",
        "name": "Laptop Dell XPS 15",
        "price": 25000000
      },
      "total_views": 1250,
      "unique_viewers": 450,
      "total_clicks": 320,
      "total_cart_adds": 89,
      "total_purchases": 45,
      "total_revenue": 1125000000,
      "conversion_rate": 14.06,
      "avg_time_on_page": 180,
      "bounce_rate": 35.5,
      "popularity_score": 87.5,
      "trending_score": 92.3,
      "date": "2025-10-24"
    }
  ]
}
```

---

### 3.2 Top Products
**Endpoint:** `GET /product-analytics/top_products/`

**Description:** Get top performing products

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of products (default: 10) |
| metric | string | No | Metric to sort by (default: popularity_score) |

**Metric Options:**
- `popularity_score` - Overall popularity
- `total_views` - Most viewed
- `total_purchases` - Most purchased
- `total_revenue` - Highest revenue
- `conversion_rate` - Best conversion

**Response 200:**
```json
[
  {
    "id": 1,
    "product": {
      "id": "uuid",
      "name": "Laptop Dell XPS 15",
      "image": "https://cdn.asoud.ir/products/laptop.jpg"
    },
    "total_views": 1250,
    "total_purchases": 45,
    "total_revenue": 1125000000,
    "conversion_rate": 14.06,
    "popularity_score": 87.5
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/product-analytics/top_products/?limit=5&metric=total_revenue" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 3.3 Trending Products
**Endpoint:** `GET /product-analytics/trending_products/`

**Description:** Get trending products based on recent activity

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of products (default: 10) |

**Response 200:**
```json
[
  {
    "id": 5,
    "product": {
      "id": "uuid",
      "name": "iPhone 15 Pro",
      "price": 45000000
    },
    "trending_score": 95.8,
    "total_views": 890,
    "growth_rate": 125.5
  }
]
```

---

### 3.4 Calculate Product Metrics
**Endpoint:** `POST /product-analytics/{id}/calculate_metrics/`

**Description:** Recalculate metrics for a specific product

**Response 200:**
```json
{
  "id": 1,
  "product": {"id": "uuid", "name": "Product Name"},
  "total_views": 1300,
  "conversion_rate": 14.5,
  "popularity_score": 88.2,
  "message": "Metrics recalculated successfully"
}
```

---

## 4. Market Analytics

### 4.1 List Market Analytics
**Endpoint:** `GET /market-analytics/`

**Description:** Get analytics for all markets

**Response 200:**
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "market": {
        "id": "uuid",
        "name": "بازار الکترونیک تهران",
        "owner": "Market Owner"
      },
      "total_products": 150,
      "active_products": 135,
      "total_sales": 450,
      "total_revenue": 45000000000,
      "total_visitors": 12500,
      "unique_visitors": 8900,
      "conversion_rate": 3.6,
      "avg_order_value": 100000000,
      "rating_avg": 4.5,
      "rating_count": 230,
      "date": "2025-10-24"
    }
  ]
}
```

---

### 4.2 Top Markets
**Endpoint:** `GET /market-analytics/top_markets/`

**Description:** Get top performing markets

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of markets (default: 10) |
| metric | string | No | Metric to sort by (default: total_revenue) |

**Metric Options:**
- `total_revenue` - Highest revenue
- `total_sales` - Most sales
- `total_visitors` - Most visitors
- `conversion_rate` - Best conversion
- `rating_avg` - Highest rated

**Response 200:**
```json
[
  {
    "id": 1,
    "market": {
      "id": "uuid",
      "name": "بازار الکترونیک تهران"
    },
    "total_revenue": 45000000000,
    "total_sales": 450,
    "conversion_rate": 3.6,
    "rating_avg": 4.5
  }
]
```

---

### 4.3 Market Comparison
**Endpoint:** `GET /market-analytics/market_comparison/`

**Description:** Compare multiple markets

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| market_ids | array | Yes | List of market IDs to compare |

**Request Example:**
```
GET /market-analytics/market_comparison/?market_ids=1&market_ids=2&market_ids=3
```

**Response 200:**
```json
[
  {
    "id": 1,
    "market": {"id": "uuid", "name": "Market 1"},
    "total_revenue": 45000000000,
    "total_sales": 450,
    "conversion_rate": 3.6
  },
  {
    "id": 2,
    "market": {"id": "uuid", "name": "Market 2"},
    "total_revenue": 38000000000,
    "total_sales": 380,
    "conversion_rate": 3.2
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/market-analytics/market_comparison/?market_ids=1&market_ids=2" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 5. User Analytics

### 5.1 List User Analytics
**Endpoint:** `GET /user-analytics/`

**Description:** Get analytics for all users (admin only)

**Response 200:**
```json
{
  "count": 500,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 123,
        "username": "user123",
        "email": "user@example.com"
      },
      "total_sessions": 45,
      "total_page_views": 320,
      "avg_session_duration": 1800,
      "last_activity": "2025-10-24T11:00:00Z",
      "total_orders": 12,
      "total_spent": 15000000,
      "avg_order_value": 1250000,
      "last_purchase": "2025-10-20T15:30:00Z",
      "preferred_categories": ["electronics", "fashion"],
      "preferred_price_range": {
        "min": 500000,
        "max": 2000000
      },
      "shopping_patterns": {
        "preferred_time": "evening",
        "preferred_day": "weekend"
      },
      "customer_segment": "Champions",
      "churn_probability": 0.12,
      "lifetime_value": 25000000
    }
  ]
}
```

---

### 5.2 Top Customers
**Endpoint:** `GET /user-analytics/top_customers/`

**Description:** Get top customers by spending

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of customers (default: 10) |

**Response 200:**
```json
[
  {
    "id": 1,
    "user": {
      "id": 123,
      "username": "top_customer",
      "email": "customer@example.com"
    },
    "total_spent": 50000000,
    "total_orders": 35,
    "avg_order_value": 1428571,
    "lifetime_value": 75000000,
    "customer_segment": "Champions"
  }
]
```

---

### 5.3 Customer Segments
**Endpoint:** `GET /user-analytics/customer_segments/`

**Description:** Get customer segmentation distribution

**Response 200:**
```json
[
  {
    "customer_segment": "Champions",
    "count": 45,
    "avg_spent": 25000000,
    "avg_orders": 15
  },
  {
    "customer_segment": "Loyal Customers",
    "count": 120,
    "avg_spent": 12000000,
    "avg_orders": 8
  },
  {
    "customer_segment": "At Risk",
    "count": 35,
    "avg_spent": 8000000,
    "avg_orders": 5
  }
]
```

**Customer Segments:**
- **Champions** - Best customers (high value, high frequency)
- **Loyal Customers** - Regular buyers
- **Potential Loyalists** - Recent customers with potential
- **New Customers** - Just started buying
- **At Risk** - Used to buy, might churn
- **Can't Lose Them** - High value but decreasing
- **Hibernating** - Haven't bought recently
- **Lost** - Churned customers

---

### 5.4 User Insights
**Endpoint:** `GET /user-analytics/{id}/insights/`

**Description:** Get detailed insights and ML recommendations for a user

**Response 200:**
```json
{
  "user_id": 123,
  "username": "user123",
  "total_sessions": 45,
  "total_page_views": 320,
  "avg_session_duration": 1800,
  "last_activity": "2025-10-24T11:00:00Z",
  "total_orders": 12,
  "total_spent": 15000000,
  "avg_order_value": 1250000,
  "last_purchase": "2025-10-20T15:30:00Z",
  "preferred_categories": ["electronics", "fashion"],
  "preferred_price_range": {
    "min": 500000,
    "max": 2000000
  },
  "shopping_patterns": {
    "preferred_time": "evening",
    "preferred_day": "weekend",
    "device_preference": "mobile"
  },
  "customer_segment": "Champions",
  "churn_probability": 0.12,
  "lifetime_value": 25000000,
  "recommended_products": [
    {
      "id": "uuid",
      "name": "Product 1",
      "score": 0.95,
      "reason": "Based on your browsing history"
    }
  ],
  "recommended_categories": ["electronics", "home"],
  "recommended_markets": [
    {
      "id": "uuid",
      "name": "Market 1",
      "score": 0.88
    }
  ]
}
```

---

## 6. Analytics Dashboard

### 6.1 Dashboard Overview
**Endpoint:** `GET /dashboard/`

**Description:** Get comprehensive dashboard data (cached for 5 minutes)

**Response 200:**
```json
{
  "overview": {
    "total_users": 1500,
    "active_users_today": 450,
    "total_sessions_today": 890,
    "total_page_views_today": 5600,
    "total_revenue_today": 125000000,
    "total_orders_today": 89
  },
  "trends": {
    "users_growth": 12.5,
    "revenue_growth": 18.3,
    "orders_growth": 15.7
  },
  "top_products": [
    {
      "id": "uuid",
      "name": "Product 1",
      "views": 1250,
      "sales": 45
    }
  ],
  "top_markets": [
    {
      "id": "uuid",
      "name": "Market 1",
      "revenue": 45000000
    }
  ],
  "conversion_funnel": {
    "product_views": 5000,
    "cart_adds": 800,
    "checkouts": 400,
    "purchases": 180
  },
  "geographic_distribution": {
    "Tehran": 450,
    "Shiraz": 120,
    "Isfahan": 95
  }
}
```

---

### 6.2 Real-Time Metrics
**Endpoint:** `GET /dashboard/real_time/`

**Description:** Get real-time analytics metrics

**Response 200:**
```json
{
  "active_users": 450,
  "current_sessions": 520,
  "page_views_last_hour": 1250,
  "events_last_minute": 45,
  "recent_purchases": [
    {
      "product": "Product Name",
      "amount": 1500000,
      "timestamp": "2025-10-24T11:58:30Z"
    }
  ],
  "trending_products": [
    {"id": "uuid", "name": "Product 1", "trend": "up"}
  ]
}
```

---

### 6.3 Time Series Data
**Endpoint:** `GET /dashboard/time_series/`

**Description:** Get time series data for charts

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to include (default: 30) |
| metric | string | No | Metric to track (default: revenue) |

**Metric Options:**
- `revenue` - Daily revenue
- `orders` - Daily orders
- `users` - Daily active users
- `sessions` - Daily sessions
- `page_views` - Daily page views

**Response 200:**
```json
{
  "metric": "revenue",
  "period": "30_days",
  "data": [
    {
      "date": "2025-09-24",
      "value": 98000000
    },
    {
      "date": "2025-09-25",
      "value": 105000000
    },
    {
      "date": "2025-10-24",
      "value": 125000000
    }
  ],
  "total": 3150000000,
  "average": 105000000,
  "trend": "increasing"
}
```

---

### 6.4 Top Performers
**Endpoint:** `GET /dashboard/top_performers/`

**Description:** Get top performing entities

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | No | Entity type (default: products) |
| limit | integer | No | Number of items (default: 10) |

**Type Options:**
- `products` - Top products
- `markets` - Top markets
- `categories` - Top categories
- `users` - Top customers

**Response 200:**
```json
{
  "type": "products",
  "items": [
    {
      "id": "uuid",
      "name": "Product 1",
      "metric_value": 1125000000,
      "metric_name": "revenue"
    }
  ]
}
```

---

### 6.5 Conversion Funnel
**Endpoint:** `GET /dashboard/conversion_funnel/`

**Description:** Get conversion funnel analysis

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to analyze (default: 30) |

**Response 200:**
```json
{
  "funnel": [
    {
      "stage": "Product Views",
      "count": 5000,
      "percentage": 100,
      "drop_off": 0
    },
    {
      "stage": "Add to Cart",
      "count": 800,
      "percentage": 16,
      "drop_off": 84
    },
    {
      "stage": "Checkout Initiated",
      "count": 400,
      "percentage": 8,
      "drop_off": 50
    },
    {
      "stage": "Purchase Completed",
      "count": 180,
      "percentage": 3.6,
      "drop_off": 55
    }
  ],
  "overall_conversion_rate": 3.6,
  "optimization_suggestions": [
    "Optimize cart page to reduce 84% drop-off",
    "Simplify checkout process"
  ]
}
```

---

### 6.6 Geographic Analysis
**Endpoint:** `GET /dashboard/geographic_analysis/`

**Description:** Get geographic distribution of users/sales

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to analyze (default: 30) |

**Response 200:**
```json
{
  "by_city": [
    {
      "city": "Tehran",
      "users": 450,
      "orders": 890,
      "revenue": 125000000
    },
    {
      "city": "Shiraz",
      "users": 120,
      "orders": 230,
      "revenue": 35000000
    }
  ],
  "by_province": [
    {
      "province": "Tehran",
      "users": 600,
      "orders": 1200,
      "revenue": 180000000
    }
  ],
  "top_regions": [
    {"region": "Tehran", "percentage": 45.5}
  ]
}
```

---

### 6.7 Device Analysis
**Endpoint:** `GET /dashboard/device_analysis/`

**Description:** Get device and platform analysis

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to analyze (default: 30) |

**Response 200:**
```json
{
  "by_device_type": [
    {
      "device_type": "mobile",
      "sessions": 1250,
      "percentage": 65.5,
      "avg_session_duration": 1200
    },
    {
      "device_type": "desktop",
      "sessions": 550,
      "percentage": 28.8,
      "avg_session_duration": 2400
    },
    {
      "device_type": "tablet",
      "sessions": 108,
      "percentage": 5.7,
      "avg_session_duration": 1800
    }
  ],
  "by_os": [
    {"os": "Android", "count": 750, "percentage": 60.0},
    {"os": "iOS", "count": 350, "percentage": 28.0},
    {"os": "Windows", "count": 150, "percentage": 12.0}
  ],
  "by_browser": [
    {"browser": "Chrome", "count": 980, "percentage": 78.4},
    {"browser": "Safari", "count": 180, "percentage": 14.4},
    {"browser": "Firefox", "count": 90, "percentage": 7.2}
  ]
}
```

---

## 7. ML Recommendations

### 7.1 Product Recommendations
**Endpoint:** `GET /ml-recommendations/product_recommendations/`

**Description:** Get personalized product recommendations for current user

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Number of recommendations (default: 10) |
| algorithm | string | No | Algorithm to use (collaborative/content/hybrid) |

**Response 200:**
```json
{
  "user_id": 123,
  "recommendations": [
    {
      "product": {
        "id": "uuid",
        "name": "Laptop Dell XPS 15",
        "price": 25000000,
        "image": "https://cdn.asoud.ir/products/laptop.jpg"
      },
      "score": 0.95,
      "reason": "Based on your recent purchases in electronics",
      "algorithm": "collaborative_filtering"
    },
    {
      "product": {
        "id": "uuid",
        "name": "iPhone 15 Pro",
        "price": 45000000,
        "image": "https://cdn.asoud.ir/products/iphone.jpg"
      },
      "score": 0.88,
      "reason": "Frequently bought together with your cart items",
      "algorithm": "content_based"
    }
  ],
  "cached": false,
  "generated_at": "2025-10-24T12:00:00Z"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/ml-recommendations/product_recommendations/?limit=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 7.2 Similar Products
**Endpoint:** `GET /ml-recommendations/similar_products/`

**Description:** Get similar products based on content similarity

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | string | Yes | Product ID to find similar products |
| limit | integer | No | Number of recommendations (default: 10) |

**Response 200:**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "similar_products": [
    {
      "product": {
        "id": "uuid",
        "name": "Similar Product 1",
        "price": 23000000
      },
      "similarity": 0.92,
      "common_features": ["brand", "category", "price_range"]
    },
    {
      "product": {
        "id": "uuid",
        "name": "Similar Product 2",
        "price": 27000000
      },
      "similarity": 0.85,
      "common_features": ["category", "specs"]
    }
  ]
}
```

**Response 400 - Missing product_id:**
```json
{
  "error": "product_id parameter is required"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/ml-recommendations/similar_products/?product_id=550e8400-e29b-41d4-a716-446655440000&limit=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 7.3 Price Optimization
**Endpoint:** `GET /ml-recommendations/price_optimization/`

**Description:** Get optimal price suggestions for a product

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | string | Yes | Product ID for optimization |
| target | string | No | Optimization target (revenue/sales/profit) |

**Response 200:**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_price": 25000000,
  "optimal_price": 23500000,
  "price_change": -1500000,
  "price_change_percentage": -6.0,
  "expected_impact": {
    "sales_increase": 18.5,
    "revenue_increase": 12.3,
    "profit_increase": 8.7
  },
  "confidence": 0.87,
  "recommendation": "Lower price by 6% to maximize revenue",
  "price_elasticity": -1.8,
  "competitive_analysis": {
    "market_avg_price": 24000000,
    "min_competitor_price": 22000000,
    "max_competitor_price": 28000000
  }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/ml-recommendations/price_optimization/?product_id=uuid&target=revenue" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 7.4 Demand Forecasting
**Endpoint:** `GET /ml-recommendations/demand_forecast/`

**Description:** Forecast future demand for a product

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | string | Yes | Product ID for forecast |
| days | integer | No | Days to forecast (default: 30) |

**Response 200:**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_name": "Laptop Dell XPS 15",
  "forecast_period": 30,
  "forecast": [
    {
      "date": "2025-10-25",
      "predicted_sales": 15,
      "confidence_interval": {
        "lower": 12,
        "upper": 18
      }
    },
    {
      "date": "2025-10-26",
      "predicted_sales": 18,
      "confidence_interval": {
        "lower": 14,
        "upper": 22
      }
    }
  ],
  "total_forecast": 450,
  "trend": "increasing",
  "seasonality": {
    "detected": true,
    "pattern": "weekly",
    "peak_days": ["saturday", "sunday"]
  },
  "recommendations": [
    "Stock up for weekend demand",
    "Expected 20% increase next week"
  ]
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/ml-recommendations/demand_forecast/?product_id=uuid&days=14" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 7.5 Customer Segmentation
**Endpoint:** `GET /ml-recommendations/customer_segmentation/`

**Description:** Get ML-based customer segmentation analysis

**Response 200:**
```json
{
  "total_customers": 1500,
  "segments": [
    {
      "segment_id": 0,
      "segment_name": "Champions",
      "count": 180,
      "percentage": 12.0,
      "characteristics": {
        "avg_spent": 25000000,
        "avg_orders": 15,
        "avg_recency": 5,
        "avg_frequency": 12,
        "avg_monetary": 25000000
      },
      "recommended_actions": [
        "VIP treatment",
        "Early access to new products",
        "Exclusive discounts"
      ]
    },
    {
      "segment_id": 1,
      "segment_name": "Loyal Customers",
      "count": 450,
      "percentage": 30.0,
      "characteristics": {
        "avg_spent": 12000000,
        "avg_orders": 8,
        "avg_recency": 15,
        "avg_frequency": 7,
        "avg_monetary": 12000000
      },
      "recommended_actions": [
        "Loyalty rewards",
        "Personalized recommendations",
        "Upsell opportunities"
      ]
    },
    {
      "segment_id": 2,
      "segment_name": "At Risk",
      "count": 120,
      "percentage": 8.0,
      "characteristics": {
        "avg_spent": 8000000,
        "avg_orders": 5,
        "avg_recency": 60,
        "avg_frequency": 3,
        "avg_monetary": 8000000
      },
      "recommended_actions": [
        "Win-back campaigns",
        "Special offers",
        "Re-engagement emails"
      ]
    }
  ],
  "segmentation_method": "K-Means Clustering",
  "features_used": ["recency", "frequency", "monetary"],
  "model_accuracy": 0.89
}
```

---

### 7.6 Fraud Detection
**Endpoint:** `GET /ml-recommendations/fraud_detection/`

**Description:** Get fraud detection analysis for recent transactions

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | integer | No | Days to analyze (default: 7) |
| threshold | float | No | Fraud score threshold (default: 0.7) |

**Response 200:**
```json
{
  "analysis_period": 7,
  "total_transactions": 890,
  "flagged_transactions": 12,
  "fraud_percentage": 1.35,
  "suspicious_transactions": [
    {
      "transaction_id": "uuid",
      "user_id": 456,
      "amount": 50000000,
      "fraud_score": 0.89,
      "risk_level": "high",
      "fraud_indicators": [
        "Unusual transaction amount",
        "New payment method",
        "Multiple failed attempts",
        "IP address mismatch"
      ],
      "timestamp": "2025-10-24T10:30:00Z",
      "recommended_action": "Manual review required"
    },
    {
      "transaction_id": "uuid",
      "user_id": 789,
      "amount": 15000000,
      "fraud_score": 0.73,
      "risk_level": "medium",
      "fraud_indicators": [
        "Velocity check failed",
        "Unusual time of purchase"
      ],
      "timestamp": "2025-10-24T09:15:00Z",
      "recommended_action": "Additional verification"
    }
  ],
  "fraud_patterns": {
    "peak_fraud_hours": ["02:00-04:00", "23:00-01:00"],
    "high_risk_amount_range": {
      "min": 30000000,
      "max": 100000000
    },
    "common_indicators": [
      "Multiple payment methods",
      "Rapid transactions",
      "IP mismatches"
    ]
  },
  "model_performance": {
    "accuracy": 0.94,
    "precision": 0.87,
    "recall": 0.91,
    "f1_score": 0.89
  }
}
```

**cURL Example:**
```bash
curl -X GET "https://api.asoud.ir/api/v1/analytics/ml-recommendations/fraud_detection/?days=3&threshold=0.8" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🔐 Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 400 Bad Request
```json
{
  "error": "Invalid parameter",
  "details": {
    "field": ["This field is required."]
  }
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

---

## 📈 Rate Limiting

All API endpoints are rate-limited:

- **Authenticated users:** 1000 requests/hour
- **Anonymous users:** 100 requests/hour
- **ML endpoints:** 100 requests/hour (computationally expensive)

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1635174000
```

---

## 🎯 Best Practices

### 1. Use Caching
Many endpoints cache data for 5-15 minutes. Don't make excessive requests.

### 2. Pagination
Always use pagination for list endpoints to avoid large response sizes.

### 3. Filter Data
Use query parameters to filter data and reduce response size:
```bash
# Good
GET /events/?event_type=purchase&days=7

# Avoid
GET /events/  # Returns all events
```

### 4. Batch Requests
For ML recommendations, batch similar requests:
```bash
# Good - Get all recommendations at once
GET /ml-recommendations/product_recommendations/?limit=20

# Avoid - Multiple requests
GET /ml-recommendations/product_recommendations/?limit=5
GET /ml-recommendations/similar_products/?product_id=...
```

### 5. Monitor Performance
Check response times and use cached endpoints when possible.

---

## 📚 Related Documentation

- **Full ML Guide:** `ANALYTICS_ML_DOCUMENTATION.md`
- **Quick Reference:** `ANALYTICS_ML_QUICK_REFERENCE.md`
- **API Progress:** `../api/API_DOCUMENTATION_PROGRESS.md`

---

**Version:** 1.0.0  
**Last Updated:** October 24, 2025  
**Total Endpoints:** 30+  
**Status:** ✅ Complete
