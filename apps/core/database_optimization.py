"""
Advanced Database Optimization for ASOUD Platform
"""

import logging
from django.db import connection, transaction
from django.db.models import Q, F, Count, Sum, Avg, Max, Min, Case, When, Value, CharField
from django.db.models.functions import Coalesce, Concat, Extract, Trunc
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """
    Comprehensive database optimization utilities
    """
    
    def __init__(self):
        self.connection = connection
    
    def create_optimized_indexes(self):
        """Create comprehensive database indexes for optimal performance"""
        try:
            # Check if we can connect to database
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            logger.error(f"Cannot connect to database: {e}")
            return False
            
        indexes = [
            # User indexes
            "CREATE INDEX IF NOT EXISTS idx_user_mobile ON users_user(mobile_number);",
            "CREATE INDEX IF NOT EXISTS idx_user_email ON users_user(email);",
            "CREATE INDEX IF NOT EXISTS idx_user_owner ON users_user(is_owner);",
            "CREATE INDEX IF NOT EXISTS idx_user_verified ON users_user(is_verified);",
            "CREATE INDEX IF NOT EXISTS idx_user_active ON users_user(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_user_created ON users_user(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_user_last_login ON users_user(last_login);",
            "CREATE INDEX IF NOT EXISTS idx_user_last_activity ON users_user(last_activity);",
            
            # Product indexes
            "CREATE INDEX IF NOT EXISTS idx_product_market ON apps_product(market_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_category ON apps_product(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_subcategory ON apps_product(sub_category_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_status ON apps_product(status);",
            "CREATE INDEX IF NOT EXISTS idx_product_price ON apps_product(price);",
            "CREATE INDEX IF NOT EXISTS idx_product_stock ON apps_product(stock);",
            "CREATE INDEX IF NOT EXISTS idx_product_created ON apps_product(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_product_updated ON apps_product(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_product_name ON apps_product(name);",
            "CREATE INDEX IF NOT EXISTS idx_product_is_marketer ON apps_product(is_marketer);",
            "CREATE INDEX IF NOT EXISTS idx_product_tag ON apps_product(tag);",
            "CREATE INDEX IF NOT EXISTS idx_product_sell_type ON apps_product(sell_type);",
            
            # Market indexes
            "CREATE INDEX IF NOT EXISTS idx_market_owner ON apps_market(owner_id);",
            "CREATE INDEX IF NOT EXISTS idx_market_business_id ON apps_market(business_id);",
            "CREATE INDEX IF NOT EXISTS idx_market_verified ON apps_market(is_verified);",
            "CREATE INDEX IF NOT EXISTS idx_market_subcategory ON apps_market(sub_category_id);",
            "CREATE INDEX IF NOT EXISTS idx_market_created ON apps_market(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_market_updated ON apps_market(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_market_name ON apps_market(name);",
            "CREATE INDEX IF NOT EXISTS idx_market_status ON apps_market(status);",
            
            # Order indexes
            "CREATE INDEX IF NOT EXISTS idx_order_user ON apps_cart_order(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_order_market ON apps_cart_order(market_id);",
            "CREATE INDEX IF NOT EXISTS idx_order_status ON apps_cart_order(status);",
            "CREATE INDEX IF NOT EXISTS idx_order_paid ON apps_cart_order(is_paid);",
            "CREATE INDEX IF NOT EXISTS idx_order_created ON apps_cart_order(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_order_updated ON apps_cart_order(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_order_type ON apps_cart_order(type);",
            
            # OrderItem indexes
            "CREATE INDEX IF NOT EXISTS idx_orderitem_order ON apps_cart_orderitem(order_id);",
            "CREATE INDEX IF NOT EXISTS idx_orderitem_product ON apps_cart_orderitem(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_orderitem_affiliate ON apps_cart_orderitem(affiliate_id);",
            "CREATE INDEX IF NOT EXISTS idx_orderitem_created ON apps_cart_orderitem(created_at);",
            
            # Payment indexes
            "CREATE INDEX IF NOT EXISTS idx_payment_user ON apps_payment_payment(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_payment_status ON apps_payment_payment(status);",
            "CREATE INDEX IF NOT EXISTS idx_payment_created ON apps_payment_payment(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_payment_updated ON apps_payment_payment(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_payment_amount ON apps_payment_payment(amount);",
            
            # Wallet indexes
            "CREATE INDEX IF NOT EXISTS idx_wallet_user ON apps_wallet_wallet(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_wallet_active ON apps_wallet_wallet(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_wallet_created ON apps_wallet_wallet(created_at);",
            
            # Transaction indexes
            "CREATE INDEX IF NOT EXISTS idx_transaction_user ON apps_wallet_transaction(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_from_wallet ON apps_wallet_transaction(from_wallet_id);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_to_wallet ON apps_wallet_transaction(to_wallet_id);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_action ON apps_wallet_transaction(action);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_created ON apps_wallet_transaction(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_amount ON apps_wallet_transaction(amount);",
            
            # Inventory indexes
            "CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory_log(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_action ON inventory_log(action);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_created ON inventory_log(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_order ON inventory_log(order_id);",
            
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_product_market_status ON apps_product(market_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_product_category_status ON apps_product(category_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_product_price_status ON apps_product(price, status);",
            "CREATE INDEX IF NOT EXISTS idx_product_stock_status ON apps_product(stock, status);",
            "CREATE INDEX IF NOT EXISTS idx_order_user_status ON apps_cart_order(user_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_order_market_status ON apps_cart_order(market_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_order_user_paid ON apps_cart_order(user_id, is_paid);",
            "CREATE INDEX IF NOT EXISTS idx_payment_user_status ON apps_payment_payment(user_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_user_action ON apps_wallet_transaction(user_id, action);",
            "CREATE INDEX IF NOT EXISTS idx_transaction_created_action ON apps_wallet_transaction(created_at, action);",
            
            # Text search indexes
            "CREATE INDEX IF NOT EXISTS idx_product_name_trgm ON apps_product USING gin(name gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_product_description_trgm ON apps_product USING gin(description gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_market_name_trgm ON apps_market USING gin(name gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_market_description_trgm ON apps_market USING gin(description gin_trgm_ops);",
            
            # Partial indexes for active records
            "CREATE INDEX IF NOT EXISTS idx_product_active ON apps_product(id) WHERE status = 'published';",
            "CREATE INDEX IF NOT EXISTS idx_market_active ON apps_market(id) WHERE is_verified = true;",
            "CREATE INDEX IF NOT EXISTS idx_user_active ON users_user(id) WHERE is_active = true;",
            "CREATE INDEX IF NOT EXISTS idx_order_pending ON apps_cart_order(id) WHERE status = 'pending';",
            "CREATE INDEX IF NOT EXISTS idx_payment_pending ON apps_payment_payment(id) WHERE status = 'pending';",
        ]
        
        with self.connection.cursor() as cursor:
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.info(f"Created index: {index_sql}")
                except Exception as e:
                    logger.error(f"Failed to create index: {e}")
    
    def analyze_query_performance(self):
        """Analyze query performance and identify slow queries"""
        with self.connection.cursor() as cursor:
            # Get slow queries from pg_stat_statements
            cursor.execute("""
                SELECT 
                    query,
                    mean_time,
                    calls,
                    total_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE mean_time > 100
                ORDER BY mean_time DESC
                LIMIT 20;
            """)
            
            slow_queries = cursor.fetchall()
            
            logger.info("Slow queries analysis:")
            for query in slow_queries:
                logger.warning(f"Query: {query[0][:100]}...")
                logger.warning(f"Mean time: {query[1]}ms, Calls: {query[2]}, Total time: {query[3]}ms")
                logger.warning(f"Rows: {query[4]}, Cache hit: {query[5]:.2f}%")
    
    def get_table_statistics(self):
        """Get table statistics for optimization"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation,
                    most_common_vals,
                    most_common_freqs
                FROM pg_stats
                WHERE schemaname = 'public'
                ORDER BY tablename, attname;
            """)
            
            stats = cursor.fetchall()
            
            logger.info("Table statistics:")
            for stat in stats:
                logger.info(f"Table: {stat[1]}, Column: {stat[2]}, Distinct: {stat[3]}, Correlation: {stat[4]}")
    
    def optimize_database_settings(self):
        """Optimize database settings for performance"""
        with self.connection.cursor() as cursor:
            # Check current settings
            cursor.execute("SHOW shared_buffers;")
            shared_buffers = cursor.fetchone()[0]
            
            cursor.execute("SHOW effective_cache_size;")
            effective_cache_size = cursor.fetchone()[0]
            
            cursor.execute("SHOW work_mem;")
            work_mem = cursor.fetchone()[0]
            
            cursor.execute("SHOW maintenance_work_mem;")
            maintenance_work_mem = cursor.fetchone()[0]
            
            logger.info(f"Current database settings:")
            logger.info(f"shared_buffers: {shared_buffers}")
            logger.info(f"effective_cache_size: {effective_cache_size}")
            logger.info(f"work_mem: {work_mem}")
            logger.info(f"maintenance_work_mem: {maintenance_work_mem}")
    
    def vacuum_and_analyze(self):
        """Run VACUUM and ANALYZE for optimal performance"""
        with self.connection.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """)
            
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                try:
                    # VACUUM ANALYZE
                    cursor.execute(f"VACUUM ANALYZE {table_name};")
                    logger.info(f"VACUUM ANALYZE completed for {table_name}")
                except Exception as e:
                    logger.error(f"Failed to VACUUM ANALYZE {table_name}: {e}")

class QueryOptimizer:
    """
    Query optimization utilities
    """
    
    @staticmethod
    def optimize_queryset(queryset, select_related=None, prefetch_related=None, only=None, defer=None):
        """Optimize queryset with select_related and prefetch_related"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        if only:
            queryset = queryset.only(*only)
        
        if defer:
            queryset = queryset.defer(*defer)
        
        return queryset
    
    @staticmethod
    def get_optimized_products():
        """Get optimized products queryset"""
        from apps.product.models import Product
        
        return Product.objects.select_related(
            'market',
            'market__owner',
            'category',
            'sub_category'
        ).prefetch_related(
            'images',
            'discounts',
            'keywords',
            'comments'
        ).only(
            'id', 'name', 'description', 'price', 'stock', 'status',
            'market__name', 'market__business_id', 'category__name'
        )
    
    @staticmethod
    def get_optimized_markets():
        """Get optimized markets queryset"""
        from apps.market.models import Market
        
        return Market.objects.select_related(
            'owner',
            'sub_category',
            'location',
            'contact'
        ).prefetch_related(
            'products',
            'viewed_by'
        ).only(
            'id', 'name', 'business_id', 'description', 'is_verified',
            'owner__first_name', 'owner__last_name', 'sub_category__name'
        )
    
    @staticmethod
    def get_optimized_orders():
        """Get optimized orders queryset"""
        from apps.cart.models import Order
        
        return Order.objects.select_related(
            'user',
            'market'
        ).prefetch_related(
            'items',
            'items__product',
            'items__affiliate'
        ).only(
            'id', 'description', 'status', 'is_paid', 'created_at',
            'user__first_name', 'user__last_name', 'market__name'
        )
    
    @staticmethod
    def get_optimized_user_products(user_id):
        """Get optimized user products with statistics"""
        from apps.product.models import Product
        from apps.cart.models import OrderItem
        
        return Product.objects.filter(
            market__owner_id=user_id
        ).select_related(
            'market', 'category', 'sub_category'
        ).prefetch_related(
            'images', 'discounts'
        ).annotate(
            total_sold=Sum(
                'orderitem__quantity',
                filter=Q(orderitem__order__is_paid=True)
            ),
            total_revenue=Sum(
                F('orderitem__quantity') * F('price'),
                filter=Q(orderitem__order__is_paid=True)
            ),
            order_count=Count(
                'orderitem__order',
                filter=Q(orderitem__order__is_paid=True),
                distinct=True
            )
        ).only(
            'id', 'name', 'price', 'stock', 'status', 'created_at',
            'market__name', 'category__name'
        )
    
    @staticmethod
    def get_optimized_market_analytics(market_id):
        """Get optimized market analytics"""
        from apps.product.models import Product
        from apps.cart.models import OrderItem
        from apps.market.models import Market
        
        return Market.objects.filter(
            id=market_id
        ).select_related(
            'owner', 'sub_category'
        ).prefetch_related(
            'products'
        ).annotate(
            total_products=Count('products'),
            published_products=Count('products', filter=Q(products__status='published')),
            total_sales=Sum(
                'products__orderitem__quantity',
                filter=Q(products__orderitem__order__is_paid=True)
            ),
            total_revenue=Sum(
                F('products__orderitem__quantity') * F('products__price'),
                filter=Q('products__orderitem__order__is_paid=True')
            ),
            average_product_price=Avg('products__price'),
            low_stock_products=Count('products', filter=Q(products__stock__lte=10))
        ).only(
            'id', 'name', 'business_id', 'description', 'is_verified',
            'owner__first_name', 'owner__last_name'
        )

class DatabaseMaintenance:
    """
    Database maintenance utilities
    """
    
    @staticmethod
    def cleanup_old_data():
        """Clean up old data to improve performance"""
        from apps.users.models import User
        from apps.cart.models import Order
        from apps.payment.models import Payment
        from apps.wallet.models import Transaction
        from django.utils import timezone
        from datetime import timedelta
        
        # Clean up old inactive users (older than 1 year)
        old_users = User.objects.filter(
            is_active=False,
            last_login__lt=timezone.now() - timedelta(days=365)
        )
        deleted_users = old_users.count()
        old_users.delete()
        logger.info(f"Cleaned up {deleted_users} old inactive users")
        
        # Clean up old cancelled orders (older than 6 months)
        old_orders = Order.objects.filter(
            status='cancelled',
            created_at__lt=timezone.now() - timedelta(days=180)
        )
        deleted_orders = old_orders.count()
        old_orders.delete()
        logger.info(f"Cleaned up {deleted_orders} old cancelled orders")
        
        # Clean up old failed payments (older than 3 months)
        old_payments = Payment.objects.filter(
            status='failed',
            created_at__lt=timezone.now() - timedelta(days=90)
        )
        deleted_payments = old_payments.count()
        old_payments.delete()
        logger.info(f"Cleaned up {deleted_payments} old failed payments")
        
        # Clean up old transactions (older than 2 years)
        old_transactions = Transaction.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=730)
        )
        deleted_transactions = old_transactions.count()
        old_transactions.delete()
        logger.info(f"Cleaned up {deleted_transactions} old transactions")
    
    @staticmethod
    def update_table_statistics():
        """Update table statistics for query planner"""
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE;")
            logger.info("Table statistics updated")
    
    @staticmethod
    def check_database_health():
        """Check database health and performance"""
        with connection.cursor() as cursor:
            # Check database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """)
            db_size = cursor.fetchone()[0]
            logger.info(f"Database size: {db_size}")
            
            # Check table sizes
            cursor.execute("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """)
            
            table_sizes = cursor.fetchall()
            logger.info("Largest tables:")
            for table, size in table_sizes:
                logger.info(f"  {table}: {size}")
            
            # Check index usage
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                ORDER BY tablename, indexname;
            """)
            
            unused_indexes = cursor.fetchall()
            if unused_indexes:
                logger.warning("Unused indexes found:")
                for index in unused_indexes:
                    logger.warning(f"  {index[1]}.{index[2]}")
            else:
                logger.info("All indexes are being used")

# Management command for database optimization
class Command(BaseCommand):
    help = 'Optimize database performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create optimized indexes',
        )
        parser.add_argument(
            '--analyze-performance',
            action='store_true',
            help='Analyze query performance',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old data',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM and ANALYZE',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Check database health',
        )
    
    def handle(self, *args, **options):
        optimizer = DatabaseOptimizer()
        
        if options['create_indexes']:
            self.stdout.write('Creating optimized indexes...')
            optimizer.create_optimized_indexes()
            self.stdout.write(self.style.SUCCESS('Indexes created successfully'))
        
        if options['analyze_performance']:
            self.stdout.write('Analyzing query performance...')
            optimizer.analyze_query_performance()
            self.stdout.write(self.style.SUCCESS('Performance analysis completed'))
        
        if options['cleanup']:
            self.stdout.write('Cleaning up old data...')
            DatabaseMaintenance.cleanup_old_data()
            self.stdout.write(self.style.SUCCESS('Data cleanup completed'))
        
        if options['vacuum']:
            self.stdout.write('Running VACUUM and ANALYZE...')
            optimizer.vacuum_and_analyze()
            self.stdout.write(self.style.SUCCESS('VACUUM and ANALYZE completed'))
        
        if options['health_check']:
            self.stdout.write('Checking database health...')
            DatabaseMaintenance.check_database_health()
            self.stdout.write(self.style.SUCCESS('Health check completed'))

