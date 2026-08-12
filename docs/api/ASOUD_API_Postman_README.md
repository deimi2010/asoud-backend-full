# ASOUD Platform - Complete Postman Collection

## 📋 Overview

This repository contains a comprehensive Postman collection for the ASOUD Platform API with **255+ endpoints** covering all major functionalities including:

- 🔐 Authentication & User Management
- 🏪 Market Management
- 📦 Product Management
- 🛒 Cart & Order Management
- 💳 Payment System
- 💬 Chat & Support System
- 🔔 Notification System
- 📊 Analytics & ML
- 📱 SMS Services
- 💰 Wallet System
- 🤝 Affiliate System
- 🔗 Referral System
- 💰 Price Inquiry System
- 📅 Reservation System
- 📢 Advertisement System
- 💬 Comment System
- 🎫 Discount System
- 📂 Category Management
- 🌍 Region Management
- ℹ️ Information Services
- 🔒 Security & System Endpoints
- 📱 Flutter-Specific Endpoints
- 🌐 WebSocket Endpoints

## 🚀 Quick Start

### 1. Import Collection

1. Open Postman
2. Click **Import** button
3. Select `legacy-artifacts/ASOUD_API_Complete_Postman_Collection.json`
4. Click **Import**

### 2. Import Environment

1. In Postman, click **Environments** tab
2. Click **Import**
3. Select `legacy-artifacts/ASOUD_API_Environment.json`
4. Click **Import**
5. Select **ASOUD API Environment** from the environment dropdown

### 3. Configure Base URL

The default base URL is set to `http://localhost:8000` for development. To change it:

1. Select **ASOUD API Environment**
2. Click **Edit** (pencil icon)
3. Update the `base_url` variable
4. Click **Save**

## 🔧 Environment Variables

The collection uses the following environment variables:

### Core Variables
- `base_url`: API base URL (default: http://localhost:8000)
- `api_version`: API version (default: v1)

### Authentication Variables
- `auth_token`: JWT authentication token (auto-populated after login)
- `refresh_token`: JWT refresh token (auto-populated after login)
- `user_id`: Current user ID (auto-populated after login)

### Entity Variables
- `market_id`: Market ID for market-related operations
- `product_id`: Product ID for product-related operations
- `order_id`: Order ID for order-related operations
- `category_id`: Category ID for category-related operations
- `bank_id`: Bank ID for bank-related operations
- `bank_info_id`: Bank information ID
- `location_id`: Location ID for market locations
- `contact_id`: Contact ID for market contacts
- `schedule_id`: Schedule ID for market schedules
- `room_id`: Chat room ID
- `message_id`: Message ID
- `ticket_id`: Support ticket ID
- `notification_id`: Notification ID
- `template_id`: Template ID
- `payment_id`: Payment ID
- `wallet_balance`: Current wallet balance
- `affiliate_product_id`: Affiliate product ID
- `referral_id`: Referral ID
- `inquiry_id`: Price inquiry ID
- `answer_id`: Inquiry answer ID
- `service_id`: Service ID for reservations
- `specialist_id`: Specialist ID for reservations
- `reservation_id`: Reservation ID
- `advertisement_id`: Advertisement ID
- `comment_id`: Comment ID
- `discount_id`: Discount ID
- `group_id`: Category group ID
- `country_id`: Country ID
- `province_id`: Province ID
- `city_id`: City ID
- `theme_id`: Theme ID
- `dayoff_id`: Day off ID
- `line_id`: SMS line ID
- `bulk_id`: Bulk SMS ID
- `pattern_id`: Pattern SMS ID
- `preference_id`: User preference ID
- `session_id`: User session ID
- `event_id`: Analytics event ID
- `business_id`: Business ID
- `subdomain`: Market subdomain

## 🔐 Authentication Flow

### 1. Send Verification Code
```http
POST /api/v1/user/pin/create/
Content-Type: application/json

{
    "mobile_number": "09123456789"
}
```

### 2. Verify PIN Code
```http
POST /api/v1/user/pin/verify/
Content-Type: application/json

{
    "mobile_number": "09123456789",
    "pin": 1234
}
```

The authentication token will be automatically saved to the `auth_token` environment variable after successful verification.

## 📁 Collection Structure

### 1. Authentication & User Management
- Send Verification Code
- Verify PIN Code
- Get Available Banks
- Create Bank Information
- Get User Bank Information
- Update Bank Information
- Delete Bank Information
- Get Bank Information Detail

### 2. Market Management
#### Owner Market Operations
- Create Market
- Get Owner Markets List
- Get Market Detail (Owner)
- Update Market
- Create Market Location
- Get Market Location
- Update Market Location
- Create Market Contact
- Get Market Contact
- Update Market Contact
- Set Market Inactive
- Set Market in Queue
- Upload Market Logo
- Upload Market Background
- Upload Market Slider
- Set Market Theme
- Create Market Schedule
- Get Market Schedules
- Update Market Schedule
- Delete Market Schedule

#### User Market Operations
- Get Market List
- Get Public Market List
- Report Market
- Bookmark Market
- Remove Market Bookmark
- Get Market Schedule

### 3. Product Management
#### Owner Product Operations
- Create Product
- Get Product List
- Get Product Detail
- Create Product Discount
- Create Product Shipping
- Get Product Shipping List
- Product Theme Management (CRUD)

### 4. Cart & Order Management
#### Owner Order Operations
- Verify Order
- Get Owner Orders List
- Get Owner Order Detail

#### Cart Operations
- Get Cart Items
- Add Item to Cart
- Update Cart Item
- Remove Cart Item
- Checkout Cart

#### Order Management
- Create Order
- Get Order List
- Get Order Detail
- Update Order
- Delete Order

### 5. Payment System
- Create Payment
- Payment Redirect
- Verify Payment
- Get Payment List
- Get Payment Detail

### 6. Chat & Support System
#### Chat Room Management
- Get Chat Rooms
- Create Chat Room
- Get Chat Room Detail
- Update Chat Room
- Delete Chat Room
- Add Participant to Chat Room
- Remove Participant from Chat Room
- Get Chat Room Participants
- Get Chat Room Analytics

#### Message Management
- Get Messages
- Send Message
- Get Message Detail
- Update Message
- Delete Message
- Mark Message as Read
- Edit Message
- Get Room Messages

#### Support Ticket System
- Get Support Tickets
- Create Support Ticket
- Get Support Ticket Detail
- Update Support Ticket
- Delete Support Ticket
- Assign Support Ticket
- Resolve Support Ticket
- Close Support Ticket
- Get Support Ticket Statistics

#### Chat Analytics
- Get Chat Analytics
- Search Chat Messages

### 7. Notification System
#### Notification Management
- Get Notifications
- Create Notification
- Get Notification Detail
- Mark Notification as Read
- Delete Notification
- Mark All Notifications as Read
- Get Unread Notifications Count
- Get Notification Statistics

#### Notification Templates
- Get Notification Templates
- Create Notification Template
- Update Notification Template
- Delete Notification Template
- Test Notification Template

#### Notification Preferences
- Get User Preferences
- Update User Preferences

#### Bulk Notifications
- Send Bulk Notification

#### Notification Statistics
- Get Notification Stats
- Get Notification Queue Status
- Cleanup Old Notifications

### 8. Analytics & ML
#### User Behavior Analytics
- Track User Event
- Get User Sessions
- Get Events by Type
- Get Events Timeline
- Get Active Sessions
- Get Conversion Analysis

#### Product Analytics
- Get Product Analytics
- Get Top Products
- Get Trending Products
- Calculate Product Metrics

#### Market Analytics
- Get Market Analytics

#### User Analytics
- Get User Analytics

#### Advanced Analytics
- Get Sales Analytics
- Get Business Intelligence
- Get Advanced Analytics

#### Machine Learning
- Get ML Recommendations
- Price Optimization
- Demand Forecasting
- ML Optimization

#### Fraud Detection & Security
- Fraud Detection
- Customer Segmentation
- Security Analytics

#### Analytics Dashboard
- Get Analytics Dashboard
- Get Real-time Analytics
- Get Event Tracking

### 9. SMS Services
#### Admin SMS Management
- Create SMS Line
- Get SMS Lines
- Update SMS Line
- Delete SMS Line

#### SMS Templates
- Create SMS Template
- Get SMS Templates
- Update SMS Template
- Delete SMS Template

#### Bulk SMS
- Get Bulk SMS List
- Get Bulk SMS Detail
- Update Bulk SMS

#### Pattern SMS
- Get Pattern SMS List
- Get Pattern SMS Detail

#### Owner SMS Operations
- Get Available Lines
- Get Available Templates
- Send Bulk SMS
- Send Pattern SMS

### 10. Wallet System
- Get Wallet Balance
- Check Wallet Balance
- Pay with Wallet
- Get Wallet Transactions

### 11. Affiliate System
#### User Affiliate Operations
- Get Products for Affiliate
- Get Affiliate Product Detail
- Create Affiliate Product
- Get Affiliate Products List
- Get Affiliate Product Detail
- Update Affiliate Product
- Delete Affiliate Product

#### Affiliate Product Themes
- Create Affiliate Product Theme
- Get Affiliate Product Themes
- Update Affiliate Product Theme

### 12. Referral System
- Create Referral
- Get Referral List

### 13. Price Inquiry System
#### Owner Price Inquiry Operations
- Get Owner Inquiries List
- Get Owner Inquiry Detail
- Get Owner Inquiry Answers
- Create Inquiry Answer
- Get Owner Inquiry Answer Detail

#### User Price Inquiry Operations
- Get Price Inquiries List
- Create Price Inquiry
- Update Price Inquiry
- Delete Price Inquiry
- Get Price Inquiry Detail
- Upload Inquiry Image
- Send Price Inquiry
- Renew Inquiry Expiry

#### Inquiry Answers
- Get Inquiry Answers
- Get Inquiry Answer Detail

### 14. Reservation System
#### Owner Reservation Operations
- Service Management (CRUD)
- Specialist Management (CRUD)
- Reserve Time Management (CRUD)
- Day Off Management (CRUD)
- Reservation Management (List, Detail)

#### User Reservation Operations
- Get Services List
- Get Specialists List
- Get Reserve Times
- Get Days Off
- Create Reservation
- Get Reservation Detail
- Get Reservations List
- Reservation Payment
- Reservation Payment Complete

### 15. Advertisement System
- Get Advertisements List
- Create Advertisement
- Get Advertisement Detail
- Update Advertisement
- Delete Advertisement
- Get Own Advertisements
- Advertisement Payment

### 16. Comment System
- Create Comment
- Get Comment Detail
- Update Comment
- Get Content Comments

### 17. Discount System
#### Owner Discount Operations
- Create Discount
- Get Discounts List
- Get Discount Detail
- Delete Discount

#### User Discount Operations
- Validate Discount Code

### 18. Category Management
#### Category Operations
- Get Category Groups
- Get Categories by Group
- Get Subcategories
- Get Slider Images

#### Product Categories
- Get Product Groups
- Get Product Categories
- Get Product Subcategories

### 19. Region Management
- Get Countries List
- Get Provinces by Country
- Get Cities by Province

### 20. Information Services
- Get Terms and Conditions

### 21. Analytics Dashboard Endpoints
- Get Analytics Dashboard
- Get Real-time Dashboard
- Get User Analytics Dashboard
- Get Product Analytics Dashboard
- Get Market Analytics Dashboard
- Get ML Recommendations Dashboard

### 22. Market Subdomain Endpoints
- Get Market Detail (Subdomain)
- Get Market Products (Subdomain)
- Get Product Detail (Subdomain)

### 23. Security & System Endpoints
- Health Check
- Security Audit
- CSRF Failure Handler
- Rate Limit Handler

### 24. Flutter-Specific Endpoints
- Get Market Detail for Flutter
- Get Product Detail for Flutter
- Get Advertisement Detail for Flutter
- Get Visit Card
- Get Bank Share Card

### 25. WebSocket Endpoints
- Chat WebSocket
- Support WebSocket
- Notification WebSocket
- Analytics WebSocket

## 🧪 Testing Features

### Pre-request Scripts
Each request includes pre-request scripts that:
- Log the request URL
- Set up necessary headers
- Validate required environment variables

### Test Scripts
Each request includes test scripts that:
- Validate response time (< 5000ms)
- Check for success field in response
- Automatically save tokens and IDs to environment variables
- Validate response structure

### Global Test Scripts
The collection includes global test scripts that run on every request:
- Response time validation
- Success field validation
- Error handling

## 🔄 Workflow Examples

### 1. Complete User Registration Flow
1. **Send Verification Code** → Get PIN
2. **Verify PIN Code** → Get auth token (auto-saved)
3. **Create Bank Information** → Set up banking
4. **Get Available Banks** → View bank options

### 2. Market Owner Setup Flow
1. **Create Market** → Create new market
2. **Create Market Location** → Set market location
3. **Create Market Contact** → Add contact info
4. **Create Market Schedule** → Set business hours
5. **Upload Market Logo** → Add branding

### 3. Product Management Flow
1. **Create Product** → Add new product
2. **Create Product Discount** → Set up promotions
3. **Create Product Shipping** → Configure delivery
4. **Get Product List** → View all products

### 4. Order Processing Flow
1. **Add Item to Cart** → Add products to cart
2. **Get Cart Items** → Review cart
3. **Checkout Cart** → Create order
4. **Create Payment** → Process payment
5. **Verify Payment** → Confirm payment

### 5. Chat & Support Flow
1. **Create Chat Room** → Start conversation
2. **Send Message** → Send message
3. **Create Support Ticket** → Get help
4. **Get Support Tickets** → View tickets

## 📊 Response Formats

### Success Response
```json
{
    "success": true,
    "code": 200,
    "data": {
        // Response data
    },
    "message": "Operation successful"
}
```

### Error Response
```json
{
    "success": false,
    "code": 400,
    "error": {
        "code": "error_code",
        "detail": "Error description",
        "field_errors": {
            "field_name": ["Error message"]
        }
    }
}
```

### Paginated Response
```json
{
    "success": true,
    "code": 200,
    "data": {
        "results": [...],
        "count": 100,
        "next": "http://localhost:8000/api/v1/endpoint/?page=2",
        "previous": null
    }
}
```

## 🔒 Security Features

### Authentication
- JWT token-based authentication
- Automatic token refresh
- Secure token storage in environment variables

### Rate Limiting
- Different rate limits for different endpoints
- Authentication endpoints: 10 requests/minute
- Payment endpoints: 5 requests/minute
- Upload endpoints: 20 requests/hour
- Default endpoints: 1000 requests/hour

### Error Handling
- Comprehensive error codes
- Detailed error messages
- Field-level validation errors

## 🌐 WebSocket Support

The collection includes WebSocket endpoints for real-time features:

### Chat WebSocket
```javascript
const chatSocket = new WebSocket('ws://localhost:8000/ws/chat/{room_name}/');
```

### Support WebSocket
```javascript
const supportSocket = new WebSocket('ws://localhost:8000/ws/support/{ticket_id}/');
```

### Notification WebSocket
```javascript
const notificationSocket = new WebSocket('ws://localhost:8000/ws/notifications');
```

## 📱 Flutter Integration

The collection includes Flutter-specific endpoints optimized for mobile app integration:

- Market detail endpoints
- Product detail endpoints
- Advertisement endpoints
- Visit card generation
- Bank share card generation

## 🔧 Customization

### Adding New Endpoints
1. Create new request in appropriate folder
2. Set up proper headers and authentication
3. Add pre-request and test scripts
4. Update environment variables if needed

### Modifying Environment Variables
1. Edit the environment file
2. Add new variables as needed
3. Update collection to use new variables

### Custom Test Scripts
Add custom validation in test scripts:
```javascript
pm.test("Custom validation", function () {
    const response = pm.response.json();
    pm.expect(response.data).to.have.property('custom_field');
});
```

## 📚 Additional Resources

### API Documentation
- Complete API documentation: `API_DOCUMENTATION.md`
- Technical documentation: `COMPREHENSIVE_TECHNICAL_DOCUMENTATION.md`

### Development Resources
- Flutter improvements: `FLUTER_IMPROVEMENTS_DOCUMENTATION.md`
- Long-term development plan: `LONG_TERM_DEVELOPMENT_PLAN.md`
- Security implementation: `../security/PHASE1_SECURITY_IMPLEMENTATION.md`

## 🆘 Support

For issues or questions:
1. Check the API documentation
2. Review the test scripts for examples
3. Verify environment variables are set correctly
4. Check the server logs for detailed error messages

## 📝 Changelog

### Version 2.0
- Complete collection with 255+ endpoints
- Comprehensive environment variables
- Advanced test scripts
- WebSocket support
- Flutter-specific endpoints
- Security features
- Detailed documentation

### Version 1.0
- Basic collection structure
- Core endpoints
- Simple authentication flow

## 🎯 Best Practices

1. **Always use environment variables** for dynamic values
2. **Run tests** after each request to validate responses
3. **Check response times** to monitor performance
4. **Use pagination** for large datasets
5. **Handle errors gracefully** with proper error checking
6. **Keep tokens secure** and refresh them when needed
7. **Use WebSocket** for real-time features
8. **Validate responses** with test scripts

---

**Total Endpoints:** 255+  
**Collection Version:** 2.0  
**Last Updated:** December 2024  
**API Version:** v1  
**Base URL:** `http://localhost:8000` (Development)

This comprehensive Postman collection provides everything you need to test and integrate with the ASOUD Platform API. All endpoints are fully documented with examples, test scripts, and proper error handling.
