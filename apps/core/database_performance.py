"""
Advanced Database Optimization Middleware and Utilities
Monitors query performance and implements automatic optimizations
"""

import logging
import time
from django.db import connection, reset_queries
from django.conf import settings
from django.core.cache import cache
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DatabasePerformanceMiddleware:
    """
    Middleware to monitor database query performance
    Tracks slow queries and provides optimization recommendations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_query_threshold = 0.1  # 100ms
        
    def __call__(self, request):
        # Reset query tracking
        reset_queries()
        
        # Start timing
        start_time = time.time()
        start_queries = len(connection.queries)
        
        # Process request
        response = self.get_response(request)
        
        # Calculate metrics
        end_time = time.time()
        total_time = end_time - start_time
        num_queries = len(connection.queries) - start_queries
        
        # Log if performance issues detected
        if settings.DEBUG or settings.ENVIRONMENT == 'development':
            if num_queries > 20:
                logger.warning(
                    f"High query count detected: {num_queries} queries for {request.path}"
                )
            
            # Check for slow queries
            slow_queries = [
                q for q in connection.queries 
                if float(q.get('time', 0)) > self.slow_query_threshold
            ]
            
            if slow_queries:
                logger.warning(
                    f"Slow queries detected on {request.path}: "
                    f"{len(slow_queries)} queries > {self.slow_query_threshold}s"
                )
                for query in slow_queries[:3]:  # Log first 3
                    logger.debug(f"Slow query ({query['time']}s): {query['sql'][:200]}")
        
        # Add performance headers in debug mode
        if settings.DEBUG:
            response['X-DB-Query-Count'] = str(num_queries)
            response['X-DB-Query-Time'] = f"{sum(float(q.get('time', 0)) for q in connection.queries):.3f}s"
            response['X-Total-Time'] = f"{total_time:.3f}s"
        
        return response


def cache_queryset(timeout=300, key_prefix=''):
    """
    Decorator to cache queryset results
    
    Usage:
        @cache_queryset(timeout=600, key_prefix='markets')
        def get_active_markets():
            return Market.objects.filter(status='published')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache keys matching a pattern
    
    Usage:
        invalidate_cache_pattern('markets:*')
    """
    try:
        # This requires django-redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('default')
        
        # Get all keys matching pattern
        keys = redis_conn.keys(f"asoud:{pattern}")
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")


class QueryOptimizer:
    """
    Utility class for query optimization
    """
    
    @staticmethod
    def bulk_create_with_batch(model, objects, batch_size=1000):
        """
        Bulk create objects with batching for memory efficiency
        
        Usage:
            QueryOptimizer.bulk_create_with_batch(Product, product_list)
        """
        total = len(objects)
        for i in range(0, total, batch_size):
            batch = objects[i:i + batch_size]
            model.objects.bulk_create(batch, ignore_conflicts=True)
            logger.debug(f"Created batch {i//batch_size + 1}: {len(batch)} objects")
    
    @staticmethod
    def bulk_update_with_batch(model, objects, fields, batch_size=1000):
        """
        Bulk update objects with batching
        
        Usage:
            QueryOptimizer.bulk_update_with_batch(Product, products, ['price', 'stock'])
        """
        total = len(objects)
        for i in range(0, total, batch_size):
            batch = objects[i:i + batch_size]
            model.objects.bulk_update(batch, fields)
            logger.debug(f"Updated batch {i//batch_size + 1}: {len(batch)} objects")
    
    @staticmethod
    def get_or_create_cached(model, cache_key, timeout=300, **lookup_kwargs):
        """
        Get or create with caching
        
        Usage:
            user = QueryOptimizer.get_or_create_cached(
                User, 
                f'user:{mobile}',
                mobile_number=mobile
            )
        """
        # Try cache first
        obj_id = cache.get(cache_key)
        if obj_id:
            try:
                return model.objects.get(id=obj_id), False
            except model.DoesNotExist:
                cache.delete(cache_key)
        
        # Get or create
        obj, created = model.objects.get_or_create(**lookup_kwargs)
        
        # Cache the ID
        cache.set(cache_key, obj.id, timeout)
        
        return obj, created


class QuerySetCache:
    """
    Context manager for caching querysets within a view
    """
    
    def __init__(self, queryset, cache_key, timeout=300):
        self.queryset = queryset
        self.cache_key = cache_key
        self.timeout = timeout
        
    def __enter__(self):
        # Try to get from cache
        cached_ids = cache.get(self.cache_key)
        if cached_ids is not None:
            logger.debug(f"Using cached queryset: {self.cache_key}")
            return self.queryset.model.objects.filter(id__in=cached_ids)
        
        return self.queryset
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Cache successful queryset IDs
            try:
                ids = list(self.queryset.values_list('id', flat=True))
                cache.set(self.cache_key, ids, self.timeout)
                logger.debug(f"Cached queryset: {self.cache_key} ({len(ids)} items)")
            except Exception as e:
                logger.error(f"Failed to cache queryset: {e}")


# Global query statistics
class QueryStatistics:
    """
    Track query statistics for monitoring
    """
    _stats = {
        'total_queries': 0,
        'slow_queries': 0,
        'cache_hits': 0,
        'cache_misses': 0,
    }
    
    @classmethod
    def increment(cls, key: str, value: int = 1):
        cls._stats[key] = cls._stats.get(key, 0) + value
    
    @classmethod
    def get_stats(cls):
        return cls._stats.copy()
    
    @classmethod
    def reset(cls):
        cls._stats = {k: 0 for k in cls._stats}


# Decorator for monitoring view performance
def monitor_performance(view_name: str = None):
    """
    Decorator to monitor view performance
    
    Usage:
        @monitor_performance('market_list')
        def get(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            reset_queries()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                num_queries = len(connection.queries)
                
                name = view_name or func.__name__
                
                if num_queries > 15:
                    logger.warning(
                        f"Performance warning [{name}]: "
                        f"{num_queries} queries in {elapsed:.3f}s"
                    )
                elif settings.DEBUG:
                    logger.info(
                        f"Performance [{name}]: "
                        f"{num_queries} queries in {elapsed:.3f}s"
                    )
        
        return wrapper
    return decorator
