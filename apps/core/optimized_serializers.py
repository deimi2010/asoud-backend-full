"""
Optimized Serializers for ASOUD Platform with Performance Enhancements
"""

import logging
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from django.db.models import Prefetch, Q, F, Count, Sum, Avg, Max, Min
from django.core.cache import cache
from apps.core.caching import cache_manager, cache_result
from apps.core.performance import QueryProfiler

logger = logging.getLogger(__name__)

class OptimizedModelSerializer(ModelSerializer):
    """
    Base optimized model serializer with performance enhancements
    """
    
    def __init__(self, *args, **kwargs):
        self.optimize_queries = kwargs.pop('optimize_queries', True)
        self.cache_result = kwargs.pop('cache_result', False)
        self.cache_timeout = kwargs.pop('cache_timeout', 300)
        super().__init__(*args, **kwargs)
    
    def to_representation(self, instance):
        """Optimized representation with caching"""
        if self.cache_result:
            cache_key = f"{self.__class__.__name__}:{instance.__class__.__name__}:{instance.id}"
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        with QueryProfiler():
            result = super().to_representation(instance)
        
        if self.cache_result:
            cache_manager.set(cache_key, result, self.cache_timeout)
        
        return result

class OptimizedProductSerializer(OptimizedModelSerializer):
    """
    Optimized product serializer with performance enhancements
    """
    
    market_name = serializers.CharField(source='market.name', read_only=True)
    market_business_id = serializers.CharField(source='market.business_id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    owner_name = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    discounts = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    total_sold = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    
    class Meta:
        model = None  # Will be set dynamically
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'status',
            'market_name', 'market_business_id', 'category_name', 'sub_category_name',
            'owner_name', 'images', 'discounts', 'keywords',
            'total_sold', 'total_revenue', 'view_count', 'created_at', 'updated_at'
        ]
    
    def get_owner_name(self, obj):
        """Get owner name with caching"""
        if hasattr(obj, 'market') and hasattr(obj.market, 'owner'):
            return f"{obj.market.owner.first_name} {obj.market.owner.last_name}"
        return None
    
    def get_images(self, obj):
        """Get product images with optimization"""
        if hasattr(obj, 'images'):
            return [{'id': img.id, 'image': img.image.url} for img in obj.images.all()]
        return []
    
    def get_discounts(self, obj):
        """Get active discounts with optimization"""
        if hasattr(obj, 'discounts'):
            from django.utils import timezone
            now = timezone.now()
            active_discounts = obj.discounts.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )
            return [{'id': d.id, 'percentage': d.percentage, 'position': d.position} for d in active_discounts]
        return []
    
    def get_keywords(self, obj):
        """Get product keywords with optimization"""
        if hasattr(obj, 'keywords'):
            return [{'id': k.id, 'name': k.name} for k in obj.keywords.all()]
        return []
    
    def get_total_sold(self, obj):
        """Get total sold quantity with caching"""
        cache_key = f"product_total_sold:{obj.id}"
        total_sold = cache_manager.get(cache_key)
        
        if total_sold is None:
            from apps.cart.models import OrderItem
            total_sold = OrderItem.objects.filter(
                product=obj,
                order__is_paid=True
            ).aggregate(total=Sum('quantity'))['total'] or 0
            cache_manager.set(cache_key, total_sold, 1800)  # 30 minutes
        
        return total_sold
    
    def get_total_revenue(self, obj):
        """Get total revenue with caching"""
        cache_key = f"product_total_revenue:{obj.id}"
        total_revenue = cache_manager.get(cache_key)
        
        if total_revenue is None:
            from apps.cart.models import OrderItem
            total_revenue = OrderItem.objects.filter(
                product=obj,
                order__is_paid=True
            ).aggregate(
                total=Sum(F('quantity') * F('product__price'))
            )['total'] or 0
            cache_manager.set(cache_key, total_revenue, 1800)  # 30 minutes
        
        return total_revenue
    
    def get_view_count(self, obj):
        """Get view count with caching"""
        if hasattr(obj, 'view_count'):
            return obj.view_count
        return 0

class OptimizedMarketSerializer(OptimizedModelSerializer):
    """
    Optimized market serializer with performance enhancements
    """
    
    owner_name = serializers.CharField(source='owner.first_name', read_only=True)
    owner_last_name = serializers.CharField(source='owner.last_name', read_only=True)
    sub_category_name = serializers.CharField(source='sub_category.name', read_only=True)
    products_count = serializers.SerializerMethodField()
    total_products = serializers.SerializerMethodField()
    published_products = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    average_product_price = serializers.SerializerMethodField()
    low_stock_products = serializers.SerializerMethodField()
    
    class Meta:
        model = None  # Will be set dynamically
        fields = [
            'id', 'name', 'business_id', 'description', 'is_verified',
            'owner_name', 'owner_last_name', 'sub_category_name',
            'products_count', 'total_products', 'published_products',
            'total_sales', 'total_revenue', 'average_product_price',
            'low_stock_products', 'created_at', 'updated_at'
        ]
    
    def get_products_count(self, obj):
        """Get products count with caching"""
        cache_key = f"market_products_count:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.products.count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_total_products(self, obj):
        """Get total products with caching"""
        cache_key = f"market_total_products:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.products.count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_published_products(self, obj):
        """Get published products count with caching"""
        cache_key = f"market_published_products:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.products.filter(status='published').count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_total_sales(self, obj):
        """Get total sales with caching"""
        cache_key = f"market_total_sales:{obj.id}"
        total_sales = cache_manager.get(cache_key)
        
        if total_sales is None:
            from apps.cart.models import OrderItem
            total_sales = OrderItem.objects.filter(
                product__market=obj,
                order__is_paid=True
            ).aggregate(total=Sum('quantity'))['total'] or 0
            cache_manager.set(cache_key, total_sales, 1800)  # 30 minutes
        
        return total_sales
    
    def get_total_revenue(self, obj):
        """Get total revenue with caching"""
        cache_key = f"market_total_revenue:{obj.id}"
        total_revenue = cache_manager.get(cache_key)
        
        if total_revenue is None:
            from apps.cart.models import OrderItem
            total_revenue = OrderItem.objects.filter(
                product__market=obj,
                order__is_paid=True
            ).aggregate(
                total=Sum(F('quantity') * F('product__price'))
            )['total'] or 0
            cache_manager.set(cache_key, total_revenue, 1800)  # 30 minutes
        
        return total_revenue
    
    def get_average_product_price(self, obj):
        """Get average product price with caching"""
        cache_key = f"market_avg_price:{obj.id}"
        avg_price = cache_manager.get(cache_key)
        
        if avg_price is None:
            avg_price = obj.products.aggregate(avg=Avg('price'))['avg'] or 0
            cache_manager.set(cache_key, avg_price, 1800)  # 30 minutes
        
        return avg_price
    
    def get_low_stock_products(self, obj):
        """Get low stock products count with caching"""
        cache_key = f"market_low_stock:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.products.filter(stock__lte=10).count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count

class OptimizedOrderSerializer(OptimizedModelSerializer):
    """
    Optimized order serializer with performance enhancements
    """
    
    user_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    market_name = serializers.CharField(source='market.name', read_only=True)
    items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = None  # Will be set dynamically
        fields = [
            'id', 'description', 'status', 'is_paid', 'type',
            'user_name', 'user_last_name', 'market_name',
            'items', 'total_price', 'total_items', 'created_at', 'updated_at'
        ]
    
    def get_items(self, obj):
        """Get order items with optimization"""
        if hasattr(obj, 'items'):
            return [{
                'id': item.id,
                'product_name': item.product.name if item.product else None,
                'affiliate_name': item.affiliate.name if item.affiliate else None,
                'quantity': item.quantity,
                'total_price': item.total_price()
            } for item in obj.items.all()]
        return []
    
    def get_total_price(self, obj):
        """Get total price with caching"""
        cache_key = f"order_total_price:{obj.id}"
        total_price = cache_manager.get(cache_key)
        
        if total_price is None:
            total_price = obj.total_price()
            cache_manager.set(cache_key, total_price, 1800)  # 30 minutes
        
        return total_price
    
    def get_total_items(self, obj):
        """Get total items count with caching"""
        cache_key = f"order_total_items:{obj.id}"
        total_items = cache_manager.get(cache_key)
        
        if total_items is None:
            total_items = obj.total_items()
            cache_manager.set(cache_key, total_items, 1800)  # 30 minutes
        
        return total_items

class OptimizedUserSerializer(OptimizedModelSerializer):
    """
    Optimized user serializer with performance enhancements
    """
    
    markets_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = None  # Will be set dynamically
        fields = [
            'id', 'first_name', 'last_name', 'email', 'mobile_number',
            'is_owner', 'is_verified', 'is_active',
            'markets_count', 'products_count', 'orders_count', 'total_spent',
            'created_at', 'last_login'
        ]
    
    def get_markets_count(self, obj):
        """Get markets count with caching"""
        cache_key = f"user_markets_count:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.markets.count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_products_count(self, obj):
        """Get products count with caching"""
        cache_key = f"user_products_count:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            count = obj.markets.aggregate(
                total=Count('products')
            )['total'] or 0
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_orders_count(self, obj):
        """Get orders count with caching"""
        cache_key = f"user_orders_count:{obj.id}"
        count = cache_manager.get(cache_key)
        
        if count is None:
            from apps.cart.models import Order
            count = Order.objects.filter(user=obj).count()
            cache_manager.set(cache_key, count, 1800)  # 30 minutes
        
        return count
    
    def get_total_spent(self, obj):
        """Get total spent with caching"""
        cache_key = f"user_total_spent:{obj.id}"
        total_spent = cache_manager.get(cache_key)
        
        if total_spent is None:
            from apps.cart.models import Order
            total_spent = Order.objects.filter(
                user=obj,
                is_paid=True
            ).aggregate(total=Sum('total_price'))['total'] or 0
            cache_manager.set(cache_key, total_spent, 1800)  # 30 minutes
        
        return total_spent

class OptimizedSerializerMixin:
    """
    Mixin for optimized serializers
    """
    
    def get_optimized_queryset(self, queryset):
        """Get optimized queryset with select_related and prefetch_related"""
        if hasattr(self, 'optimize_queries') and self.optimize_queries:
            return queryset.select_related(
                'market', 'market__owner', 'category', 'sub_category'
            ).prefetch_related(
                'images', 'discounts', 'keywords'
            )
        return queryset
    
    def get_cached_data(self, cache_key, callable_func, timeout=300):
        """Get cached data or execute callable"""
        if hasattr(self, 'cache_result') and self.cache_result:
            return cache_manager.get_or_set(cache_key, callable_func, timeout)
        return callable_func()

class PaginatedSerializer(serializers.Serializer):
    """
    Paginated response serializer
    """
    
    def __init__(self, data_serializer, *args, **kwargs):
        self.data_serializer = data_serializer
        super().__init__(*args, **kwargs)
    
    def to_representation(self, paginated_data):
        """Convert paginated data to representation"""
        return {
            'results': self.data_serializer(paginated_data['results'], many=True).data,
            'count': paginated_data['count'],
            'total_pages': paginated_data['total_pages'],
            'current_page': paginated_data['current_page'],
            'has_next': paginated_data['has_next'],
            'has_previous': paginated_data['has_previous'],
            'next_page': paginated_data.get('next_page'),
            'previous_page': paginated_data.get('previous_page'),
        }

class BulkSerializer(serializers.Serializer):
    """
    Bulk operation serializer
    """
    
    def __init__(self, item_serializer, *args, **kwargs):
        self.item_serializer = item_serializer
        super().__init__(*args, **kwargs)
    
    def to_representation(self, bulk_data):
        """Convert bulk data to representation"""
        return {
            'created': self.item_serializer(bulk_data['created'], many=True).data,
            'updated': self.item_serializer(bulk_data['updated'], many=True).data,
            'deleted': bulk_data['deleted'],
            'errors': bulk_data.get('errors', []),
        }

# Performance monitoring decorators
def monitor_serializer_performance(serializer_class):
    """Monitor serializer performance"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            with QueryProfiler():
                return func(self, *args, **kwargs)
        return wrapper
    return decorator

def cache_serializer_result(timeout=300):
    """Cache serializer result"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            cache_key = f"{self.__class__.__name__}:{hash(str(args) + str(kwargs))}"
            return cache_manager.get_or_set(cache_key, lambda: func(self, *args, **kwargs), timeout)
        return wrapper
    return decorator


