#!/usr/bin/env python3
"""
Performance Testing Script for Database Indexes
Tests query performance before and after index creation

Usage:
    python test_index_performance.py --before  # Test before indexes
    python test_index_performance.py --after   # Test after indexes
    python test_index_performance.py --compare # Compare results
"""

import os
import sys
import time
import json
import django
from datetime import datetime
from django.db import connection
from django.db.models import Count, Sum, Q

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.product.models import Product
from apps.market.models import Market
from apps.cart.models import Order


class PerformanceTester:
    """Test database query performance"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': []
        }
    
    def reset_query_counter(self):
        """Reset Django query counter"""
        connection.queries_log.clear()
    
    def measure_query(self, name, query_func, iterations=10):
        """
        Measure query execution time
        
        Args:
            name: Test name
            query_func: Function that executes the query
            iterations: Number of times to run the query
        
        Returns:
            dict: Test results
        """
        times = []
        query_counts = []
        
        for i in range(iterations):
            self.reset_query_counter()
            start_time = time.time()
            
            # Execute query
            result = query_func()
            
            # Force evaluation if QuerySet
            if hasattr(result, '__iter__'):
                list(result)
            
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            times.append(execution_time)
            query_counts.append(len(connection.queries))
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        avg_queries = sum(query_counts) / len(query_counts)
        
        test_result = {
            'name': name,
            'avg_time_ms': round(avg_time, 2),
            'min_time_ms': round(min_time, 2),
            'max_time_ms': round(max_time, 2),
            'avg_query_count': round(avg_queries, 1),
            'iterations': iterations
        }
        
        self.results['tests'].append(test_result)
        
        print(f"✓ {name}")
        print(f"  Avg: {test_result['avg_time_ms']}ms")
        print(f"  Min: {test_result['min_time_ms']}ms")
        print(f"  Max: {test_result['max_time_ms']}ms")
        print(f"  Queries: {test_result['avg_query_count']}")
        print()
        
        return test_result
    
    def test_product_queries(self):
        """Test Product model queries"""
        print("=" * 60)
        print("PRODUCT MODEL TESTS")
        print("=" * 60)
        
        # Test 1: Filter by market and status
        self.measure_query(
            "Product: Filter by market and status",
            lambda: Product.objects.filter(
                market_id=1,
                status=Product.PUBLISHED
            )[:20]
        )
        
        # Test 2: Filter by category and status
        self.measure_query(
            "Product: Filter by category and status",
            lambda: Product.objects.filter(
                sub_category_id=1,
                status=Product.PUBLISHED
            )[:20]
        )
        
        # Test 3: List products with ordering
        self.measure_query(
            "Product: List with created_at ordering",
            lambda: Product.objects.filter(
                status=Product.PUBLISHED
            ).order_by('-created_at')[:20]
        )
        
        # Test 4: Filter by tag
        self.measure_query(
            "Product: Filter by tag (special offers)",
            lambda: Product.objects.filter(
                tag=Product.SPECIAL_OFFER
            )[:20]
        )
        
        # Test 5: Marketer products
        self.measure_query(
            "Product: Filter marketer products",
            lambda: Product.objects.filter(
                is_marketer=True
            )[:20]
        )
    
    def test_market_queries(self):
        """Test Market model queries"""
        print("=" * 60)
        print("MARKET MODEL TESTS")
        print("=" * 60)
        
        # Test 1: User's markets
        self.measure_query(
            "Market: User's markets with status",
            lambda: Market.objects.filter(
                user_id=1,
                status=Market.PUBLISHED
            )
        )
        
        # Test 2: Public markets listing
        self.measure_query(
            "Market: Public listing with ordering",
            lambda: Market.objects.filter(
                status=Market.PUBLISHED
            ).order_by('-created_at')[:20]
        )
        
        # Test 3: Category markets
        self.measure_query(
            "Market: Filter by category",
            lambda: Market.objects.filter(
                sub_category_id=1,
                status=Market.PUBLISHED
            )[:20]
        )
        
        # Test 4: Business ID lookup
        self.measure_query(
            "Market: Lookup by business_id",
            lambda: Market.objects.filter(
                business_id='12345'
            ).first()
        )
        
        # Test 5: Paid active markets
        self.measure_query(
            "Market: Paid and active markets",
            lambda: Market.objects.filter(
                is_paid=True,
                status=Market.PUBLISHED
            )[:20]
        )
    
    def test_order_queries(self):
        """Test Order model queries"""
        print("=" * 60)
        print("ORDER MODEL TESTS")
        print("=" * 60)
        
        # Test 1: User's orders
        self.measure_query(
            "Order: User's orders with status",
            lambda: Order.objects.filter(
                user_id=1,
                status=Order.COMPLETED
            )[:20]
        )
        
        # Test 2: Order history
        self.measure_query(
            "Order: User's order history (sorted)",
            lambda: Order.objects.filter(
                user_id=1
            ).order_by('-created_at')[:20]
        )
        
        # Test 3: Financial report query
        self.measure_query(
            "Order: Paid orders for reporting",
            lambda: Order.objects.filter(
                status=Order.COMPLETED,
                is_paid=True
            ).aggregate(total=Sum('id'))  # Simplified
        )
        
        # Test 4: Recent paid orders
        self.measure_query(
            "Order: Recent paid orders",
            lambda: Order.objects.filter(
                is_paid=True
            ).order_by('-created_at')[:20]
        )
        
        # Test 5: Payment type analysis
        self.measure_query(
            "Order: Group by payment type and status",
            lambda: Order.objects.filter(
                type=Order.ONLINE,
                status=Order.COMPLETED
            )[:20]
        )
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("\n" + "=" * 60)
        print("DATABASE INDEX PERFORMANCE TEST")
        print("=" * 60)
        print()
        
        self.test_product_queries()
        self.test_market_queries()
        self.test_order_queries()
        
        return self.results
    
    def save_results(self, filename):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Results saved to: {filename}")
    
    def compare_results(self, before_file, after_file):
        """Compare before and after results"""
        with open(before_file, 'r') as f:
            before = json.load(f)
        with open(after_file, 'r') as f:
            after = json.load(f)
        
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        print()
        
        before_tests = {t['name']: t for t in before['tests']}
        after_tests = {t['name']: t for t in after['tests']}
        
        improvements = []
        
        for name in before_tests.keys():
            if name in after_tests:
                before_time = before_tests[name]['avg_time_ms']
                after_time = after_tests[name]['avg_time_ms']
                improvement = ((before_time - after_time) / before_time) * 100
                
                improvements.append({
                    'name': name,
                    'before': before_time,
                    'after': after_time,
                    'improvement_pct': round(improvement, 1)
                })
                
                status = "✓" if improvement > 0 else "✗"
                print(f"{status} {name}")
                print(f"  Before: {before_time}ms")
                print(f"  After:  {after_time}ms")
                print(f"  Change: {improvement:+.1f}%")
                print()
        
        # Calculate overall improvement
        avg_improvement = sum(i['improvement_pct'] for i in improvements) / len(improvements)
        
        print("=" * 60)
        print(f"AVERAGE IMPROVEMENT: {avg_improvement:+.1f}%")
        print("=" * 60)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test database index performance')
    parser.add_argument('--before', action='store_true', help='Test before indexes')
    parser.add_argument('--after', action='store_true', help='Test after indexes')
    parser.add_argument('--compare', action='store_true', help='Compare results')
    
    args = parser.parse_args()
    
    tester = PerformanceTester()
    
    if args.before:
        print("Running BEFORE index tests...")
        results = tester.run_all_tests()
        tester.save_results('performance_before_indexes.json')
    
    elif args.after:
        print("Running AFTER index tests...")
        results = tester.run_all_tests()
        tester.save_results('performance_after_indexes.json')
    
    elif args.compare:
        tester.compare_results(
            'performance_before_indexes.json',
            'performance_after_indexes.json'
        )
    
    else:
        print("Usage:")
        print("  python test_index_performance.py --before")
        print("  python test_index_performance.py --after")
        print("  python test_index_performance.py --compare")


if __name__ == '__main__':
    main()


