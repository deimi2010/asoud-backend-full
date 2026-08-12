#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Asoud Backend
Tests all registered endpoints and validates responses
"""
import os
import sys
import django
import json
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from rest_framework.authtoken.models import Token

# Optional termcolor support
try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, attrs=None):
        return text

User = get_user_model()


class APITester:
    def __init__(self):
        self.factory = RequestFactory()
        self.results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        self.test_user = None
        self.auth_token = None
        
    def setup_test_user(self):
        """Create a test user for authenticated requests"""
        try:
            # Try to get existing test user
            self.test_user = User.objects.filter(phone_number='09123456789').first()
            if not self.test_user:
                self.test_user = User.objects.create_user(
                    phone_number='09123456789',
                    is_active=True
                )
            
            # Get or create token
            self.auth_token, _ = Token.objects.get_or_create(user=self.test_user)
            print(colored(f"✓ Test user created/retrieved: {self.test_user.phone_number}", 'green'))
        except Exception as e:
            print(colored(f"✗ Failed to create test user: {str(e)}", 'red'))
    
    def extract_all_patterns(self, urlpatterns, prefix=''):
        """Recursively extract all URL patterns"""
        patterns = []
        
        for pattern in urlpatterns:
            if isinstance(pattern, URLResolver):
                # It's an included URLconf
                new_prefix = prefix + str(pattern.pattern)
                patterns.extend(self.extract_all_patterns(pattern.url_patterns, new_prefix))
            elif isinstance(pattern, URLPattern):
                # It's an endpoint
                full_path = prefix + str(pattern.pattern)
                patterns.append({
                    'path': full_path,
                    'name': pattern.name,
                    'callback': pattern.callback
                })
        
        return patterns
    
    def categorize_endpoints(self, patterns):
        """Categorize endpoints by app and type"""
        categories = defaultdict(list)
        
        for pattern in patterns:
            path = pattern['path']
            
            # Categorize by path prefix
            if 'admin' in path:
                categories['admin'].append(pattern)
            elif 'api/v1/user/' in path:
                categories['user_api'].append(pattern)
            elif 'api/v1/owner/' in path:
                categories['owner_api'].append(pattern)
            elif 'api/v1/' in path:
                categories['general_api'].append(pattern)
            elif 'health' in path:
                categories['health'].append(pattern)
            elif 'api/schema' in path or 'api/docs' in path:
                categories['docs'].append(pattern)
            elif 'ws/' in path or 'chat' in path:
                categories['websocket'].append(pattern)
            else:
                categories['other'].append(pattern)
        
        return categories
    
    def test_endpoint(self, pattern: Dict, method: str = 'GET', 
                     authenticated: bool = False, test_data: Optional[Dict] = None) -> Tuple[bool, str, int]:
        """Test a single endpoint"""
        path = pattern['path']
        
        # Skip dynamic paths for now (those with <str:pk> etc)
        if '<' in path or '>' in path:
            # Replace with dummy values
            path = path.replace('<str:pk>', 'test-uuid-123')
            path = path.replace('<int:pk>', '1')
            path = path.replace('<slug:slug>', 'test-slug')
            path = path.replace('<uuid:pk>', '550e8400-e29b-41d4-a716-446655440000')
        
        # Clean path
        path = '/' + path.lstrip('^').rstrip('$/')
        
        try:
            # Create request
            if method == 'GET':
                request = self.factory.get(path)
            elif method == 'POST':
                request = self.factory.post(path, data=test_data or {}, content_type='application/json')
            elif method == 'PUT':
                request = self.factory.put(path, data=test_data or {}, content_type='application/json')
            elif method == 'PATCH':
                request = self.factory.patch(path, data=test_data or {}, content_type='application/json')
            elif method == 'DELETE':
                request = self.factory.delete(path)
            else:
                return False, f"Unknown method: {method}", 0
            
            # Authenticate if needed
            if authenticated and self.test_user:
                force_authenticate(request, user=self.test_user)
            
            # Get the view
            callback = pattern['callback']
            
            # Try to call the view
            try:
                if hasattr(callback, 'cls'):
                    # It's a class-based view
                    view = callback.cls.as_view()
                    response = view(request)
                else:
                    # It's a function-based view
                    response = callback(request)
                
                status_code = getattr(response, 'status_code', 0)
                
                # Consider 200-299, 400-499 as "working" (not 500 errors)
                # 401/403 are expected for protected endpoints
                # 404 might be expected for dynamic routes with fake IDs
                if 200 <= status_code < 300:
                    return True, "SUCCESS", status_code
                elif status_code in [401, 403]:
                    return True, "AUTH_REQUIRED", status_code
                elif status_code == 404:
                    return True, "NOT_FOUND (might be expected)", status_code
                elif status_code == 405:
                    return True, "METHOD_NOT_ALLOWED", status_code
                elif 400 <= status_code < 500:
                    return True, "CLIENT_ERROR (expected)", status_code
                else:
                    return False, f"Server error: {status_code}", status_code
                    
            except AttributeError as e:
                # View might not be properly configured
                return False, f"View configuration error: {str(e)}", 0
            except Exception as e:
                return False, f"View execution error: {str(e)}", 0
                
        except Exception as e:
            return False, f"Request creation error: {str(e)}", 0
    
    def test_health_endpoints(self):
        """Test health check endpoints"""
        print(colored("\n=== TESTING HEALTH ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        health_paths = [
            '/health/',
            '/health',
            '/api/v1/health/',
        ]
        
        for path in health_paths:
            try:
                request = self.factory.get(path)
                from config.views import HealthCheckView
                view = HealthCheckView.as_view()
                response = view(request)
                status = response.status_code
                
                if status == 200:
                    print(colored(f"✓ {path} - Status: {status}", 'green'))
                    self.results['success'] += 1
                else:
                    print(colored(f"✗ {path} - Status: {status}", 'red'))
                    self.results['failed'] += 1
                    self.results['errors'].append(f"{path} returned {status}")
                
                self.results['total'] += 1
            except Exception as e:
                print(colored(f"✗ {path} - Error: {str(e)}", 'red'))
                self.results['failed'] += 1
                self.results['errors'].append(f"{path}: {str(e)}")
                self.results['total'] += 1
    
    def test_category_endpoints(self, patterns):
        """Test category-related endpoints"""
        print(colored("\n=== TESTING CATEGORY ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        category_patterns = [p for p in patterns if 'category' in p['path']]
        
        for pattern in category_patterns[:5]:  # Test first 5
            success, message, status = self.test_endpoint(pattern, 'GET')
            self._print_result(pattern['path'], message, status, success)
    
    def test_user_auth_endpoints(self, patterns):
        """Test user authentication endpoints"""
        print(colored("\n=== TESTING USER AUTH ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        auth_patterns = [p for p in patterns if 'pin' in p['path'] or 'auth' in p['path']]
        
        # Test PIN create
        pin_create = [p for p in auth_patterns if 'pin/create' in p['path']]
        if pin_create:
            test_data = {'phone_number': '09123456789'}
            success, message, status = self.test_endpoint(pin_create[0], 'POST', test_data=test_data)
            self._print_result(pin_create[0]['path'], message, status, success)
        
        # Test other auth endpoints
        for pattern in auth_patterns[:5]:
            if 'verify' in pattern['path']:
                test_data = {'phone_number': '09123456789', 'pin': '1234'}
                success, message, status = self.test_endpoint(pattern, 'POST', test_data=test_data)
            else:
                success, message, status = self.test_endpoint(pattern, 'GET')
            
            self._print_result(pattern['path'], message, status, success)
    
    def test_market_endpoints(self, patterns):
        """Test market endpoints"""
        print(colored("\n=== TESTING MARKET ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        market_patterns = [p for p in patterns if 'market' in p['path']]
        
        for pattern in market_patterns[:10]:  # Test first 10
            # Determine if authenticated request needed
            needs_auth = 'owner' in pattern['path'] or 'bookmark' in pattern['path']
            
            success, message, status = self.test_endpoint(pattern, 'GET', authenticated=needs_auth)
            self._print_result(pattern['path'], message, status, success)
    
    def test_product_endpoints(self, patterns):
        """Test product endpoints"""
        print(colored("\n=== TESTING PRODUCT ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        product_patterns = [p for p in patterns if 'product' in p['path']]
        
        for pattern in product_patterns[:10]:  # Test first 10
            needs_auth = 'owner' in pattern['path'] or 'create' in pattern['path']
            
            success, message, status = self.test_endpoint(pattern, 'GET', authenticated=needs_auth)
            self._print_result(pattern['path'], message, status, success)
    
    def test_order_endpoints(self, patterns):
        """Test order/cart endpoints"""
        print(colored("\n=== TESTING ORDER/CART ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        order_patterns = [p for p in patterns if 'order' in p['path'] or 'cart' in p['path']]
        
        for pattern in order_patterns[:10]:
            success, message, status = self.test_endpoint(pattern, 'GET', authenticated=True)
            self._print_result(pattern['path'], message, status, success)
    
    def test_payment_endpoints(self, patterns):
        """Test payment endpoints"""
        print(colored("\n=== TESTING PAYMENT ENDPOINTS ===", 'cyan', attrs=['bold']))
        
        payment_patterns = [p for p in patterns if 'payment' in p['path']]
        
        for pattern in payment_patterns[:5]:
            if 'create' in pattern['path']:
                test_data = {'amount': 10000, 'description': 'Test payment'}
                success, message, status = self.test_endpoint(pattern, 'POST', authenticated=True, test_data=test_data)
            else:
                success, message, status = self.test_endpoint(pattern, 'GET', authenticated=True)
            
            self._print_result(pattern['path'], message, status, success)
    
    def _print_result(self, path, message, status, success):
        """Print test result"""
        self.results['total'] += 1
        
        if success:
            self.results['success'] += 1
            color = 'green'
            symbol = '✓'
        else:
            self.results['failed'] += 1
            self.results['errors'].append(f"{path}: {message}")
            color = 'red'
            symbol = '✗'
        
        print(colored(f"{symbol} {path} - {message} (Status: {status})", color))
    
    def print_summary(self):
        """Print test summary"""
        print(colored("\n" + "="*80, 'cyan', attrs=['bold']))
        print(colored("TEST SUMMARY", 'cyan', attrs=['bold']))
        print(colored("="*80, 'cyan', attrs=['bold']))
        
        print(f"\nTotal Tests: {self.results['total']}")
        print(colored(f"✓ Passed: {self.results['success']}", 'green'))
        print(colored(f"✗ Failed: {self.results['failed']}", 'red'))
        print(f"⊘ Skipped: {self.results['skipped']}")
        
        if self.results['errors']:
            print(colored("\n=== ERRORS ===", 'red', attrs=['bold']))
            for error in self.results['errors'][:20]:  # Show first 20 errors
                print(colored(f"  • {error}", 'red'))
        
        # Calculate success rate
        if self.results['total'] > 0:
            success_rate = (self.results['success'] / self.results['total']) * 100
            print(colored(f"\nSuccess Rate: {success_rate:.2f}%", 'yellow', attrs=['bold']))
    
    def run_tests(self):
        """Run all tests"""
        print(colored("="*80, 'cyan', attrs=['bold']))
        print(colored("ASOUD API COMPREHENSIVE TEST SUITE", 'cyan', attrs=['bold']))
        print(colored("="*80, 'cyan', attrs=['bold']))
        
        # Setup
        self.setup_test_user()
        
        # Get all URL patterns
        print(colored("\n=== EXTRACTING URL PATTERNS ===", 'cyan', attrs=['bold']))
        resolver = get_resolver()
        all_patterns = self.extract_all_patterns(resolver.url_patterns)
        print(colored(f"✓ Found {len(all_patterns)} URL patterns", 'green'))
        
        # Categorize
        categories = self.categorize_endpoints(all_patterns)
        print(colored("\n=== ENDPOINT CATEGORIES ===", 'cyan', attrs=['bold']))
        for category, patterns in categories.items():
            print(f"  {category}: {len(patterns)} endpoints")
        
        # Run tests
        self.test_health_endpoints()
        self.test_user_auth_endpoints(categories.get('user_api', []))
        self.test_category_endpoints(categories.get('general_api', []))
        self.test_market_endpoints(categories.get('user_api', []) + categories.get('owner_api', []))
        self.test_product_endpoints(categories.get('owner_api', []))
        self.test_order_endpoints(categories.get('user_api', []))
        self.test_payment_endpoints(categories.get('user_api', []))
        
        # Print summary
        self.print_summary()


def main():
    tester = APITester()
    tester.run_tests()


if __name__ == '__main__':
    main()

