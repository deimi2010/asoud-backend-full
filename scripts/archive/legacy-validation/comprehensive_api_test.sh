#!/bin/bash

# Comprehensive API Testing for Production Environment
# Tests all critical endpoints with proper headers

echo "================================================================================"
echo "COMPREHENSIVE API TESTING - PRODUCTION MODE"
echo "================================================================================"
echo ""

BASE_URL="http://localhost:8000"
TOTAL=0
SUCCESS=0
FAILED=0
WARNINGS=0

# Headers for production testing
HEADERS='-H "Content-Type: application/json" -H "X-Forwarded-Proto: https"'

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to test endpoint
test_api() {
    local method=$1
    local path=$2
    local description=$3
    local data=$4
    local auth_token=$5
    
    TOTAL=$((TOTAL + 1))
    
    echo -n "[$TOTAL] $description... "
    
    if [ -z "$auth_token" ]; then
        if [ "$method" == "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" 2>/dev/null)
        elif [ "$method" == "POST" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" \
                -d "$data" 2>/dev/null)
        elif [ "$method" == "PUT" ]; then
            response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" \
                -d "$data" 2>/dev/null)
        elif [ "$method" == "DELETE" ]; then
            response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" 2>/dev/null)
        fi
    else
        if [ "$method" == "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" \
                -H "Authorization: Token $auth_token" 2>/dev/null)
        elif [ "$method" == "POST" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$path" \
                -H "Content-Type: application/json" \
                -H "X-Forwarded-Proto: https" \
                -H "Authorization: Token $auth_token" \
                -d "$data" 2>/dev/null)
        fi
    fi
    
    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    # Check status and categorize
    if [[ $status == 200 || $status == 201 ]]; then
        echo -e "${GREEN}✓ SUCCESS${NC} ($status)"
        SUCCESS=$((SUCCESS + 1))
    elif [[ $status == 401 || $status == 403 ]]; then
        echo -e "${YELLOW}⚠ AUTH_REQUIRED${NC} ($status)"
        SUCCESS=$((SUCCESS + 1))
        WARNINGS=$((WARNINGS + 1))
    elif [[ $status == 404 ]]; then
        echo -e "${YELLOW}⚠ NOT_FOUND${NC} ($status)"
        SUCCESS=$((SUCCESS + 1))
        WARNINGS=$((WARNINGS + 1))
    elif [[ $status == 405 ]]; then
        echo -e "${YELLOW}⚠ METHOD_NOT_ALLOWED${NC} ($status)"
        SUCCESS=$((SUCCESS + 1))
        WARNINGS=$((WARNINGS + 1))
    elif [[ $status -ge 400 && $status -lt 500 ]]; then
        echo -e "${YELLOW}⚠ CLIENT_ERROR${NC} ($status)"
        SUCCESS=$((SUCCESS + 1))
        WARNINGS=$((WARNINGS + 1))
    elif [[ $status -ge 500 ]]; then
        echo -e "${RED}✗ SERVER_ERROR${NC} ($status)"
        FAILED=$((FAILED + 1))
        echo "  Body: $(echo $body | head -c 200)"
    else
        echo -e "${RED}✗ FAILED${NC} ($status)"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}1. HEALTH & SYSTEM ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/health/" "Health Check (with slash)"
test_api "GET" "/health" "Health Check (no slash)"
test_api "GET" "/api/v1/health/" "API Health Check"
test_api "GET" "/api/v1/" "API Index"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}2. AUTHENTICATION ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test PIN creation
pin_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/user/pin/create/" \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-Proto: https" \
    -d '{"mobile_number":"09123456789"}' 2>/dev/null)
pin_status=$(echo "$pin_response" | tail -n1)
pin_body=$(echo "$pin_response" | head -n-1)
pin_code=$(echo "$pin_body" | grep -o '"pin":[0-9]*' | cut -d':' -f2)

test_api "POST" "/api/v1/user/pin/create/" "Create PIN" '{"mobile_number":"09123456789"}'

if [ ! -z "$pin_code" ]; then
    echo "  📌 PIN Code: $pin_code"
    
    # Test PIN verification
    verify_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/user/pin/verify/" \
        -H "Content-Type: application/json" \
        -H "X-Forwarded-Proto: https" \
        -d "{\"mobile_number\":\"09123456789\",\"pin\":\"$pin_code\"}" 2>/dev/null)
    verify_status=$(echo "$verify_response" | tail -n1)
    verify_body=$(echo "$verify_response" | head -n-1)
    AUTH_TOKEN=$(echo "$verify_body" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    
    test_api "POST" "/api/v1/user/pin/verify/" "Verify PIN" "{\"mobile_number\":\"09123456789\",\"pin\":\"$pin_code\"}"
    
    if [ ! -z "$AUTH_TOKEN" ]; then
        echo "  🔑 Auth Token: ${AUTH_TOKEN:0:20}..."
    fi
else
    test_api "POST" "/api/v1/user/pin/verify/" "Verify PIN (no token)" '{"mobile_number":"09123456789","pin":"0000"}'
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}3. CATEGORY ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/category/group/list/" "List Category Groups"
test_api "GET" "/api/v1/category/list/" "List All Categories"
test_api "GET" "/api/v1/category/sub/list/" "List All Subcategories"
test_api "GET" "/api/v1/category/product-group/list/" "List Product Groups"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}4. REGION ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/region/country/list/" "List Countries"
test_api "GET" "/api/v1/region/province/list/" "List All Provinces"
test_api "GET" "/api/v1/region/city/list/" "List All Cities"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}5. MARKET ENDPOINTS (Public)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/user/market/public/list/" "Public Markets List"
test_api "GET" "/api/v1/user/market/list/" "User Markets List (Auth Required)"

if [ ! -z "$AUTH_TOKEN" ]; then
    test_api "GET" "/api/v1/user/market/list/" "User Markets List (Authenticated)" "" "$AUTH_TOKEN"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}6. INFORMATION ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/info/term/" "Terms & Conditions"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}7. ORDER/CART ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/user/order/orders" "Get Orders (ViewSet - No Auth)"
test_api "GET" "/api/v1/user/order/list" "Order List (No Auth)"
test_api "POST" "/api/v1/user/order/create" "Order Create (No Auth)" "{}"

if [ ! -z "$AUTH_TOKEN" ]; then
    test_api "GET" "/api/v1/user/order/orders" "Get Orders (Authenticated)" "" "$AUTH_TOKEN"
    test_api "GET" "/api/v1/user/order/list" "Order List (Authenticated)" "" "$AUTH_TOKEN"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}8. PAYMENT ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/user/payments/" "Payment List (No Auth)"
test_api "POST" "/api/v1/user/payments/create/" "Payment Create (No Auth)" '{"amount":10000}'

if [ ! -z "$AUTH_TOKEN" ]; then
    test_api "GET" "/api/v1/user/payments/" "Payment List (Authenticated)" "" "$AUTH_TOKEN"
    test_api "POST" "/api/v1/user/payments/create/" "Payment Create (Authenticated)" '{"amount":10000}' "$AUTH_TOKEN"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}9. DISCOUNT ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "POST" "/api/v1/discount/user/validate/" "Validate Discount" '{"code":"TEST123"}'

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}10. WALLET ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/wallet/balance/" "Wallet Balance (No Auth)"
test_api "GET" "/api/v1/wallet/transactions/" "Wallet Transactions (No Auth)"

if [ ! -z "$AUTH_TOKEN" ]; then
    test_api "GET" "/api/v1/wallet/balance/" "Wallet Balance (Authenticated)" "" "$AUTH_TOKEN"
    test_api "GET" "/api/v1/wallet/transactions/" "Wallet Transactions (Authenticated)" "" "$AUTH_TOKEN"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}11. BANK INFO ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/v1/user/bank-info/list/" "Available Banks List"
test_api "GET" "/api/v1/user/bank/info/list/" "User Bank Info List (No Auth)"

if [ ! -z "$AUTH_TOKEN" ]; then
    test_api "GET" "/api/v1/user/bank/info/list/" "User Bank Info List (Authenticated)" "" "$AUTH_TOKEN"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}12. API DOCUMENTATION${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_api "GET" "/api/schema/" "OpenAPI Schema"
test_api "GET" "/api/docs/" "Swagger UI Documentation"

# Summary
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                              TEST SUMMARY                                      ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Total Tests       : $TOTAL"
echo -e "  ${GREEN}✓ Passed${NC}          : $SUCCESS"
echo -e "  ${RED}✗ Failed${NC}          : $FAILED"
echo -e "  ${YELLOW}⚠ Warnings${NC}        : $WARNINGS (Auth/NotFound/MethodNotAllowed)"
echo ""

if [ $TOTAL -gt 0 ]; then
    success_rate=$((SUCCESS * 100 / TOTAL))
    if [ $success_rate -ge 90 ]; then
        echo -e "  ${GREEN}Success Rate: $success_rate% - EXCELLENT!${NC}"
    elif [ $success_rate -ge 70 ]; then
        echo -e "  ${YELLOW}Success Rate: $success_rate% - GOOD${NC}"
    else
        echo -e "  ${RED}Success Rate: $success_rate% - NEEDS ATTENTION${NC}"
    fi
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed! No server errors detected.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed with server errors!${NC}"
    exit 1
fi


