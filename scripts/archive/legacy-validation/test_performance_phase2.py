#!/usr/bin/env python3
"""
Performance Phase 2 Testing Script for ASOUD Platform
"""

import os
import sys
import django
import requests
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project directory to Python path
sys.path.append('/home/devops/projects/asoud-main-1-/asoud-main')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

class PerformanceTester:
    """Performance testing utilities"""
    
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.results = []
    
    def test_api_response_time(self, endpoint, method='GET', data=None, headers=None):
        """Test API response time"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time': response_time,
                'success': response.status_code < 400
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': 0,
                'response_time': 0,
                'success': False,
                'error': str(e)
            }
            self.results.append(result)
            return result
    
    def test_concurrent_requests(self, endpoint, num_requests=10, method='GET', data=None, headers=None):
        """Test concurrent requests"""
        print(f"Testing {num_requests} concurrent requests to {endpoint}")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(num_requests):
                future = executor.submit(self.test_api_response_time, endpoint, method, data, headers)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def test_database_performance(self):
        """Test database performance"""
        print("Testing database performance...")
        
        # Test product list endpoint
        result = self.test_api_response_time('/api/v1/user/products/')
        print(f"Product list: {result['response_time']:.3f}s")
        
        # Test market list endpoint
        result = self.test_api_response_time('/api/v1/user/markets/')
        print(f"Market list: {result['response_time']:.3f}s")
        
        # Test order list endpoint
        result = self.test_api_response_time('/api/v1/user/order/')
        print(f"Order list: {result['response_time']:.3f}s")
    
    def test_caching_performance(self):
        """Test caching performance"""
        print("Testing caching performance...")
        
        # Test first request (cache miss)
        result1 = self.test_api_response_time('/api/v1/user/products/')
        print(f"First request (cache miss): {result1['response_time']:.3f}s")
        
        # Test second request (cache hit)
        result2 = self.test_api_response_time('/api/v1/user/products/')
        print(f"Second request (cache hit): {result2['response_time']:.3f}s")
        
        # Calculate cache improvement
        if result1['response_time'] > 0 and result2['response_time'] > 0:
            improvement = ((result1['response_time'] - result2['response_time']) / result1['response_time']) * 100
            print(f"Cache improvement: {improvement:.1f}%")
    
    def test_pagination_performance(self):
        """Test pagination performance"""
        print("Testing pagination performance...")
        
        # Test different page sizes
        page_sizes = [10, 20, 50, 100]
        
        for page_size in page_sizes:
            result = self.test_api_response_time(f'/api/v1/user/products/?page_size={page_size}')
            print(f"Page size {page_size}: {result['response_time']:.3f}s")
    
    def test_search_performance(self):
        """Test search performance"""
        print("Testing search performance...")
        
        # Test product search
        result = self.test_api_response_time('/api/v1/user/products/?search=test')
        print(f"Product search: {result['response_time']:.3f}s")
        
        # Test market search
        result = self.test_api_response_time('/api/v1/user/markets/?search=test')
        print(f"Market search: {result['response_time']:.3f}s")
    
    def test_concurrent_load(self):
        """Test concurrent load"""
        print("Testing concurrent load...")
        
        # Test concurrent product requests
        results = self.test_concurrent_requests('/api/v1/user/products/', num_requests=20)
        
        # Calculate statistics
        response_times = [r['response_time'] for r in results if r['success']]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"Concurrent load test (20 requests):")
            print(f"  Average response time: {avg_time:.3f}s")
            print(f"  Max response time: {max_time:.3f}s")
            print(f"  Min response time: {min_time:.3f}s")
            print(f"  Success rate: {len(response_times)}/20")
    
    def test_memory_usage(self):
        """Test memory usage"""
        print("Testing memory usage...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make several requests
        for _ in range(10):
            self.test_api_response_time('/api/v1/user/products/')
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        print(f"Memory usage:")
        print(f"  Before: {memory_before:.1f} MB")
        print(f"  After: {memory_after:.1f} MB")
        print(f"  Increase: {memory_increase:.1f} MB")
    
    def generate_report(self):
        """Generate performance report"""
        print("\n" + "="*50)
        print("PERFORMANCE TEST REPORT")
        print("="*50)
        
        if not self.results:
            print("No test results available")
            return
        
        # Calculate statistics
        successful_results = [r for r in self.results if r['success']]
        failed_results = [r for r in self.results if not r['success']]
        
        if successful_results:
            response_times = [r['response_time'] for r in successful_results]
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"Total tests: {len(self.results)}")
            print(f"Successful: {len(successful_results)}")
            print(f"Failed: {len(failed_results)}")
            print(f"Success rate: {len(successful_results)/len(self.results)*100:.1f}%")
            print(f"Average response time: {avg_time:.3f}s")
            print(f"Max response time: {max_time:.3f}s")
            print(f"Min response time: {min_time:.3f}s")
        
        # Performance recommendations
        print("\nPERFORMANCE RECOMMENDATIONS:")
        
        if successful_results:
            avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
            
            if avg_time > 1.0:
                print("⚠️  Average response time is high (>1s) - consider optimization")
            elif avg_time > 0.5:
                print("⚠️  Average response time is moderate (>0.5s) - consider caching")
            else:
                print("✅ Average response time is good (<0.5s)")
        
        if len(failed_results) > 0:
            print(f"⚠️  {len(failed_results)} requests failed - check error logs")
        
        # Slow endpoints
        slow_endpoints = [r for r in successful_results if r['response_time'] > 0.5]
        if slow_endpoints:
            print(f"⚠️  {len(slow_endpoints)} endpoints are slow (>0.5s)")
            for endpoint in slow_endpoints:
                print(f"    - {endpoint['endpoint']}: {endpoint['response_time']:.3f}s")

def run_all_tests():
    """Run all performance tests"""
    print("🚀 Starting Performance Phase 2 Tests...")
    print("="*50)
    
    tester = PerformanceTester()
    
    # Run tests
    tester.test_database_performance()
    tester.test_caching_performance()
    tester.test_pagination_performance()
    tester.test_search_performance()
    tester.test_concurrent_load()
    tester.test_memory_usage()
    
    # Generate report
    tester.generate_report()
    
    print("="*50)
    print("✅ Performance Phase 2 Tests Completed!")

if __name__ == "__main__":
    run_all_tests()


