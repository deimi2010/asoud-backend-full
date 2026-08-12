#!/usr/bin/env python3
"""
Security Phase 1 Testing Script for ASOUD Platform
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Add the project directory to Python path
sys.path.append('/home/devops/projects/asoud-main-1-/asoud-main')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

def test_csrf_protection():
    """Test CSRF protection"""
    print("🔒 Testing CSRF Protection...")
    
    # Test CSRF token requirement
    try:
        response = requests.post('http://localhost:8000/api/v1/user/products/', 
                               json={'name': 'test'})
        if response.status_code == 403:
            print("✅ CSRF protection is working")
        else:
            print("❌ CSRF protection failed")
    except Exception as e:
        print(f"❌ CSRF test error: {e}")

def test_rate_limiting():
    """Test rate limiting"""
    print("🚦 Testing Rate Limiting...")
    
    # Test rate limit
    try:
        for i in range(15):  # Exceed rate limit
            response = requests.get('http://localhost:8000/api/v1/user/products/')
            if response.status_code == 429:
                print("✅ Rate limiting is working")
                break
        else:
            print("❌ Rate limiting failed")
    except Exception as e:
        print(f"❌ Rate limiting test error: {e}")

def test_security_headers():
    """Test security headers"""
    print("🛡️ Testing Security Headers...")
    
    try:
        response = requests.get('http://localhost:8000/health/')
        headers = response.headers
        
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        missing_headers = []
        for header in security_headers:
            if header not in headers:
                missing_headers.append(header)
        
        if not missing_headers:
            print("✅ All security headers present")
        else:
            print(f"❌ Missing security headers: {missing_headers}")
    except Exception as e:
        print(f"❌ Security headers test error: {e}")

def test_input_validation():
    """Test input validation"""
    print("🔍 Testing Input Validation...")
    
    # Test SQL injection
    try:
        response = requests.post('http://localhost:8000/api/v1/user/products/', 
                               json={'name': "'; DROP TABLE products; --"})
        if response.status_code == 400:
            print("✅ SQL injection protection working")
        else:
            print("❌ SQL injection protection failed")
    except Exception as e:
        print(f"❌ Input validation test error: {e}")

def test_authentication():
    """Test authentication"""
    print("🔐 Testing Authentication...")
    
    # Test protected endpoint without token
    try:
        response = requests.get('http://localhost:8000/api/v1/user/profile/')
        if response.status_code == 401:
            print("✅ Authentication required")
        else:
            print("❌ Authentication bypassed")
    except Exception as e:
        print(f"❌ Authentication test error: {e}")

def test_password_validation():
    """Test password validation"""
    print("🔑 Testing Password Validation...")
    
    # Test weak password
    try:
        response = requests.post('http://localhost:8000/api/v1/auth/register/', 
                               json={
                                   'mobile_number': '09123456789',
                                   'password': '123456'
                               })
        if response.status_code == 400:
            print("✅ Password validation working")
        else:
            print("❌ Password validation failed")
    except Exception as e:
        print(f"❌ Password validation test error: {e}")

def test_error_handling():
    """Test error handling"""
    print("⚠️ Testing Error Handling...")
    
    # Test 404 error
    try:
        response = requests.get('http://localhost:8000/api/v1/nonexistent/')
        if response.status_code == 404:
            print("✅ 404 error handling working")
        else:
            print("❌ 404 error handling failed")
    except Exception as e:
        print(f"❌ Error handling test error: {e}")

def test_logging():
    """Test logging"""
    print("📝 Testing Logging...")
    
    # Check if log files exist
    log_files = [
        '/home/devops/projects/asoud-main-1-/asoud-main/logs/django.log',
        '/home/devops/projects/asoud-main-1-/asoud-main/logs/security.log',
        '/home/devops/projects/asoud-main-1-/asoud-main/logs/error.log'
    ]
    
    existing_logs = []
    for log_file in log_files:
        if os.path.exists(log_file):
            existing_logs.append(log_file)
    
    if existing_logs:
        print(f"✅ Log files created: {existing_logs}")
    else:
        print("❌ Log files not created")

def run_all_tests():
    """Run all security tests"""
    print("🚀 Starting Security Phase 1 Tests...")
    print("=" * 50)
    
    test_csrf_protection()
    test_rate_limiting()
    test_security_headers()
    test_input_validation()
    test_authentication()
    test_password_validation()
    test_error_handling()
    test_logging()
    
    print("=" * 50)
    print("✅ Security Phase 1 Tests Completed!")

if __name__ == "__main__":
    run_all_tests()



