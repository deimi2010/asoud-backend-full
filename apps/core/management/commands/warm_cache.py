from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.core.caching import cache_manager
from apps.product.models import Product
from apps.market.models import Market
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Warm up cache with frequently accessed data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            action='store_true',
            help='Warm user data cache',
        )
        parser.add_argument(
            '--products',
            action='store_true',
            help='Warm product data cache',
        )
        parser.add_argument(
            '--markets',
            action='store_true',
            help='Warm market data cache',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Warm all caches',
        )

    def handle(self, *args, **options):
        """Handle cache warming command"""
        self.stdout.write(self.style.SUCCESS('🔥 Starting cache warming...'))
        
        if options['all'] or options['users']:
            self.warm_user_cache()
        
        if options['all'] or options['products']:
            self.warm_product_cache()
        
        if options['all'] or options['markets']:
            self.warm_market_cache()
        
        self.stdout.write(self.style.SUCCESS('✅ Cache warming completed!'))

    def warm_user_cache(self):
        """Warm user data cache"""
        self.stdout.write('👥 Warming user cache...')
        
        try:
            # Warm active users
            active_users = User.objects.filter(is_active=True)[:100]
            for user in active_users:
                cache_manager.warm_user_data(user.id)
            
            self.stdout.write(f'✅ Warmed cache for {len(active_users)} users')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error warming user cache: {e}'))

    def warm_product_cache(self):
        """Warm product data cache"""
        self.stdout.write('📦 Warming product cache...')
        
        try:
            # Warm popular products
            popular_products = Product.objects.filter(
                status='published'
            ).order_by('-view_count')[:50]
            
            for product in popular_products:
                cache_key = f"product:detail:{product.id}"
                cache_manager.set(cache_key, product, 3600)  # 1 hour
            
            self.stdout.write(f'✅ Warmed cache for {len(popular_products)} products')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error warming product cache: {e}'))

    def warm_market_cache(self):
        """Warm market data cache"""
        self.stdout.write('🏪 Warming market cache...')
        
        try:
            # Warm active markets
            active_markets = Market.objects.filter(
                is_active=True
            ).select_related('user', 'sub_category')[:50]
            
            for market in active_markets:
                cache_key = f"market:detail:{market.id}"
                cache_manager.set(cache_key, market, 3600)  # 1 hour
            
            self.stdout.write(f'✅ Warmed cache for {len(active_markets)} markets')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error warming market cache: {e}'))

