#!/usr/bin/env python3
"""
Complete Performance Testing Script for ASOUD Platform Phase 2

This is a manually-invoked benchmark, not a Django unit test.  Keeping the
historical filename is useful for operators, but unittest discovery must not
import production settings or optional host-monitoring dependencies.
"""

if __name__ != "__main__":
    import unittest

    raise unittest.SkipTest("manual performance benchmark")

import os
import sys
import django
from django.db.models import Avg, Count, Max
import requests
import time
import json
import psutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add the project directory to Python path
sys.path.append('/home/devops/projects/asoud-main-1-/asoud-main')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

class ComprehensivePerformanceTester:
    """Comprehensive performance testing for Phase 2"""
    
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.results = []
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def test_system_resources(self):
        """Test system resource usage"""
        print("🖥️ Testing system resources...")
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        system_metrics = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'memory_used_gb': round(memory_used_gb, 2),
            'memory_total_gb': round(memory_total_gb, 2),
            'disk_percent': disk_percent,
            'disk_used_gb': round(disk_used_gb, 2),
            'disk_total_gb': round(disk_total_gb, 2),
        }
        
        print(f"  CPU: {cpu_percent}%")
        print(f"  Memory: {memory_percent}% ({memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB)")
        print(f"  Disk: {disk_percent}% ({disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB)")
        
        return system_metrics
    
    def test_database_performance(self):
        """Test database performance"""
        print("🗄️ Testing database performance...")
        
        from django.db import connection
        from apps.product.models import Product
        from apps.market.models import Market
        from apps.cart.models import Order
        
        db_results = {}
        
        # Test 1: Simple query
        start_time = time.time()
        products = list(Product.objects.all()[:100])
        simple_query_time = time.time() - start_time
        db_results['simple_query_time'] = round(simple_query_time * 1000, 2)
        
        # Test 2: Complex query with joins
        start_time = time.time()
        markets = list(Market.objects.select_related('user', 'sub_category').all()[:50])
        complex_query_time = time.time() - start_time
        db_results['complex_query_time'] = round(complex_query_time * 1000, 2)
        
        # Test 3: Aggregation query
        start_time = time.time()
        stats = Product.objects.aggregate(
            total=Count('id'),
            avg_price=Avg('price'),
            max_price=Max('price')
        )
        aggregation_time = time.time() - start_time
        db_results['aggregation_time'] = round(aggregation_time * 1000, 2)
        
        # Test 4: Query count
        query_count = len(connection.queries)
        db_results['query_count'] = query_count
        
        print(f"  Simple query: {db_results['simple_query_time']}ms")
        print(f"  Complex query: {db_results['complex_query_time']}ms")
        print(f"  Aggregation: {db_results['aggregation_time']}ms")
        print(f"  Total queries: {query_count}")
        
        return db_results
    
    def test_caching_performance(self):
        """Test caching performance"""
        print("💾 Testing caching performance...")
        
        from django.core.cache import cache
        from apps.core.caching import cache_manager
        
        cache_results = {}
        
        # Test 1: Django cache
        start_time = time.time()
        cache.set('test_key', 'test_value', 60)
        cache_value = cache.get('test_key')
        django_cache_time = time.time() - start_time
        cache_results['django_cache_time'] = round(django_cache_time * 1000, 2)
        
        # Test 2: Advanced cache manager
        start_time = time.time()
        cache_manager.set('test_advanced', {'data': 'test'}, 60)
        advanced_value = cache_manager.get('test_advanced')
        advanced_cache_time = time.time() - start_time
        cache_results['advanced_cache_time'] = round(advanced_cache_time * 1000, 2)
        
        # Test 3: Cache hit rate
        cache_hits = 0
        cache_misses = 0
        
        for i in range(10):
            key = f'test_key_{i}'
            if cache.get(key):
                cache_hits += 1
            else:
                cache_misses += 1
                cache.set(key, f'value_{i}', 60)
        
        hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100 if (cache_hits + cache_misses) > 0 else 0
        cache_results['hit_rate'] = round(hit_rate, 2)
        
        print(f"  Django cache: {cache_results['django_cache_time']}ms")
        print(f"  Advanced cache: {cache_results['advanced_cache_time']}ms")
        print(f"  Cache hit rate: {hit_rate}%")
        
        return cache_results
    
    def test_api_endpoint(self, endpoint, method='GET', data=None, headers=None):
        """Test single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time_ms': round(response_time, 2),
                'success': response.status_code < 400,
                'content_length': len(response.content),
                'headers': dict(response.headers),
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
            
        except Exception as e:
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': 0,
                'response_time_ms': 0,
                'success': False,
                'error': str(e),
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
    
    def test_api_performance(self):
        """Test API performance"""
        print("🌐 Testing API performance...")
        
        endpoints = [
            '/api/v1/user/products/',
            '/api/v1/user/markets/',
            '/api/v1/user/order/',
            '/health/',
            '/api/v1/user/products/?page=1&page_size=10',
            '/api/v1/user/markets/?search=test',
        ]
        
        api_results = {}
        
        for endpoint in endpoints:
            result = self.test_api_endpoint(endpoint)
            api_results[endpoint] = result
            print(f"  {endpoint}: {result['response_time_ms']}ms ({result['status_code']})")
        
        return api_results
    
    def test_concurrent_load(self, num_requests=20):
        """Test concurrent load"""
        print(f"⚡ Testing concurrent load ({num_requests} requests)...")
        
        endpoints = [
            '/api/v1/user/products/',
            '/api/v1/user/markets/',
            '/health/',
        ]
        
        concurrent_results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for _ in range(num_requests):
                endpoint = endpoints[_ % len(endpoints)]
                future = executor.submit(self.test_api_endpoint, endpoint)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                concurrent_results.append(result)
        
        # Calculate statistics
        successful_results = [r for r in concurrent_results if r['success']]
        response_times = [r['response_time_ms'] for r in successful_results]
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            success_rate = (len(successful_results) / len(concurrent_results)) * 100
            
            concurrent_stats = {
                'total_requests': num_requests,
                'successful_requests': len(successful_results),
                'success_rate': round(success_rate, 2),
                'avg_response_time_ms': round(avg_time, 2),
                'max_response_time_ms': round(max_time, 2),
                'min_response_time_ms': round(min_time, 2),
            }
            
            print(f"  Total requests: {num_requests}")
            print(f"  Successful: {len(successful_results)} ({success_rate:.1f}%)")
            print(f"  Avg response time: {avg_time:.2f}ms")
            print(f"  Max response time: {max_time:.2f}ms")
            print(f"  Min response time: {min_time:.2f}ms")
            
            return concurrent_stats
        
        return {'error': 'No successful requests'}
    
    def test_memory_usage(self):
        """Test memory usage during operations"""
        print("🧠 Testing memory usage...")
        
        process = psutil.Process()
        memory_before = process.memory_info().rss / (1024**2)  # MB
        
        # Perform memory-intensive operations
        for i in range(100):
            self.test_api_endpoint('/api/v1/user/products/')
        
        memory_after = process.memory_info().rss / (1024**2)  # MB
        memory_increase = memory_after - memory_before
        
        memory_stats = {
            'memory_before_mb': round(memory_before, 2),
            'memory_after_mb': round(memory_after, 2),
            'memory_increase_mb': round(memory_increase, 2),
        }
        
        print(f"  Memory before: {memory_before:.1f} MB")
        print(f"  Memory after: {memory_after:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        
        return memory_stats
    
    def generate_comprehensive_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT - PHASE 2")
        print("="*60)
        
        total_time = time.time() - self.start_time
        
        # System resources
        system_metrics = self.test_system_resources()
        
        # Database performance
        db_metrics = self.test_database_performance()
        
        # Caching performance
        cache_metrics = self.test_caching_performance()
        
        # API performance
        api_metrics = self.test_api_performance()
        
        # Concurrent load
        concurrent_metrics = self.test_concurrent_load()
        
        # Memory usage
        memory_metrics = self.test_memory_usage()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            system_metrics, db_metrics, cache_metrics, 
            api_metrics, concurrent_metrics, memory_metrics
        )
        
        report = {
            'test_session': {
                'start_time': datetime.now().isoformat(),
                'total_duration_seconds': round(total_time, 2),
            },
            'system_metrics': system_metrics,
            'database_metrics': db_metrics,
            'cache_metrics': cache_metrics,
            'api_metrics': api_metrics,
            'concurrent_metrics': concurrent_metrics,
            'memory_metrics': memory_metrics,
            'recommendations': recommendations,
            'phase2_status': self._evaluate_phase2_status(
                system_metrics, db_metrics, cache_metrics, 
                api_metrics, concurrent_metrics, memory_metrics
            )
        }
        
        return report
    
    def _generate_recommendations(self, system, db, cache, api, concurrent, memory):
        """Generate performance recommendations"""
        recommendations = []
        
        # System recommendations
        if system['cpu_percent'] > 80:
            recommendations.append("⚠️ High CPU usage - consider optimizing queries or scaling")
        
        if system['memory_percent'] > 80:
            recommendations.append("⚠️ High memory usage - consider increasing memory or optimizing caching")
        
        if system['disk_percent'] > 90:
            recommendations.append("⚠️ High disk usage - consider cleaning up old files")
        
        # Database recommendations
        if db['simple_query_time'] > 100:
            recommendations.append("⚠️ Slow simple queries - check database indexes")
        
        if db['complex_query_time'] > 500:
            recommendations.append("⚠️ Slow complex queries - optimize joins and select_related")
        
        if db['query_count'] > 50:
            recommendations.append("⚠️ High query count - potential N+1 problem")
        
        # Cache recommendations
        if cache['hit_rate'] < 80:
            recommendations.append("⚠️ Low cache hit rate - optimize cache strategy")
        
        # API recommendations
        slow_endpoints = [ep for ep, metrics in api.items() if metrics.get('response_time_ms', 0) > 1000]
        if slow_endpoints:
            recommendations.append(f"⚠️ Slow API endpoints: {', '.join(slow_endpoints)}")
        
        # Concurrent recommendations
        if concurrent.get('success_rate', 0) < 95:
            recommendations.append("⚠️ Low success rate under load - check error handling")
        
        if concurrent.get('avg_response_time_ms', 0) > 500:
            recommendations.append("⚠️ Slow response times under load - consider optimization")
        
        # Memory recommendations
        if memory['memory_increase_mb'] > 100:
            recommendations.append("⚠️ High memory increase - check for memory leaks")
        
        if not recommendations:
            recommendations.append("✅ All performance metrics are within acceptable ranges")
        
        return recommendations
    
    def _evaluate_phase2_status(self, system, db, cache, api, concurrent, memory):
        """Evaluate Phase 2 implementation status"""
        status = {
            'database_optimization': 'PASS',
            'caching_system': 'PASS',
            'api_performance': 'PASS',
            'concurrent_handling': 'PASS',
            'memory_efficiency': 'PASS',
            'overall_status': 'PASS'
        }
        
        # Database evaluation
        if db['simple_query_time'] > 200 or db['complex_query_time'] > 1000:
            status['database_optimization'] = 'FAIL'
        
        # Caching evaluation
        if cache['hit_rate'] < 70:
            status['caching_system'] = 'FAIL'
        
        # API evaluation
        slow_apis = [ep for ep, metrics in api.items() if metrics.get('response_time_ms', 0) > 2000]
        if slow_apis:
            status['api_performance'] = 'FAIL'
        
        # Concurrent evaluation
        if concurrent.get('success_rate', 0) < 90 or concurrent.get('avg_response_time_ms', 0) > 1000:
            status['concurrent_handling'] = 'FAIL'
        
        # Memory evaluation
        if memory['memory_increase_mb'] > 200:
            status['memory_efficiency'] = 'FAIL'
        
        # Overall status
        if any(status[key] == 'FAIL' for key in status if key != 'overall_status'):
            status['overall_status'] = 'FAIL'
        
        return status

def run_comprehensive_tests():
    """Run comprehensive performance tests"""
    print("🚀 Starting Comprehensive Performance Tests for Phase 2...")
    print("="*60)
    
    tester = ComprehensivePerformanceTester()
    
    try:
        report = tester.generate_comprehensive_report()
        
        # Display results
        print("\n📊 PERFORMANCE RESULTS:")
        print("-" * 40)
        
        for category, metrics in report.items():
            if isinstance(metrics, dict) and category != 'test_session':
                print(f"\n{category.upper().replace('_', ' ')}:")
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        print(f"  {key}: {value}")
                    elif isinstance(value, dict):
                        print(f"  {key}: {len(value)} items")
        
        # Display recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        # Display Phase 2 status
        print("\n🎯 PHASE 2 STATUS:")
        print("-" * 40)
        for key, value in report['phase2_status'].items():
            status_icon = "✅" if value == "PASS" else "❌"
            print(f"{status_icon} {key.replace('_', ' ').title()}: {value}")
        
        # Save report
        with open('performance_report_phase2.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: performance_report_phase2.json")
        print("="*60)
        print("✅ Comprehensive Performance Testing Completed!")
        
        return report
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return None

if __name__ == "__main__":
    run_comprehensive_tests()

