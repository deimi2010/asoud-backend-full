import uuid
from django.core.management.base import BaseCommand
from apps.region.models import Country, Province, City
from apps.category.models import Group, Category, SubCategory
from apps.users.models import User
from django.contrib.auth import get_user_model
import random

class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Starting to seed sample data...')
        
        # Create sample users
        self.create_sample_users()
        
        # Create more regions
        self.create_more_regions()
        
        # Create more categories and subcategories
        self.create_more_categories()
        
        # Create sample stores (if Store model exists)
        self.create_sample_stores()
        
        # Create sample products (if Product model exists)
        self.create_sample_products()

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded sample data!')
        )

    def create_sample_users(self):
        """Create sample users"""
        self.stdout.write('Creating sample users...')
        
        sample_users = [
            {'mobile_number': '09123456789', 'first_name': 'علی', 'last_name': 'احمدی'},
            {'mobile_number': '09123456790', 'first_name': 'فاطمه', 'last_name': 'محمدی'},
            {'mobile_number': '09123456791', 'first_name': 'حسن', 'last_name': 'کریمی'},
            {'mobile_number': '09123456792', 'first_name': 'زهرا', 'last_name': 'نوری'},
            {'mobile_number': '09123456793', 'first_name': 'محمد', 'last_name': 'رضایی'},
            {'mobile_number': '09123456794', 'first_name': 'مریم', 'last_name': 'حسینی'},
            {'mobile_number': '09123456795', 'first_name': 'امیر', 'last_name': 'جعفری'},
            {'mobile_number': '09123456796', 'first_name': 'سارا', 'last_name': 'موسوی'},
            {'mobile_number': '09123456797', 'first_name': 'رضا', 'last_name': 'صادقی'},
            {'mobile_number': '09123456798', 'first_name': 'نرگس', 'last_name': 'کاظمی'},
        ]
        
        for user_data in sample_users:
            user, created = User.objects.get_or_create(
                mobile_number=user_data['mobile_number'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': True,
                }
            )
            self.stdout.write(f'  {user_data["first_name"]} {user_data["last_name"]}: {"created" if created else "exists"}')

    def create_more_regions(self):
        """Create more regions"""
        self.stdout.write('Creating more regions...')
        
        # More provinces
        more_provinces = [
            {'name': 'کرمان', 'country': Country.objects.first()},
            {'name': 'یزد', 'country': Country.objects.first()},
            {'name': 'اردبیل', 'country': Country.objects.first()},
            {'name': 'زنجان', 'country': Country.objects.first()},
            {'name': 'قزوین', 'country': Country.objects.first()},
        ]
        
        for prov_data in more_provinces:
            province, created = Province.objects.get_or_create(
                name=prov_data['name'],
                country=prov_data['country']
            )
            self.stdout.write(f'  {prov_data["name"]}: {"created" if created else "exists"}')
            
            # Create cities for each province
            cities = [
                f'{prov_data["name"]} شهر',
                f'{prov_data["name"]} مرکز',
                f'{prov_data["name"]} جدید',
            ]
            
            for city_name in cities:
                city, created = City.objects.get_or_create(
                    name=city_name,
                    province=province
                )
                self.stdout.write(f'    {city_name}: {"created" if created else "exists"}')

    def create_more_categories(self):
        """Create more categories and subcategories"""
        self.stdout.write('Creating more categories...')
        
        # Get existing groups
        food_group = Group.objects.get(title='غذا و رستوران')
        clothing_group = Group.objects.get(title='پوشاک و مد')
        electronics_group = Group.objects.get(title='الکترونیک و دیجیتال')
        
        # More categories
        more_categories = [
            {'title': 'کباب و جوجه', 'group': food_group, 'market_fee': 4.500},
            {'title': 'پیتزا و برگر', 'group': food_group, 'market_fee': 4.200},
            {'title': 'شیرینی و کیک', 'group': food_group, 'market_fee': 3.800},
            {'title': 'نوشیدنی', 'group': food_group, 'market_fee': 2.500},
            {'title': 'کفش مردانه', 'group': clothing_group, 'market_fee': 3.500},
            {'title': 'کفش زنانه', 'group': clothing_group, 'market_fee': 4.000},
            {'title': 'اکسسوری مردانه', 'group': clothing_group, 'market_fee': 2.800},
            {'title': 'اکسسوری زنانه', 'group': clothing_group, 'market_fee': 3.200},
            {'title': 'لپ تاپ', 'group': electronics_group, 'market_fee': 1.500},
            {'title': 'کامپیوتر', 'group': electronics_group, 'market_fee': 1.800},
        ]
        
        for cat_data in more_categories:
            category, created = Category.objects.get_or_create(
                title=cat_data['title'],
                group=cat_data['group'],
                defaults={
                    'market_fee': cat_data['market_fee']
                }
            )
            self.stdout.write(f'  {cat_data["title"]}: {"created" if created else "exists"}')
            
            # Create subcategories for each category
            subcategories = [
                {'title': f'{cat_data["title"]} برند A', 'market_fee': cat_data['market_fee'] + 0.5},
                {'title': f'{cat_data["title"]} برند B', 'market_fee': cat_data['market_fee'] + 0.3},
                {'title': f'{cat_data["title"]} ارزان', 'market_fee': cat_data['market_fee'] - 0.5},
            ]
            
            for subcat_data in subcategories:
                subcategory, created = SubCategory.objects.get_or_create(
                    title=subcat_data['title'],
                    category=category,
                    defaults={
                        'market_fee': subcat_data['market_fee']
                    }
                )
                self.stdout.write(f'    {subcat_data["title"]}: {"created" if created else "exists"}')

    def create_sample_stores(self):
        """Create sample stores if Store model exists"""
        try:
            from apps.store.models import Store
            self.stdout.write('Creating sample stores...')
            
            # Get some users and categories
            users = User.objects.all()[:5]
            categories = Category.objects.all()[:10]
            cities = City.objects.all()[:5]
            
            store_names = [
                'رستوران سنتی', 'فست فود مدرن', 'کافه کتاب', 'فروشگاه پوشاک',
                'فروشگاه موبایل', 'سوپرمارکت', 'فروشگاه کفش', 'فروشگاه اکسسوری'
            ]
            
            for i, name in enumerate(store_names):
                store, created = Store.objects.get_or_create(
                    name=name,
                    defaults={
                        'owner': users[i % len(users)],
                        'category': categories[i % len(categories)],
                        'city': cities[i % len(cities)],
                        'address': f'آدرس نمونه {i+1}',
                        'phone': f'0912345678{i}',
                        'description': f'توضیحات نمونه برای {name}',
                        'is_active': True,
                    }
                )
                self.stdout.write(f'  {name}: {"created" if created else "exists"}')
                
        except ImportError:
            self.stdout.write('  Store model not found, skipping...')

    def create_sample_products(self):
        """Create sample products if Product model exists"""
        try:
            from apps.product.models import Product
            self.stdout.write('Creating sample products...')
            
            # Get some stores and subcategories
            stores = Store.objects.all()[:5] if 'Store' in locals() else []
            subcategories = SubCategory.objects.all()[:20]
            
            product_names = [
                'برگر ویژه', 'پیتزا مارگاریتا', 'کباب کوبیده', 'جوجه کباب',
                'تی‌شرت پنبه‌ای', 'شلوار جین', 'کفش ورزشی', 'ساعت مچی',
                'گوشی هوشمند', 'تبلت', 'لپ تاپ', 'کامپیوتر',
                'کیک شکلاتی', 'شیرینی سنتی', 'نوشیدنی سرد', 'چای'
            ]
            
            for i, name in enumerate(product_names):
                if stores and subcategories:
                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'store': stores[i % len(stores)],
                            'subcategory': subcategories[i % len(subcategories)],
                            'price': random.randint(10000, 500000),
                            'description': f'توضیحات محصول {name}',
                            'is_active': True,
                            'stock': random.randint(0, 100),
                        }
                    )
                    self.stdout.write(f'  {name}: {"created" if created else "exists"}')
                else:
                    self.stdout.write('  No stores or subcategories available, skipping products...')
                    break
                    
        except ImportError:
            self.stdout.write('  Product model not found, skipping...')
