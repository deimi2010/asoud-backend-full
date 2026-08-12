"""
Advanced Caching Strategy for ASOUD Platform
"""

import json
import pickle
import hashlib
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.conf import settings
from django.core.cache.utils import make_template_fragment_key
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils import timezone
from functools import wraps
import redis
from typing import Any, Optional, Union, List, Dict

logger = logging.getLogger(__name__)

class AdvancedCacheManager:
    """
    Advanced caching manager with Redis backend
    """
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            # Connections are lazy. Importing URL configuration and management
            # commands must never perform network I/O.
            self.redis_available = True
        except (TypeError, ValueError) as exc:
            logger.error(
                "Redis client configuration failed: %s",
                type(exc).__name__,
            )
            self.redis_client = None
            self.redis_available = False
        
        self.default_timeout = 300  # 5 minutes
        self.cache_prefix = "asoud"
    
    def _make_key(self, key: str, version: Optional[str] = None) -> str:
        """Create cache key with prefix and version"""
        if version:
            return f"{self.cache_prefix}:{version}:{key}"
        return f"{self.cache_prefix}:{key}"
    
    def get(self, key: str, default=None, version: Optional[str] = None) -> Any:
        """Get value from cache"""
        if not self.redis_available:
            return default
            
        try:
            cache_key = self._make_key(key, version)
            value = self.redis_client.get(cache_key)
            
            if value is None:
                return default
            
            # Try to deserialize JSON first, then pickle
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    return force_str(value)
                    
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, version: Optional[str] = None) -> bool:
        """Set value in cache"""
        if not self.redis_available:
            return False
            
        try:
            cache_key = self._make_key(key, version)
            timeout = timeout or self.default_timeout
            
            # Serialize value
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = pickle.dumps(value)
            
            return self.redis_client.setex(cache_key, timeout, serialized_value)
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str, version: Optional[str] = None) -> bool:
        """Delete value from cache"""
        try:
            cache_key = self._make_key(key, version)
            return bool(self.redis_client.delete(cache_key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str, version: Optional[str] = None) -> int:
        """Delete all keys matching pattern"""
        try:
            if version:
                pattern = f"{self.cache_prefix}:{version}:{pattern}"
            else:
                pattern = f"{self.cache_prefix}:{pattern}"
            
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def get_or_set(self, key: str, callable_func, timeout: Optional[int] = None, version: Optional[str] = None) -> Any:
        """Get value from cache or set it using callable"""
        value = self.get(key, version=version)
        if value is None:
            value = callable_func()
            self.set(key, value, timeout, version)
        return value
    
    def get_many(self, keys: List[str], version: Optional[str] = None) -> Dict[str, Any]:
        """Get multiple values from cache"""
        try:
            cache_keys = [self._make_key(key, version) for key in keys]
            values = self.redis_client.mget(cache_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        try:
                            result[key] = pickle.loads(value)
                        except (pickle.PickleError, TypeError):
                            result[key] = force_str(value)
                else:
                    result[key] = None
            
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {key: None for key in keys}
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None, version: Optional[str] = None) -> bool:
        """Set multiple values in cache"""
        try:
            timeout = timeout or self.default_timeout
            pipe = self.redis_client.pipeline()
            
            for key, value in data.items():
                cache_key = self._make_key(key, version)
                
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, default=str)
                else:
                    serialized_value = pickle.dumps(value)
                
                pipe.setex(cache_key, timeout, serialized_value)
            
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def increment(self, key: str, delta: int = 1, timeout: Optional[int] = None, version: Optional[str] = None) -> int:
        """Increment numeric value in cache"""
        try:
            cache_key = self._make_key(key, version)
            result = self.redis_client.incr(cache_key, delta)
            
            if timeout:
                self.redis_client.expire(cache_key, timeout)
            
            return result
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    def decrement(self, key: str, delta: int = 1, timeout: Optional[int] = None, version: Optional[str] = None) -> int:
        """Decrement numeric value in cache"""
        try:
            cache_key = self._make_key(key, version)
            result = self.redis_client.decr(cache_key, delta)
            
            if timeout:
                self.redis_client.expire(cache_key, timeout)
            
            return result
        except Exception as e:
            logger.error(f"Cache decrement error for key {key}: {e}")
            return 0
    
    def get_ttl(self, key: str, version: Optional[str] = None) -> int:
        """Get time to live for key"""
        try:
            cache_key = self._make_key(key, version)
            return self.redis_client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    def extend_ttl(self, key: str, timeout: int, version: Optional[str] = None) -> bool:
        """Extend time to live for key"""
        try:
            cache_key = self._make_key(key, version)
            return bool(self.redis_client.expire(cache_key, timeout))
        except Exception as e:
            logger.error(f"Cache extend TTL error for key {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_available:
            return {'error': 'Redis not available'}
            
        try:
            info = self.redis_client.info()
            return {
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'hit_rate': self._calculate_hit_rate(info),
                'total_keys': self.redis_client.dbsize(),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'error': str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

class CacheDecorators:
    """
    Cache decorators for different use cases
    """
    
    @staticmethod
    def cache_result(timeout: int = 300, key_prefix: str = "", version: Optional[str] = None):
        """Cache function result"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key
                key_data = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                # Try to get from cache
                cache_manager = AdvancedCacheManager()
                result = cache_manager.get(cache_key, version=version)
                
                if result is None:
                    result = func(*args, **kwargs)
                    cache_manager.set(cache_key, result, timeout, version)
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_page(timeout: int = 300, key_prefix: str = "", version: Optional[str] = None):
        """Cache page result"""
        def decorator(func):
            @wraps(func)
            def wrapper(request, *args, **kwargs):
                # Create cache key based on request
                key_data = f"{key_prefix}:{func.__name__}:{request.path}:{request.GET.urlencode()}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                # Try to get from cache
                cache_manager = AdvancedCacheManager()
                result = cache_manager.get(cache_key, version=version)
                
                if result is None:
                    result = func(request, *args, **kwargs)
                    cache_manager.set(cache_key, result, timeout, version)
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def cache_queryset(timeout: int = 300, key_prefix: str = "", version: Optional[str] = None):
        """Cache queryset result"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key based on function arguments
                key_data = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                # Try to get from cache
                cache_manager = AdvancedCacheManager()
                result = cache_manager.get(cache_key, version=version)
                
                if result is None:
                    queryset = func(*args, **kwargs)
                    # Convert queryset to list for caching
                    result = list(queryset.values())
                    cache_manager.set(cache_key, result, timeout, version)
                else:
                    # Convert back to queryset-like object
                    from django.db.models import QuerySet
                    result = QuerySet()
                
                return result
            return wrapper
        return decorator

class ModelCacheManager:
    """
    Model-specific cache management
    """
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.cache_manager = AdvancedCacheManager()
        self.model_name = model_class.__name__.lower()
    
    def get_by_id(self, obj_id: int, timeout: int = 300) -> Optional[Any]:
        """Get model instance by ID with caching"""
        cache_key = f"{self.model_name}:id:{obj_id}"
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            try:
                result = self.model_class.objects.get(id=obj_id)
                self.cache_manager.set(cache_key, result, timeout)
            except self.model_class.DoesNotExist:
                return None
        
        return result
    
    def get_by_field(self, field: str, value: Any, timeout: int = 300) -> Optional[Any]:
        """Get model instance by field with caching"""
        cache_key = f"{self.model_name}:{field}:{value}"
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            try:
                result = self.model_class.objects.get(**{field: value})
                self.cache_manager.set(cache_key, result, timeout)
            except self.model_class.DoesNotExist:
                return None
        
        return result
    
    def get_queryset(self, filters: Dict[str, Any], timeout: int = 300) -> List[Dict]:
        """Get filtered queryset with caching"""
        cache_key = f"{self.model_name}:queryset:{hash(str(filters))}"
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            queryset = self.model_class.objects.filter(**filters)
            result = list(queryset.values())
            self.cache_manager.set(cache_key, result, timeout)
        
        return result
    
    def invalidate_by_id(self, obj_id: int):
        """Invalidate cache for specific object ID"""
        cache_key = f"{self.model_name}:id:{obj_id}"
        self.cache_manager.delete(cache_key)
    
    def invalidate_by_field(self, field: str, value: Any):
        """Invalidate cache for specific field value"""
        cache_key = f"{self.model_name}:{field}:{value}"
        self.cache_manager.delete(cache_key)
    
    def invalidate_queryset(self, filters: Dict[str, Any]):
        """Invalidate cache for specific queryset"""
        cache_key = f"{self.model_name}:queryset:{hash(str(filters))}"
        self.cache_manager.delete(cache_key)
    
    def invalidate_all(self):
        """Invalidate all cache for this model"""
        pattern = f"{self.model_name}:*"
        self.cache_manager.delete_pattern(pattern)

class CacheWarming:
    """
    Cache warming utilities
    """
    
    def __init__(self):
        self.cache_manager = AdvancedCacheManager()
    
    def warm_popular_products(self, limit: int = 100):
        """Warm cache with popular products"""
        if not self.cache_manager.redis_available:
            logger.warning("Redis not available, skipping cache warming")
            return
            
        from apps.product.models import Product
        
        products = Product.objects.filter(
            status='published'
        ).order_by('-view_count')[:limit]
        
        for product in products:
            cache_key = f"product:id:{product.id}"
            self.cache_manager.set(cache_key, product, 3600)  # 1 hour
    
    def warm_verified_markets(self, limit: int = 50):
        """Warm cache with verified markets"""
        if not self.cache_manager.redis_available:
            logger.warning("Redis not available, skipping cache warming")
            return
            
        from apps.market.models import Market
        
        markets = Market.objects.filter(
            is_verified=True
        ).order_by('-created_at')[:limit]
        
        for market in markets:
            cache_key = f"market:id:{market.id}"
            self.cache_manager.set(cache_key, market, 3600)  # 1 hour
    
    def warm_user_data(self, user_id: int):
        """Warm cache with user data"""
        from apps.users.models import User
        
        try:
            user = User.objects.get(id=user_id)
            cache_key = f"user:id:{user_id}"
            self.cache_manager.set(cache_key, user, 1800)  # 30 minutes
            logger.info(f"Warmed cache for user {user_id}")
        except User.DoesNotExist:
            logger.warning(f"User {user_id} not found for cache warming")
        except Exception as e:
            logger.error(f"Error warming cache for user {user_id}: {e}")
    
    def warm_analytics_data(self):
        """Warm cache with analytics data"""
        if not self.cache_manager.redis_available:
            logger.warning("Redis not available, skipping analytics cache warming")
            return
            
        from apps.product.models import Product
        from apps.market.models import Market
        from apps.cart.models import Order
        
        # Product statistics
        product_stats = Product.objects.aggregate(
            total_products=Count('id'),
            published_products=Count('id', filter=Q(status='published')),
            average_price=Avg('price'),
            total_stock=Sum('stock')
        )
        
        cache_key = "analytics:product_stats"
        self.cache_manager.set(cache_key, product_stats, 3600)  # 1 hour
        
        # Market statistics
        market_stats = Market.objects.aggregate(
            total_markets=Count('id'),
            verified_markets=Count('id', filter=Q(is_verified=True)),
        )
        
        cache_key = "analytics:market_stats"
        self.cache_manager.set(cache_key, market_stats, 3600)  # 1 hour
        
        # Order statistics
        order_stats = Order.objects.aggregate(
            total_orders=Count('id'),
            paid_orders=Count('id', filter=Q(is_paid=True)),
            total_revenue=Sum('total_price', filter=Q(is_paid=True))
        )
        
        cache_key = "analytics:order_stats"
        self.cache_manager.set(cache_key, order_stats, 3600)  # 1 hour

# Global cache manager instance
cache_manager = AdvancedCacheManager()

# Cache decorators
cache_result = CacheDecorators.cache_result
cache_page = CacheDecorators.cache_page
cache_queryset = CacheDecorators.cache_queryset

