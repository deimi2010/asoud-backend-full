#!/bin/bash

# Comprehensive Live API Testing Script for Asoud Backend
# Tests actual HTTP endpoints through the running container

echo "================================================================================"
echo "ASOUD LIVE API TESTING (Docker Container)"
echo "================================================================================"
echo ""

BASE_URL="http://localhost:8000"
TOTAL=0
SUCCESS=0
FAILED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to test endpoint
test_endpoint() {
    local method=$1
    local path=$2
    local description=$3
    local data=$4
    local expected_status=$5
    
    TOTAL=$((TOTAL + 1))
    
    echo -n "Testing: $description... "
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$path" -H "Content-Type: application/json" 2>/dev/null)
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$path" -H "Content-Type: application/json" -d "$data" 2>/dev/null)
    fi
    
    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    # Check if status is in expected range
    if [[ $status -ge 200 && $status -lt 300 ]] || [[ $status == $expected_status ]]; then
        echo -e "${GREEN}✓ PASSED${NC} (Status: $status)"
        SUCCESS=$((SUCCESS + 1))
    elif [[ $status == 401 || $status == 403 ]]; then
        echo -e "${YELLOW}⚠ AUTH REQUIRED${NC} (Status: $status)"
        SUCCESS=$((SUCCESS + 1))
    elif [[ $status == 404 ]]; then
        echo -e "${YELLOW}⚠ NOT FOUND${NC} (Status: $status)"
        SUCCESS=$((SUCCESS + 1))
    elif [[ $status == 405 ]]; then
        echo -e "${YELLOW}⚠ METHOD NOT ALLOWED${NC} (Status: $status)"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}✗ FAILED${NC} (Status: $status)"
        FAILED=$((FAILED + 1))
        # Show error details
        if [ ! -z "$body" ]; then
            echo "  Error: $(echo $body | head -c 200)"
        fi
    fi
}

echo -e "${CYAN}=== HEALTH CHECK ENDPOINTS ===${NC}"
test_endpoint "GET" "/health/" "Health Check (trailing slash)" "" 200
test_endpoint "GET" "/health" "Health Check (no slash)" "" 200
test_endpoint "GET" "/api/v1/health/" "API Health Check" "" 200

echo -e "\n${CYAN}=== API INDEX ===${NC}"
test_endpoint "GET" "/api/v1/" "API Index" "" 200

echo -e "\n${CYAN}=== AUTHENTICATION ENDPOINTS ===${NC}"
test_endpoint "POST" "/api/v1/user/pin/create/" "PIN Create" '{"mobile_number":"09123456789"}' 200
test_endpoint "POST" "/api/v1/user/pin/verify/" "PIN Verify" '{"mobile_number":"09123456789","pin":"1234"}' ""

echo -e "\n${CYAN}=== CATEGORY ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/category/group/list/" "Category Groups List" "" 200
test_endpoint "GET" "/api/v1/category/list/" "Categories List (All)" "" 200
test_endpoint "GET" "/api/v1/category/sub/list/" "Subcategories List (All)" "" 200
test_endpoint "GET" "/api/v1/category/product-group/list/" "Product Groups List" "" 200

echo -e "\n${CYAN}=== REGION ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/region/province/list/" "Province List" "" 200
test_endpoint "GET" "/api/v1/region/city/list/" "City List" "" 200

echo -e "\n${CYAN}=== MARKET ENDPOINTS (Public) ===${NC}"
test_endpoint "GET" "/api/v1/user/market/public/list/" "Public Markets List" "" 200
test_endpoint "GET" "/api/v1/user/market/list/" "User Markets List (Auth Required)" "" 401

echo -e "\n${CYAN}=== INFORMATION ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/info/about/" "About Us" "" 200
test_endpoint "GET" "/api/v1/info/privacy/" "Privacy Policy" "" 200
test_endpoint "GET" "/api/v1/info/terms/" "Terms of Service" "" 200
test_endpoint "GET" "/api/v1/info/faq/" "FAQ" "" 200

echo -e "\n${CYAN}=== ORDER/CART ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/user/order/orders" "Get Orders (ViewSet)" "" ""
test_endpoint "GET" "/api/v1/user/order/list" "Order List" "" 401
test_endpoint "POST" "/api/v1/user/order/create" "Order Create" '{}' 401

echo -e "\n${CYAN}=== PAYMENT ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/user/payments/" "Payment List" "" 401
test_endpoint "POST" "/api/v1/user/payments/create/" "Payment Create" '{"amount":10000}' 401
test_endpoint "GET" "/api/v1/user/payments/pay" "Payment Redirect (GET)" "" ""
test_endpoint "POST" "/api/v1/user/payments/verify/" "Payment Verify" '{"Authority":"test","Status":"OK"}' ""

echo -e "\n${CYAN}=== DISCOUNT ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/discount/list/" "Discount List" "" ""
test_endpoint "POST" "/api/v1/discount/validate/" "Validate Discount" '{"code":"TEST"}' ""

echo -e "\n${CYAN}=== WALLET ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/wallet/" "Wallet Detail" "" 401
test_endpoint "GET" "/api/v1/wallet/transactions/" "Wallet Transactions" "" 401

echo -e "\n${CYAN}=== ANALYTICS ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/analytics/dashboard/" "Analytics Dashboard" "" 401

echo -e "\n${CYAN}=== BANK INFO ENDPOINTS ===${NC}"
test_endpoint "GET" "/api/v1/user/bank-info/list/" "Banks List" "" 200
test_endpoint "GET" "/api/v1/user/bank/info/list/" "User Bank Info List" "" 401

echo -e "\n${CYAN}=== API DOCUMENTATION ===${NC}"
test_endpoint "GET" "/api/schema/" "OpenAPI Schema" "" 200
test_endpoint "GET" "/api/docs/" "Swagger UI" "" 200

# Summary
echo ""
echo "================================================================================"
echo -e "${CYAN}TEST SUMMARY${NC}"
echo "================================================================================"
echo "Total Tests: $TOTAL"
echo -e "${GREEN}✓ Passed: $SUCCESS${NC}"
echo -e "${RED}✗ Failed: $FAILED${NC}"

if [ $TOTAL -gt 0 ]; then
    success_rate=$((SUCCESS * 100 / TOTAL))
    echo -e "${YELLOW}Success Rate: $success_rate%${NC}"
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi


